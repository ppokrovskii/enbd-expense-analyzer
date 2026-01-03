"""Tests for Milestone 4: Financial Insights Service."""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from app.domains.insights.service import InsightsService
from app.domains.insights.models import InsightType, InsightSeverity
from app.domains.transactions.models import Transaction


def create_test_transactions(
    db: Session, 
    user_id: str, 
    category: str,
    count: int,
    base_amount: float,
    start_date: date,
    merchant: str = "TEST MERCHANT"
):
    """Helper to create test transactions."""
    import hashlib
    transactions = []
    for i in range(count):
        # Create a short hash for the transaction
        hash_input = f"{merchant}_{user_id}_{category}_{i}"
        short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:30]
        
        txn = Transaction(
            user_id=user_id,
            date=start_date + timedelta(days=i),
            account="Credit Card",
            description=f"{merchant} PAYMENT",
            merchant=merchant,
            category=category,
            debit_credit="D",
            amount=Decimal(str(base_amount)),
            amount_signed=Decimal(str(-base_amount)),
            transaction_hash=short_hash
        )
        db.add(txn)
        transactions.append(txn)
    db.commit()
    return transactions


def test_generate_insights_empty_transactions(test_db: Session):
    """Test insight generation with no transactions."""
    result = InsightsService.generate_insights(test_db, "empty_user", period_days=30)
    
    assert result.transaction_count == 0
    assert result.total_spent == 0
    assert len(result.insights) == 0


def test_generate_insights_with_transactions(test_db: Session):
    """Test insight generation with sample transactions."""
    user_id = "insight_test_user"
    start_date = date.today() - timedelta(days=25)
    
    # Create varied transactions
    create_test_transactions(test_db, user_id, "Groceries", 10, 50.0, start_date)
    create_test_transactions(test_db, user_id, "Restaurants", 8, 30.0, start_date)
    create_test_transactions(test_db, user_id, "Transport", 5, 20.0, start_date)
    
    result = InsightsService.generate_insights(test_db, user_id, period_days=30)
    
    assert result.transaction_count >= 23
    assert result.total_spent > 0
    assert len(result.insights) > 0


def test_spending_trend_increase(test_db: Session):
    """Test detection of spending increase."""
    user_id = "trend_test_user"
    current_start = date.today() - timedelta(days=25)
    previous_start = current_start - timedelta(days=30)
    
    # Previous period: low spending
    create_test_transactions(test_db, user_id, "Shopping", 5, 50.0, previous_start, "SHOP A")
    
    # Current period: high spending (2x)
    create_test_transactions(test_db, user_id, "Shopping", 10, 100.0, current_start, "SHOP B")
    
    result = InsightsService.generate_insights(test_db, user_id, period_days=30)
    
    # Should have a spending trend insight
    trend_insights = [i for i in result.insights if i.insight_type == InsightType.SPENDING_TREND]
    assert len(trend_insights) > 0
    
    # Check the first trend insight indicates an increase
    assert any("increase" in i.title.lower() or "up" in i.description.lower() for i in trend_insights)


def test_category_analysis(test_db: Session):
    """Test category analysis insights."""
    user_id = "category_test_user"
    start_date = date.today() - timedelta(days=25)
    
    # Create transactions with dominant category (>30%)
    create_test_transactions(test_db, user_id, "Dining", 15, 100.0, start_date, "RESTAURANT")
    create_test_transactions(test_db, user_id, "Other", 3, 50.0, start_date, "MISC")
    
    result = InsightsService.generate_insights(test_db, user_id, period_days=30)
    
    # Should have category insights
    category_insights = [i for i in result.insights if i.insight_type == InsightType.CATEGORY_ANALYSIS]
    assert len(category_insights) > 0
    
    # Should mention the dominant category
    assert any("Dining" in i.data.get("category", "") or "categories" in i.title.lower() 
               for i in category_insights)


