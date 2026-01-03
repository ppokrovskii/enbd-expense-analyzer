"""
TDD tests for user isolation in AI categorization endpoints.

Bug: The ai-bulk-suggest and ai-bulk-apply endpoints don't filter by user_id,
potentially exposing or modifying transactions from other users.

This is a critical security/data isolation issue.
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
    hash_val = hashlib.md5(f"isolation_{user_id}_{merchant}_{days_ago}_{amount}".encode()).hexdigest()[:30]
    
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


class TestUserIsolationAISuggest:
    """Tests for user isolation in ai-bulk-suggest endpoint."""
    
    def test_ai_suggest_only_sees_own_transactions(self, test_db: Session):
        """
        User A should only see suggestions based on their own transactions,
        not transactions from User B.
        """
        user_a = "user_isolation_a"
        user_b = "user_isolation_b"
        
        # Create transactions for User A
        for i in range(3):
            create_test_transaction(test_db, user_a, "STARBUCKS", "Other", days_ago=i+1, amount=10.0)
        
        # Create transactions for User B (different merchant)
        for i in range(5):
            create_test_transaction(test_db, user_b, "COSTA", "Other", days_ago=i+1, amount=20.0)
        
        test_db.commit()
        
        with patch('app.domains.categories.router.LLMCategorizationService') as MockLLM:
            mock_instance = MagicMock()
            mock_instance.bulk_suggest_categories.return_value = [{
                "merchant": "STARBUCKS",
                "category": "Food & Dining",
                "pattern": "STARBUCKS",
                "pattern_type": "keyword",
                "is_new_category": False
            }]
            MockLLM.return_value = mock_instance
            
            # User A requests suggestions
            response = client.post(
                "/api/categories/ai-bulk-suggest",
                json={
                    "days": 30,
                    "merchants": ["STARBUCKS"],
                    "limit": 10
                },
                headers={"X-User-Id": user_a}
            )
        
        assert response.status_code == 200
        suggestions = response.json()
        
        # User A should only see their 3 transactions for STARBUCKS
        assert len(suggestions) == 1
        assert suggestions[0]["transaction_count"] == 3, \
            f"Expected 3 (User A only), got {suggestions[0]['transaction_count']}"
    
    def test_ai_suggest_with_shared_merchant_isolates_users(self, test_db: Session):
        """
        If both users have transactions at the same merchant,
        each user should only see their own transaction counts.
        """
        user_a = "user_shared_a"
        user_b = "user_shared_b"
        shared_merchant = "CARREFOUR"
        
        # Create 2 transactions for User A
        for i in range(2):
            create_test_transaction(test_db, user_a, shared_merchant, "Other", days_ago=i+1, amount=50.0)
        
        # Create 5 transactions for User B (same merchant!)
        for i in range(5):
            create_test_transaction(test_db, user_b, shared_merchant, "Other", days_ago=i+1, amount=100.0)
        
        test_db.commit()
        
        with patch('app.domains.categories.router.LLMCategorizationService') as MockLLM:
            mock_instance = MagicMock()
            mock_instance.bulk_suggest_categories.return_value = [{
                "merchant": shared_merchant,
                "category": "Groceries",
                "pattern": "CARREFOUR",
                "pattern_type": "keyword",
                "is_new_category": False
            }]
            MockLLM.return_value = mock_instance
            
            # User A requests suggestions
            response_a = client.post(
                "/api/categories/ai-bulk-suggest",
                json={
                    "days": 30,
                    "merchants": [shared_merchant],
                    "limit": 10
                },
                headers={"X-User-Id": user_a}
            )
            
            # User B requests suggestions
            response_b = client.post(
                "/api/categories/ai-bulk-suggest",
                json={
                    "days": 30,
                    "merchants": [shared_merchant],
                    "limit": 10
                },
                headers={"X-User-Id": user_b}
            )
        
        assert response_a.status_code == 200
        assert response_b.status_code == 200
        
        suggestions_a = response_a.json()
        suggestions_b = response_b.json()
        
        # User A should see 2 transactions
        assert suggestions_a[0]["transaction_count"] == 2, \
            f"User A expected 2, got {suggestions_a[0]['transaction_count']}"
        assert abs(suggestions_a[0]["total_amount"]) == 100.0  # 2 * 50
        
        # User B should see 5 transactions
        assert suggestions_b[0]["transaction_count"] == 5, \
            f"User B expected 5, got {suggestions_b[0]['transaction_count']}"
        assert abs(suggestions_b[0]["total_amount"]) == 500.0  # 5 * 100


class TestUserIsolationAIApply:
    """Tests for user isolation in ai-bulk-apply endpoint."""
    
    def test_ai_apply_only_affects_own_transactions(self, test_db: Session):
        """
        When User A applies a category suggestion, it should only
        update User A's transactions, not User B's.
        """
        user_a = "user_apply_a"
        user_b = "user_apply_b"
        merchant = "UBER"
        
        # Create Transport category for User A
        transport_category = Category(user_id=user_a, name="Transport")
        test_db.add(transport_category)
        
        # Create uncategorized transactions for both users
        for i in range(3):
            create_test_transaction(test_db, user_a, merchant, "Other", days_ago=i+1, amount=25.0)
        
        for i in range(4):
            create_test_transaction(test_db, user_b, merchant, "Other", days_ago=i+1, amount=30.0)
        
        test_db.commit()
        
        # User A applies a suggestion
        response = client.post(
            "/api/categories/ai-bulk-apply",
            json={
                "suggestions": [{
                    "merchant": merchant,
                    "category": "Transport",
                    "pattern": "UBER",
                    "create_new_category": False
                }],
                "auto_create_rules": False
            },
            headers={"X-User-Id": user_a}
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Only User A's 3 transactions should be affected
        assert result["transactions_affected"] == 3, \
            f"Expected 3 (User A only), got {result['transactions_affected']}"
        
        # Verify User A's transactions are categorized
        user_a_transactions = test_db.query(Transaction).filter(
            Transaction.user_id == user_a,
            Transaction.merchant == merchant
        ).all()
        for txn in user_a_transactions:
            assert txn.category == "Transport", f"User A transaction should be Transport, got {txn.category}"
        
        # Verify User B's transactions are UNCHANGED
        user_b_transactions = test_db.query(Transaction).filter(
            Transaction.user_id == user_b,
            Transaction.merchant == merchant
        ).all()
        for txn in user_b_transactions:
            assert txn.category == "Other", f"User B transaction should be Other, got {txn.category}"


class TestUserIsolationApplyRulesJob:
    """Tests for user isolation in apply-rules job endpoint."""
    
    def test_apply_rules_job_only_affects_own_transactions(self, test_db: Session):
        """
        When User A runs apply-rules job, it should only
        recategorize User A's transactions.
        """
        user_a = "user_job_a"
        user_b = "user_job_b"
        
        # Create a category and rule for User A
        category_a = Category(user_id=user_a, name="Groceries A")
        test_db.add(category_a)
        test_db.commit()
        test_db.refresh(category_a)
        
        from app.domains.categories.models import Rule
        rule_a = Rule(user_id=user_a, category_id=category_a.id, keywords=["CARREFOUR"])
        test_db.add(rule_a)
        
        # Create uncategorized transactions for both users
        for i in range(2):
            create_test_transaction(test_db, user_a, "CARREFOUR", "Other", days_ago=i+1, amount=50.0)
        
        for i in range(3):
            create_test_transaction(test_db, user_b, "CARREFOUR", "Other", days_ago=i+1, amount=60.0)
        
        test_db.commit()
        
        # User A runs apply-rules job (sync mode for testing)
        response = client.post(
            f"/api/jobs/apply-rules?sync=true",
            json={"rule_ids": [rule_a.id]},
            headers={"X-User-Id": user_a}
        )
        
        assert response.status_code == 200
        
        # Wait for job and check results
        job_id = response.json()["job_id"]
        from app.domains.jobs.models import BackgroundJob
        job = test_db.query(BackgroundJob).filter_by(id=job_id).first()
        
        # Only User A's 2 transactions should be affected
        assert job.result["transactions_updated"] == 2, \
            f"Expected 2 (User A only), got {job.result['transactions_updated']}"
        
        # Verify User B's transactions are UNCHANGED
        user_b_transactions = test_db.query(Transaction).filter(
            Transaction.user_id == user_b,
            Transaction.merchant == "CARREFOUR"
        ).all()
        for txn in user_b_transactions:
            assert txn.category == "Other", f"User B transaction should be Other, got {txn.category}"

