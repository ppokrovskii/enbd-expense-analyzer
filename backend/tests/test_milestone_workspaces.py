"""Tests for Milestone 2: Multi-Workspace Management."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.domains.workspaces.models import Workspace
from app.domains.workspaces.service import WorkspaceService


client = TestClient(app)


def test_create_first_workspace(test_db: Session):
    """Test creating the first workspace for a user - should be auto-activated."""
    response = client.post(
        "/api/workspaces/",
        json={"name": "John Doe"},
        headers={"X-User-Id": "test_user"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "John Doe"
    assert data["is_active"] == True  # First workspace is auto-active
    assert data["user_id"] == "test_user"


def test_create_second_workspace(test_db: Session):
    """Test creating a second workspace - should NOT be auto-activated."""
    # Create first workspace
    client.post(
        "/api/workspaces/",
        json={"name": "John Doe"},
        headers={"X-User-Id": "test_user"}
    )
    
    # Create second workspace
    response = client.post(
        "/api/workspaces/",
        json={"name": "Jane Doe"},
        headers={"X-User-Id": "test_user"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Jane Doe"
    assert data["is_active"] == False  # Second workspace is NOT auto-active


def test_list_workspaces(test_db: Session):
    """Test listing all workspaces for a user."""
    # Create multiple workspaces
    client.post("/api/workspaces/", json={"name": "John"}, headers={"X-User-Id": "test_user"})
    client.post("/api/workspaces/", json={"name": "Jane"}, headers={"X-User-Id": "test_user"})
    client.post("/api/workspaces/", json={"name": "Alice"}, headers={"X-User-Id": "test_user"})
    
    response = client.get("/api/workspaces/", headers={"X-User-Id": "test_user"})
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    names = [w["name"] for w in data]
    assert "John" in names
    assert "Jane" in names
    assert "Alice" in names


def test_get_active_workspace(test_db: Session):
    """Test getting the currently active workspace."""
    # Create a workspace
    client.post("/api/workspaces/", json={"name": "John"}, headers={"X-User-Id": "test_user"})
    
    response = client.get("/api/workspaces/active", headers={"X-User-Id": "test_user"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "John"
    assert data["is_active"] == True


def test_get_active_workspace_auto_creates_default(test_db: Session):
    """Test that getting active workspace auto-creates default if none exists."""
    response = client.get("/api/workspaces/active", headers={"X-User-Id": "new_user"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Default"
    assert data["is_active"] == True


def test_activate_workspace(test_db: Session):
    """Test switching active workspace."""
    # Create two workspaces
    response1 = client.post("/api/workspaces/", json={"name": "John"}, headers={"X-User-Id": "test_user"})
    response2 = client.post("/api/workspaces/", json={"name": "Jane"}, headers={"X-User-Id": "test_user"})
    
    john_id = response1.json()["id"]
    jane_id = response2.json()["id"]
    
    # John should be active initially
    assert response1.json()["is_active"] == True
    
    # Activate Jane
    response = client.put(f"/api/workspaces/{jane_id}/activate", headers={"X-User-Id": "test_user"})
    
    assert response.status_code == 200
    assert response.json()["is_active"] == True
    
    # Verify John is now inactive
    john_response = client.get(f"/api/workspaces/{john_id}", headers={"X-User-Id": "test_user"})
    assert john_response.json()["is_active"] == False
    
    # Verify Jane is now active
    jane_response = client.get(f"/api/workspaces/{jane_id}", headers={"X-User-Id": "test_user"})
    assert jane_response.json()["is_active"] == True


def test_update_workspace_name(test_db: Session):
    """Test updating a workspace's name."""
    response = client.post("/api/workspaces/", json={"name": "John"}, headers={"X-User-Id": "test_user"})
    workspace_id = response.json()["id"]
    
    update_response = client.put(
        f"/api/workspaces/{workspace_id}",
        json={"name": "John Doe"},
        headers={"X-User-Id": "test_user"}
    )
    
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "John Doe"


