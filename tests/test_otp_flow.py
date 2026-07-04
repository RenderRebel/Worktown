from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from main import app
from datetime import datetime, timezone, timedelta
import pytest

client = TestClient(app)

@pytest.fixture
def mock_db():
    with patch("services.otp_service.db") as mock:
        yield mock

@pytest.fixture
def mock_firebase_auth():
    with patch("services.otp_service.firebase_auth") as mock:
        yield mock

@pytest.mark.anyio
async def test_send_otp_success(mock_db):
    # Mock Firestore doc (does not exist, so no rate limit)
    mock_doc = MagicMock()
    mock_doc.exists = False
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

    # Mock httpx response from 2Factor
    mock_response = MagicMock()
    mock_response.json.return_value = {"Status": "Success", "Details": "mock-session-id-123"}
    
    with patch("httpx.AsyncClient.get", return_value=mock_response):
        response = client.post("/otp/send-otp", json={"phone": "919876543210"})
        
        assert response.status_code == 200
        assert response.json() == {"success": True, "message": "OTP sent successfully", "token": None}
        
        # Verify stored in Firestore
        mock_db.collection.assert_any_call("otp_sessions")
        mock_db.collection.return_value.document.assert_any_call("919876543210")
        mock_db.collection.return_value.document.return_value.set.assert_called_once()
        set_data = mock_db.collection.return_value.document.return_value.set.call_args[0][0]
        assert set_data["session_id"] == "mock-session-id-123"
        assert set_data["attempts"] == 0

@pytest.mark.anyio
async def test_send_otp_rate_limit(mock_db):
    # Mock Firestore doc (exists, recently created)
    mock_doc = MagicMock()
    mock_doc.exists = True
    now = datetime.now(timezone.utc)
    mock_doc.to_dict.return_value = {
        "created_at": now - timedelta(seconds=30),
        "locked_until": None
    }
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

    response = client.post("/otp/send-otp", json={"phone": "919876543210"})
    assert response.status_code == 429
    assert "Please wait" in response.json()["detail"]

@pytest.mark.anyio
async def test_verify_otp_success(mock_db, mock_firebase_auth):
    # Mock Firestore session doc
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "session_id": "mock-session-id-123",
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
        "attempts": 0,
        "created_at": datetime.now(timezone.utc) - timedelta(minutes=1),
        "locked_until": None
    }
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

    # Mock user document search
    mock_user_doc = MagicMock()
    mock_user_doc.id = "test_user_uid"
    mock_db.collection.return_value.where.return_value.limit.return_value.get.return_value = [mock_user_doc]

    # Mock 2Factor verify API response
    mock_verify_response = MagicMock()
    mock_verify_response.json.return_value = {"Status": "Success", "Details": "OTP Matched"}
    
    # Mock custom token generation
    mock_firebase_auth.create_custom_token.return_value = b"firebase-custom-token-xyz"

    with patch("httpx.AsyncClient.get", return_value=mock_verify_response):
        response = client.post("/otp/verify-otp", json={"phone": "919876543210", "code": "123456"})
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["token"] == "firebase-custom-token-xyz"
        
        # Verify session deleted
        mock_db.collection.return_value.document.return_value.delete.assert_called_once()
        # Verify user marked phone_verified = True
        mock_user_doc.reference.update.assert_called_once_with({"phone_verified": True})

@pytest.mark.anyio
async def test_verify_otp_failure_and_lockout(mock_db):
    # Mock Firestore session doc with 4 attempts
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "session_id": "mock-session-id-123",
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
        "attempts": 4,
        "created_at": datetime.now(timezone.utc) - timedelta(minutes=1),
        "locked_until": None
    }
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

    # Mock 2Factor verify API response showing failure
    mock_verify_response = MagicMock()
    mock_verify_response.json.return_value = {"Status": "Error", "Details": "OTP Mismatch"}

    with patch("httpx.AsyncClient.get", return_value=mock_verify_response):
        response = client.post("/otp/verify-otp", json={"phone": "919876543210", "code": "111111"})
        
        # 5th attempt should result in lockout (429)
        assert response.status_code == 429
        assert "Too many failed attempts" in response.json()["detail"]
        
        # Verify that locked_until was updated in Firestore
        mock_db.collection.return_value.document.return_value.update.assert_called_once()
        update_args = mock_db.collection.return_value.document.return_value.update.call_args[0][0]
        assert update_args["attempts"] == 5
        assert "locked_until" in update_args
