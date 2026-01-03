"""
Milestone 6 Tests: Category Context and AI Category Management

Tests:
1. Category filtering in context
2. AI tool: list_categories
3. AI tool: get_category_details
4. AI tool: create_category
5. AI tool: update_category
6. AI tool: delete_category
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from app.models import Transaction, Category
from app.services.ai_tools import AITools
from app.services.chat_service import ChatService


def create_test_data(db, user_id: str = "test_user"):
    """Create test categories and transactions."""
    # Create categories (new architecture: color instead of emoji)
    categories = [
        Category(user_id=user_id, name="Food & Dining", color="#FF6B6B"),
        Category(user_id=user_id, name="Transportation", color="#4CAF50"),
        Category(user_id=user_id, name="Shopping", color="#2196F3"),
        Category(user_id=user_id, name="Entertainment", color="#9C27B0"),
        Category(user_id=user_id, name="Utilities", color="#FF9800"),
    ]
    db.add_all(categories)
    db.commit()

    # Create transactions for different categories
    base_date = date.today() - timedelta(days=30)
    transactions = [
        # Food & Dining
        Transaction(
            user_id=user_id,
            date=base_date + timedelta(days=1),
            account="Credit Card",
            description="Restaurant ABC",
            details="",
            debit_credit="D",
            amount=Decimal("150.0"),
            amount_signed=Decimal("-150.0"),
            category="Food & Dining",
            merchant="Restaurant ABC",
            transaction_hash=f"hash_{user_id}_1",
            created_at=datetime.utcnow(),
        ),
        Transaction(
            user_id=user_id,
            date=base_date + timedelta(days=5),
            account="Credit Card",
            description="Grocery Store",
            details="",
            debit_credit="D",
            amount=Decimal("300.0"),
            amount_signed=Decimal("-300.0"),
            category="Food & Dining",
            merchant="Grocery Store",
            transaction_hash=f"hash_{user_id}_2",
            created_at=datetime.utcnow(),
        ),
        # Transportation
        Transaction(
            user_id=user_id,
            date=base_date + timedelta(days=2),
            account="Credit Card",
            description="Uber",
            details="",
            debit_credit="D",
            amount=Decimal("50.0"),
            amount_signed=Decimal("-50.0"),
            category="Transportation",
            merchant="Uber",
            transaction_hash=f"hash_{user_id}_3",
            created_at=datetime.utcnow(),
        ),
        Transaction(
            user_id=user_id,
            date=base_date + timedelta(days=10),
            account="Credit Card",
            description="Gas Station",
            details="",
            debit_credit="D",
            amount=Decimal("200.0"),
            amount_signed=Decimal("-200.0"),
            category="Transportation",
            merchant="Gas Station",
            transaction_hash=f"hash_{user_id}_4",
            created_at=datetime.utcnow(),
        ),
        # Shopping
        Transaction(
            user_id=user_id,
            date=base_date + timedelta(days=7),
            account="Credit Card",
            description="Online Store",
            details="",
            debit_credit="D",
            amount=Decimal("500.0"),
            amount_signed=Decimal("-500.0"),
            category="Shopping",
            merchant="Online Store",
            transaction_hash=f"hash_{user_id}_5",
            created_at=datetime.utcnow(),
        ),
        # Entertainment
        Transaction(
            user_id=user_id,
            date=base_date + timedelta(days=15),
            account="Credit Card",
            description="Cinema",
            details="",
            debit_credit="D",
            amount=Decimal("100.0"),
            amount_signed=Decimal("-100.0"),
            category="Entertainment",
            merchant="Cinema",
            transaction_hash=f"hash_{user_id}_6",
            created_at=datetime.utcnow(),
        ),
    ]
    db.add_all(transactions)
    db.commit()

    return categories, transactions


# ============================================
# Test 1: Category Filtering in Context Summary
# ============================================
def test_category_filtering_in_context(test_db):
    """Test that context can be filtered by specific categories."""
    from app.domains.transactions.service import TransactionService
    
    user_id = "test_user"
    categories, transactions = create_test_data(test_db, user_id)

    # Build transaction summary with category filter using TransactionService
    filtered_transactions, total = TransactionService.get_filtered_transactions(
        db=test_db,
        user_id=user_id,
        start_date=date.today() - timedelta(days=60),
        end_date=date.today(),
        categories=["Food & Dining", "Transportation"],
        page=1,
        page_size=100
    )
    
    # Build summary from filtered transactions
    summary = ChatService._build_transaction_summary(filtered_transactions)

    # Verify context
    assert total == 4  # 2 food + 2 transportation
    assert summary["total_expenses"] == 700.0  # 150 + 300 + 50 + 200


# ============================================
# Test 2: AI Tool - list_categories
# ============================================
def test_ai_tool_list_categories(test_db):
    """Test AI tool for listing all categories."""
    user_id = "test_user"
    categories, _ = create_test_data(test_db, user_id)

    # Execute the tool
    result = AITools.execute_tool(
        tool_name="list_categories",
        arguments={},
        db=test_db,
        user_id=user_id,
    )

    # Verify result
    assert "categories" in result
    assert len(result["categories"]) == 5
    
    # Check category structure
    first_cat = result["categories"][0]
    assert "name" in first_cat
    assert "color" in first_cat or "transaction_count" in first_cat  # color or stats
    assert "transaction_count" in first_cat
    assert "total_amount" in first_cat


# ============================================
# Test 3: AI Tool - get_category_details
# ============================================
def test_ai_tool_get_category_details(test_db):
    """Test AI tool for getting category details."""
    user_id = "test_user"
    categories, _ = create_test_data(test_db, user_id)

    # Execute the tool
    result = AITools.execute_tool(
        tool_name="get_category_details",
        arguments={"category_name": "Food & Dining"},
        db=test_db,
        user_id=user_id,
    )

    # Verify result
    assert result["name"] == "Food & Dining"
    assert result["color"] == "#FF6B6B"
    assert result["transaction_count"] == 2
    assert result["total_amount"] == -450.0  # 150 + 300


# ============================================
# Test 4: AI Tool - create_category
# ============================================
def test_ai_tool_create_category(test_db):
    """Test AI tool for creating a new category."""
    user_id = "test_user"

    # Execute the tool
    result = AITools.execute_tool(
        tool_name="create_category",
        arguments={
            "name": "Healthcare",
            "color": "#E91E63",
        },
        db=test_db,
        user_id=user_id,
    )

    # Verify result
    assert result["name"] == "Healthcare"
    assert result["color"] == "#E91E63"
    assert result["transaction_count"] == 0

    # Verify in database
    category = test_db.query(Category).filter(
        Category.user_id == user_id,
        Category.name == "Healthcare"
    ).first()
    assert category is not None
    assert category.color == "#E91E63"


# ============================================
# Test 5: AI Tool - update_category
# ============================================
def test_ai_tool_update_category(test_db):
    """Test AI tool for updating an existing category."""
    user_id = "test_user"
    categories, _ = create_test_data(test_db, user_id)

    # Execute the tool
    result = AITools.execute_tool(
        tool_name="update_category",
        arguments={
            "category_name": "Food & Dining",
            "new_name": "Food & Restaurants",
            "new_color": "#FF5722",
        },
        db=test_db,
        user_id=user_id,
    )

    # Verify result
    assert result["name"] == "Food & Restaurants"
    assert result["color"] == "#FF5722"

    # Verify in database
    category = test_db.query(Category).filter(
        Category.user_id == user_id,
        Category.name == "Food & Restaurants"
    ).first()
    assert category is not None
    assert category.color == "#FF5722"

    # Old name should not exist
    old_category = test_db.query(Category).filter(
        Category.user_id == user_id,
        Category.name == "Food & Dining"
    ).first()
    assert old_category is None


# ============================================
# Test 6: AI Tool - delete_category
# ============================================
def test_ai_tool_delete_category(test_db):
    """Test AI tool for deleting a category."""
    user_id = "test_user"
    categories, _ = create_test_data(test_db, user_id)

    # Count categories before
    count_before = test_db.query(Category).filter(
        Category.user_id == user_id
    ).count()
    assert count_before == 5

    # Execute the tool
    result = AITools.execute_tool(
        tool_name="delete_category",
        arguments={"category_name": "Entertainment"},
        db=test_db,
        user_id=user_id,
    )

    # Verify result
    assert result["deleted"] is True
    assert "Entertainment" in result["message"]

    # Verify in database
    count_after = test_db.query(Category).filter(
        Category.user_id == user_id
    ).count()
    assert count_after == 4

    category = test_db.query(Category).filter(
        Category.user_id == user_id,
        Category.name == "Entertainment"
    ).first()
    assert category is None


# ============================================
# Test 7: Category Filter with No Matches
# ============================================
def test_category_filter_no_matches(test_db):
    """Test category filtering when no transactions match."""
    from app.domains.transactions.service import TransactionService
    
    user_id = "test_user"
    categories, _ = create_test_data(test_db, user_id)

    # Try to get context with category that has no transactions
    filtered_transactions, total = TransactionService.get_filtered_transactions(
        db=test_db,
        user_id=user_id,
        start_date=date.today() - timedelta(days=60),
        end_date=date.today(),
        categories=["Utilities"],  # No transactions in this category
        page=1,
        page_size=100
    )
    
    # Build summary from filtered transactions
    summary = ChatService._build_transaction_summary(filtered_transactions)

    assert total == 0
    assert summary["total_expenses"] == 0


# ============================================
# Test 8: Multi-User Category Isolation
# ============================================
def test_multi_user_category_isolation(test_db):
    """Test that categories are isolated between users."""
    user1 = "user1"
    user2 = "user2"

    # Create categories for user1
    cat1 = Category(user_id=user1, name="User1 Category", color="#2196F3")
    test_db.add(cat1)
    test_db.commit()

    # Create categories for user2
    cat2 = Category(user_id=user2, name="User2 Category", color="#F44336")
    test_db.add(cat2)
    test_db.commit()

    # User1 should only see their category
    result1 = AITools.execute_tool(
        tool_name="list_categories",
        arguments={},
        db=test_db,
        user_id=user1,
    )
    assert len(result1["categories"]) == 1
    assert result1["categories"][0]["name"] == "User1 Category"

    # User2 should only see their category
    result2 = AITools.execute_tool(
        tool_name="list_categories",
        arguments={},
        db=test_db,
        user_id=user2,
    )
    assert len(result2["categories"]) == 1
    assert result2["categories"][0]["name"] == "User2 Category"


# ============================================
# Test 9: Create Duplicate Category (Should Fail)
# ============================================
def test_create_duplicate_category(test_db):
    """Test that creating a duplicate category fails gracefully."""
    user_id = "test_user"
    categories, _ = create_test_data(test_db, user_id)

    # Try to create a category that already exists
    with pytest.raises(Exception):  # Should raise an error
        AITools.execute_tool(
            tool_name="create_category",
            arguments={
                "name": "Food & Dining",  # Already exists
                "color": "#795548",
            },
            db=test_db,
            user_id=user_id,
        )


# ============================================
# Test 10: Update Non-Existent Category
# ============================================
def test_update_nonexistent_category(test_db):
    """Test updating a category that doesn't exist."""
    user_id = "test_user"

    with pytest.raises(ValueError):
        AITools.execute_tool(
            tool_name="update_category",
            arguments={
                "category_name": "NonExistent",
                "new_name": "New Name",
            },
            db=test_db,
            user_id=user_id,
        )

