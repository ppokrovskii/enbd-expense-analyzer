"""
Test for Bug Fix: Chart API returning empty data due to NULL category filtering.

Bug Description:
- Chart API was filtering out transactions where category != 'Transfer Between My Accounts'
- This excluded ALL transactions with NULL category (which was all uncategorized transactions)
- Result: Empty chart even when transactions existed

Expected Behavior:
- Chart should include transactions with NULL categories (as "Other")
- Only exclude transactions where category = 'Transfer Between My Accounts'
- Chart aggregations should match transaction totals

Fix:
- Use CASE expression to treat NULL as 'Other'
- Filter on the CASE expression, not raw category column
"""
import pytest
from decimal import Decimal
from datetime import date
from sqlalchemy.orm import Session
from app.models import Transaction
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def uncategorized_transactions(test_db: Session):
    """Create transactions with NULL categories (uncategorized)."""
    transactions = [
        Transaction(
            transaction_hash="uncategorized_1",
            date=date(2025, 1, 1),
            account="Current",
            description="Grocery",
            debit_credit="D",
            amount=Decimal("100.00"),
            merchant="Store",
            amount_signed=Decimal("-100.00"),
            category=None,  # NULL category
            week_start=date(2024, 12, 30),
            month="2025-01",
            year=2025
        ),
        Transaction(
            transaction_hash="uncategorized_2",
            date=date(2025, 1, 2),
            account="Current",
            description="Restaurant",
            debit_credit="D",
            amount=Decimal("50.00"),
            merchant="Restaurant",
            amount_signed=Decimal("-50.00"),
            category=None,  # NULL category
            week_start=date(2024, 12, 30),
            month="2025-01",
            year=2025
        ),
        Transaction(
            transaction_hash="categorized_1",
            date=date(2025, 1, 3),
            account="Current",
            description="Transfer",
            debit_credit="D",
            amount=Decimal("1000.00"),
            merchant="Transfer",
            amount_signed=Decimal("-1000.00"),
            category="Transfer Between My Accounts",  # Should be excluded
            week_start=date(2024, 12, 30),
            month="2025-01",
            year=2025
        ),
    ]
    
    for txn in transactions:
        test_db.add(txn)
    test_db.commit()
    
    return transactions


def test_chart_includes_null_categories_as_other(uncategorized_transactions):
    """
    BUG FIX TEST: Chart should include NULL categories as 'Other'.
    
    Before fix: Chart returned empty data
    After fix: Chart includes uncategorized transactions as "Other"
    """
    client = TestClient(app)
    response = client.get("/api/chart/weekly")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have data (not empty)
    assert len(data["data"]) > 0, "Chart should return data for uncategorized transactions"
    
    # Should include "Other" category
    assert "Other" in data["categories"], "NULL categories should appear as 'Other'"
    
    # Find the "Other" category data
    other_data = [d for d in data["data"] if d["category"] == "Other"]
    assert len(other_data) > 0, "Should have aggregated data for 'Other' category"
    
    # Verify total (should be sum of uncategorized transactions)
    total = sum(float(d["total"]) for d in other_data)
    assert total == 150.0, f"Expected 150.00 (100+50), got {total}"


def test_chart_excludes_internal_transfers(uncategorized_transactions):
    """
    BUG FIX TEST: Chart should exclude 'Transfer Between My Accounts'.
    
    Ensures internal transfers don't appear in chart aggregations.
    """
    client = TestClient(app)
    response = client.get("/api/chart/weekly")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should NOT include "Transfer Between My Accounts" category
    assert "Transfer Between My Accounts" not in data["categories"], \
        "Internal transfers should be excluded from chart"
    
    # Verify no data for transfers
    transfer_data = [d for d in data["data"] if d["category"] == "Transfer Between My Accounts"]
    assert len(transfer_data) == 0, "No transfer data should appear in chart"


