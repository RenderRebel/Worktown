from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from main import app

client = TestClient(app)

@patch("api.routes.users.db")
def test_update_profile_image_direct_success(mock_db):
    """
    Verify that updating profile image URL succeeds when user exists
    and URL starts with https://res.cloudinary.com/
    """
    uid = "test_user_123"
    profile_image_url = "https://res.cloudinary.com/demo/image/upload/sample.jpg"
    
    # Mock user_ref.get() to return a doc that exists
    mock_doc = MagicMock()
    mock_doc.exists = True
    # The second get() call after update gets the updated data
    mock_updated_doc = MagicMock()
    mock_updated_doc.to_dict.return_value = {
        "uid": uid,
        "name": "Test User",
        "profile_image_url": profile_image_url
    }
    
    mock_ref = MagicMock()
    mock_ref.get.side_effect = [mock_doc, mock_updated_doc]
    mock_db.collection.return_value.document.return_value = mock_ref
    
    response = client.patch(
        f"/users/{uid}/profile-image",
        json={"profile_image_url": profile_image_url}
    )
    
    assert response.status_code == 200
    assert response.json() == {
        "uid": uid,
        "name": "Test User",
        "profile_image_url": profile_image_url
    }
    
    # Assert database interactions
    mock_db.collection.assert_called_with("users")
    mock_db.collection.return_value.document.assert_called_with(uid)
    mock_ref.update.assert_called_once_with({"profile_image_url": profile_image_url})


@patch("api.routes.users.db")
def test_update_profile_image_direct_user_not_found(mock_db):
    """
    Verify that updating profile image returns 404 if the user does not exist in Firestore.
    """
    uid = "non_existent_user"
    profile_image_url = "https://res.cloudinary.com/demo/image/upload/sample.jpg"
    
    mock_doc = MagicMock()
    mock_doc.exists = False
    
    mock_ref = MagicMock()
    mock_ref.get.return_value = mock_doc
    mock_db.collection.return_value.document.return_value = mock_ref
    
    response = client.patch(
        f"/users/{uid}/profile-image",
        json={"profile_image_url": profile_image_url}
    )
    
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"
    mock_ref.update.assert_not_called()


@patch("api.routes.users.db")
def test_update_profile_image_direct_invalid_url(mock_db):
    """
    Verify that updating profile image returns 400 if the URL does not start with https://res.cloudinary.com/
    """
    uid = "test_user_123"
    invalid_url = "https://example.com/bad_image.jpg"
    
    mock_doc = MagicMock()
    mock_doc.exists = True
    
    mock_ref = MagicMock()
    mock_ref.get.return_value = mock_doc
    mock_db.collection.return_value.document.return_value = mock_ref
    
    response = client.patch(
        f"/users/{uid}/profile-image",
        json={"profile_image_url": invalid_url}
    )
    
    assert response.status_code == 400
    assert "Profile image URL must start with https://res.cloudinary.com/" in response.json()["detail"]
    mock_ref.update.assert_not_called()
