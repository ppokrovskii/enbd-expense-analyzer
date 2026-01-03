"""Tests for rule application background job."""
import pytest
import hashlib
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.main import app
from app.domains.transactions.models import Transaction
from app.domains.categories.models import Category, Rule
from app.domains.jobs.models import BackgroundJob
from app.domains.jobs.service import JobService


client = TestClient(app)


def create_test_category(db: Session, user_id: str, name: str, color: str = "#000000") -> Category:
    """Helper to create a test category."""
    category = Category(user_id=user_id, name=name, color=color)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def create_test_rule(db: Session, user_id: str, category_id: int, keywords: list, priority: int = 1) -> Rule:
    """Helper to create a test rule."""
    rule = Rule(
        user_id=user_id,
        category_id=category_id,
        keywords=keywords,
        priority=priority
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def create_uncategorized_transactions(
    db: Session, 
    user_id: str, 
    merchant: str,
    count: int = 5
) -> list:
    """Helper to create uncategorized transactions."""
    transactions = []
    start_date = date.today() - timedelta(days=30)
    
    for i in range(count):
        hash_val = hashlib.md5(f"rule_test_{user_id}_{merchant}_{i}".encode()).hexdigest()[:30]
        txn = Transaction(
            user_id=user_id,
            date=start_date + timedelta(days=i),
            account="Credit Card",
            description=f"{merchant} PAYMENT",
            merchant=merchant,
            category="Other",  # Uncategorized
            debit_credit="D",
            amount=Decimal("50.00"),
            amount_signed=Decimal("-50.00"),
            transaction_hash=hash_val,
            search_text=f"{merchant} PAYMENT"
        )
        db.add(txn)
        transactions.append(txn)
    
    db.commit()
    return transactions


def test_apply_rules_endpoint(test_db: Session):
    """Test the apply-rules endpoint."""
    user_id = "rule_apply_user"
    
    # Create category and rule
    category = create_test_category(test_db, user_id, "Groceries")
    rule = create_test_rule(test_db, user_id, category.id, ["CARREFOUR", "SPINNEYS"])
    
    # Create uncategorized transactions
    create_uncategorized_transactions(test_db, user_id, "CARREFOUR", 3)
    create_uncategorized_transactions(test_db, user_id, "RANDOM SHOP", 2)
    
    # Call apply-rules endpoint with sync=true for testing
    response = client.post(
        "/api/jobs/apply-rules?sync=true",
        json={"rule_ids": [rule.id]},
        headers={"X-User-Id": user_id}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["rule_count"] == 1
    assert "job_id" in data
    
    # Verify job in database
    job_id = data["job_id"]
    job = test_db.query(BackgroundJob).filter_by(id=job_id).first()
    
    assert job.status == "completed"
    assert job.result["transactions_updated"] == 3  # Only CARREFOUR transactions
    assert job.result["by_category"]["Groceries"] == 3


def test_apply_multiple_rules(test_db: Session):
    """Test applying multiple rules at once."""
    user_id = "multi_rule_user"
    
    # Create categories and rules
    groceries = create_test_category(test_db, user_id, "Groceries")
    transport = create_test_category(test_db, user_id, "Transport")
    
    rule1 = create_test_rule(test_db, user_id, groceries.id, ["CARREFOUR"])
    rule2 = create_test_rule(test_db, user_id, transport.id, ["RTA", "SALIK"])
    
    # Create transactions
    create_uncategorized_transactions(test_db, user_id, "CARREFOUR", 3)
    create_uncategorized_transactions(test_db, user_id, "RTA", 2)
    create_uncategorized_transactions(test_db, user_id, "UNMATCHED", 5)
    
    # Apply both rules (sync for testing)
    response = client.post(
        "/api/jobs/apply-rules?sync=true",
        json={"rule_ids": [rule1.id, rule2.id]},
        headers={"X-User-Id": user_id}
    )
    
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    
    job = test_db.query(BackgroundJob).filter_by(id=job_id).first()
    
    assert job.status == "completed"
    assert job.result["transactions_updated"] == 5  # 3 + 2
    assert job.result["by_category"]["Groceries"] == 3
    assert job.result["by_category"]["Transport"] == 2


def test_apply_rules_no_matches(test_db: Session):
    """Test applying rules when no transactions match."""
    user_id = "no_match_user"
    
    # Create category and rule
    category = create_test_category(test_db, user_id, "Rare Category")
    rule = create_test_rule(test_db, user_id, category.id, ["NONEXISTENT_MERCHANT"])
    
    # Create transactions that won't match
    create_uncategorized_transactions(test_db, user_id, "DIFFERENT SHOP", 3)
    
    response = client.post(
        "/api/jobs/apply-rules?sync=true",
        json={"rule_ids": [rule.id]},
        headers={"X-User-Id": user_id}
    )
    
    job_id = response.json()["job_id"]
    job = test_db.query(BackgroundJob).filter_by(id=job_id).first()
    
    assert job.status == "completed"
    assert job.result["transactions_updated"] == 0


def test_apply_rules_empty_list(test_db: Session):
    """Test that empty rule list returns error."""
    response = client.post(
        "/api/jobs/apply-rules",
        json={"rule_ids": []},
        headers={"X-User-Id": "test_user"}
    )
    
    assert response.status_code == 400
    assert "rule_id" in response.json()["detail"].lower()


def test_apply_rules_invalid_rule_ids(test_db: Session):
    """Test applying rules with invalid rule IDs."""
    user_id = "invalid_rule_user"
    
    # Create some transactions
    create_uncategorized_transactions(test_db, user_id, "SHOP", 3)
    
    response = client.post(
        "/api/jobs/apply-rules?sync=true",
        json={"rule_ids": [99999, 99998]},  # Non-existent rule IDs
        headers={"X-User-Id": user_id}
    )
    
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    
    job = test_db.query(BackgroundJob).filter_by(id=job_id).first()
    
    assert job.status == "completed"
    assert job.result["transactions_updated"] == 0
    assert "No valid rules" in job.result.get("message", "")


def test_apply_rules_only_affects_other_category(test_db: Session):
    """Test that only 'Other'/uncategorized transactions are affected."""
    user_id = "other_only_user"
    
    category = create_test_category(test_db, user_id, "Groceries")
    rule = create_test_rule(test_db, user_id, category.id, ["SHOP"])
    
    # Create some "Other" transactions
    create_uncategorized_transactions(test_db, user_id, "SHOP A", 2)
    
    # Create some already-categorized transactions
    for i in range(3):
        hash_val = hashlib.md5(f"already_cat_{user_id}_{i}".encode()).hexdigest()[:30]
        txn = Transaction(
            user_id=user_id,
            date=date.today(),
            account="Card",
            description="SHOP B",
            merchant="SHOP B",
            category="Dining",  # Already categorized
            debit_credit="D",
            amount=Decimal("50.00"),
            amount_signed=Decimal("-50.00"),
            transaction_hash=hash_val,
            search_text="SHOP B"
        )
        test_db.add(txn)
    test_db.commit()
    
    response = client.post(
        "/api/jobs/apply-rules?sync=true",
        json={"rule_ids": [rule.id]},
        headers={"X-User-Id": user_id}
    )
    
    job_id = response.json()["job_id"]
    job = test_db.query(BackgroundJob).filter_by(id=job_id).first()
    
    # Only the 2 "Other" transactions should be updated
    assert job.result["transactions_updated"] == 2
    
    # Verify Dining transactions are unchanged
    dining_txns = test_db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.category == "Dining"
    ).count()
    assert dining_txns == 3


def test_rule_priority_respected(test_db: Session):
    """Test that higher priority rules are applied first."""
    user_id = "priority_user"
    
    low_priority_cat = create_test_category(test_db, user_id, "Generic Shopping")
    high_priority_cat = create_test_category(test_db, user_id, "Electronics")
    
    # Low priority rule - matches "STORE"
    low_rule = create_test_rule(test_db, user_id, low_priority_cat.id, ["STORE"], priority=1)
    # High priority rule - matches "ELECTRONICS STORE"
    high_rule = create_test_rule(test_db, user_id, high_priority_cat.id, ["ELECTRONICS"], priority=10)
    
    # Create transaction that matches both
    hash_val = hashlib.md5(f"priority_test_{user_id}".encode()).hexdigest()[:30]
    txn = Transaction(
        user_id=user_id,
        date=date.today(),
        account="Card",
        description="ELECTRONICS STORE",
        merchant="ELECTRONICS STORE",
        category="Other",
        debit_credit="D",
        amount=Decimal("500.00"),
        amount_signed=Decimal("-500.00"),
        transaction_hash=hash_val,
        search_text="ELECTRONICS STORE"
    )
    test_db.add(txn)
    test_db.commit()
    
    response = client.post(
        "/api/jobs/apply-rules?sync=true",
        json={"rule_ids": [low_rule.id, high_rule.id]},
        headers={"X-User-Id": user_id}
    )
    
    # Refresh transaction
    test_db.refresh(txn)
    
    # High priority rule should win
    assert txn.category == "Electronics"

