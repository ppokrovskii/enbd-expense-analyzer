"""
Tests for Milestone 1: Multi-Tenant Database Schema

Validates that:
- Migration created all new tables
- Existing tables have user_id column
- Indexes are created
- Transactions are filtered by user_id
- Categories are isolated per user
- LLM cache is per user
"""
import pytest
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import inspect
from app.models import Transaction, Category, LLMCache, ChatSession, ChatMessage, ChatContext, TokenUsage
from app.services.transaction_query_service import TransactionQueryService


def test_migration_created_chat_tables(test_db):
    """Test that migration created all new chat-related tables."""
    inspector = inspect(test_db.bind)
    tables = inspector.get_table_names()
    
    assert 'chat_sessions' in tables
    assert 'chat_messages' in tables
    assert 'chat_contexts' in tables
    assert 'token_usage' in tables


def test_existing_tables_have_user_id(test_db):
    """Test that existing tables have user_id column."""
    inspector = inspect(test_db.bind)
    
    # Check transactions table
    transactions_columns = {col['name'] for col in inspector.get_columns('transactions')}
    assert 'user_id' in transactions_columns
    
    # Check categories table
    categories_columns = {col['name'] for col in inspector.get_columns('categories')}
    assert 'user_id' in categories_columns
    
    # Check llm_cache table
    llm_cache_columns = {col['name'] for col in inspector.get_columns('llm_cache')}
    assert 'user_id' in llm_cache_columns


def test_user_id_indexes_created(test_db):
    """Test that user_id indexes were created."""
    inspector = inspect(test_db.bind)
    
    # Check transactions indexes
    transactions_indexes = inspector.get_indexes('transactions')
    index_names = [idx['name'] for idx in transactions_indexes]
    assert 'ix_transactions_user_id' in index_names
    assert 'idx_transactions_user_date' in index_names
    assert 'idx_transactions_user_category' in index_names
    assert 'idx_transactions_user_merchant' in index_names
    
    # Check categories indexes
    categories_indexes = inspector.get_indexes('categories')
    index_names = [idx['name'] for idx in categories_indexes]
    assert 'ix_categories_user_id' in index_names
    assert 'idx_categories_user_name' in index_names


def test_transactions_filtered_by_user_id(test_db):
    """Test that transactions are properly isolated per user."""
    # Create transactions for two different users
    transaction1 = Transaction(
        user_id='user1',
        date=date(2025, 12, 1),
        account='Current Account',
        description='Test transaction 1',
        details='Details 1',
        debit_credit='D',
        amount=Decimal('100.00'),
        amount_signed=Decimal('-100.00'),
        merchant='Merchant A',
        category='Shopping',
        transaction_hash='hash1',
        created_at=datetime.utcnow()
    )
    
    transaction2 = Transaction(
        user_id='user2',
        date=date(2025, 12, 2),
        account='Current Account',
        description='Test transaction 2',
        details='Details 2',
        debit_credit='D',
        amount=Decimal('200.00'),
        amount_signed=Decimal('-200.00'),
        merchant='Merchant B',
        category='Food',
        transaction_hash='hash2',
        created_at=datetime.utcnow()
    )
    
    test_db.add(transaction1)
    test_db.add(transaction2)
    test_db.commit()
    
    # Query with TransactionQueryService for user1
    transactions_user1, total_user1 = TransactionQueryService.get_filtered_transactions(
        db=test_db,
        user_id='user1',
        page=1,
        page_size=50
    )
    
    # Query with TransactionQueryService for user2
    transactions_user2, total_user2 = TransactionQueryService.get_filtered_transactions(
        db=test_db,
        user_id='user2',
        page=1,
        page_size=50
    )
    
    # Each user should see only their own transactions
    assert total_user1 == 1
    assert total_user2 == 1
    assert transactions_user1[0].user_id == 'user1'
    assert transactions_user1[0].merchant == 'Merchant A'
    assert transactions_user2[0].user_id == 'user2'
    assert transactions_user2[0].merchant == 'Merchant B'


