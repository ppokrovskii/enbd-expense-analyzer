"""Tests for Milestone 3: Recurring Transaction Detection."""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from app.domains.recurring.service import RecurringDetectionService
from app.domains.recurring.models import Frequency, RecurringGroup
from app.domains.transactions.models import Transaction


def create_monthly_subscription(db: Session, user_id: str, merchant: str, amount: float, months: int = 6):
    """Helper to create monthly subscription transactions."""
    base_date = date.today() - timedelta(days=30 * months)
    transactions = []
    
    for i in range(months):
        txn_date = base_date + timedelta(days=30 * i + (i % 3))  # Slight variation
        txn = Transaction(
            user_id=user_id,
            date=txn_date,
            account="Credit Card",
            description=f"{merchant} SUBSCRIPTION",
            merchant=merchant,
            debit_credit="D",
            amount=Decimal(str(amount + (i % 2))),  # Slight amount variation
            amount_signed=Decimal(str(-amount - (i % 2))),
            transaction_hash=f"{merchant}_{user_id}_{i}"
        )
        db.add(txn)
        transactions.append(txn)
    
    db.commit()
    return transactions


def create_weekly_payment(db: Session, user_id: str, merchant: str, amount: float, weeks: int = 8):
    """Helper to create weekly payment transactions."""
    base_date = date.today() - timedelta(days=7 * weeks)
    transactions = []
    
    for i in range(weeks):
        txn_date = base_date + timedelta(days=7 * i)
        txn = Transaction(
            user_id=user_id,
            date=txn_date,
            account="Current",
            description=f"{merchant} PAYMENT",
            merchant=merchant,
            debit_credit="D",
            amount=Decimal(str(amount)),
            amount_signed=Decimal(str(-amount)),
            transaction_hash=f"{merchant}_{user_id}_{i}"
        )
        db.add(txn)
        transactions.append(txn)
    
    db.commit()
    return transactions


def test_detect_monthly_subscription(test_db: Session):
    """Test detection of monthly recurring subscription."""
    user_id = "test_user"
    create_monthly_subscription(test_db, user_id, "NETFLIX", 15.99, months=6)
    
    result = RecurringDetectionService.detect_patterns(test_db, user_id)
    
    assert result.total_transactions_analyzed >= 6
    assert len(result.recurring_groups) >= 1
    
    netflix_group = next((g for g in result.recurring_groups if "NETFLIX" in g.merchant.upper()), None)
    assert netflix_group is not None
    assert netflix_group.frequency == Frequency.MONTHLY
    assert netflix_group.occurrences >= 6
    assert 15 <= netflix_group.estimated_amount <= 17  # Amount with variance


def test_detect_weekly_recurring(test_db: Session):
    """Test detection of weekly recurring payment."""
    user_id = "test_user"
    create_weekly_payment(test_db, user_id, "GYM MEMBERSHIP", 25.00, weeks=8)
    
    result = RecurringDetectionService.detect_patterns(test_db, user_id)
    
    assert len(result.recurring_groups) >= 1
    
    gym_group = next((g for g in result.recurring_groups if "GYM" in g.merchant.upper()), None)
    assert gym_group is not None
    assert gym_group.frequency == Frequency.WEEKLY
    assert gym_group.occurrences >= 8


def test_no_recurring_for_random_transactions(test_db: Session):
    """Test that random transactions are not detected as recurring."""
    user_id = "test_user"
    
    # Create random, non-recurring transactions
    for i in range(10):
        txn = Transaction(
            user_id=user_id,
            date=date.today() - timedelta(days=i * 17),  # Irregular intervals
            account="Credit Card",
            description=f"RANDOM STORE {i}",
            merchant=f"STORE {i}",  # Different merchants
            debit_credit="D",
            amount=Decimal(str(50 + i * 10)),  # Different amounts
            amount_signed=Decimal(str(-50 - i * 10)),
            transaction_hash=f"random_{user_id}_{i}"
        )
        test_db.add(txn)
    test_db.commit()
    
    result = RecurringDetectionService.detect_patterns(test_db, user_id)
    
    # Should not detect any recurring patterns from random transactions
    assert len(result.recurring_groups) == 0


def test_forgotten_subscription_detection(test_db: Session):
    """Test detection of forgotten subscriptions (>60 days since last seen)."""
    user_id = "test_user"
    
    # Create subscription that stopped 90 days ago
    base_date = date.today() - timedelta(days=90 + 30 * 5)
    for i in range(6):
        txn = Transaction(
            user_id=user_id,
            date=base_date + timedelta(days=30 * i),
            account="Credit Card",
            description="OLD STREAMING SERVICE",
            merchant="OLD SERVICE",
            debit_credit="D",
            amount=Decimal("9.99"),
            amount_signed=Decimal("-9.99"),
            transaction_hash=f"old_service_{user_id}_{i}"
        )
        test_db.add(txn)
    test_db.commit()
    
    result = RecurringDetectionService.detect_patterns(test_db, user_id)
    
    old_service = next((g for g in result.recurring_groups if "OLD SERVICE" in g.merchant), None)
    assert old_service is not None
    assert old_service.forgotten == True


