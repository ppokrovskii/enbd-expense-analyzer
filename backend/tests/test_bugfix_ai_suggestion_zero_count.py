"""
TDD test for bug: AI Suggestions page shows 0 transactions for rules.

Bug Description:
When AI suggestions are generated, the transaction_count shown is often 0,
even though the suggestion was generated FROM transactions that exist.

Root Cause:
The `ai-bulk-suggest` endpoint queries transaction stats without filtering by:
1. The date range (days parameter)
2. Only uncategorized transactions (which were the source of the suggestions)

This test reproduces the bug and verifies the fix.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock
import hashlib

from app.main import app
from app.domains.transactions.models import Transaction
from app.domains.categories.models import Category

client = TestClient(app)


def create_test_transaction(db: Session, user_id: str, merchant: str, category: str, 
                            days_ago: int = 5, amount: float = 100.0) -> Transaction:
    """Helper to create a test transaction."""
    tx_date = date.today() - timedelta(days=days_ago)
    hash_val = hashlib.md5(f"ai_bug_{user_id}_{merchant}_{days_ago}_{amount}".encode()).hexdigest()[:30]
    
    txn = Transaction(
        user_id=user_id,
        date=tx_date,
        account="Credit Card",
        description=f"{merchant} PAYMENT",
        merchant=merchant,
        category=category,
        debit_credit="D",
        amount=Decimal(str(amount)),
        amount_signed=Decimal(str(-amount)),
        transaction_hash=hash_val,
        search_text=f"{merchant} PAYMENT"
    )
    db.add(txn)
    return txn


class TestAISuggestionTransactionCount:
    """Tests for AI suggestion transaction count accuracy."""
    
    def test_suggestion_count_includes_uncategorized_transactions_in_date_range(self, test_db: Session):
        """
        REPRODUCES BUG: When suggestions are generated for merchants,
        the transaction_count should reflect the actual uncategorized transactions
        within the specified date range.
        """
        user_id = "ai_bug_user1"
        merchant = "STARBUCKS"
        
        # Create 3 recent uncategorized transactions (within 30 days)
        for i in range(3):
            create_test_transaction(test_db, user_id, merchant, "Other", days_ago=i+1, amount=10.0)
        
        # Create 2 old uncategorized transactions (outside 30-day window)
        for i in range(2):
            create_test_transaction(test_db, user_id, merchant, "Other", days_ago=40+i, amount=10.0)
        
        test_db.commit()
        
        # Mock LLM service to return a suggestion for this merchant
        with patch('app.domains.categories.router.LLMCategorizationService') as MockLLM:
            mock_instance = MagicMock()
            mock_instance.bulk_suggest_categories.return_value = [{
                "merchant": merchant,
                "category": "Food & Dining",
                "pattern": "STARBUCKS",
                "pattern_type": "keyword",
                "is_new_category": False
            }]
            MockLLM.return_value = mock_instance
            
            response = client.post(
                "/api/categories/ai-bulk-suggest",
                json={
                    "days": 30,
                    "merchants": [merchant],
                    "limit": 10
                },
                headers={"X-User-Id": user_id}
            )
        
        assert response.status_code == 200
        suggestions = response.json()
        assert len(suggestions) == 1
        
        # BUG: This was returning 5 (all transactions) or 0 (if filtered wrong)
        # FIX: Should return 3 (only recent uncategorized transactions)
        assert suggestions[0]["transaction_count"] == 3, \
            f"Expected 3 transactions within 30 days, got {suggestions[0]['transaction_count']}"
        
        # Total amount should be 30.0 (3 * 10.0)
        assert abs(suggestions[0]["total_amount"]) == 30.0, \
            f"Expected total_amount 30.0, got {suggestions[0]['total_amount']}"
    
    def test_suggestion_count_excludes_already_categorized_transactions(self, test_db: Session):
        """
        Transaction count should only include uncategorized ('Other' or null) transactions,
        not transactions that have already been assigned a category.
        """
        user_id = "ai_bug_user2"
        merchant = "CARREFOUR"
        
        # Create 2 uncategorized transactions
        for i in range(2):
            create_test_transaction(test_db, user_id, merchant, "Other", days_ago=i+1, amount=50.0)
        
        # Create 3 already-categorized transactions (should NOT be counted)
        for i in range(3):
            create_test_transaction(test_db, user_id, merchant, "Groceries", days_ago=i+5, amount=50.0)
        
        test_db.commit()
        
        with patch('app.domains.categories.router.LLMCategorizationService') as MockLLM:
            mock_instance = MagicMock()
            mock_instance.bulk_suggest_categories.return_value = [{
                "merchant": merchant,
                "category": "Groceries",
                "pattern": "CARREFOUR",
                "pattern_type": "keyword",
                "is_new_category": False
            }]
            MockLLM.return_value = mock_instance
            
            response = client.post(
                "/api/categories/ai-bulk-suggest",
                json={
                    "days": 30,
                    "merchants": [merchant],
                    "limit": 10
                },
                headers={"X-User-Id": user_id}
            )
        
        assert response.status_code == 200
        suggestions = response.json()
        assert len(suggestions) == 1
        
        # Should only count uncategorized transactions
        assert suggestions[0]["transaction_count"] == 2, \
            f"Expected 2 uncategorized transactions, got {suggestions[0]['transaction_count']}"
    
    def test_suggestion_count_handles_null_category(self, test_db: Session):
        """
        Transactions with NULL category (not just 'Other') should also be counted.
        """
        user_id = "ai_bug_user3"
        merchant = "UBER"
        
        # Create transaction with NULL category
        txn = create_test_transaction(test_db, user_id, merchant, None, days_ago=2, amount=25.0)
        
        # Create transaction with empty string category
        txn2 = create_test_transaction(test_db, user_id, merchant, "", days_ago=3, amount=25.0)
        
        # Create transaction with 'Other' category
        txn3 = create_test_transaction(test_db, user_id, merchant, "Other", days_ago=4, amount=25.0)
        
        test_db.commit()
        
        with patch('app.domains.categories.router.LLMCategorizationService') as MockLLM:
            mock_instance = MagicMock()
            mock_instance.bulk_suggest_categories.return_value = [{
                "merchant": merchant,
                "category": "Transport",
                "pattern": "UBER",
                "pattern_type": "keyword",
                "is_new_category": False
            }]
            MockLLM.return_value = mock_instance
            
            response = client.post(
                "/api/categories/ai-bulk-suggest",
                json={
                    "days": 30,
                    "merchants": [merchant],
                    "limit": 10
                },
                headers={"X-User-Id": user_id}
            )
        
        assert response.status_code == 200
        suggestions = response.json()
        assert len(suggestions) == 1
        
        # All 3 should be counted (NULL, empty string, and 'Other')
        assert suggestions[0]["transaction_count"] == 3, \
            f"Expected 3 uncategorized transactions (including NULL and empty), got {suggestions[0]['transaction_count']}"
    
    def test_suggestion_count_zero_when_no_matching_transactions(self, test_db: Session):
        """
        If a merchant is passed but has no matching uncategorized transactions
        in the date range, the count should be 0 (this is valid).
        """
        user_id = "ai_bug_user4"
        merchant = "NONEXISTENT_SHOP"
        
        # No transactions created for this merchant
        test_db.commit()
        
        with patch('app.domains.categories.router.LLMCategorizationService') as MockLLM:
            mock_instance = MagicMock()
            mock_instance.bulk_suggest_categories.return_value = [{
                "merchant": merchant,
                "category": "Shopping",
                "pattern": "NONEXISTENT_SHOP",
                "pattern_type": "keyword",
                "is_new_category": False
            }]
            MockLLM.return_value = mock_instance
            
            response = client.post(
                "/api/categories/ai-bulk-suggest",
                json={
                    "days": 30,
                    "merchants": [merchant],
                    "limit": 10
                },
                headers={"X-User-Id": user_id}
            )
        
        assert response.status_code == 200
        suggestions = response.json()
        assert len(suggestions) == 1
        
        # 0 is valid here since no transactions exist
        assert suggestions[0]["transaction_count"] == 0

