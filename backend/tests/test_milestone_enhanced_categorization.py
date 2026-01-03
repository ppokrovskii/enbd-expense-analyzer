"""Integration tests for Milestone 2: Enhanced Categorization."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date
from decimal import Decimal
from app.main import app
from app.database import get_db, engine, Base
from app.services.category_service import CategoryService
from app.services.account_service import AccountService
from app.models import Transaction, Category, Rule, UserAccount

client = TestClient(app)


@pytest.fixture(scope="function")
def test_db():
    """Create a test database session."""
    Base.metadata.create_all(bind=engine)
    
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    # Clean up before test
    try:
        session.query(Transaction).filter(Transaction.user_id.like('%test%')).delete()
        session.query(Category).filter(Category.user_id.like('%test%')).delete()
        session.query(UserAccount).filter(UserAccount.user_id.like('%test%')).delete()
        session.commit()
    except Exception as e:
        print(f"Pre-cleanup error: {e}")
        session.rollback()
    
    def override_get_db():
        try:
            yield session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield session
    
    # Cleanup after test
    try:
        session.rollback()
        session.query(Transaction).filter(Transaction.user_id.like('%test%')).delete()
        session.query(Category).filter(Category.user_id.like('%test%')).delete()
        session.query(UserAccount).filter(UserAccount.user_id.like('%test%')).delete()
        session.commit()
    except Exception as e:
        print(f"Post-cleanup error: {e}")
        session.rollback()
    finally:
        session.close()
    
    app.dependency_overrides.clear()


def test_search_text_populated_on_import(test_db):
    """Test that search_text is populated with combined details and description."""
    transaction = Transaction(
        user_id='test_user',
        date=date(2024, 1, 1),
        account='Test Account',
        description='CARREFOUR SUPERMARKET',
        details='Transfer from account',
        debit_credit='DR',
        amount=Decimal('100.00'),
        transaction_hash='test_hash_001'
    )
    
    # Manually set search_text as ImportService would
    transaction.search_text = f"{transaction.details} {transaction.description}".strip()
    
    test_db.add(transaction)
    test_db.commit()
    
    # Verify search_text is populated
    saved = test_db.query(Transaction).filter_by(transaction_hash='test_hash_001').first()
    assert saved.search_text == "Transfer from account CARREFOUR SUPERMARKET"
    assert "CARREFOUR" in saved.search_text
    assert "Transfer" in saved.search_text


def test_categorization_with_account_variables(test_db):
    """Test categorization using account variables like {current_account}."""
    # Create account
    account = UserAccount(
        user_id='test_user',
        account_name='current_account',
        account_number='1234',
        account_number_masked='****1234',
        bank='ENBD'
    )
    test_db.add(account)
    test_db.commit()
    
    # Create category (new architecture: no keywords on Category)
    category = Category(
        user_id='test_user',
        name='Internal Transfer'
    )
    test_db.add(category)
    test_db.commit()
    
    # Create rule with account variable keywords
    rule = Rule(
        category_id=category.id,
        user_id='test_user',
        keywords=['{current_account}', 'TRANSFER']
    )
    test_db.add(rule)
    test_db.commit()
    
    # Get account variables
    account_vars = AccountService.get_account_variables(test_db, 'test_user')
    
    # Load rules
    category_service = CategoryService()
    rules = category_service.load_categories(test_db, 'test_user')
    
    # Test categorization with account number in search text
    search_text = "Transfer to 1234"
    result = category_service.categorize_with_variables(search_text, rules, account_vars)
    assert result == "Internal Transfer"


def test_exclude_keywords(test_db):
    """Test that exclude keywords prevent categorization."""
    # Create category
    category = Category(
        user_id='test_user',
        name='Groceries'
    )
    test_db.add(category)
    test_db.commit()
    
    # Create rule with exclude keywords
    rule = Rule(
        category_id=category.id,
        user_id='test_user',
        keywords=['CARREFOUR', 'SUPERMARKET'],
        exclude_keywords=['REFUND', 'REVERSAL']
    )
    test_db.add(rule)
    test_db.commit()
    
    category_service = CategoryService()
    rules = category_service.load_categories(test_db, 'test_user')
    account_vars = {}
    
    # Should match
    result1 = category_service.categorize_with_variables("CARREFOUR PURCHASE", rules, account_vars)
    assert result1 == "Groceries"
    
    # Should NOT match (excluded)
    result2 = category_service.categorize_with_variables("CARREFOUR REFUND", rules, account_vars)
    assert result2 == "Other"
    
    result3 = category_service.categorize_with_variables("CARREFOUR REVERSAL", rules, account_vars)
    assert result3 == "Other"


def test_longest_match_priority(test_db):
    """Test that longest keyword match wins."""
    # Create two categories with overlapping keywords
    cat_a = Category(
        user_id='test_user',
        name='Shopping'
    )
    cat_b = Category(
        user_id='test_user',
        name='Groceries'
    )
    test_db.add(cat_a)
    test_db.add(cat_b)
    test_db.commit()
    
    # Create rules
    rule_a = Rule(category_id=cat_a.id, user_id='test_user', keywords=['SUPER'])
    rule_b = Rule(category_id=cat_b.id, user_id='test_user', keywords=['SUPERMARKET'])
    test_db.add(rule_a)
    test_db.add(rule_b)
    test_db.commit()
    
    category_service = CategoryService()
    rules = category_service.load_categories(test_db, 'test_user')
    account_vars = {}
    
    # "SUPERMARKET" should match Groceries (longer/more specific)
    result = category_service.categorize_with_variables("CARREFOUR SUPERMARKET", rules, account_vars)
    assert result == "Groceries"


def test_details_and_description_combined(test_db):
    """Test matching across both details and description fields."""
    # Create category
    category = Category(
        user_id='test_user',
        name='Groceries'
    )
    test_db.add(category)
    test_db.commit()
    
    # Create rule with keyword
    rule = Rule(category_id=category.id, user_id='test_user', keywords=['CARREFOUR'])
    test_db.add(rule)
    test_db.commit()
    
    category_service = CategoryService()
    rules = category_service.load_categories(test_db, 'test_user')
    account_vars = {}
    
    # Test with keyword only in "description" part
    search_text = "Transfer from account CARREFOUR MARKET"
    result = category_service.categorize_with_variables(search_text, rules, account_vars)
    assert result == "Groceries"
    
    # Test with keyword only in "details" part
    search_text2 = "CARREFOUR Payment completed"
    result2 = category_service.categorize_with_variables(search_text2, rules, account_vars)
    assert result2 == "Groceries"


def test_pipe_separated_alternatives(test_db):
    """Test pipe-separated keyword alternatives."""
    category = Category(
        user_id='test_user',
        name='Food Delivery'
    )
    test_db.add(category)
    test_db.commit()
    
    # Create rule with pipe-separated keywords
    rule = Rule(category_id=category.id, user_id='test_user', keywords=['TALABAT|DELIVEROO|ZOMATO'])
    test_db.add(rule)
    test_db.commit()
    
    category_service = CategoryService()
    rules = category_service.load_categories(test_db, 'test_user')
    account_vars = {}
    
    # All three should match
    assert category_service.categorize_with_variables("Order from TALABAT", rules, account_vars) == "Food Delivery"
    assert category_service.categorize_with_variables("Order from DELIVEROO", rules, account_vars) == "Food Delivery"
    assert category_service.categorize_with_variables("Order from ZOMATO", rules, account_vars) == "Food Delivery"
    
    # Non-matching should return Other
    assert category_service.categorize_with_variables("Order from MCDONALDS", rules, account_vars) == "Other"


def test_case_insensitive_matching(test_db):
    """Test that matching is case-insensitive."""
    category = Category(
        user_id='test_user',
        name='Gas'
    )
    test_db.add(category)
    test_db.commit()
    
    # Create rule
    rule = Rule(category_id=category.id, user_id='test_user', keywords=['ENOC', 'ADNOC'])
    test_db.add(rule)
    test_db.commit()
    
    category_service = CategoryService()
    rules = category_service.load_categories(test_db, 'test_user')
    account_vars = {}
    
    # Different cases should all match
    assert category_service.categorize_with_variables("enoc station", rules, account_vars) == "Gas"
    assert category_service.categorize_with_variables("ENOC STATION", rules, account_vars) == "Gas"
    assert category_service.categorize_with_variables("Enoc Station", rules, account_vars) == "Gas"

