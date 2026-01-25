"""
Integration tests for Daily Chart endpoint - Daily Spending Heatmap.

Tests:
- Daily aggregation returns correct totals
- Excludes Salary, Incoming Transfer, Transfer Between My Accounts
- Date range filtering works
- Workspace isolation works
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.domains.transactions.models import Transaction
from app.domains.workspaces.models import Workspace
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def test_daily_transactions(test_db: Session):
    """Create test transactions for daily spending heatmap."""
    # Create transactions spread across multiple days
    # Use 'default_user' to match the default X-User-Id header
    default_user = 'default_user'
    base_date = date(2026, 1, 20)  # Monday
    
    transactions = [
        # Day 1 (Monday) - Multiple expenses
        Transaction(
            transaction_hash="d1",
            user_id=default_user,
            date=base_date,
            account="Current",
            description="Groceries",
            debit_credit="D",
            amount=Decimal("200.00"),
            merchant="Carrefour",
            amount_signed=Decimal("-200.00"),
            category="Groceries",
            week_start=base_date,
            month="2026-01",
            year=2026
        ),
        Transaction(
            transaction_hash="d2",
            user_id=default_user,
            date=base_date,
            account="Current",
            description="Coffee",
            debit_credit="D",
            amount=Decimal("50.00"),
            merchant="Starbucks",
            amount_signed=Decimal("-50.00"),
            category="Food & Dining",
            week_start=base_date,
            month="2026-01",
            year=2026
        ),
        # Day 2 (Tuesday) - Expense
        Transaction(
            transaction_hash="d3",
            user_id=default_user,
            date=base_date + timedelta(days=1),
            account="Current",
            description="Restaurant",
            debit_credit="D",
            amount=Decimal("150.00"),
            merchant="Restaurant",
            amount_signed=Decimal("-150.00"),
            category="Food & Dining",
            week_start=base_date,
            month="2026-01",
            year=2026
        ),
        # Day 3 (Wednesday) - Salary (should be EXCLUDED)
        Transaction(
            transaction_hash="d4",
            user_id=default_user,
            date=base_date + timedelta(days=2),
            account="Current",
            description="Monthly Salary",
            debit_credit="C",
            amount=Decimal("10000.00"),
            merchant="Employer",
            amount_signed=Decimal("10000.00"),
            category="Salary",
            week_start=base_date,
            month="2026-01",
            year=2026
        ),
        # Day 3 (Wednesday) - Expense on same day as salary
        Transaction(
            transaction_hash="d5",
            user_id=default_user,
            date=base_date + timedelta(days=2),
            account="Current",
            description="Shopping",
            debit_credit="D",
            amount=Decimal("300.00"),
            merchant="Amazon",
            amount_signed=Decimal("-300.00"),
            category="Shopping",
            week_start=base_date,
            month="2026-01",
            year=2026
        ),
        # Day 4 (Thursday) - Incoming Transfer (should be EXCLUDED)
        Transaction(
            transaction_hash="d6",
            user_id=default_user,
            date=base_date + timedelta(days=3),
            account="Current",
            description="Transfer from friend",
            debit_credit="C",
            amount=Decimal("500.00"),
            merchant="John",
            amount_signed=Decimal("500.00"),
            category="Incoming Transfer",
            week_start=base_date,
            month="2026-01",
            year=2026
        ),
        # Day 5 (Friday) - Transfer Between Accounts (should be EXCLUDED)
        Transaction(
            transaction_hash="d7",
            user_id=default_user,
            date=base_date + timedelta(days=4),
            account="Current",
            description="Transfer to savings",
            debit_credit="D",
            amount=Decimal("1000.00"),
            merchant="Savings Account",
            amount_signed=Decimal("-1000.00"),
            category="Transfer Between My Accounts",
            week_start=base_date,
            month="2026-01",
            year=2026
        ),
        # Day 5 (Friday) - Real expense
        Transaction(
            transaction_hash="d8",
            user_id=default_user,
            date=base_date + timedelta(days=4),
            account="Current",
            description="Fuel",
            debit_credit="D",
            amount=Decimal("100.00"),
            merchant="ENOC",
            amount_signed=Decimal("-100.00"),
            category="Transport",
            week_start=base_date,
            month="2026-01",
            year=2026
        ),
        # Day 7 (Sunday) - No expense (gap in data)
        # Day 8 (Next Monday) - Expense
        Transaction(
            transaction_hash="d9",
            user_id=default_user,
            date=base_date + timedelta(days=7),
            account="Current",
            description="Utilities",
            debit_credit="D",
            amount=Decimal("400.00"),
            merchant="DEWA",
            amount_signed=Decimal("-400.00"),
            category="Utilities",
            week_start=base_date + timedelta(days=7),
            month="2026-01",
            year=2026
        ),
    ]
    
    for txn in transactions:
        test_db.add(txn)
    test_db.commit()
    
    return transactions


def test_daily_chart_returns_correct_structure(test_daily_transactions):
    """Test that daily chart returns correct response structure."""
    client = TestClient(app)
    response = client.get("/api/chart/daily")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "data" in data
    assert "total" in data
    assert isinstance(data["data"], list)
    assert isinstance(data["total"], (int, float))


def test_daily_chart_aggregates_by_day(test_daily_transactions):
    """Test that daily chart aggregates multiple transactions per day."""
    client = TestClient(app)
    response = client.get(
        "/api/chart/daily",
        params={
            "start_date": "2026-01-20",
            "end_date": "2026-01-20"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have 1 day with aggregated amount (200 + 50 = 250)
    assert len(data["data"]) == 1
    assert data["data"][0]["date"] == "2026-01-20"
    assert data["data"][0]["amount"] == 250.0
    assert data["total"] == 250.0


def test_daily_chart_excludes_salary(test_daily_transactions):
    """Test that Salary transactions are excluded."""
    client = TestClient(app)
    response = client.get(
        "/api/chart/daily",
        params={
            "start_date": "2026-01-22",  # Wednesday (has Salary + Shopping)
            "end_date": "2026-01-22"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should only include the Shopping expense (300), not Salary (10000)
    assert len(data["data"]) == 1
    assert data["data"][0]["amount"] == 300.0


def test_daily_chart_excludes_incoming_transfer(test_daily_transactions):
    """Test that Incoming Transfer transactions are excluded."""
    client = TestClient(app)
    response = client.get(
        "/api/chart/daily",
        params={
            "start_date": "2026-01-23",  # Thursday (only has Incoming Transfer)
            "end_date": "2026-01-23"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have no data (Incoming Transfer is excluded)
    assert len(data["data"]) == 0
    assert data["total"] == 0.0


def test_daily_chart_excludes_internal_transfers(test_daily_transactions):
    """Test that Transfer Between My Accounts is excluded."""
    client = TestClient(app)
    response = client.get(
        "/api/chart/daily",
        params={
            "start_date": "2026-01-24",  # Friday (has Transfer + Fuel)
            "end_date": "2026-01-24"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should only include Fuel (100), not the Transfer (1000)
    assert len(data["data"]) == 1
    assert data["data"][0]["amount"] == 100.0


def test_daily_chart_date_range_filtering(test_daily_transactions):
    """Test date range filtering works correctly."""
    client = TestClient(app)
    
    # Get full week
    response = client.get(
        "/api/chart/daily",
        params={
            "start_date": "2026-01-20",
            "end_date": "2026-01-26"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have 4 days with expenses (Mon, Tue, Wed, Fri)
    # Mon: 250, Tue: 150, Wed: 300, Fri: 100
    assert len(data["data"]) == 4
    assert data["total"] == 800.0
    
    # Verify dates are in order
    dates = [item["date"] for item in data["data"]]
    assert dates == sorted(dates)


def test_daily_chart_total_calculation(test_daily_transactions):
    """Test that total is correctly calculated across all days."""
    client = TestClient(app)
    response = client.get(
        "/api/chart/daily",
        params={
            "start_date": "2026-01-20",
            "end_date": "2026-01-27"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify total matches sum of all amounts
    calculated_total = sum(item["amount"] for item in data["data"])
    assert abs(data["total"] - calculated_total) < 0.01


def test_daily_chart_empty_result(test_db: Session):
    """Test daily chart with no transactions."""
    client = TestClient(app)
    
    response = client.get(
        "/api/chart/daily",
        params={
            "start_date": "2099-01-01",
            "end_date": "2099-01-31"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["data"]) == 0
    assert data["total"] == 0.0


def test_daily_chart_workspace_isolation(test_db: Session):
    """Test that daily chart respects workspace isolation."""
    test_user_id = "workspace_test_user"
    
    # Create two workspaces
    workspace1 = Workspace(name="Workspace 1", user_id=test_user_id)
    workspace2 = Workspace(name="Workspace 2", user_id=test_user_id)
    test_db.add(workspace1)
    test_db.add(workspace2)
    test_db.commit()
    test_db.refresh(workspace1)
    test_db.refresh(workspace2)
    
    # Create transactions in different workspaces
    txn1 = Transaction(
        transaction_hash="w1",
        user_id=test_user_id,
        workspace_id=workspace1.id,
        date=date(2026, 1, 20),
        account="Current",
        description="Workspace 1 expense",
        debit_credit="D",
        amount=Decimal("100.00"),
        merchant="Store 1",
        amount_signed=Decimal("-100.00"),
        category="Shopping",
        week_start=date(2026, 1, 20),
        month="2026-01",
        year=2026
    )
    txn2 = Transaction(
        transaction_hash="w2",
        user_id=test_user_id,
        workspace_id=workspace2.id,
        date=date(2026, 1, 20),
        account="Current",
        description="Workspace 2 expense",
        debit_credit="D",
        amount=Decimal("500.00"),
        merchant="Store 2",
        amount_signed=Decimal("-500.00"),
        category="Shopping",
        week_start=date(2026, 1, 20),
        month="2026-01",
        year=2026
    )
    test_db.add(txn1)
    test_db.add(txn2)
    test_db.commit()
    
    client = TestClient(app)
    
    # Query with workspace1 - must pass X-User-Id header too
    response = client.get(
        "/api/chart/daily",
        params={
            "start_date": "2026-01-20",
            "end_date": "2026-01-20"
        },
        headers={"X-User-Id": test_user_id, "X-Workspace-Id": str(workspace1.id)}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should only see workspace1's transaction (100)
    assert len(data["data"]) == 1
    assert data["data"][0]["amount"] == 100.0
    
    # Query with workspace2
    response = client.get(
        "/api/chart/daily",
        params={
            "start_date": "2026-01-20",
            "end_date": "2026-01-20"
        },
        headers={"X-User-Id": test_user_id, "X-Workspace-Id": str(workspace2.id)}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should only see workspace2's transaction (500)
    assert len(data["data"]) == 1
    assert data["data"][0]["amount"] == 500.0
