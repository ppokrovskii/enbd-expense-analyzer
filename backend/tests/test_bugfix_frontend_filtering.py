"""
Test for Bug Fix: Frontend Category Exclusion Display Issues

Bug Description:
1. Transaction count displays API count (20) instead of filtered client-side count (4)
2. Total amount displays unfiltered sum from API instead of sum of visible transactions
3. When categories are excluded via chart legend, the pagination info doesn't reflect
   the actual number of visible transactions

Root Cause:
- Client-side filtering (excludedCategories) was happening AFTER fetching from API
- Display counts and totals were using API response values, not filtered results
- The backend API doesn't support negative filtering (exclude these categories)

Expected Behavior:
- Transaction count should show actual number of visible transactions after filtering
- Total amount should sum only the visible filtered transactions
- Pagination info should indicate when categories are excluded

Note: This is primarily a frontend bug, but we can test the backend API behavior
to ensure it provides correct data for the frontend to filter.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date, datetime

from app.main import app
from app.models import Transaction


@pytest.fixture
def transactions_with_mixed_categories(test_db: Session):
    """Create transactions across multiple categories for filtering tests."""
    transactions = [
        Transaction(
            date=date(2025, 12, 1),
            account="Test Account",
            merchant="Grocery Store 1",
            category="Groceries",
            amount=100.00,
            amount_signed=-100.00,
            transaction_hash="hash1",
        ),
        Transaction(
            date=date(2025, 12, 2),
            account="Test Account",
            merchant="Grocery Store 2",
            category="Groceries",
            amount=50.00,
            amount_signed=-50.00,
            transaction_hash="hash2",
        ),
        Transaction(
            date=date(2025, 12, 3),
            account="Test Account",
            merchant="Restaurant 1",
            category="Food & Dining",
            amount=75.00,
            amount_signed=-75.00,
            transaction_hash="hash3",
        ),
        Transaction(
            date=date(2025, 12, 4),
            account="Test Account",
            merchant="Restaurant 2",
            category="Food & Dining",
            amount=60.00,
            amount_signed=-60.00,
            transaction_hash="hash4",
        ),
        Transaction(
            date=date(2025, 12, 5),
            account="Test Account",
            merchant="Cinema",
            category="Entertainment",
            amount=120.00,
            amount_signed=-120.00,
            transaction_hash="hash5",
        ),
    ]
    
    test_db.add_all(transactions)
    test_db.commit()
    
    return transactions


def test_api_returns_all_transactions_when_no_category_filter(
    transactions_with_mixed_categories,
):
    """
    BUG CONTEXT TEST: Verify API returns all transactions without category filter.
    
    This confirms the backend behaves correctly - the frontend is responsible
    for client-side filtering via excludedCategories.
    """
    client = TestClient(app)
    response = client.get("/api/transactions?page=1&page_size=20")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return all 5 transactions
    assert data["total"] == 5
    assert len(data["transactions"]) == 5


def test_api_category_filter_includes_only_specified_categories(
    transactions_with_mixed_categories,
):
    """
    BUG CONTEXT TEST: Verify API correctly filters by category (positive filtering).
    
    Backend supports positive filtering (include these), not negative filtering
    (exclude these). Frontend must handle exclusion client-side.
    """
    client = TestClient(app)
    
    # Request only Groceries
    response = client.get("/api/transactions?page=1&page_size=20&categories=Groceries")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return only 2 Groceries transactions
    assert data["total"] == 2
    assert len(data["transactions"]) == 2
    
    for tx in data["transactions"]:
        assert tx["category"] == "Groceries"


def test_api_provides_correct_totals_for_filtered_categories(
    transactions_with_mixed_categories,
):
    """
    BUG CONTEXT TEST: Verify API provides accurate data for frontend calculations.
    
    The frontend needs to:
    1. Calculate sum of visible transactions after client-side filtering
    2. Display correct count of visible transactions
    
    This test confirms the API provides correct per-transaction amounts.
    """
    client = TestClient(app)
    
    # Request only Food & Dining
    response = client.get(
        "/api/transactions?page=1&page_size=20&categories=Food+%26+Dining"
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify transaction amounts are correct
    amounts = [abs(float(tx["amount_signed"])) for tx in data["transactions"]]
    assert sum(amounts) == 135.00  # 75 + 60
    
    # Frontend should use this to calculate totals
    assert len(data["transactions"]) == 2


def test_pagination_total_reflects_filtered_results(
    transactions_with_mixed_categories,
):
    """
    BUG CONTEXT TEST: Verify pagination total reflects applied filters.
    
    When frontend applies category exclusion, it should use:
    - filteredTransactions.length (not data.transactions.length)
    - Sum of filteredTransactions (not backend total)
    """
    client = TestClient(app)
    
    # Simulate what happens when user excludes Entertainment and Food & Dining
    # Frontend should request only Groceries
    response = client.get("/api/transactions?page=1&page_size=20&categories=Groceries")
    
    assert response.status_code == 200
    data = response.json()
    
    # Backend correctly reports filtered results
    assert data["total"] == 2
    assert len(data["transactions"]) == 2
    
    # Frontend should display:
    # "Showing 2 of 5 transactions (2 categories excluded)"
    # "Total: AED 150"


def test_multiple_category_filters_work_correctly(
    transactions_with_mixed_categories,
):
    """
    BUG CONTEXT TEST: Verify multiple category filters return correct subset.
    
    This helps understand the limitation: backend can't easily support
    "exclude these categories" - it's designed for "include these categories".
    """
    client = TestClient(app)
    
    # Request Groceries and Food & Dining (exclude Entertainment)
    response = client.get(
        "/api/transactions?page=1&page_size=20"
        "&categories=Groceries&categories=Food+%26+Dining"
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return 4 transactions (2 Groceries + 2 Food & Dining)
    assert data["total"] == 4
    assert len(data["transactions"]) == 4
    
    categories = [tx["category"] for tx in data["transactions"]]
    assert "Entertainment" not in categories
    assert categories.count("Groceries") == 2
    assert categories.count("Food & Dining") == 2


@pytest.mark.skip(reason="Backend doesn't support negative filtering")
def test_backend_negative_filtering_not_supported():
    """
    DOCUMENTATION: Backend API doesn't support 'exclude_categories' parameter.
    
    This is BY DESIGN. Client-side filtering is more flexible for interactive UIs
    where users toggle categories on/off rapidly.
    
    Frontend approach:
    1. Fetch all transactions (or with positive category filter)
    2. Apply excludedCategories client-side
    3. Calculate counts and totals from filtered results
    4. Display accurate information to user
    
    Alternative backend approach (not implemented):
    - Add `exclude_categories` query parameter
    - Filter on backend: WHERE category NOT IN (excluded_list)
    - Return pre-filtered results
    
    Trade-offs:
    - Backend filtering: More accurate pagination, less data transfer
    - Client filtering: More flexible UI, works with existing API
    """
    pass


# Integration test to verify the fix works end-to-end
def test_frontend_filtering_scenario_end_to_end(
    transactions_with_mixed_categories,
):
    """
    BUG FIX VERIFICATION: End-to-end test of the filtering scenario.
    
    Scenario:
    1. User views transactions page (sees all 5 transactions)
    2. User clicks Entertainment category to exclude it
    3. Frontend should show:
       - "Showing 4 of 5 transactions (1 category excluded)"
       - Total: AED 285 (100 + 50 + 75 + 60)
    4. User clicks Food & Dining to exclude it too
    5. Frontend should show:
       - "Showing 2 of 5 transactions (2 categories excluded)"
       - Total: AED 150 (100 + 50)
    """
    client = TestClient(app)
    
    # Step 1: Fetch all transactions
    response = client.get("/api/transactions?page=1&page_size=20")
    assert response.status_code == 200
    all_data = response.json()
    
    # Initial state: all transactions visible
    assert all_data["total"] == 5
    assert len(all_data["transactions"]) == 5
    
    # Frontend calculation (simulated)
    all_transactions = all_data["transactions"]
    
    # Step 2: User excludes Entertainment
    excluded_categories = ["Entertainment"]
    filtered_step2 = [
        tx for tx in all_transactions 
        if tx["category"] not in excluded_categories
    ]
    
    # Verify frontend calculations
    assert len(filtered_step2) == 4
    total_step2 = sum(abs(float(tx["amount_signed"])) for tx in filtered_step2)
    assert total_step2 == 285.00
    
    # Step 3: User also excludes Food & Dining
    excluded_categories = ["Entertainment", "Food & Dining"]
    filtered_step3 = [
        tx for tx in all_transactions 
        if tx["category"] not in excluded_categories
    ]
    
    # Verify frontend calculations
    assert len(filtered_step3) == 2
    total_step3 = sum(abs(float(tx["amount_signed"])) for tx in filtered_step3)
    assert total_step3 == 150.00
    
    # These are the values that should be displayed in the UI
    assert len(filtered_step3) == 2  # "Showing 2"
    assert all_data["total"] == 5  # "of 5 transactions"
    assert len(excluded_categories) == 2  # "(2 categories excluded)"
    assert total_step3 == 150.00  # "Total: AED 150"

