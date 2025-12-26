"""
Integration tests for Milestone 5: Chart visualization.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models import Transaction
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def test_chart_transactions(test_db: Session):
    """Create test transactions for chart visualization."""
    base_date = date(2025, 1, 1)  # Wednesday
    
    # Week 1 transactions
    transactions = [
        Transaction(
            transaction_hash="c1",
            date=base_date,
            account="Current",
            description="Groceries",
            debit_credit="D",
            amount=Decimal("200.00"),
            merchant="Carrefour",
            amount_signed=Decimal("-200.00"),
            category="Groceries",
            week_start=base_date - timedelta(days=base_date.weekday()),  # Monday
            month="2025-01",
            year=2025
        ),
        Transaction(
            transaction_hash="c2",
            date=base_date + timedelta(days=1),
            account="Current",
            description="Restaurant",
            debit_credit="D",
            amount=Decimal("100.00"),
            merchant="Restaurant",
            amount_signed=Decimal("-100.00"),
            category="Food & Dining",
            week_start=base_date - timedelta(days=base_date.weekday()),
            month="2025-01",
            year=2025
        ),
        # Week 2 transactions
        Transaction(
            transaction_hash="c3",
            date=base_date + timedelta(days=7),
            account="Current",
            description="Salary",
            debit_credit="C",
            amount=Decimal("5000.00"),
            merchant="Employer",
            amount_signed=Decimal("5000.00"),
            category="Salary",
            week_start=base_date + timedelta(days=7) - timedelta(days=(base_date + timedelta(days=7)).weekday()),
            month="2025-01",
            year=2025
        ),
        Transaction(
            transaction_hash="c4",
            date=base_date + timedelta(days=8),
            account="Current",
            description="Shopping",
            debit_credit="D",
            amount=Decimal("150.00"),
            merchant="Amazon",
            amount_signed=Decimal("-150.00"),
            category="Shopping",
            week_start=base_date + timedelta(days=7) - timedelta(days=(base_date + timedelta(days=7)).weekday()),
            month="2025-01",
            year=2025
        ),
        # Next month
        Transaction(
            transaction_hash="c5",
            date=date(2025, 2, 1),
            account="Current",
            description="Utilities",
            debit_credit="D",
            amount=Decimal("300.00"),
            merchant="DEWA",
            amount_signed=Decimal("-300.00"),
            category="Utilities",
            week_start=date(2025, 2, 1) - timedelta(days=date(2025, 2, 1).weekday()),
            month="2025-02",
            year=2025
        ),
    ]
    
    for txn in transactions:
        test_db.add(txn)
    test_db.commit()
    
    return transactions


def test_weekly_chart_no_filters(test_chart_transactions):
    """Test weekly chart with no filters."""
    client = TestClient(app)
    response = client.get("/api/chart/weekly")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "data" in data
    assert "categories" in data
    assert "periods" in data
    assert len(data["data"]) > 0
    assert len(data["categories"]) > 0
    assert len(data["periods"]) >= 2


def test_weekly_chart_with_date_filter(test_chart_transactions):
    """Test weekly chart with date range filter."""
    client = TestClient(app)
    
    # Filter for January only
    response = client.get(
        "/api/chart/weekly",
        params={
            "start_date": "2025-01-01",
            "end_date": "2025-01-31"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should not include February data
    for item in data["data"]:
        # Week might start in late December
        assert item["period"].startswith("2025-01") or item["period"].startswith("2024-12")


def test_weekly_chart_with_category_filter(test_chart_transactions):
    """Test weekly chart with category filter."""
    client = TestClient(app)
    
    response = client.get(
        "/api/chart/weekly",
        params={"categories": ["Groceries", "Food & Dining"]}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should only have selected categories
    categories = {item["category"] for item in data["data"]}
    assert categories.issubset({"Groceries", "Food & Dining"})


def test_monthly_chart_no_filters(test_chart_transactions):
    """Test monthly chart with no filters."""
    client = TestClient(app)
    response = client.get("/api/chart/monthly")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "data" in data
    assert "categories" in data
    assert "periods" in data
    assert len(data["periods"]) >= 2  # At least 2 months


def test_monthly_chart_aggregation(test_chart_transactions):
    """Test that monthly chart aggregates correctly."""
    client = TestClient(app)
    
    response = client.get(
        "/api/chart/monthly",
        params={
            "start_date": "2025-01-01",
            "end_date": "2025-01-31"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have January period
    assert "2025-01" in data["periods"]
    
    # Check that Groceries + Food & Dining total 300 in January
    groceries_total = next((item["total"] for item in data["data"] if item["period"] == "2025-01" and item["category"] == "Groceries"), 0)
    dining_total = next((item["total"] for item in data["data"] if item["period"] == "2025-01" and item["category"] == "Food & Dining"), 0)
    
    assert float(groceries_total) == 200.0
    assert float(dining_total) == 100.0


def test_chart_excludes_internal_transfers(test_chart_transactions, test_db: Session):
    """Test that internal transfers are excluded from charts."""
    # Add an internal transfer
    transfer = Transaction(
        transaction_hash="t1",
        date=date(2025, 1, 5),
        account="Current",
        description="Transfer",
        debit_credit="D",
        amount=Decimal("1000.00"),
        merchant="Transfer",
        amount_signed=Decimal("-1000.00"),
        category="Transfer Between My Accounts",
        week_start=date(2025, 1, 5) - timedelta(days=date(2025, 1, 5).weekday()),
        month="2025-01",
        year=2025
    )
    test_db.add(transfer)
    test_db.commit()
    
    client = TestClient(app)
    response = client.get("/api/chart/weekly")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should not include Transfer Between My Accounts
    assert "Transfer Between My Accounts" not in data["categories"]


def test_chart_empty_result(test_db: Session):
    """Test chart with no data."""
    client = TestClient(app)
    
    response = client.get(
        "/api/chart/weekly",
        params={"categories": ["NonExistent"]}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["data"]) == 0
    assert len(data["categories"]) == 0
    assert len(data["periods"]) == 0

