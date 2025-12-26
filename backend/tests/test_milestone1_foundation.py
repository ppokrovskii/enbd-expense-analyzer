"""Integration tests for Milestone 1: Backend foundation + database schema."""
import pytest
from sqlalchemy import text
from app.models import Transaction, Category, LLMCache


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


def test_create_category(test_db):
    """Test creating a category in the database."""
    from datetime import datetime
    
    category = Category(
        name="Food & Dining",
        keywords=["CARREFOUR", "LULU", "STARBUCKS"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    test_db.add(category)
    test_db.commit()
    test_db.refresh(category)
    
    assert category.id is not None
    assert category.name == "Food & Dining"
    assert len(category.keywords) == 3
    assert "CARREFOUR" in category.keywords


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
    """Test that category name must be unique."""
    from datetime import datetime
    
    # Create first category
    category1 = Category(
        name="Shopping",
        keywords=["IKEA"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    test_db.add(category1)
    test_db.commit()
    
    # Try to create duplicate category
    category2 = Category(
        name="Shopping",
        keywords=["H&M"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    test_db.add(category2)
    
    with pytest.raises(Exception):  # Should raise integrity error
        test_db.commit()

