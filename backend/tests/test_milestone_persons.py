"""Tests for Milestone 2: Multi-Person Management."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.domains.persons.models import Person
from app.domains.persons.service import PersonService


client = TestClient(app)


def test_create_first_person(test_db: Session):
    """Test creating the first person for a user - should be auto-activated."""
    response = client.post(
        "/api/persons/",
        json={"name": "John Doe"},
        headers={"X-User-Id": "test_user"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "John Doe"
    assert data["is_active"] == True  # First person is auto-active
    assert data["user_id"] == "test_user"


def test_create_second_person(test_db: Session):
    """Test creating a second person - should NOT be auto-activated."""
    # Create first person
    client.post(
        "/api/persons/",
        json={"name": "John Doe"},
        headers={"X-User-Id": "test_user"}
    )
    
    # Create second person
    response = client.post(
        "/api/persons/",
        json={"name": "Jane Doe"},
        headers={"X-User-Id": "test_user"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Jane Doe"
    assert data["is_active"] == False  # Second person is NOT auto-active


def test_list_persons(test_db: Session):
    """Test listing all persons for a user."""
    # Create multiple persons
    client.post("/api/persons/", json={"name": "John"}, headers={"X-User-Id": "test_user"})
    client.post("/api/persons/", json={"name": "Jane"}, headers={"X-User-Id": "test_user"})
    client.post("/api/persons/", json={"name": "Alice"}, headers={"X-User-Id": "test_user"})
    
    response = client.get("/api/persons/", headers={"X-User-Id": "test_user"})
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    names = [p["name"] for p in data]
    assert "John" in names
    assert "Jane" in names
    assert "Alice" in names


def test_get_active_person(test_db: Session):
    """Test getting the currently active person."""
    # Create a person
    client.post("/api/persons/", json={"name": "John"}, headers={"X-User-Id": "test_user"})
    
    response = client.get("/api/persons/active", headers={"X-User-Id": "test_user"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "John"
    assert data["is_active"] == True


def test_get_active_person_auto_creates_default(test_db: Session):
    """Test that getting active person auto-creates default if none exists."""
    response = client.get("/api/persons/active", headers={"X-User-Id": "new_user"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Default"
    assert data["is_active"] == True


def test_activate_person(test_db: Session):
    """Test switching active person."""
    # Create two persons
    response1 = client.post("/api/persons/", json={"name": "John"}, headers={"X-User-Id": "test_user"})
    response2 = client.post("/api/persons/", json={"name": "Jane"}, headers={"X-User-Id": "test_user"})
    
    john_id = response1.json()["id"]
    jane_id = response2.json()["id"]
    
    # John should be active initially
    assert response1.json()["is_active"] == True
    
    # Activate Jane
    response = client.put(f"/api/persons/{jane_id}/activate", headers={"X-User-Id": "test_user"})
    
    assert response.status_code == 200
    assert response.json()["is_active"] == True
    
    # Verify John is now inactive
    john_response = client.get(f"/api/persons/{john_id}", headers={"X-User-Id": "test_user"})
    assert john_response.json()["is_active"] == False
    
    # Verify Jane is now active
    jane_response = client.get(f"/api/persons/{jane_id}", headers={"X-User-Id": "test_user"})
    assert jane_response.json()["is_active"] == True


def test_update_person_name(test_db: Session):
    """Test updating a person's name."""
    response = client.post("/api/persons/", json={"name": "John"}, headers={"X-User-Id": "test_user"})
    person_id = response.json()["id"]
    
    update_response = client.put(
        f"/api/persons/{person_id}",
        json={"name": "John Doe"},
        headers={"X-User-Id": "test_user"}
    )
    
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "John Doe"


def test_delete_person(test_db: Session):
    """Test deleting a person."""
    response = client.post("/api/persons/", json={"name": "ToDelete"}, headers={"X-User-Id": "test_user"})
    person_id = response.json()["id"]
    
    delete_response = client.delete(f"/api/persons/{person_id}", headers={"X-User-Id": "test_user"})
    
    assert delete_response.status_code == 204
    
    # Verify deleted
    get_response = client.get(f"/api/persons/{person_id}", headers={"X-User-Id": "test_user"})
    assert get_response.status_code == 404


def test_delete_active_person_activates_another(test_db: Session):
    """Test that deleting the active person activates another if available."""
    # Create two persons
    response1 = client.post("/api/persons/", json={"name": "John"}, headers={"X-User-Id": "test_user"})
    response2 = client.post("/api/persons/", json={"name": "Jane"}, headers={"X-User-Id": "test_user"})
    
    john_id = response1.json()["id"]
    jane_id = response2.json()["id"]
    
    # John is active
    assert response1.json()["is_active"] == True
    
    # Delete John
    client.delete(f"/api/persons/{john_id}", headers={"X-User-Id": "test_user"})
    
    # Jane should now be active
    jane_response = client.get(f"/api/persons/{jane_id}", headers={"X-User-Id": "test_user"})
    assert jane_response.json()["is_active"] == True


def test_user_isolation(test_db: Session):
    """Test that persons are isolated between users."""
    # User 1 creates a person
    client.post("/api/persons/", json={"name": "User1 Person"}, headers={"X-User-Id": "user1"})
    
    # User 2 creates a person
    client.post("/api/persons/", json={"name": "User2 Person"}, headers={"X-User-Id": "user2"})
    
    # User 1 should only see their person
    user1_persons = client.get("/api/persons/", headers={"X-User-Id": "user1"})
    assert len(user1_persons.json()) == 1
    assert user1_persons.json()[0]["name"] == "User1 Person"
    
    # User 2 should only see their person
    user2_persons = client.get("/api/persons/", headers={"X-User-Id": "user2"})
    assert len(user2_persons.json()) == 1
    assert user2_persons.json()[0]["name"] == "User2 Person"


def test_get_nonexistent_person(test_db: Session):
    """Test getting a person that doesn't exist returns 404."""
    response = client.get("/api/persons/99999", headers={"X-User-Id": "test_user"})
    assert response.status_code == 404


def test_update_nonexistent_person(test_db: Session):
    """Test updating a person that doesn't exist returns 404."""
    response = client.put(
        "/api/persons/99999",
        json={"name": "New Name"},
        headers={"X-User-Id": "test_user"}
    )
    assert response.status_code == 404


def test_activate_nonexistent_person(test_db: Session):
    """Test activating a person that doesn't exist returns 404."""
    response = client.put("/api/persons/99999/activate", headers={"X-User-Id": "test_user"})
    assert response.status_code == 404


def test_delete_nonexistent_person(test_db: Session):
    """Test deleting a person that doesn't exist returns 404."""
    response = client.delete("/api/persons/99999", headers={"X-User-Id": "test_user"})
    assert response.status_code == 404


def test_cannot_access_other_users_person(test_db: Session):
    """Test that a user cannot access another user's person."""
    # User 1 creates a person
    response = client.post("/api/persons/", json={"name": "User1 Person"}, headers={"X-User-Id": "user1"})
    person_id = response.json()["id"]
    
    # User 2 tries to access it
    get_response = client.get(f"/api/persons/{person_id}", headers={"X-User-Id": "user2"})
    assert get_response.status_code == 404
    
    # User 2 tries to update it
    update_response = client.put(
        f"/api/persons/{person_id}",
        json={"name": "Hacked"},
        headers={"X-User-Id": "user2"}
    )
    assert update_response.status_code == 404
    
    # User 2 tries to delete it
    delete_response = client.delete(f"/api/persons/{person_id}", headers={"X-User-Id": "user2"})
    assert delete_response.status_code == 404

