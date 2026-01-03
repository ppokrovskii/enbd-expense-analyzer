"""Integration tests for Milestone 1: Account Management.

Updated for new API format:
- 'name' instead of 'account_name'
- 'value' instead of 'account_number'
- 'bank' remains the same
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.database import get_db, engine, Base
from app.services.account_service import AccountService

client = TestClient(app)


@pytest.fixture(scope="function")
def test_db():
    """Create a test database session that uses the actual database."""
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Create a new session
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    # Override dependency
    def override_get_db():
        try:
            yield session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield session
    
    # Cleanup: delete all test data
    from app.models import UserAccount
    try:
        # Rollback any pending transactions first
        session.rollback()
        session.query(UserAccount).filter(UserAccount.user_id.like('%test%')).delete()
        session.query(UserAccount).filter(UserAccount.user_id.like('%user%')).delete()
        session.commit()
    except Exception as e:
        print(f"Cleanup error: {e}")
        session.rollback()
    finally:
        session.close()
    
    # Clear overrides
    app.dependency_overrides.clear()


def test_create_account(test_db):
    """Test creating a user account."""
    response = client.post("/api/accounts/", json={
        "name": "current account",  # Will be normalized to 'current-account'
        "value": "1234",
        "bank": "ENBD"
    }, headers={"X-User-Id": "test_user"})
    
    assert response.status_code == 201
    data = response.json()
    assert data["account_name"] == "current-account"
    assert data["account_number"] == "1234"
    assert data["bank"] == "ENBD"
    assert "id" in data


def test_list_accounts(test_db):
    """Test listing user accounts."""
    # Create multiple accounts
    client.post("/api/accounts/", json={
        "name": "current",
        "value": "1234",
        "bank": "ENBD"
    }, headers={"X-User-Id": "test_user"})
    
    client.post("/api/accounts/", json={
        "name": "savings",
        "value": "5678",
        "bank": "ENBD"
    }, headers={"X-User-Id": "test_user"})
    
    response = client.get("/api/accounts/", headers={"X-User-Id": "test_user"})
    assert response.status_code == 200
    accounts = response.json()
    assert len(accounts) == 2
    
    account_names = [a["account_name"] for a in accounts]
    assert "current" in account_names
    assert "savings" in account_names


def test_account_variables(test_db):
    """Test getting account variables for rule substitution."""
    from app.models import UserAccount
    
    # Create accounts directly in DB
    acc1 = UserAccount(
        user_id='test_user',
        account_name='current_account',
        account_number='1234',
        bank='ENBD'
    )
    acc2 = UserAccount(
        user_id='test_user',
        account_name='savings_account',
        account_number='5678',
        bank='ENBD'
    )
    test_db.add(acc1)
    test_db.add(acc2)
    test_db.commit()
    
    variables = AccountService.get_account_variables(test_db, "test_user")
    
    # Check individual account variables
    assert "{current_account}" in variables
    assert variables["{current_account}"] == "1234"
    
    assert "{savings_account}" in variables
    assert variables["{savings_account}"] == "5678"
    
    # Check generic own_account variable
    assert "{own_account}" in variables
    own_account_value = variables["{own_account}"]
    assert "1234" in own_account_value
    assert "5678" in own_account_value
    assert "|" in own_account_value  # Should be pipe-separated


def test_duplicate_account_name(test_db):
    """Test that duplicate account names are rejected."""
    # Create first account
    response1 = client.post("/api/accounts/", json={
        "name": "current",
        "value": "1234",
        "bank": "ENBD"
    }, headers={"X-User-Id": "test_user"})
    assert response1.status_code == 201
    
    # Try to create duplicate
    response2 = client.post("/api/accounts/", json={
        "name": "current",
        "value": "9999",
        "bank": "ENBD"
    }, headers={"X-User-Id": "test_user"})
    
    assert response2.status_code == 409  # Conflict
    assert "already exists" in response2.json()["detail"].lower()


def test_delete_account(test_db):
    """Test deleting an account."""
    # Create account
    create_response = client.post("/api/accounts/", json={
        "name": "temp",
        "value": "9999",
        "bank": "ENBD"
    }, headers={"X-User-Id": "test_user"})
    
    assert create_response.status_code == 201
    account_id = create_response.json()["id"]
    
    # Delete account
    delete_response = client.delete(f"/api/accounts/{account_id}", headers={"X-User-Id": "test_user"})
    assert delete_response.status_code == 204
    
    # Verify deleted - list should not contain this account
    list_response = client.get("/api/accounts/", headers={"X-User-Id": "test_user"})
    accounts = list_response.json()
    assert not any(a["id"] == account_id for a in accounts)


def test_delete_nonexistent_account(test_db):
    """Test deleting a non-existent account returns 404."""
    response = client.delete("/api/accounts/99999", headers={"X-User-Id": "test_user"})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_user_isolation(test_db):
    """Test that users can only see their own accounts."""
    # User 1 creates account
    client.post("/api/accounts/", json={
        "name": "user1 account",
        "value": "1111",
        "bank": "ENBD"
    }, headers={"X-User-Id": "user1"})
    
    # User 2 creates account
    client.post("/api/accounts/", json={
        "name": "user2 account",
        "value": "2222",
        "bank": "ENBD"
    }, headers={"X-User-Id": "user2"})
    
    # User 1 should only see their account
    response1 = client.get("/api/accounts/", headers={"X-User-Id": "user1"})
    accounts1 = response1.json()
    assert len(accounts1) == 1
    assert accounts1[0]["account_name"] == "user1-account"
    
    # User 2 should only see their account
    response2 = client.get("/api/accounts/", headers={"X-User-Id": "user2"})
    accounts2 = response2.json()
    assert len(accounts2) == 1
    assert accounts2[0]["account_name"] == "user2-account"