def test_multiple_recurring_patterns(test_db: Session):
    """Test detection of multiple different recurring patterns."""
    user_id = "test_user"
    
    # Create multiple subscriptions
    create_monthly_subscription(test_db, user_id, "NETFLIX", 15.99, months=6)
    create_monthly_subscription(test_db, user_id, "SPOTIFY", 9.99, months=5)
    create_weekly_payment(test_db, user_id, "GYM FIT", 20.00, weeks=8)
    
    result = RecurringDetectionService.detect_patterns(test_db, user_id)
    
    assert len(result.recurring_groups) >= 3
    
    # Verify each is detected
    merchants = [g.merchant for g in result.recurring_groups]
    assert any("NETFLIX" in m for m in merchants)
    assert any("SPOTIFY" in m for m in merchants)
    assert any("GYM" in m for m in merchants)


def test_user_isolation(test_db: Session):
    """Test that recurring detection is isolated per user."""
    # Create subscription for user1
    create_monthly_subscription(test_db, "user1", "USER1 SUBSCRIPTION", 10.00, months=4)
    
    # Create subscription for user2
    create_monthly_subscription(test_db, "user2", "USER2 SUBSCRIPTION", 20.00, months=4)
    
    # Check user1's recurring
    result1 = RecurringDetectionService.detect_patterns(test_db, "user1")
    merchants1 = [g.merchant for g in result1.recurring_groups]
    
    assert any("USER1" in m for m in merchants1)
    assert not any("USER2" in m for m in merchants1)
    
    # Check user2's recurring
    result2 = RecurringDetectionService.detect_patterns(test_db, "user2")
    merchants2 = [g.merchant for g in result2.recurring_groups]
    
    assert any("USER2" in m for m in merchants2)
    assert not any("USER1" in m for m in merchants2)


def test_confidence_calculation(test_db: Session):
    """Test that confidence is calculated correctly."""
    user_id = "test_user"
    
    # Create very consistent subscription (should have high confidence)
    base_date = date.today() - timedelta(days=180)
    for i in range(6):
        txn = Transaction(
            user_id=user_id,
            date=base_date + timedelta(days=30 * i),  # Exactly 30 days apart
            account="Credit Card",
            description="CONSISTENT SERVICE",
            merchant="CONSISTENT",
            debit_credit="D",
            amount=Decimal("10.00"),  # Exactly the same amount
            amount_signed=Decimal("-10.00"),
            transaction_hash=f"consistent_{user_id}_{i}"
        )
        test_db.add(txn)
    test_db.commit()
    
    result = RecurringDetectionService.detect_patterns(test_db, user_id)
    
    consistent_group = next((g for g in result.recurring_groups if "CONSISTENT" in g.merchant), None)
    assert consistent_group is not None
    assert consistent_group.confidence >= 0.8  # High confidence


def test_pattern_name_generation(test_db: Session):
    """Test that pattern names are generated correctly for known services."""
    user_id = "test_user"
    create_monthly_subscription(test_db, user_id, "NETFLIX INC", 15.99, months=4)
    
    result = RecurringDetectionService.detect_patterns(test_db, user_id)
    
    netflix_group = next((g for g in result.recurring_groups if "NETFLIX" in g.merchant.upper()), None)
    assert netflix_group is not None
    assert "Netflix" in netflix_group.pattern_name


def test_monthly_recurring_total(test_db: Session):
    """Test calculation of total monthly recurring expenses."""
    user_id = "test_user"
    
    # Create subscriptions with known amounts
    create_monthly_subscription(test_db, user_id, "SERVICE A", 10.00, months=4)
    create_monthly_subscription(test_db, user_id, "SERVICE B", 20.00, months=4)
    
    total = RecurringDetectionService.get_monthly_recurring_total(test_db, user_id)
    
    # Should be roughly 30 (10 + 20)
    assert 25 <= total <= 35


def test_min_occurrences_requirement(test_db: Session):
    """Test that single transactions are not detected as recurring."""
    user_id = "test_user"
    
    # Create just one transaction
    txn = Transaction(
        user_id=user_id,
        date=date.today(),
        account="Credit Card",
        description="SINGLE PAYMENT",
        merchant="SINGLE",
        debit_credit="D",
        amount=Decimal("100.00"),
        amount_signed=Decimal("-100.00"),
        transaction_hash=f"single_{user_id}"
    )
    test_db.add(txn)
    test_db.commit()
    
    result = RecurringDetectionService.detect_patterns(test_db, user_id)
    
    # Should not detect single transaction as recurring
    single_group = next((g for g in result.recurring_groups if "SINGLE" in g.merchant), None)
    assert single_group is None


def test_result_to_dict(test_db: Session):
    """Test that result can be serialized to dict."""
    user_id = "test_user"
    create_monthly_subscription(test_db, user_id, "TEST SERVICE", 15.00, months=4)
    
    result = RecurringDetectionService.detect_patterns(test_db, user_id)
    result_dict = result.to_dict()
    
    assert "recurring_groups" in result_dict
    assert "total_transactions_analyzed" in result_dict
    assert "summary" in result_dict
    assert "monthly_recurring_total" in result_dict["summary"]
    assert "forgotten_subscriptions" in result_dict["summary"]

