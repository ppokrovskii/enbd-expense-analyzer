"""Integration tests for Milestone 1: Backend foundation + database schema."""
import pytest
from sqlalchemy import text
from app.models import Transaction, Category, Rule, LLMCache


def test_database_connection(test_db):
    """Test that we can connect to the database."""
    result = test_db.execute(text("SELECT 1")).scalar()
    assert result == 1


def test_create_transaction(test_db):
    """Test creating a transaction in the database."""
    from datetime import date, datetime
    from decimal import Decimal
    import hashlib
    
    # Create a transaction
    transaction = Transaction(
        date=date(2025, 12, 26),
        account="Current Account",
        description="CARREFOUR DUBAI",
        details="Shopping",
        debit_credit="Debit",
        amount=Decimal("250.50"),
        balance=Decimal("5000.00"),
        merchant="CARREFOUR",
        amount_signed=Decimal("-250.50"),
        category="Groceries",
        week_start=date(2025, 12, 23),
        month="2025-12",
        year=2025,
        transaction_hash=hashlib.md5(b"test_transaction").hexdigest(),
        created_at=datetime.utcnow()
    )
    
    test_db.add(transaction)
    test_db.commit()
    test_db.refresh(transaction)
    
    # Verify transaction was created
    assert transaction.id is not None
    assert transaction.merchant == "CARREFOUR"
    assert transaction.category == "Groceries"
    assert float(transaction.amount_signed) == -250.50


def test_create_category_with_rules(test_db):
    """Test creating a category and associated rules in the database.
    
    Note: In the new architecture, Category only stores name and color.
    Keywords are stored in the separate Rule model.
    """
    from datetime import datetime
    
    # Create category first (without keywords)
    category = Category(
        name="Food & Dining",
        color="#4CAF50",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    test_db.add(category)
    test_db.commit()
    test_db.refresh(category)
    
    assert category.id is not None
    assert category.name == "Food & Dining"
    
    # Now create a rule with keywords linked to the category
    rule = Rule(
        category_id=category.id,
        user_id='default_user',
        keywords=["CARREFOUR", "LULU", "STARBUCKS"],
        exclude_keywords=[],
        priority=0,
        created_at=datetime.utcnow()
    )
    
    test_db.add(rule)
    test_db.commit()
    test_db.refresh(rule)
    
    assert rule.id is not None
    assert rule.category_id == category.id
    assert len(rule.keywords) == 3
    assert "CARREFOUR" in rule.keywords


def test_create_llm_cache(test_db):
    """Test creating an LLM cache entry."""
    from datetime import datetime
    
    cache_entry = LLMCache(
        merchant="AMAZON.COM",
        category="Shopping",
        created_at=datetime.utcnow()
    )
    
    test_db.add(cache_entry)
    test_db.commit()
    test_db.refresh(cache_entry)
    
    assert cache_entry.id is not None
    assert cache_entry.merchant == "AMAZON.COM"
    assert cache_entry.category == "Shopping"


def test_transaction_hash_unique_constraint(test_db):
    """Test that transaction hash must be unique."""
    from datetime import date, datetime
    from decimal import Decimal
    import hashlib
    
    hash_value = hashlib.md5(b"duplicate_test").hexdigest()
    
    # Create first transaction
    transaction1 = Transaction(
        date=date(2025, 12, 26),
        account="Current Account",
        description="Test 1",
        amount=Decimal("100.00"),
        transaction_hash=hash_value,
        created_at=datetime.utcnow()
    )
    test_db.add(transaction1)
    test_db.commit()
    
    # Try to create duplicate transaction
    transaction2 = Transaction(
        date=date(2025, 12, 27),
        account="Savings Account",
        description="Test 2",
        amount=Decimal("200.00"),
        transaction_hash=hash_value,
        created_at=datetime.utcnow()
    )
    test_db.add(transaction2)
    
    with pytest.raises(Exception):  # Should raise integrity error
        test_db.commit()


def test_category_name_unique_constraint(test_db):
    """Test that category name must be unique per user.
    
    Note: In the new architecture, uniqueness is per (user_id, name) combination.
    """
    from datetime import datetime
    
    # Create first category
    category1 = Category(
        user_id='default_user',
        name="Shopping",
        color="#2196F3",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    test_db.add(category1)
    test_db.commit()
    
    # Try to create duplicate category for same user
    category2 = Category(
        user_id='default_user',
        name="Shopping",
        color="#F44336",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    test_db.add(category2)
    
    with pytest.raises(Exception):  # Should raise integrity error
        test_db.commit()

