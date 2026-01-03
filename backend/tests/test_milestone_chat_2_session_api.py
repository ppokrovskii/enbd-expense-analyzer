"""
Tests for Milestone 2: Chat Session Management API

Validates that:
- Create new chat session works
- List sessions for user works
- Get session by ID works
- Delete session works
- Update session title works
- Sessions are isolated per user
- Cannot access other user's sessions
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import ChatSession
from datetime import datetime


client = TestClient(app)


def test_create_chat_session(test_db):
    """Test creating a new chat session."""
    response = client.post(
        "/api/chat/sessions",
        json={"title": "My First Chat"},
        headers={"X-User-Id": "test_user"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data['title'] == "My First Chat"
    assert data['message_count'] == 0
    assert 'id' in data
    assert 'created_at' in data
    assert 'updated_at' in data


def test_create_chat_session_without_title(test_db):
    """Test creating a chat session without providing a title."""
    response = client.post(
        "/api/chat/sessions",
        json={},
        headers={"X-User-Id": "test_user"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "New Chat" in data['title']  # Should have auto-generated title


def test_list_chat_sessions(test_db):
    """Test listing all chat sessions for a user."""
    # Create a few sessions
    client.post(
        "/api/chat/sessions",
        json={"title": "Chat 1"},
        headers={"X-User-Id": "user1"}
    )
    client.post(
        "/api/chat/sessions",
        json={"title": "Chat 2"},
        headers={"X-User-Id": "user1"}
    )
    
    # List sessions
    response = client.get(
        "/api/chat/sessions",
        headers={"X-User-Id": "user1"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]['title'] in ["Chat 1", "Chat 2"]
    assert data[1]['title'] in ["Chat 1", "Chat 2"]


def test_get_chat_session_by_id(test_db):
    """Test getting a specific chat session."""
    # Create session
    create_response = client.post(
        "/api/chat/sessions",
        json={"title": "Test Chat"},
        headers={"X-User-Id": "test_user"}
    )
    session_id = create_response.json()['id']
    
    # Get session
    response = client.get(
        f"/api/chat/sessions/{session_id}",
        headers={"X-User-Id": "test_user"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data['id'] == session_id
    assert data['title'] == "Test Chat"
    assert data['messages'] == []
    assert data['context'] is None


def test_get_nonexistent_session(test_db):
    """Test getting a session that doesn't exist."""
    response = client.get(
        "/api/chat/sessions/00000000-0000-0000-0000-000000000000",
        headers={"X-User-Id": "test_user"}
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()['detail'].lower()


def test_update_session_title(test_db):
    """Test updating a chat session's title."""
    # Create session
    create_response = client.post(
        "/api/chat/sessions",
        json={"title": "Old Title"},
        headers={"X-User-Id": "test_user"}
    )
    session_id = create_response.json()['id']
    
    # Update title
    response = client.put(
        f"/api/chat/sessions/{session_id}",
        json={"title": "New Title"},
        headers={"X-User-Id": "test_user"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data['title'] == "New Title"
    
    # Verify it was updated
    get_response = client.get(
        f"/api/chat/sessions/{session_id}",
        headers={"X-User-Id": "test_user"}
    )
    assert get_response.json()['title'] == "New Title"


def test_delete_session(test_db):
    """Test deleting a chat session."""
    # Create session
    create_response = client.post(
        "/api/chat/sessions",
        json={"title": "To Delete"},
        headers={"X-User-Id": "test_user"}
    )
    session_id = create_response.json()['id']
    
    # Delete session
    response = client.delete(
        f"/api/chat/sessions/{session_id}",
        headers={"X-User-Id": "test_user"}
    )
    
    assert response.status_code == 204
    
    # Verify it's gone
    get_response = client.get(
        f"/api/chat/sessions/{session_id}",
        headers={"X-User-Id": "test_user"}
    )
    assert get_response.status_code == 404


def test_sessions_isolated_per_user(test_db):
    """Test that sessions are properly isolated per user."""
    # User 1 creates a session
    create_response = client.post(
        "/api/chat/sessions",
        json={"title": "User 1 Chat"},
        headers={"X-User-Id": "user1"}
    )
    session_id = create_response.json()['id']
    
    # User 1 can see their session
    response1 = client.get(
        "/api/chat/sessions",
        headers={"X-User-Id": "user1"}
    )
    assert response1.status_code == 200
    assert len(response1.json()) == 1
    assert response1.json()[0]['title'] == "User 1 Chat"
    
    # User 2 cannot see user 1's session
    response2 = client.get(
        "/api/chat/sessions",
        headers={"X-User-Id": "user2"}
    )
    assert response2.status_code == 200
    assert len(response2.json()) == 0
    
    # User 2 cannot access user 1's session directly
    response3 = client.get(
        f"/api/chat/sessions/{session_id}",
        headers={"X-User-Id": "user2"}
    )
    assert response3.status_code == 404


def test_cannot_update_other_users_session(test_db):
    """Test that users cannot update other users' sessions."""
    # User 1 creates a session
    create_response = client.post(
        "/api/chat/sessions",
        json={"title": "User 1 Chat"},
        headers={"X-User-Id": "user1"}
    )
    session_id = create_response.json()['id']
    
    # User 2 tries to update it
    response = client.put(
        f"/api/chat/sessions/{session_id}",
        json={"title": "Hacked Title"},
        headers={"X-User-Id": "user2"}
    )
    
    assert response.status_code == 404
    
    # Verify title wasn't changed
    get_response = client.get(
        f"/api/chat/sessions/{session_id}",
        headers={"X-User-Id": "user1"}
    )
    assert get_response.json()['title'] == "User 1 Chat"


def test_cannot_delete_other_users_session(test_db):
    """Test that users cannot delete other users' sessions."""
    # User 1 creates a session
    create_response = client.post(
        "/api/chat/sessions",
        json={"title": "User 1 Chat"},
        headers={"X-User-Id": "user1"}
    )
    session_id = create_response.json()['id']
    
    # User 2 tries to delete it
    response = client.delete(
        f"/api/chat/sessions/{session_id}",
        headers={"X-User-Id": "user2"}
    )
    
    assert response.status_code == 404
    
    # Verify session still exists for user 1
    get_response = client.get(
        f"/api/chat/sessions/{session_id}",
        headers={"X-User-Id": "user1"}
    )
    assert get_response.status_code == 200


def test_sessions_ordered_by_updated_at(test_db):
    """Test that sessions are ordered by most recently updated."""
    import time
    
    # Create sessions with small delays
    response1 = client.post(
        "/api/chat/sessions",
        json={"title": "First Chat"},
        headers={"X-User-Id": "user1"}
    )
    session1_id = response1.json()['id']
    
    time.sleep(0.1)
    
    response2 = client.post(
        "/api/chat/sessions",
        json={"title": "Second Chat"},
        headers={"X-User-Id": "user1"}
    )
    
    time.sleep(0.1)
    
    # Update first session (should move it to top)
    client.put(
        f"/api/chat/sessions/{session1_id}",
        json={"title": "First Chat Updated"},
        headers={"X-User-Id": "user1"}
    )
    
    # List sessions
    response = client.get(
        "/api/chat/sessions",
        headers={"X-User-Id": "user1"}
    )
    
    sessions = response.json()
    assert len(sessions) == 2
    # First Chat (updated most recently) should be first
    assert sessions[0]['title'] == "First Chat Updated"
    assert sessions[1]['title'] == "Second Chat"

