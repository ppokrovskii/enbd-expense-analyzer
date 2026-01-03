"""
Tests for Milestone 3: Transaction Context Injection

Validates that:
- Add context with valid filters works
- Context returns summary stats
- Transaction count capped at 1000
- Get context for session works
- Remove context works
- Estimate tokens before adding works
- Context isolated per session
- Cannot add context to other user's session
"""
import pytest
from fastapi.testclient import TestClient
from datetime import date, datetime
from decimal import Decimal
from app.main import app
from app.models import Transaction


client = TestClient(app)


def create_test_transactions(test_db, user_id, count=10):
    """Helper to create test transactions."""
    transactions = []
    for i in range(count):
        transaction = Transaction(
            user_id=user_id,
            date=date(2025, 12, i % 28 + 1),
            account='Current Account',
            description=f'Test transaction {i}',
            details=f'Details {i}',
            debit_credit='D' if i % 3 != 0 else 'C',
            amount=Decimal('100.00'),
            amount_signed=Decimal('-100.00') if i % 3 != 0 else Decimal('100.00'),
            merchant=f'Merchant {i % 5}',
            category='Shopping' if i % 2 == 0 else 'Food',
            transaction_hash=f'hash_{user_id}_{i}',
            created_at=datetime.utcnow()
        )
        transactions.append(transaction)
        test_db.add(transaction)
    test_db.commit()
    return transactions