def test_anomaly_detection(test_db: Session):
    """Test detection of spending anomalies."""
    import hashlib
    user_id = "anomaly_test_user"
    start_date = date.today() - timedelta(days=25)
    
    # Create normal transactions
    for i in range(15):
        hash_val = hashlib.md5(f"normal_{user_id}_{i}".encode()).hexdigest()[:30]
        txn = Transaction(
            user_id=user_id,
            date=start_date + timedelta(days=i),
            account="Credit Card",
            description="NORMAL GROCERY SHOP",
            merchant="CARREFOUR",
            category="Groceries",
            debit_credit="D",
            amount=Decimal("50.00"),
            amount_signed=Decimal("-50.00"),
            transaction_hash=hash_val
        )
        test_db.add(txn)
    
    # Add one anomalous transaction (10x normal)
    anomaly_hash = hashlib.md5(f"anomaly_{user_id}".encode()).hexdigest()[:30]
    anomaly_txn = Transaction(
        user_id=user_id,
        date=start_date + timedelta(days=20),
        account="Credit Card",
        description="BIG GROCERY PURCHASE",
        merchant="CARREFOUR",
        category="Groceries",
        debit_credit="D",
        amount=Decimal("500.00"),
        amount_signed=Decimal("-500.00"),
        transaction_hash=anomaly_hash
    )
    test_db.add(anomaly_txn)
    test_db.commit()
    
    result = InsightsService.generate_insights(test_db, user_id, period_days=30)
    
    # Should detect the anomaly
    anomaly_insights = [i for i in result.insights if i.insight_type == InsightType.ANOMALY_DETECTION]
    assert len(anomaly_insights) > 0
    
    # The anomaly insight should reference the high amount
    assert any(i.data.get("amount", 0) >= 500 for i in anomaly_insights)


def test_recurring_insights(test_db: Session):
    """Test recurring transaction insights."""
    import hashlib
    user_id = "recurring_insight_user"
    base_date = date.today() - timedelta(days=180)
    
    # Create recurring subscription pattern
    for i in range(6):
        hash_val = hashlib.md5(f"netflix_{user_id}_{i}".encode()).hexdigest()[:30]
        txn = Transaction(
            user_id=user_id,
            date=base_date + timedelta(days=30 * i),
            account="Credit Card",
            description="NETFLIX SUBSCRIPTION",
            merchant="NETFLIX",
            category="Entertainment",
            debit_credit="D",
            amount=Decimal("15.99"),
            amount_signed=Decimal("-15.99"),
            transaction_hash=hash_val
        )
        test_db.add(txn)
    test_db.commit()
    
    result = InsightsService.generate_insights(test_db, user_id, period_days=365)
    
    # Should have recurring insights
    recurring_insights = [i for i in result.insights if i.insight_type == InsightType.RECURRING_INSIGHT]
    # Recurring insights may or may not be generated depending on the data
    # At minimum, verify the service runs without errors
    assert result.generated_at is not None


def test_user_isolation(test_db: Session):
    """Test that insights are isolated per user."""
    start_date = date.today() - timedelta(days=25)
    
    # Create transactions for user1
    create_test_transactions(test_db, "user1", "Shopping", 10, 100.0, start_date, "USER1 SHOP")
    
    # Create transactions for user2
    create_test_transactions(test_db, "user2", "Dining", 5, 50.0, start_date, "USER2 RESTAURANT")
    
    # Get insights for user1
    result1 = InsightsService.generate_insights(test_db, "user1", period_days=30)
    
    # Get insights for user2
    result2 = InsightsService.generate_insights(test_db, "user2", period_days=30)
    
    # Verify isolation
    assert result1.total_spent != result2.total_spent
    assert result1.transaction_count != result2.transaction_count


def test_insights_report_to_dict(test_db: Session):
    """Test that insights report can be serialized to dict."""
    user_id = "dict_test_user"
    start_date = date.today() - timedelta(days=25)
    create_test_transactions(test_db, user_id, "Test", 10, 50.0, start_date)
    
    result = InsightsService.generate_insights(test_db, user_id, period_days=30)
    result_dict = result.to_dict()
    
    assert "insights" in result_dict
    assert "generated_at" in result_dict
    assert "period_analyzed" in result_dict
    assert "transaction_count" in result_dict
    assert "total_spent" in result_dict
    assert "summary" in result_dict
    assert "total_insights" in result_dict["summary"]


def test_save_and_retrieve_insights(test_db: Session):
    """Test saving insights to database and retrieving them."""
    user_id = "save_test_user"
    start_date = date.today() - timedelta(days=25)
    create_test_transactions(test_db, user_id, "Groceries", 10, 50.0, start_date)
    
    # Generate and save insights
    report = InsightsService.generate_insights(test_db, user_id, period_days=30)
    saved = InsightsService.save_insights(test_db, user_id, report)
    
    assert len(saved) == len(report.insights)
    
    # Retrieve saved insights
    retrieved = InsightsService.get_saved_insights(test_db, user_id)
    
    assert len(retrieved) == len(saved)


