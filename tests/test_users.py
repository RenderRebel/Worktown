from fastapi.testclient import TestClient
from main import app
from core.security import get_current_user

client = TestClient(app)

# 1. Create a mock user to simulate a logged-in user
def override_get_current_user():
    return {"uid": "test_user_123", "email": "testworker@example.com"}

# 2. Override the dependency in the app
app.dependency_overrides[get_current_user] = override_get_current_user

def test_read_root():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["server_status"] == "running"

def test_get_users():
    # Because we overrode get_current_user, this will act as if we are authenticated
    with TestClient(app) as client:
        response = client.get("/users/")
        assert response.status_code == 200, response.text
        assert isinstance(response.json(), list)