def test_add_context_to_session(test_db):
    """Test adding transaction context to a chat session."""
    # Create session
    session_response = client.post(
        "/api/chat/sessions",
        json={"title": "Test Chat"},
        headers={"X-User-Id": "test_user"}
    )
    session_id = session_response.json()['id']
    
    # Create some transactions
    create_test_transactions(test_db, "test_user", 20)
    
    # Add context
    response = client.post(
        f"/api/chat/sessions/{session_id}/context",
        json={
            "date_range": {
                "from": "2025-12-01",
                "to": "2025-12-31"
            }
        },
        headers={"X-User-Id": "test_user"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data['transaction_count'] == 20
    assert data['limited'] == False
    assert 'context_id' in data
    assert 'summary' in data
    assert data['summary']['total_expenses'] > 0


def test_context_returns_summary_stats(test_db):
    """Test that context includes summary statistics."""
    # Create session
    session_response = client.post(
        "/api/chat/sessions",
        json={"title": "Test Chat"},
        headers={"X-User-Id": "test_user"}
    )
    session_id = session_response.json()['id']
    
    # Create transactions with income and expenses
    create_test_transactions(test_db, "test_user", 30)
    
    # Add context
    response = client.post(
        f"/api/chat/sessions/{session_id}/context",
        json={
            "date_range": {
                "from": "2025-12-01",
                "to": "2025-12-31"
            }
        },
        headers={"X-User-Id": "test_user"}
    )
    
    data = response.json()
    summary = data['summary']
    
    assert 'total_income' in summary
    assert 'total_expenses' in summary
    assert 'net' in summary
    assert 'top_categories' in summary
    assert len(summary['top_categories']) > 0
    assert summary['total_income'] > 0
    assert summary['total_expenses'] > 0


def test_transaction_count_capped_at_1000(test_db):
    """Test that transaction count is capped at 1000."""
    # Create session
    session_response = client.post(
        "/api/chat/sessions",
        json={"title": "Test Chat"},
        headers={"X-User-Id": "test_user"}
    )
    session_id = session_response.json()['id']
    
    # Create 1500 transactions
    create_test_transactions(test_db, "test_user", 1500)
    
    # Add context
    response = client.post(
        f"/api/chat/sessions/{session_id}/context",
        json={
            "date_range": {
                "from": "2025-12-01",
                "to": "2025-12-31"
            }
        },
        headers={"X-User-Id": "test_user"}
    )
    
    data = response.json()
    assert data['transaction_count'] == 1000  # Capped
    assert data['limited'] == True  # Flag set


def test_get_context_for_session(test_db):
    """Test retrieving context for a session."""
    # Create session
    session_response = client.post(
        "/api/chat/sessions",
        json={"title": "Test Chat"},
        headers={"X-User-Id": "test_user"}
    )
    session_id = session_response.json()['id']
    
    # Create transactions
    create_test_transactions(test_db, "test_user", 10)
    
    # Add context
    client.post(
        f"/api/chat/sessions/{session_id}/context",
        json={
            "date_range": {
                "from": "2025-12-01",
                "to": "2025-12-31"
            },
            "categories": ["Shopping"]
        },
        headers={"X-User-Id": "test_user"}
    )
    
    # Get context
    response = client.get(
        f"/api/chat/sessions/{session_id}/context",
        headers={"X-User-Id": "test_user"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data is not None
    assert 'transaction_filters' in data
    assert 'transaction_count' in data
    assert 'summary' in data
    assert data['transaction_filters']['categories'] == ["Shopping"]


def test_remove_context(test_db):
    """Test removing context from a session."""
    # Create session
    session_response = client.post(
        "/api/chat/sessions",
        json={"title": "Test Chat"},
        headers={"X-User-Id": "test_user"}
    )
    session_id = session_response.json()['id']
    
    # Create transactions and add context
    create_test_transactions(test_db, "test_user", 10)
    client.post(
        f"/api/chat/sessions/{session_id}/context",
        json={
            "date_range": {
                "from": "2025-12-01",
                "to": "2025-12-31"
            }
        },
        headers={"X-User-Id": "test_user"}
    )
    
    # Remove context
    response = client.delete(
        f"/api/chat/sessions/{session_id}/context",
        headers={"X-User-Id": "test_user"}
    )
    
    assert response.status_code == 204
    
    # Verify context is gone
    get_response = client.get(
        f"/api/chat/sessions/{session_id}/context",
        headers={"X-User-Id": "test_user"}
    )
    data = get_response.json()
    assert data['transaction_count'] is None
    assert data['transaction_filters'] is None


def test_estimate_context_before_adding(test_db):
    """Test estimating context size before adding it."""
    # Create transactions
    create_test_transactions(test_db, "test_user", 100)
    
    # Estimate context
    response = client.post(
        "/api/chat/sessions/context/estimate",
        json={
            "date_range": {
                "from": "2025-12-01",
                "to": "2025-12-31"
            }
        },
        headers={"X-User-Id": "test_user"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert 'estimated_transactions' in data
    assert 'actual_transactions' in data
    assert 'estimated_tokens' in data
    assert 'estimated_cost_usd' in data
    assert 'limited' in data
    assert data['estimated_transactions'] == 100
    assert data['actual_transactions'] == 100
    assert data['limited'] == False


def test_estimate_shows_limit_warning(test_db):
    """Test that estimate shows warning when over 1000 transactions."""
    # Create 1200 transactions
    create_test_transactions(test_db, "test_user", 1200)
    
    # Estimate context
    response = client.post(
        "/api/chat/sessions/context/estimate",
        json={
            "date_range": {
                "from": "2025-12-01",
                "to": "2025-12-31"
            }
        },
        headers={"X-User-Id": "test_user"}
    )
    
    data = response.json()
    assert data['estimated_transactions'] == 1200
    assert data['actual_transactions'] == 1000  # Capped
    assert data['limited'] == True


def test_context_isolated_per_session(test_db):
    """Test that context is isolated per session."""
    # Create two sessions
    session1_response = client.post(
        "/api/chat/sessions",
        json={"title": "Chat 1"},
        headers={"X-User-Id": "test_user"}
    )
    session1_id = session1_response.json()['id']
    
    session2_response = client.post(
        "/api/chat/sessions",
        json={"title": "Chat 2"},
        headers={"X-User-Id": "test_user"}
    )
    session2_id = session2_response.json()['id']
    
    # Create transactions
    create_test_transactions(test_db, "test_user", 20)
    
    # Add context to session 1 only
    client.post(
        f"/api/chat/sessions/{session1_id}/context",
        json={
            "date_range": {
                "from": "2025-12-01",
                "to": "2025-12-31"
            }
        },
        headers={"X-User-Id": "test_user"}
    )
    
    # Session 1 should have context
    response1 = client.get(
        f"/api/chat/sessions/{session1_id}/context",
        headers={"X-User-Id": "test_user"}
    )
    data1 = response1.json()
    assert data1['transaction_count'] is not None
    assert data1['transaction_count'] > 0
    
    # Session 2 should not have context
    response2 = client.get(
        f"/api/chat/sessions/{session2_id}/context",
        headers={"X-User-Id": "test_user"}
    )
    data2 = response2.json()
    assert data2['transaction_count'] is None


def test_cannot_add_context_to_other_users_session(test_db):
    """Test that users cannot add context to other users' sessions."""
    # User 1 creates session
    session_response = client.post(
        "/api/chat/sessions",
        json={"title": "User 1 Chat"},
        headers={"X-User-Id": "user1"}
    )
    session_id = session_response.json()['id']
    
    # Create transactions for user 2
    create_test_transactions(test_db, "user2", 10)
    
    # User 2 tries to add context to user 1's session
    response = client.post(
        f"/api/chat/sessions/{session_id}/context",
        json={
            "date_range": {
                "from": "2025-12-01",
                "to": "2025-12-31"
            }
        },
        headers={"X-User-Id": "user2"}
    )
    
    assert response.status_code == 404


def test_context_filters_by_category(test_db):
    """Test that context respects category filters."""
    # Create session
    session_response = client.post(
        "/api/chat/sessions",
        json={"title": "Test Chat"},
        headers={"X-User-Id": "test_user"}
    )
    session_id = session_response.json()['id']
    
    # Create transactions
    create_test_transactions(test_db, "test_user", 30)
    
    # Add context with category filter
    response = client.post(
        f"/api/chat/sessions/{session_id}/context",
        json={
            "date_range": {
                "from": "2025-12-01",
                "to": "2025-12-31"
            },
            "categories": ["Shopping"]
        },
        headers={"X-User-Id": "test_user"}
    )
    
    data = response.json()
    # Should have filtered down to only Shopping category
    assert data['transaction_count'] < 30
    assert data['transaction_count'] > 0


def test_update_existing_context(test_db):
    """Test that adding context again updates the existing context."""
    # Create session
    session_response = client.post(
        "/api/chat/sessions",
        json={"title": "Test Chat"},
        headers={"X-User-Id": "test_user"}
    )
    session_id = session_response.json()['id']
    
    # Create transactions
    create_test_transactions(test_db, "test_user", 20)
    
    # Add context first time
    response1 = client.post(
        f"/api/chat/sessions/{session_id}/context",
        json={
            "date_range": {
                "from": "2025-12-01",
                "to": "2025-12-15"
            }
        },
        headers={"X-User-Id": "test_user"}
    )
    first_count = response1.json()['transaction_count']
    
    # Add context second time with different filters
    response2 = client.post(
        f"/api/chat/sessions/{session_id}/context",
        json={
            "date_range": {
                "from": "2025-12-01",
                "to": "2025-12-31"
            }
        },
        headers={"X-User-Id": "test_user"}
    )
    second_count = response2.json()['transaction_count']
    
    # Should be updated, not duplicated
    assert second_count >= first_count
    
    # Verify only one context exists
    get_response = client.get(
        f"/api/chat/sessions/{session_id}/context",
        headers={"X-User-Id": "test_user"}
    )
    assert get_response.json() is not None

