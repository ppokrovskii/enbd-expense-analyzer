"""
Integration tests for TransactionQueryService migration.

Tests ensure that the service layer provides consistent data across
transactions list, weekly charts, and monthly charts.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models import Transaction
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def mixed_transactions(test_db: Session):
    """Create a realistic mix of transactions for testing."""
    base_date = date(2025, 1, 1)
    
    transactions = [
        # Groceries
        Transaction(
            transaction_hash="grocery_1",
            date=base_date,
            account="Current Account",
            description="Grocery shopping",
            debit_credit="D",
            amount=Decimal("200.00"),
            merchant="Carrefour",
            amount_signed=Decimal("-200.00"),
            category="Groceries",
            week_start=base_date - timedelta(days=base_date.weekday()),
            month="2025-01",
            year=2025
        ),
        # Food & Dining
        Transaction(
            transaction_hash="food_1",
            date=base_date + timedelta(days=1),
            account="Current Account",
            description="Restaurant",
            debit_credit="D",
            amount=Decimal("150.00"),
            merchant="Paul Cafe",
            amount_signed=Decimal("-150.00"),
            category="Food & Dining",
            week_start=base_date - timedelta(days=base_date.weekday()),
            month="2025-01",
            year=2025
        ),
        # Uncategorized (NULL category)
        Transaction(
            transaction_hash="uncategorized_1",
            date=base_date + timedelta(days=2),
            account="Savings Account",
            description="Unknown merchant",
            debit_credit="D",
            amount=Decimal("75.00"),
            merchant="XYZ Store",
            amount_signed=Decimal("-75.00"),
            category=None,  # NULL
            week_start=base_date - timedelta(days=base_date.weekday()),
            month="2025-01",
            year=2025
        ),
        # Internal Transfer (should be excluded)
        Transaction(
            transaction_hash="transfer_1",
            date=base_date + timedelta(days=3),
            account="Current Account",
            description="Transfer to savings",
            debit_credit="D",
            amount=Decimal("1000.00"),
            merchant="Internal",
            amount_signed=Decimal("-1000.00"),
            category="Transfer Between My Accounts",
            week_start=base_date - timedelta(days=base_date.weekday()),
            month="2025-01",
            year=2025
        ),
        # Different week
        Transaction(
            transaction_hash="grocery_2",
            date=base_date + timedelta(days=10),
            account="Current Account",
            description="Weekly shopping",
            debit_credit="D",
            amount=Decimal("180.00"),
            merchant="Choithrams",
            amount_signed=Decimal("-180.00"),
            category="Groceries",
            week_start=base_date + timedelta(days=7) - timedelta(days=(base_date + timedelta(days=7)).weekday()),
            month="2025-01",
            year=2025
        ),
    ]
    
    for txn in transactions:
        test_db.add(txn)
    test_db.commit()
    
    return transactions


def test_service_layer_transactions_and_weekly_chart_consistency(mixed_transactions):
    """
    Integration test: Transactions list and weekly chart must show same data.
    
    This is the critical test that ensures the service layer guarantees consistency.
    """
    client = TestClient(app)
    
    # Get transactions (excluding transfers)
    txn_response = client.get("/api/transactions?page_size=100&exclude_transfers=true")
    assert txn_response.status_code == 200
    txn_data = txn_response.json()
    
    # Get weekly chart (excluding transfers)
    chart_response = client.get("/api/chart/weekly?exclude_transfers=true")
    assert chart_response.status_code == 200
    chart_data = chart_response.json()
    
    # Calculate totals
    txn_total = sum(abs(float(t["amount_signed"])) for t in txn_data["transactions"])
    chart_total = sum(float(d["total"]) for d in chart_data["data"])
    
    # CRITICAL ASSERTION: Totals must match
    assert abs(txn_total - chart_total) < 0.01, \
        f"Transaction total ({txn_total}) must match chart total ({chart_total})"
    
    # Should exclude transfer
    assert txn_data["total"] == 4, "Should have 4 non-transfer transactions"


def test_service_layer_transactions_and_monthly_chart_consistency(mixed_transactions):
    """Integration test: Transactions and monthly chart consistency."""
    client = TestClient(app)
    
    txn_response = client.get("/api/transactions?page_size=100&exclude_transfers=true")
    chart_response = client.get("/api/chart/monthly?exclude_transfers=true")
    
    assert txn_response.status_code == 200
    assert chart_response.status_code == 200
    
    txn_data = txn_response.json()
    chart_data = chart_response.json()
    
    txn_total = sum(abs(float(t["amount_signed"])) for t in txn_data["transactions"])
    chart_total = sum(float(d["total"]) for d in chart_data["data"])
    
    assert abs(txn_total - chart_total) < 0.01


def test_service_layer_category_filter_consistency(mixed_transactions):
    """
    Integration test: Same category filter produces same data in list and chart.
    """
    client = TestClient(app)
    
    # Filter by "Groceries" category
    txn_response = client.get("/api/transactions?categories=Groceries&page_size=100")
    chart_response = client.get("/api/chart/weekly?categories=Groceries")
    
    assert txn_response.status_code == 200
    assert chart_response.status_code == 200
    
    txn_data = txn_response.json()
    chart_data = chart_response.json()
    
    # Should only have Groceries category
    assert all(t["category"] == "Groceries" for t in txn_data["transactions"])
    assert chart_data["categories"] == ["Groceries"]
    
    # Totals should match
    txn_total = sum(abs(float(t["amount_signed"])) for t in txn_data["transactions"])
    chart_total = sum(float(d["total"]) for d in chart_data["data"])
    
    assert abs(txn_total - chart_total) < 0.01
    assert txn_total == 380.0  # 200 + 180


def test_service_layer_other_category_filter(mixed_transactions):
    """
    Integration test: Filtering by "Other" returns NULL category transactions.
    """
    client = TestClient(app)
    
    # Filter by "Other" (NULL categories)
    txn_response = client.get("/api/transactions?categories=Other&page_size=100")
    chart_response = client.get("/api/chart/weekly?categories=Other")
    
    assert txn_response.status_code == 200
    assert chart_response.status_code == 200
    
    chart_data = chart_response.json()
    
    # Chart should show "Other" category
    assert "Other" in chart_data["categories"]
    
    # Total should be 75.00 (the uncategorized transaction)
    other_total = sum(float(d["total"]) for d in chart_data["data"] if d["category"] == "Other")
    assert other_total == 75.0


def test_service_layer_date_filter_consistency(mixed_transactions):
    """
    Integration test: Date filters produce same data in list and chart.
    """
    client = TestClient(app)
    
    base_date = date(2025, 1, 1)
    filter_params = f"start_date={base_date}&end_date={base_date + timedelta(days=5)}&exclude_transfers=false"
    
    txn_response = client.get(f"/api/transactions?{filter_params}&page_size=100")
    chart_response = client.get(f"/api/chart/weekly?{filter_params}")
    
    assert txn_response.status_code == 200
    assert chart_response.status_code == 200
    
    txn_data = txn_response.json()
    chart_data = chart_response.json()
    
    # Should have 4 transactions (including transfer when exclude_transfers=false)
    assert txn_data["total"] == 4
    
    # Totals should match
    txn_total = sum(abs(float(t["amount_signed"])) for t in txn_data["transactions"])
    chart_total = sum(float(d["total"]) for d in chart_data["data"])
    
    assert abs(txn_total - chart_total) < 0.01


def test_service_layer_account_filter_consistency(mixed_transactions):
    """
    Integration test: Account filters work consistently.
    """
    client = TestClient(app)
    
    txn_response = client.get("/api/transactions?accounts=Current Account&page_size=100")
    chart_response = client.get("/api/chart/weekly?accounts=Current Account")
    
    assert txn_response.status_code == 200
    assert chart_response.status_code == 200
    
    txn_data = txn_response.json()
    
    # Should only have Current Account transactions
    assert all(t["account"] == "Current Account" for t in txn_data["transactions"])


def test_service_layer_merchant_filter_consistency(mixed_transactions):
    """
    Integration test: Merchant substring filter works in list and chart.
    """
    client = TestClient(app)
    
    # Search for merchants containing "car" (Carrefour)
    txn_response = client.get("/api/transactions?merchant=car&page_size=100")
    chart_response = client.get("/api/chart/weekly?merchant=car")
    
    assert txn_response.status_code == 200
    assert chart_response.status_code == 200
    
    txn_data = txn_response.json()
    chart_data = chart_response.json()
    
    # Should find Carrefour transaction
    assert txn_data["total"] >= 1
    assert any("car" in t["merchant"].lower() for t in txn_data["transactions"])
    
    # Totals should match
    txn_total = sum(abs(float(t["amount_signed"])) for t in txn_data["transactions"])
    chart_total = sum(float(d["total"]) for d in chart_data["data"])
    
    assert abs(txn_total - chart_total) < 0.01


def test_service_layer_combined_filters(mixed_transactions):
    """
    Integration test: Multiple filters combined work consistently.
    """
    client = TestClient(app)
    
    base_date = date(2025, 1, 1)
    params = (
        f"start_date={base_date}&"
        f"end_date={base_date + timedelta(days=5)}&"
        f"categories=Groceries&"
        f"categories=Food & Dining&"
        f"accounts=Current Account"
    )
    
    txn_response = client.get(f"/api/transactions?{params}&page_size=100")
    chart_response = client.get(f"/api/chart/weekly?{params}")
    
    assert txn_response.status_code == 200
    assert chart_response.status_code == 200
    
    txn_data = txn_response.json()
    chart_data = chart_response.json()
    
    # Verify filters applied
    for txn in txn_data["transactions"]:
        assert txn["category"] in ["Groceries", "Food & Dining"]
        assert txn["account"] == "Current Account"
        txn_date = date.fromisoformat(txn["date"])
        assert base_date <= txn_date <= base_date + timedelta(days=5)
    
    # Totals should match
    txn_total = sum(abs(float(t["amount_signed"])) for t in txn_data["transactions"])
    chart_total = sum(float(d["total"]) for d in chart_data["data"])
    
    assert abs(txn_total - chart_total) < 0.01


def test_service_layer_exclude_transfers_toggle(mixed_transactions):
    """
    Integration test: exclude_transfers parameter works consistently.
    """
    client = TestClient(app)
    
    # With transfers excluded (default)
    txn_excluded = client.get("/api/transactions?exclude_transfers=true&page_size=100")
    chart_excluded = client.get("/api/chart/weekly?exclude_transfers=true")
    
    # With transfers included
    txn_included = client.get("/api/transactions?exclude_transfers=false&page_size=100")
    chart_included = client.get("/api/chart/weekly?exclude_transfers=false")
    
    assert all(r.status_code == 200 for r in [txn_excluded, txn_included, chart_excluded, chart_included])
    
    # Excluded should have fewer transactions
    assert txn_excluded.json()["total"] < txn_included.json()["total"]
    
    # Excluded should not have transfer category
    chart_excluded_data = chart_excluded.json()
    assert "Transfer Between My Accounts" not in chart_excluded_data["categories"]
    
    # Included should have transfer category
    chart_included_data = chart_included.json()
    assert "Transfer Between My Accounts" in chart_included_data["categories"]


def test_service_layer_pagination_with_filters(mixed_transactions):
    """
    Integration test: Pagination doesn't affect filter consistency.
    """
    client = TestClient(app)
    
    # Get all transactions in one page
    all_response = client.get("/api/transactions?page_size=100&exclude_transfers=true")
    
    # Get same transactions in pages of 2
    page1 = client.get("/api/transactions?page=1&page_size=2&exclude_transfers=true")
    page2 = client.get("/api/transactions?page=2&page_size=2&exclude_transfers=true")
    
    assert all(r.status_code == 200 for r in [all_response, page1, page2])
    
    all_data = all_response.json()
    page1_data = page1.json()
    page2_data = page2.json()
    
    # Total should be consistent across pages
    assert page1_data["total"] == page2_data["total"] == all_data["total"]
    
    # Pages should have different transactions
    page1_ids = {t["id"] for t in page1_data["transactions"]}
    page2_ids = {t["id"] for t in page2_data["transactions"]}
    assert page1_ids.isdisjoint(page2_ids)


def test_service_layer_weekly_vs_monthly_aggregation(mixed_transactions):
    """
    Integration test: Weekly and monthly aggregations use same filtering logic.
    """
    client = TestClient(app)
    
    # Same filters, different aggregation periods
    weekly = client.get("/api/chart/weekly?categories=Groceries")
    monthly = client.get("/api/chart/monthly?categories=Groceries")
    
    assert weekly.status_code == 200
    assert monthly.status_code == 200
    
    weekly_data = weekly.json()
    monthly_data = monthly.json()
    
    # Both should only have Groceries
    assert weekly_data["categories"] == ["Groceries"]
    assert monthly_data["categories"] == ["Groceries"]
    
    # Monthly should aggregate weekly data (same total, different periods)
    weekly_total = sum(float(d["total"]) for d in weekly_data["data"])
    monthly_total = sum(float(d["total"]) for d in monthly_data["data"])
    
    assert abs(weekly_total - monthly_total) < 0.01
    assert weekly_total == 380.0  # 200 + 180

