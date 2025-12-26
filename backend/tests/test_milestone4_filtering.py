"""
Integration tests for Milestone 4: Filtering functionality.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models import Transaction
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def test_transactions(test_db: Session):
    """Create test transactions with various attributes for filtering."""
    base_date = date(2025, 1, 1)
    
    transactions = [
        Transaction(
            transaction_hash="hash1",
            date=base_date,
            account="Current Account",
            description="Grocery Shopping",
            debit_credit="D",
            amount=Decimal("100.00"),
            balance=Decimal("1000.00"),
            merchant="Carrefour",
            amount_signed=Decimal("-100.00"),
            category="Groceries",
            week_start=base_date,
            month="2025-01",
            year=2025
        ),
        Transaction(
            transaction_hash="hash2",
            date=base_date + timedelta(days=1),
            account="Current Account",
            description="Restaurant",
            debit_credit="D",
            amount=Decimal("50.00"),
            balance=Decimal("950.00"),
            merchant="Paul Cafe",
            amount_signed=Decimal("-50.00"),
            category="Food & Dining",
            week_start=base_date,
            month="2025-01",
            year=2025
        ),
        Transaction(
            transaction_hash="hash3",
            date=base_date + timedelta(days=7),
            account="Savings Account",
            description="Salary",
            debit_credit="C",
            amount=Decimal("5000.00"),
            balance=Decimal("6000.00"),
            merchant="Employer",
            amount_signed=Decimal("5000.00"),
            category="Salary",
            week_start=base_date + timedelta(days=7),
            month="2025-01",
            year=2025
        ),
        Transaction(
            transaction_hash="hash4",
            date=base_date + timedelta(days=8),
            account="Current Account",
            description="Amazon Purchase",
            debit_credit="D",
            amount=Decimal("75.00"),
            balance=Decimal("875.00"),
            merchant="Amazon.com",
            amount_signed=Decimal("-75.00"),
            category="Shopping",
            week_start=base_date + timedelta(days=7),
            month="2025-01",
            year=2025
        ),
        Transaction(
            transaction_hash="hash5",
            date=base_date + timedelta(days=9),
            account="Current Account",
            description="Amazon Prime",
            debit_credit="D",
            amount=Decimal("20.00"),
            balance=Decimal("855.00"),
            merchant="Amazon Prime",
            amount_signed=Decimal("-20.00"),
            category="Subscriptions",
            week_start=base_date + timedelta(days=7),
            month="2025-01",
            year=2025
        ),
    ]
    
    for txn in transactions:
        test_db.add(txn)
    test_db.commit()
    
    return transactions


def test_get_transactions_no_filters(test_transactions):
    """Test getting all transactions without filters."""
    client = TestClient(app)
    response = client.get("/api/transactions")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["transactions"]) == 5


def test_filter_by_date_range(test_transactions):
    """Test filtering by date range."""
    client = TestClient(app)
    base_date = date(2025, 1, 1)
    
    # Filter for first week only
    response = client.get(
        "/api/transactions",
        params={
            "start_date": base_date.isoformat(),
            "end_date": (base_date + timedelta(days=6)).isoformat()
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2  # Only first 2 transactions


def test_filter_by_category(test_transactions):
    """Test filtering by category."""
    client = TestClient(app)
    
    response = client.get(
        "/api/transactions",
        params={"categories": ["Groceries", "Food & Dining"]}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    categories = [t["category"] for t in data["transactions"]]
    assert set(categories) == {"Groceries", "Food & Dining"}


def test_filter_by_account(test_transactions):
    """Test filtering by account."""
    client = TestClient(app)
    
    response = client.get(
        "/api/transactions",
        params={"accounts": ["Savings Account"]}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["transactions"][0]["account"] == "Savings Account"


def test_filter_by_merchant_substring(test_transactions):
    """Test filtering by merchant substring."""
    client = TestClient(app)
    
    # Search for "amazon" (case-insensitive)
    response = client.get(
        "/api/transactions",
        params={"merchant": "amazon"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2  # Amazon.com and Amazon Prime
    merchants = [t["merchant"] for t in data["transactions"]]
    assert all("amazon" in m.lower() for m in merchants)


def test_combined_filters(test_transactions):
    """Test combining multiple filters."""
    client = TestClient(app)
    base_date = date(2025, 1, 1)
    
    # Filter by date range, category, and account
    response = client.get(
        "/api/transactions",
        params={
            "start_date": base_date.isoformat(),
            "end_date": (base_date + timedelta(days=10)).isoformat(),
            "categories": ["Shopping", "Subscriptions"],
            "accounts": ["Current Account"]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2  # Amazon purchases


def test_pagination_with_filters(test_transactions):
    """Test pagination works with filters."""
    client = TestClient(app)
    
    # Get first page with page_size=2
    response = client.get(
        "/api/transactions",
        params={"page": 1, "page_size": 2, "categories": ["Groceries", "Food & Dining", "Shopping"]}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["transactions"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2


def test_get_filter_options(test_transactions):
    """Test getting available filter options."""
    client = TestClient(app)
    
    response = client.get("/api/filters/options")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "categories" in data
    assert "accounts" in data
    assert "min_date" in data
    assert "max_date" in data
    
    assert len(data["categories"]) == 5  # Unique categories
    assert len(data["accounts"]) == 2  # Current and Savings
    assert data["min_date"] == "2025-01-01"
    assert data["max_date"] == "2025-01-10"


def test_empty_results_with_filters(test_transactions):
    """Test that filters returning no results work correctly."""
    client = TestClient(app)
    
    response = client.get(
        "/api/transactions",
        params={"categories": ["NonExistentCategory"]}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["transactions"]) == 0

