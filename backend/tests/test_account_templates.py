"""Tests for account template simplification (TDD)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.database import get_db, engine, Base
from app.models import UserAccount
from app.services.account_service import AccountService

client = TestClient(app)


@pytest.fixture(scope="function")
def test_db():
    """Create a test database session for each test."""
    Base.metadata.create_all(bind=engine)
    
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    # Clean up before test
    try:
        session.query(UserAccount).filter(UserAccount.user_id.like('%test%')).delete()
        session.commit()
    except Exception as e:
        print(f"Pre-cleanup error: {e}")
        session.rollback()
    
    def override_get_db():
        try:
            yield session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield session
    
    # Cleanup after test
    try:
        session.rollback()
        session.query(UserAccount).filter(UserAccount.user_id.like('%test%')).delete()
        session.commit()
    except Exception as e:
        print(f"Post-cleanup error: {e}")
        session.rollback()
    finally:
        session.close()
    
    app.dependency_overrides.clear()


def test_create_account_with_value_and_name_only(test_db):
    """Account should accept value='123456' name='current-account'."""
    response = client.post("/api/accounts/", json={
        "name": "current-account",
        "value": "1234567890"
    }, headers={"X-User-Id": "test_user"})
    
    assert response.status_code == 201
    data = response.json()
    assert data["account_name"] == "current-account"
    assert data["account_number"] == "1234567890"


def test_account_name_replaces_spaces_with_dashes(test_db):
    """'current account' -> 'current-account'."""
    response = client.post("/api/accounts/", json={
        "name": "current account",  # With space
        "value": "9876543210"
    }, headers={"X-User-Id": "test_user"})
    
    assert response.status_code == 201
    data = response.json()
    assert data["account_name"] == "current-account"  # Converted to dash


def test_account_name_lowercase_conversion(test_db):
    """Account names should be converted to lowercase."""
    response = client.post("/api/accounts/", json={
        "name": "Savings Account",  # Mixed case with space
        "value": "1111222233"
    }, headers={"X-User-Id": "test_user"})
    
    assert response.status_code == 201
    data = response.json()
    assert data["account_name"] == "savings-account"  # Lowercase with dash


def test_account_variables_use_name_as_key(test_db):
    """{current-account} -> '123456'."""
    # Create account
    account = UserAccount(
        user_id="test_user",
        account_name="current-account",
        account_number="1234567890",
        bank="ENBD"
    )
    test_db.add(account)
    test_db.commit()
    
    # Get account variables
    account_service = AccountService()
    variables = account_service.get_account_variables(test_db, "test_user")
    
    assert "{current-account}" in variables
    assert variables["{current-account}"] == "1234567890"


def test_account_masked_variable(test_db):
    """{current-account-masked} should work for masked values."""
    # User creates two separate accounts
    account1 = UserAccount(
        user_id="test_user",
        account_name="current-account",
        account_number="1234567890",
        bank="ENBD"
    )
    account2 = UserAccount(
        user_id="test_user",
        account_name="current-account-masked",
        account_number="****7890",
        bank="ENBD"
    )
    test_db.add_all([account1, account2])
    test_db.commit()
    
    # Get account variables
    account_service = AccountService()
    variables = account_service.get_account_variables(test_db, "test_user")
    
    assert "{current-account}" in variables
    assert variables["{current-account}"] == "1234567890"
    assert "{current-account-masked}" in variables
    assert variables["{current-account-masked}"] == "****7890"


def test_multiple_accounts_with_different_names(test_db):
    """Multiple accounts should all be available as variables."""
    accounts_data = [
        {"name": "checking", "value": "1111111111"},
        {"name": "savings", "value": "2222222222"},
        {"name": "credit card", "value": "3333333333"},
    ]
    
    for acc_data in accounts_data:
        response = client.post("/api/accounts/", json=acc_data, headers={"X-User-Id": "test_user"})
        assert response.status_code == 201
    
    # Get variables
    account_service = AccountService()
    variables = account_service.get_account_variables(test_db, "test_user")
    
    assert "{checking}" in variables
    assert "{savings}" in variables
    assert "{credit-card}" in variables  # Space converted to dash
    assert variables["{checking}"] == "1111111111"
    assert variables["{savings}"] == "2222222222"
    assert variables["{credit-card}"] == "3333333333"


def test_account_duplicate_name_prevented(test_db):
    """Duplicate account names should be prevented."""
    # Create first account
    response1 = client.post("/api/accounts/", json={
        "name": "current-account",
        "value": "1111111111"
    }, headers={"X-User-Id": "test_user"})
    assert response1.status_code == 201
    
    # Try to create duplicate
    response2 = client.post("/api/accounts/", json={
        "name": "current-account",
        "value": "2222222222"
    }, headers={"X-User-Id": "test_user"})
    assert response2.status_code in [400, 409]  # Conflict error
