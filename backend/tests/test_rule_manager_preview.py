"""Integration tests for Rule Manager Preview API (Milestone 1)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import date, timedelta

from app.main import app
from app.domains.transactions.models import Transaction
from app.domains.categories.models import Category, Rule

client = TestClient(app)


class TestRulePreviewAPI:
    """Tests for POST /api/rules/test endpoint."""
    
    def test_preview_returns_matching_merchants(self, test_db):
        """Rule preview returns merchants that match the keywords."""
        # Create test transactions
        txns = [
            Transaction(
                user_id="test_user",
                date=date.today() - timedelta(days=5),
                account="Test Account",
                description="STARBUCKS DUBAI",
                details="Coffee purchase",
                amount=Decimal("25.00"),
                amount_signed=Decimal("-25.00"),
                category=None,
                search_text="Coffee purchase STARBUCKS DUBAI",
                transaction_hash="hash_starbucks_1",
                merchant="STARBUCKS DUBAI"
            ),
            Transaction(
                user_id="test_user",
                date=date.today() - timedelta(days=3),
                account="Test Account",
                description="STARBUCKS JBR",
                details="Coffee",
                amount=Decimal("30.00"),
                amount_signed=Decimal("-30.00"),
                category=None,
                search_text="Coffee STARBUCKS JBR",
                transaction_hash="hash_starbucks_2",
                merchant="STARBUCKS JBR"
            ),
            Transaction(
                user_id="test_user",
                date=date.today() - timedelta(days=1),
                account="Test Account",
                description="CARREFOUR",
                details="Groceries",
                amount=Decimal("150.00"),
                amount_signed=Decimal("-150.00"),
                category=None,
                search_text="Groceries CARREFOUR",
                transaction_hash="hash_carrefour_1",
                merchant="CARREFOUR"
            ),
        ]
        test_db.add_all(txns)
        test_db.commit()
        
        response = client.post(
            "/api/rules/test",
            json={"keywords": ["STARBUCKS"], "exclude_keywords": []},
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["match_count"] == 2  # Two different Starbucks merchants
        assert data["total_transactions"] == 2
        assert len(data["matching_merchants"]) == 2
        
        # Check merchants are included
        merchant_names = [m["merchant"] for m in data["matching_merchants"]]
        assert "STARBUCKS DUBAI" in merchant_names
        assert "STARBUCKS JBR" in merchant_names
        assert "CARREFOUR" not in merchant_names
    
    def test_preview_exclude_keywords_filter(self, test_db):
        """Exclude keywords filter out matching merchants correctly."""
        txns = [
            Transaction(
                user_id="test_user",
                date=date.today() - timedelta(days=5),
                account="Test Account",
                description="STARBUCKS PURCHASE",
                details="Coffee",
                amount=Decimal("25.00"),
                amount_signed=Decimal("-25.00"),
                category=None,
                search_text="Coffee STARBUCKS PURCHASE",
                transaction_hash="hash_sb_purchase",
                merchant="STARBUCKS"
            ),
            Transaction(
                user_id="test_user",
                date=date.today() - timedelta(days=3),
                account="Test Account",
                description="STARBUCKS REFUND",
                details="Return",
                amount=Decimal("25.00"),
                amount_signed=Decimal("25.00"),
                category=None,
                search_text="Return STARBUCKS REFUND",
                transaction_hash="hash_sb_refund",
                merchant="STARBUCKS REFUND"
            ),
        ]
        test_db.add_all(txns)
        test_db.commit()
        
        # Without exclude
        response = client.post(
            "/api/rules/test",
            json={"keywords": ["STARBUCKS"], "exclude_keywords": []},
            headers={"X-User-Id": "test_user"}
        )
        assert response.status_code == 200
        assert response.json()["total_transactions"] == 2
        
        # With exclude
        response = client.post(
            "/api/rules/test",
            json={"keywords": ["STARBUCKS"], "exclude_keywords": ["REFUND"]},
            headers={"X-User-Id": "test_user"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_transactions"] == 1
        assert data["matching_merchants"][0]["merchant"] == "STARBUCKS"
    
    def test_preview_empty_pattern_returns_empty(self, test_db):
        """Empty pattern returns empty results."""
        # Create a transaction
        txn = Transaction(
            user_id="test_user",
            date=date.today(),
            account="Test",
            description="TEST",
            details="Test",
            amount=Decimal("10.00"),
            amount_signed=Decimal("-10.00"),
            category=None,
            search_text="Test TEST",
            transaction_hash="hash_empty_test",
            merchant="TEST"
        )
        test_db.add(txn)
        test_db.commit()
        
        response = client.post(
            "/api/rules/test",
            json={"keywords": [], "exclude_keywords": []},
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["match_count"] == 0
        assert data["total_transactions"] == 0
        assert data["matching_merchants"] == []
    
    def test_preview_or_patterns(self, test_db):
        """Pipe-separated OR patterns match correctly."""
        txns = [
            Transaction(
                user_id="test_user",
                date=date.today() - timedelta(days=5),
                account="Test Account",
                description="COSTA COFFEE",
                details="Coffee shop",
                amount=Decimal("20.00"),
                amount_signed=Decimal("-20.00"),
                category=None,
                search_text="Coffee shop COSTA COFFEE",
                transaction_hash="hash_costa",
                merchant="COSTA COFFEE"
            ),
            Transaction(
                user_id="test_user",
                date=date.today() - timedelta(days=3),
                account="Test Account",
                description="STARBUCKS",
                details="Cafe",
                amount=Decimal("25.00"),
                amount_signed=Decimal("-25.00"),
                category=None,
                search_text="Cafe STARBUCKS",
                transaction_hash="hash_starbucks_or",
                merchant="STARBUCKS"
            ),
            Transaction(
                user_id="test_user",
                date=date.today() - timedelta(days=1),
                account="Test Account",
                description="RESTAURANT",
                details="Lunch",
                amount=Decimal("100.00"),
                amount_signed=Decimal("-100.00"),
                category=None,
                search_text="Lunch RESTAURANT",
                transaction_hash="hash_restaurant",
                merchant="RESTAURANT"
            ),
        ]
        test_db.add_all(txns)
        test_db.commit()
        
        response = client.post(
            "/api/rules/test",
            json={"keywords": ["STARBUCKS|COSTA"], "exclude_keywords": []},
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["match_count"] == 2
        assert data["total_transactions"] == 2
        
        merchant_names = [m["merchant"] for m in data["matching_merchants"]]
        assert "COSTA COFFEE" in merchant_names
        assert "STARBUCKS" in merchant_names
        assert "RESTAURANT" not in merchant_names
    
    def test_preview_case_insensitive(self, test_db):
        """Pattern matching is case insensitive."""
        txn = Transaction(
            user_id="test_user",
            date=date.today(),
            account="Test",
            description="starbucks coffee",
            details="cafe",
            amount=Decimal("25.00"),
            amount_signed=Decimal("-25.00"),
            category=None,
            search_text="cafe starbucks coffee",
            transaction_hash="hash_case_test",
            merchant="Starbucks Coffee"
        )
        test_db.add(txn)
        test_db.commit()
        
        response = client.post(
            "/api/rules/test",
            json={"keywords": ["STARBUCKS"], "exclude_keywords": []},
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["match_count"] == 1
        assert data["matching_merchants"][0]["merchant"] == "Starbucks Coffee"
    
    def test_preview_includes_sample_transactions(self, test_db):
        """Preview includes sample transactions with matched text."""
        txn = Transaction(
            user_id="test_user",
            date=date.today(),
            account="Test",
            description="STARBUCKS MALL",
            details="Coffee purchase",
            amount=Decimal("35.00"),
            amount_signed=Decimal("-35.00"),
            category=None,
            search_text="Coffee purchase STARBUCKS MALL",
            transaction_hash="hash_sample_test",
            merchant="STARBUCKS MALL"
        )
        test_db.add(txn)
        test_db.commit()
        
        response = client.post(
            "/api/rules/test",
            json={"keywords": ["STARBUCKS"], "exclude_keywords": []},
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["sample_transactions"]) == 1
        sample = data["sample_transactions"][0]
        assert sample["merchant"] == "STARBUCKS MALL"
        assert sample["matched_text"] == "STARBUCKS"
        assert sample["amount"] == -35.0
    
    def test_preview_respects_user_isolation(self, test_db):
        """Preview only shows transactions for the current user."""
        # Create transactions for two different users
        txn1 = Transaction(
            user_id="user1",
            date=date.today(),
            account="Test",
            description="STARBUCKS",
            details="Coffee",
            amount=Decimal("25.00"),
            amount_signed=Decimal("-25.00"),
            category=None,
            search_text="Coffee STARBUCKS",
            transaction_hash="hash_user1",
            merchant="STARBUCKS"
        )
        txn2 = Transaction(
            user_id="user2",
            date=date.today(),
            account="Test",
            description="STARBUCKS OTHER",
            details="Coffee",
            amount=Decimal("30.00"),
            amount_signed=Decimal("-30.00"),
            category=None,
            search_text="Coffee STARBUCKS OTHER",
            transaction_hash="hash_user2",
            merchant="STARBUCKS OTHER"
        )
        test_db.add_all([txn1, txn2])
        test_db.commit()
        
        # User 1 should only see their transaction
        response = client.post(
            "/api/rules/test",
            json={"keywords": ["STARBUCKS"], "exclude_keywords": []},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["match_count"] == 1
        assert data["matching_merchants"][0]["merchant"] == "STARBUCKS"
    
    def test_preview_date_range_filter(self, test_db):
        """Preview respects date range filters."""
        # Transaction within range
        txn_recent = Transaction(
            user_id="test_user",
            date=date.today() - timedelta(days=5),
            account="Test",
            description="STARBUCKS",
            details="Coffee",
            amount=Decimal("25.00"),
            amount_signed=Decimal("-25.00"),
            category=None,
            search_text="Coffee STARBUCKS",
            transaction_hash="hash_recent",
            merchant="STARBUCKS"
        )
        # Transaction outside range
        txn_old = Transaction(
            user_id="test_user",
            date=date.today() - timedelta(days=100),
            account="Test",
            description="STARBUCKS OLD",
            details="Coffee",
            amount=Decimal("20.00"),
            amount_signed=Decimal("-20.00"),
            category=None,
            search_text="Coffee STARBUCKS OLD",
            transaction_hash="hash_old",
            merchant="STARBUCKS OLD"
        )
        test_db.add_all([txn_recent, txn_old])
        test_db.commit()
        
        # With explicit date range
        start_date = (date.today() - timedelta(days=30)).isoformat()
        end_date = date.today().isoformat()
        
        response = client.post(
            "/api/rules/test",
            json={
                "keywords": ["STARBUCKS"],
                "exclude_keywords": [],
                "start_date": start_date,
                "end_date": end_date
            },
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["match_count"] == 1
        assert data["matching_merchants"][0]["merchant"] == "STARBUCKS"