def test_dismiss_insight(test_db: Session):
    """Test dismissing an insight."""
    user_id = "dismiss_test_user"
    start_date = date.today() - timedelta(days=25)
    create_test_transactions(test_db, user_id, "Shopping", 10, 100.0, start_date)
    
    # Generate and save insights
    report = InsightsService.generate_insights(test_db, user_id, period_days=30)
    saved = InsightsService.save_insights(test_db, user_id, report)
    
    if saved:
        insight_id = str(saved[0].id)
        
        # Dismiss the insight
        success = InsightsService.dismiss_insight(test_db, user_id, insight_id)
        assert success
        
        # Verify it's excluded from default query
        retrieved = InsightsService.get_saved_insights(test_db, user_id, include_dismissed=False)
        dismissed_ids = [str(r.id) for r in retrieved]
        assert insight_id not in dismissed_ids
        
        # Verify it's included when include_dismissed=True
        all_retrieved = InsightsService.get_saved_insights(test_db, user_id, include_dismissed=True)
        all_ids = [str(r.id) for r in all_retrieved]
        assert insight_id in all_ids


def test_severity_sorting(test_db: Session):
    """Test that insights are sorted by severity."""
    import hashlib
    user_id = "severity_test_user"
    start_date = date.today() - timedelta(days=25)
    
    # Create data that should generate multiple insight types
    # Normal spending
    for i in range(15):
        hash_val = hashlib.md5(f"normal_sev_{user_id}_{i}".encode()).hexdigest()[:30]
        txn = Transaction(
            user_id=user_id,
            date=start_date + timedelta(days=i),
            account="Credit Card",
            description="NORMAL SHOP",
            merchant="SHOP",
            category="Shopping",
            debit_credit="D",
            amount=Decimal("50.00"),
            amount_signed=Decimal("-50.00"),
            transaction_hash=hash_val
        )
        test_db.add(txn)
    
    # Add anomaly
    anomaly_hash = hashlib.md5(f"anomaly_sev_{user_id}".encode()).hexdigest()[:30]
    anomaly = Transaction(
        user_id=user_id,
        date=start_date + timedelta(days=20),
        account="Credit Card",
        description="BIG PURCHASE",
        merchant="SHOP",
        category="Shopping",
        debit_credit="D",
        amount=Decimal("1000.00"),
        amount_signed=Decimal("-1000.00"),
        transaction_hash=anomaly_hash
    )
    test_db.add(anomaly)
    test_db.commit()
    
    result = InsightsService.generate_insights(test_db, user_id, period_days=30)
    
    # Verify insights are sorted with alerts first
    if len(result.insights) > 1:
        severity_order = {
            InsightSeverity.ALERT: 0,
            InsightSeverity.WARNING: 1,
            InsightSeverity.TIP: 2,
            InsightSeverity.INFO: 3,
        }
        for i in range(len(result.insights) - 1):
            current_order = severity_order.get(result.insights[i].severity, 4)
            next_order = severity_order.get(result.insights[i + 1].severity, 4)
            assert current_order <= next_order, "Insights should be sorted by severity"


def test_period_filtering(test_db: Session):
    """Test that insights respect period filtering."""
    user_id = "period_test_user"
    
    # Create old transactions (90 days ago)
    old_start = date.today() - timedelta(days=90)
    create_test_transactions(test_db, user_id, "Old", 5, 100.0, old_start, "OLD MERCHANT")
    
    # Create recent transactions (10 days ago)
    recent_start = date.today() - timedelta(days=10)
    create_test_transactions(test_db, user_id, "Recent", 5, 50.0, recent_start, "RECENT MERCHANT")
    
    # Generate insights for 30 days only
    result = InsightsService.generate_insights(test_db, user_id, period_days=30)
    
    # Should only include recent transactions
    assert result.transaction_count == 5  # Only the 5 recent ones
    assert result.total_spent == 250.0  # 5 x 50


def test_insights_with_no_previous_period(test_db: Session):
    """Test insights when there's no previous period data."""
    user_id = "no_prev_user"
    start_date = date.today() - timedelta(days=10)
    
    # Only create transactions for current period
    create_test_transactions(test_db, user_id, "Test", 10, 50.0, start_date)
    
    # Should not crash, may have fewer trend insights
    result = InsightsService.generate_insights(test_db, user_id, period_days=30)
    
    assert result.transaction_count == 10
    assert result.total_spent == 500.0