def test_categories_isolated_per_user(test_db):
    """Test that categories are properly isolated per user.
    
    Note: In the new architecture, keywords are stored in Rule model, not Category.
    """
    from app.models import Rule
    
    # Create categories for two different users
    category1 = Category(
        user_id='user1',
        name='Shopping',
        color='#FF6B6B',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    category2 = Category(
        user_id='user2',
        name='Shopping',  # Same name but different user
        color='#4CAF50',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    test_db.add(category1)
    test_db.add(category2)
    test_db.commit()
    test_db.refresh(category1)
    test_db.refresh(category2)
    
    # Create rules with keywords for each category
    rule1 = Rule(category_id=category1.id, user_id='user1', keywords=['MALL', 'SHOP'])
    rule2 = Rule(category_id=category2.id, user_id='user2', keywords=['IKEA', 'H&M'])
    test_db.add(rule1)
    test_db.add(rule2)
    test_db.commit()
    
    # Query categories for each user
    categories_user1 = test_db.query(Category).filter(Category.user_id == 'user1').all()
    categories_user2 = test_db.query(Category).filter(Category.user_id == 'user2').all()
    
    # Each user should see only their own categories
    assert len(categories_user1) == 1
    assert len(categories_user2) == 1
    
    # Query rules for each user
    rules_user1 = test_db.query(Rule).filter(Rule.user_id == 'user1').all()
    rules_user2 = test_db.query(Rule).filter(Rule.user_id == 'user2').all()
    assert rules_user1[0].keywords == ['MALL', 'SHOP']
    assert rules_user2[0].keywords == ['IKEA', 'H&M']


def test_llm_cache_per_user(test_db):
    """Test that LLM cache is properly isolated per user."""
    # Create cache entries for two different users
    cache1 = LLMCache(
        user_id='user1',
        merchant='STARBUCKS',
        category='Coffee',
        created_at=datetime.utcnow()
    )
    
    cache2 = LLMCache(
        user_id='user2',
        merchant='STARBUCKS',  # Same merchant but different user
        category='Food & Dining',  # Different category
        created_at=datetime.utcnow()
    )
    
    test_db.add(cache1)
    test_db.add(cache2)
    test_db.commit()
    
    # Query cache for each user
    cache_user1 = test_db.query(LLMCache).filter(
        LLMCache.user_id == 'user1',
        LLMCache.merchant == 'STARBUCKS'
    ).first()
    
    cache_user2 = test_db.query(LLMCache).filter(
        LLMCache.user_id == 'user2',
        LLMCache.merchant == 'STARBUCKS'
    ).first()
    
    # Each user should have their own cache
    assert cache_user1 is not None
    assert cache_user2 is not None
    assert cache_user1.category == 'Coffee'
    assert cache_user2.category == 'Food & Dining'


def test_chat_models_created(test_db):
    """Test that chat models can be created and queried."""
    # Create a chat session
    session = ChatSession(
        user_id='user1',
        title='Test Chat',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)
    
    # Create a chat message
    message = ChatMessage(
        session_id=session.id,
        role='user',
        content='Hello, AI!',
        created_at=datetime.utcnow()
    )
    test_db.add(message)
    test_db.commit()
    
    # Create a chat context
    context = ChatContext(
        session_id=session.id,
        transaction_filters={'date_range': {'from': '2025-12-01', 'to': '2025-12-31'}},
        transaction_count=100,
        transaction_summary={'total_income': 5000, 'total_expenses': 3000},
        include_categories=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    test_db.add(context)
    test_db.commit()
    
    # Create token usage
    usage = TokenUsage(
        user_id='user1',
        session_id=session.id,
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        cost_usd=Decimal('0.002'),
        created_at=datetime.utcnow()
    )
    test_db.add(usage)
    test_db.commit()
    
    # Query and verify
    retrieved_session = test_db.query(ChatSession).filter(ChatSession.id == session.id).first()
    assert retrieved_session is not None
    assert retrieved_session.title == 'Test Chat'
    assert retrieved_session.user_id == 'user1'
    
    retrieved_messages = test_db.query(ChatMessage).filter(ChatMessage.session_id == session.id).all()
    assert len(retrieved_messages) == 1
    assert retrieved_messages[0].content == 'Hello, AI!'
    
    retrieved_context = test_db.query(ChatContext).filter(ChatContext.session_id == session.id).first()
    assert retrieved_context is not None
    assert retrieved_context.transaction_count == 100
    
    retrieved_usage = test_db.query(TokenUsage).filter(TokenUsage.user_id == 'user1').all()
    assert len(retrieved_usage) == 1
    assert retrieved_usage[0].total_tokens == 150


def test_default_user_id_applied(test_db):
    """Test that default_user is used when user_id not specified (backward compatibility).
    
    Note: In the new architecture, keywords are stored in Rule model, not Category.
    """
    # Create a category without specifying user_id (should use default)
    category = Category(
        name='Test Category',
        color='#2196F3',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    test_db.add(category)
    test_db.commit()
    test_db.refresh(category)
    
    # Should have default_user as user_id
    assert category.user_id == 'default_user'


def test_cascade_delete_chat_messages(test_db):
    """Test that deleting a chat session cascades to messages and context."""
    # Create session with message and context
    session = ChatSession(
        user_id='user1',
        title='Test Chat',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)
    
    message = ChatMessage(
        session_id=session.id,
        role='user',
        content='Test message',
        created_at=datetime.utcnow()
    )
    test_db.add(message)
    
    context = ChatContext(
        session_id=session.id,
        transaction_count=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    test_db.add(context)
    test_db.commit()
    
    # Verify they exist
    assert test_db.query(ChatMessage).filter(ChatMessage.session_id == session.id).count() == 1
    assert test_db.query(ChatContext).filter(ChatContext.session_id == session.id).count() == 1
    
    # Delete session
    test_db.delete(session)
    test_db.commit()
    
    # Verify cascade delete worked
    assert test_db.query(ChatMessage).filter(ChatMessage.session_id == session.id).count() == 0
    assert test_db.query(ChatContext).filter(ChatContext.session_id == session.id).count() == 0

