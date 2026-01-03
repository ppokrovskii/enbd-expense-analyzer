"""Tests for Milestone 5: LLM categorization with caching."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.llm_service import LLMCategorizationService
from app.models import Transaction, LLMCache
from sqlalchemy.orm import Session
from datetime import date
from decimal import Decimal


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    with patch('openai.OpenAI') as mock:
        client_instance = MagicMock()
        mock.return_value = client_instance
        
        # Mock the chat completions response
        def mock_create(**kwargs):
            merchant = kwargs['messages'][1]['content']
            
            # Simple rule-based mock responses
            if 'CARREFOUR' in merchant:
                category = 'Groceries'
            elif 'UBER' in merchant:
                category = 'Transportation'
            elif 'NETFLIX' in merchant:
                category = 'Entertainment'
            else:
                category = 'Other'
            
            response = MagicMock()
            response.choices = [MagicMock()]
            response.choices[0].message.content = category
            return response
        
        client_instance.chat.completions.create = Mock(side_effect=mock_create)
        yield client_instance


def test_llm_service_initialization(test_db: Session, mock_openai_client):
    """Test LLM service can be initialized with API key."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        service = LLMCategorizationService(test_db)
        assert service.api_key == 'test-key'
        assert service.model in ['gpt-4o', 'gpt-5.2']  # Default models


def test_llm_service_requires_api_key(test_db: Session):
    """Test LLM service raises error if no API key."""
    # Clear OPENAI_API_KEY but keep other env vars
    import os
    orig_key = os.environ.pop('OPENAI_API_KEY', None)
    try:
        with pytest.raises(ValueError, match="OpenAI API key not found"):
            LLMCategorizationService(test_db)
    finally:
        if orig_key:
            os.environ['OPENAI_API_KEY'] = orig_key


def test_categorize_with_llm(test_db: Session, mock_openai_client):
    """Test basic LLM categorization."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        service = LLMCategorizationService(test_db)
        
        category = service.categorize_with_llm('CARREFOUR HYPERMARKET')
        assert category == 'Groceries'
        
        category = service.categorize_with_llm('UBER TRIP')
        assert category == 'Transportation'


def test_cache_category(test_db: Session, mock_openai_client):
    """Test caching mechanism."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        service = LLMCategorizationService(test_db)
        
        # Cache a category
        service.cache_category('CARREFOUR', 'Groceries', test_db)
        
        # Retrieve from cache
        cached = service.get_cached_category('CARREFOUR', test_db)
        assert cached == 'Groceries'
        
        # Non-existent merchant
        cached = service.get_cached_category('UNKNOWN', test_db)
        assert cached is None


def test_categorize_uncategorized_transactions(test_db: Session, mock_openai_client):
    """Test categorizing 'Other' transactions with LLM."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        # Insert test transactions
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
            merchant='CARREFOUR HYPERMARKET',  # Duplicate merchant
            amount=Decimal('75.00'),
            transaction_hash='hash3',
            category='Other'
        )
        trans4 = Transaction(
            date=date(2025, 12, 4),
            account='Current Account',
            merchant='SPINNEYS',  # Already categorized
            amount=Decimal('60.00'),
            transaction_hash='hash4',
            category='Groceries'  # Not "Other"
        )
        test_db.add_all([trans1, trans2, trans3, trans4])
        test_db.commit()
        
        # Run categorization
        service = LLMCategorizationService(test_db)
        stats = service.categorize_uncategorized_transactions(test_db)
        
        # Check stats
        assert stats['processed'] == 3  # trans1, trans2, trans3 (trans4 not "Other")
        assert stats['llm_calls'] == 2  # Only 2 unique merchants (CARREFOUR, UBER)
        assert stats['cached'] == 0  # First run, nothing cached yet
        assert stats['categorized'] == 3  # All 3 "Other" transactions categorized
        
        # Check database updates
        test_db.refresh(trans1)
        test_db.refresh(trans2)
        test_db.refresh(trans3)
        test_db.refresh(trans4)
        
        assert trans1.category == 'Groceries'
        assert trans2.category == 'Transportation'
        assert trans3.category == 'Groceries'  # Same as trans1
        assert trans4.category == 'Groceries'  # Unchanged
        
        # Check cache
        assert service.get_cached_category('CARREFOUR HYPERMARKET', test_db) == 'Groceries'
        assert service.get_cached_category('UBER TRIP', test_db) == 'Transportation'


def test_categorize_uses_cache_on_second_run(test_db: Session, mock_openai_client):
    """Test that second run uses cache instead of calling LLM."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        service = LLMCategorizationService(test_db)
        
        # Pre-populate cache
        service.cache_category('CARREFOUR', 'Groceries', test_db)
        
        # Insert transactions
        trans = Transaction(
            date=date(2025, 12, 1),
            account='Current Account',
            merchant='CARREFOUR',
            amount=Decimal('100.00'),
            transaction_hash='hash1',
            category='Other'
        )
        test_db.add(trans)
        test_db.commit()
        
        # Run categorization
        stats = service.categorize_uncategorized_transactions(test_db)
        
        # Should use cache, not call LLM
        assert stats['llm_calls'] == 0
        assert stats['cached'] == 1
        assert stats['categorized'] == 1
        
        test_db.refresh(trans)
        assert trans.category == 'Groceries'