def test_chart_monthly_includes_null_categories(uncategorized_transactions):
    """
    BUG FIX TEST: Monthly chart should also include NULL categories as 'Other'.
    
    Ensures monthly aggregation has same behavior as weekly.
    """
    client = TestClient(app)
    response = client.get("/api/chart/monthly")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have data
    assert len(data["data"]) > 0
    
    # Should include "Other" category
    assert "Other" in data["categories"]
    
    # Verify monthly aggregation
    other_data = [d for d in data["data"] if d["category"] == "Other"]
    total = sum(float(d["total"]) for d in other_data)
    assert total == 150.0


def test_transactions_and_chart_consistency(uncategorized_transactions):
    """
    BUG FIX TEST: Transactions list and chart should show same data.
    
    This is the ROOT CAUSE test - ensures chart and list are consistent.
    """
    client = TestClient(app)
    
    # Get transactions (uncategorized ones have category=None in DB)
    txn_response = client.get("/api/transactions?page_size=100")
    assert txn_response.status_code == 200
    txn_data = txn_response.json()
    
    # Get chart data
    chart_response = client.get("/api/chart/weekly")
    assert chart_response.status_code == 200
    chart_data = chart_response.json()
    
    # Calculate total from transactions (excluding transfers)
    transactions = txn_data["transactions"]
    txn_total = sum(
        abs(float(t["amount_signed"])) 
        for t in transactions 
        if t["category"] != "Transfer Between My Accounts"
    )
    
    # Calculate total from chart
    chart_total = sum(float(d["total"]) for d in chart_data["data"])
    
    # Totals should match (within rounding)
    assert abs(txn_total - chart_total) < 0.01, \
        f"Transaction total ({txn_total}) should match chart total ({chart_total})"


def test_filtering_other_category_works(test_db: Session):
    """
    BUG FIX TEST: Filtering by "Other" should return NULL category transactions.
    
    Ensures user can filter by "Other" and get uncategorized transactions.
    """
    # Create an uncategorized transaction
    txn = Transaction(
        transaction_hash="filter_test",
        date=date(2025, 1, 1),
        account="Current",
        description="Test",
        debit_credit="D",
        amount=Decimal("100.00"),
        merchant="Test",
        amount_signed=Decimal("-100.00"),
        category=None,  # NULL
        week_start=date(2024, 12, 30),
        month="2025-01",
        year=2025
    )
    test_db.add(txn)
    test_db.commit()
    
    client = TestClient(app)
    
    # Filter by "Other" category
    response = client.get("/api/chart/weekly?categories=Other")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return data for "Other" category
    assert len(data["data"]) > 0, "Should return data when filtering by 'Other'"
    assert all(d["category"] == "Other" for d in data["data"])
    
    # Verify it includes our NULL category transaction
    total = sum(float(d["total"]) for d in data["data"])
    assert total >= 100.0, "Should include the uncategorized transaction"


def test_null_category_not_excluded_by_filter(test_db: Session):
    """
    BUG FIX TEST: NULL categories should not be silently excluded.
    
    Before fix: category != 'Transfer' would exclude NULLs
    After fix: CASE expression properly handles NULLs
    """
    # Create mix of categorized and uncategorized
    transactions = [
        Transaction(
            transaction_hash="null_cat",
            date=date(2025, 1, 1),
            account="Current",
            description="Uncategorized",
            debit_credit="D",
            amount=Decimal("100.00"),
            merchant="Store",
            amount_signed=Decimal("-100.00"),
            category=None,
            week_start=date(2024, 12, 30),
            month="2025-01",
            year=2025
        ),
        Transaction(
            transaction_hash="with_cat",
            date=date(2025, 1, 1),
            account="Current",
            description="Categorized",
            debit_credit="D",
            amount=Decimal("50.00"),
            merchant="Store",
            amount_signed=Decimal("-50.00"),
            category="Groceries",
            week_start=date(2024, 12, 30),
            month="2025-01",
            year=2025
        ),
    ]
    
    for txn in transactions:
        test_db.add(txn)
    test_db.commit()
    
    client = TestClient(app)
    response = client.get("/api/chart/weekly")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have 2 categories: "Other" and "Groceries"
    assert len(data["categories"]) == 2
    assert "Other" in data["categories"]
    assert "Groceries" in data["categories"]
    
    # Both should have data
    assert len(data["data"]) == 2