def test_delete_workspace(test_db: Session):
    """Test deleting a workspace."""
    response = client.post("/api/workspaces/", json={"name": "ToDelete"}, headers={"X-User-Id": "test_user"})
    workspace_id = response.json()["id"]
    
    delete_response = client.delete(f"/api/workspaces/{workspace_id}", headers={"X-User-Id": "test_user"})
    
    assert delete_response.status_code == 204
    
    # Verify deleted
    get_response = client.get(f"/api/workspaces/{workspace_id}", headers={"X-User-Id": "test_user"})
    assert get_response.status_code == 404


def test_delete_active_workspace_activates_another(test_db: Session):
    """Test that deleting the active workspace activates another if available."""
    # Create two workspaces
    response1 = client.post("/api/workspaces/", json={"name": "John"}, headers={"X-User-Id": "test_user"})
    response2 = client.post("/api/workspaces/", json={"name": "Jane"}, headers={"X-User-Id": "test_user"})
    
    john_id = response1.json()["id"]
    jane_id = response2.json()["id"]
    
    # John is active
    assert response1.json()["is_active"] == True
    
    # Delete John
    client.delete(f"/api/workspaces/{john_id}", headers={"X-User-Id": "test_user"})
    
    # Jane should now be active
    jane_response = client.get(f"/api/workspaces/{jane_id}", headers={"X-User-Id": "test_user"})
    assert jane_response.json()["is_active"] == True


def test_user_isolation(test_db: Session):
    """Test that workspaces are isolated between users."""
    # User 1 creates a workspace
    client.post("/api/workspaces/", json={"name": "User1 Workspace"}, headers={"X-User-Id": "user1"})
    
    # User 2 creates a workspace
    client.post("/api/workspaces/", json={"name": "User2 Workspace"}, headers={"X-User-Id": "user2"})
    
    # User 1 should only see their workspace
    user1_workspaces = client.get("/api/workspaces/", headers={"X-User-Id": "user1"})
    assert len(user1_workspaces.json()) == 1
    assert user1_workspaces.json()[0]["name"] == "User1 Workspace"
    
    # User 2 should only see their workspace
    user2_workspaces = client.get("/api/workspaces/", headers={"X-User-Id": "user2"})
    assert len(user2_workspaces.json()) == 1
    assert user2_workspaces.json()[0]["name"] == "User2 Workspace"


def test_get_nonexistent_workspace(test_db: Session):
    """Test getting a workspace that doesn't exist returns 404."""
    response = client.get("/api/workspaces/99999", headers={"X-User-Id": "test_user"})
    assert response.status_code == 404


def test_update_nonexistent_workspace(test_db: Session):
    """Test updating a workspace that doesn't exist returns 404."""
    response = client.put(
        "/api/workspaces/99999",
        json={"name": "New Name"},
        headers={"X-User-Id": "test_user"}
    )
    assert response.status_code == 404


def test_activate_nonexistent_workspace(test_db: Session):
    """Test activating a workspace that doesn't exist returns 404."""
    response = client.put("/api/workspaces/99999/activate", headers={"X-User-Id": "test_user"})
    assert response.status_code == 404


def test_delete_nonexistent_workspace(test_db: Session):
    """Test deleting a workspace that doesn't exist returns 404."""
    response = client.delete("/api/workspaces/99999", headers={"X-User-Id": "test_user"})
    assert response.status_code == 404


def test_cannot_access_other_users_workspace(test_db: Session):
    """Test that a user cannot access another user's workspace."""
    # User 1 creates a workspace
    response = client.post("/api/workspaces/", json={"name": "User1 Workspace"}, headers={"X-User-Id": "user1"})
    workspace_id = response.json()["id"]
    
    # User 2 tries to access it
    get_response = client.get(f"/api/workspaces/{workspace_id}", headers={"X-User-Id": "user2"})
    assert get_response.status_code == 404
    
    # User 2 tries to update it
    update_response = client.put(
        f"/api/workspaces/{workspace_id}",
        json={"name": "Hacked"},
        headers={"X-User-Id": "user2"}
    )
    assert update_response.status_code == 404
    
    # User 2 tries to delete it
    delete_response = client.delete(f"/api/workspaces/{workspace_id}", headers={"X-User-Id": "user2"})
    assert delete_response.status_code == 404
