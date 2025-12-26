"""Tests for Milestone 4: Rule-based categorization."""
import pytest
from app.services.category_service import CategoryService
from app.models import Transaction, Category
from sqlalchemy.orm import Session
from datetime import date
from decimal import Decimal


def test_categorize_merchant():
    """Test basic merchant categorization logic."""
    service = CategoryService()
    
    rules = {
        'Food & Dining': ['CARREFOUR', 'SPINNEYS', 'RESTAURANT'],
        'Transportation': ['UBER', 'CAREEM', 'TAXI'],
        'Telecommunications': ['DU TELECOM', 'ETISALAT']
    }
    
    assert service.categorize_merchant('CARREFOUR HYPERMARKET', rules) == 'Food & Dining'
    assert service.categorize_merchant('UBER TRIP 12345', rules) == 'Transportation'
    assert service.categorize_merchant('DU TELECOM PAYMENT', rules) == 'Telecommunications'
    assert service.categorize_merchant('UNKNOWN MERCHANT', rules) == 'Other'
    assert service.categorize_merchant('', rules) == 'Other'


def test_load_categories_from_db(test_db: Session):
    """Test loading categories from database."""
    # Insert test categories
    cat1 = Category(name='Food & Dining', keywords=['CARREFOUR', 'SPINNEYS'])
    cat2 = Category(name='Transportation', keywords=['UBER', 'CAREEM'])
    test_db.add_all([cat1, cat2])
    test_db.commit()
    
    service = CategoryService()
    rules = service.load_categories(test_db)
    
    assert 'Food & Dining' in rules
    assert 'Transportation' in rules
    assert 'CARREFOUR' in rules['Food & Dining']
    assert 'UBER' in rules['Transportation']


def test_categorize_transactions(test_db: Session):
    """Test categorizing transactions in database."""
    # Insert categories
    cat1 = Category(name='Food & Dining', keywords=['CARREFOUR', 'SPINNEYS'])
    cat2 = Category(name='Transportation', keywords=['UBER', 'CAREEM'])
    test_db.add_all([cat1, cat2])
    test_db.commit()
    
    # Insert uncategorized transactions
    trans1 = Transaction(
        date=date(2025, 12, 1),
        account='Current Account',
        merchant='CARREFOUR HYPERMARKET',
        amount=Decimal('100.00'),
        transaction_hash='hash1',
        category='Other'
    )
    trans2 = Transaction(
        date=date(2025, 12, 2),
        account='Current Account',
        merchant='UBER TRIP',
        amount=Decimal('50.00'),
        transaction_hash='hash2',
        category='Other'
    )
    trans3 = Transaction(
        date=date(2025, 12, 3),
        account='Current Account',
        merchant='UNKNOWN MERCHANT',
        amount=Decimal('25.00'),
        transaction_hash='hash3',
        category='Other'
    )
    test_db.add_all([trans1, trans2, trans3])
    test_db.commit()
    
    # Categorize
    service = CategoryService()
    categorized = service.categorize_transactions(test_db)
    
    # Check results
    assert categorized == 2  # Only trans1 and trans2 should be categorized
    
    test_db.refresh(trans1)
    test_db.refresh(trans2)
    test_db.refresh(trans3)
    
    assert trans1.category == 'Food & Dining'
    assert trans2.category == 'Transportation'
    assert trans3.category == 'Other'  # No matching rule


def test_seed_categories_from_json(test_db: Session, tmp_path):
    """Test seeding categories from JSON file."""
    # Create a temporary JSON file
    json_content = '''
{
  "categories": [
    {
      "name": "Food & Dining",
      "keywords": ["CARREFOUR", "SPINNEYS", "RESTAURANT"]
    },
    {
      "name": "Transportation",
      "keywords": ["UBER", "CAREEM", "TAXI"]
    }
  ]
}
'''
    json_file = tmp_path / "test_categories.json"
    json_file.write_text(json_content)
    
    # Seed from JSON
    service = CategoryService()
    inserted = service.seed_categories_from_json(test_db, str(json_file))
    
    assert inserted == 2
    
    # Verify categories are in database
    categories = test_db.query(Category).all()
    assert len(categories) == 2
    
    food_cat = test_db.query(Category).filter_by(name='Food & Dining').first()
    assert food_cat is not None
    assert 'CARREFOUR' in food_cat.keywords
    
    # Test idempotency - running again shouldn't insert duplicates
    inserted_again = service.seed_categories_from_json(test_db, str(json_file))
    assert inserted_again == 0
    
    categories_after = test_db.query(Category).all()
    assert len(categories_after) == 2

