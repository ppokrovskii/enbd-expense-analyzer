"""Service for generating financial insights using hybrid algo+LLM approach."""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime, timedelta
from collections import defaultdict
import statistics
import time
import os

from app.domains.transactions.models import Transaction
from app.domains.recurring.service import RecurringDetectionService
from app.domains.insights.models import (
    InsightType,
    InsightSeverity,
    SpendingTrend,
    CategoryInsight,
    AnomalyInsight,
    SavingsOpportunity,
    GeneratedInsight,
    InsightsReport,
    Insight,
)


class InsightsService:
    """
    Service for generating financial insights.
    
    Uses a hybrid approach:
    1. Algorithm-based statistical analysis (fast, deterministic)
    2. LLM for natural language generation (optional, for descriptions)
    
    Cost savings: ~95% by doing analysis algorithmically and only using
    LLM for human-readable descriptions when needed.
    """
    
    # Thresholds for insight generation
    SIGNIFICANT_CHANGE_THRESHOLD = 0.15  # 15% change is significant
    ANOMALY_THRESHOLD = 2.5  # Standard deviations
    MIN_TRANSACTIONS_FOR_INSIGHTS = 5
    
    @classmethod
    def generate_insights(
        cls,
        db: Session,
        user_id: str,
        period_days: int = 30,
        person_id: Optional[str] = None,
        include_llm_descriptions: bool = False,
    ) -> InsightsReport:
        """
        Generate all insights for a user.
        
        Args:
            db: Database session
            user_id: User identifier
            period_days: Number of days to analyze
            person_id: Optional person ID for multi-person filtering
            include_llm_descriptions: Whether to generate LLM descriptions
            
        Returns:
            InsightsReport with all generated insights
        """
        start_time = time.time()
        
        # Define analysis periods
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)
        previous_start = start_date - timedelta(days=period_days)
        
        # Fetch transactions
        transactions = cls._get_transactions(db, user_id, start_date, end_date, person_id)
        previous_transactions = cls._get_transactions(db, user_id, previous_start, start_date, person_id)
        
        total_spent = sum(abs(float(t.amount_signed)) for t in transactions if t.amount_signed < 0)
        
        if len(transactions) < cls.MIN_TRANSACTIONS_FOR_INSIGHTS:
            return InsightsReport(
                insights=[],
                generated_at=datetime.utcnow(),
                period_analyzed=f"{period_days} days",
                transaction_count=len(transactions),
                total_spent=total_spent,
            )
        
        # Generate various insights
        insights = []
        
        # 1. Spending trend analysis
        trend_insights = cls._analyze_spending_trends(
            transactions, previous_transactions, start_date, end_date
        )
        insights.extend(trend_insights)
        
        # 2. Category analysis
        category_insights = cls._analyze_categories(
            transactions, total_spent, start_date, end_date
        )
        insights.extend(category_insights)
        
        # 3. Anomaly detection
        anomaly_insights = cls._detect_anomalies(transactions, start_date, end_date)
        insights.extend(anomaly_insights)
        
        # 4. Recurring transaction insights
        recurring_insights = cls._analyze_recurring(db, user_id, person_id, start_date, end_date)
        insights.extend(recurring_insights)
        
        # 5. Savings opportunities
        savings_insights = cls._find_savings_opportunities(
            transactions, previous_transactions, start_date, end_date
        )
        insights.extend(savings_insights)
        
        # Sort by severity (alerts first, then warnings, tips, info)
        severity_order = {
            InsightSeverity.ALERT: 0,
            InsightSeverity.WARNING: 1,
            InsightSeverity.TIP: 2,
            InsightSeverity.INFO: 3,
        }
        insights.sort(key=lambda x: severity_order.get(x.severity, 4))
        
        return InsightsReport(
            insights=insights,
            generated_at=datetime.utcnow(),
            period_analyzed=f"{period_days} days",
            transaction_count=len(transactions),
            total_spent=total_spent,
        )
    
    @classmethod
    def _get_transactions(
        cls,
        db: Session,
        user_id: str,
        start_date: date,
        end_date: date,
        person_id: Optional[str] = None,
    ) -> List[Transaction]:
        """Fetch transactions for the given period."""
        query = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount_signed < 0,  # Only expenses
        )
        
        if person_id:
            query = query.filter(Transaction.person_id == int(person_id))
        
        return query.order_by(Transaction.date).all()
    
    @classmethod
    def _analyze_spending_trends(
        cls,
        current_txns: List[Transaction],
        previous_txns: List[Transaction],
        start_date: date,
        end_date: date,
    ) -> List[GeneratedInsight]:
        """Analyze spending trends between periods."""
        insights = []
        
        current_total = sum(abs(float(t.amount_signed)) for t in current_txns)
        previous_total = sum(abs(float(t.amount_signed)) for t in previous_txns)
        
        if previous_total == 0:
            return insights
        
        change_percent = (current_total - previous_total) / previous_total
        
        # Overall spending change
        if abs(change_percent) > cls.SIGNIFICANT_CHANGE_THRESHOLD:
            if change_percent > 0:
                severity = InsightSeverity.WARNING if change_percent > 0.3 else InsightSeverity.INFO
                title = "Spending Increased"
                description = f"Your spending is up {abs(change_percent)*100:.1f}% compared to the previous period. " \
                            f"You spent AED {current_total:,.2f} vs AED {previous_total:,.2f} previously."
            else:
                severity = InsightSeverity.TIP
                title = "Spending Decreased"
                description = f"Great job! Your spending is down {abs(change_percent)*100:.1f}% compared to the previous period. " \
                            f"You spent AED {current_total:,.2f} vs AED {previous_total:,.2f} previously."
            
            insights.append(GeneratedInsight(
                insight_type=InsightType.SPENDING_TREND,
                severity=severity,
                title=title,
                description=description,
                data={
                    "current_total": round(current_total, 2),
                    "previous_total": round(previous_total, 2),
                    "change_percent": round(change_percent * 100, 1),
                },
                period_start=start_date,
                period_end=end_date,
            ))
        
        # Category-level trends
        current_by_cat = cls._group_by_category(current_txns)
        previous_by_cat = cls._group_by_category(previous_txns)
        
        for category, current_amount in current_by_cat.items():
            prev_amount = previous_by_cat.get(category, 0)
            if prev_amount > 0:
                cat_change = (current_amount - prev_amount) / prev_amount
                if cat_change > 0.5:  # 50% increase in a category
                    insights.append(GeneratedInsight(
                        insight_type=InsightType.CATEGORY_ANALYSIS,
                        severity=InsightSeverity.WARNING,
                        title=f"High Increase in {category}",
                        description=f"Your {category} spending jumped by {cat_change*100:.0f}%. " \
                                   f"You spent AED {current_amount:,.2f} this period vs AED {prev_amount:,.2f} previously.",
                        data={
                            "category": category,
                            "current": round(current_amount, 2),
                            "previous": round(prev_amount, 2),
                            "change_percent": round(cat_change * 100, 1),
                        },
                        period_start=start_date,
                        period_end=end_date,
                    ))
        
        return insights
    
    @classmethod
    def _analyze_categories(
        cls,
        transactions: List[Transaction],
        total_spent: float,
        start_date: date,
        end_date: date,
    ) -> List[GeneratedInsight]:
        """Analyze spending by category."""
        insights = []
        
        category_data = cls._group_by_category(transactions)
        
        if not category_data or total_spent == 0:
            return insights
        
        # Find dominant categories (>30% of spending)
        for category, amount in category_data.items():
            percentage = (amount / total_spent) * 100
            if percentage > 30:
                insights.append(GeneratedInsight(
                    insight_type=InsightType.CATEGORY_ANALYSIS,
                    severity=InsightSeverity.INFO,
                    title=f"{category} Dominates Spending",
                    description=f"{category} accounts for {percentage:.1f}% of your total spending " \
                               f"(AED {amount:,.2f} out of AED {total_spent:,.2f}).",
                    data={
                        "category": category,
                        "amount": round(amount, 2),
                        "percentage": round(percentage, 1),
                        "total_spent": round(total_spent, 2),
                    },
                    period_start=start_date,
                    period_end=end_date,
                ))
        
        # Top spending categories summary
        sorted_cats = sorted(category_data.items(), key=lambda x: x[1], reverse=True)[:5]
        if sorted_cats:
            insights.append(GeneratedInsight(
                insight_type=InsightType.CATEGORY_ANALYSIS,
                severity=InsightSeverity.INFO,
                title="Top Spending Categories",
                description=f"Your top spending categories are: " + 
                           ", ".join([f"{cat} (AED {amt:,.0f})" for cat, amt in sorted_cats]),
                data={
                    "categories": [
                        {"name": cat, "amount": round(amt, 2), "percentage": round(amt/total_spent*100, 1)}
                        for cat, amt in sorted_cats
                    ]
                },
                period_start=start_date,
                period_end=end_date,
            ))
        
        return insights
    
    @classmethod
    def _detect_anomalies(
        cls,
        transactions: List[Transaction],
        start_date: date,
        end_date: date,
    ) -> List[GeneratedInsight]:
        """Detect unusual spending patterns."""
        insights = []
        
        if len(transactions) < 10:
            return insights
        
        # Group by category and detect outliers
        category_txns = defaultdict(list)
        for txn in transactions:
            category = txn.category or "Other"
            category_txns[category].append(txn)
        
        for category, txns in category_txns.items():
            if len(txns) < 3:
                continue
            
            amounts = [abs(float(t.amount_signed)) for t in txns]
            mean = statistics.mean(amounts)
            if len(amounts) >= 2:
                stdev = statistics.stdev(amounts)
            else:
                continue
            
            if stdev == 0:
                continue
            
            # Find outliers
            for txn in txns:
                amount = abs(float(txn.amount_signed))
                z_score = (amount - mean) / stdev
                
                if z_score > cls.ANOMALY_THRESHOLD:
                    insights.append(GeneratedInsight(
                        insight_type=InsightType.ANOMALY_DETECTION,
                        severity=InsightSeverity.ALERT,
                        title=f"Unusual {category} Purchase",
                        description=f"A purchase of AED {amount:,.2f} at {txn.merchant or txn.description} " \
                                   f"on {txn.date.strftime('%b %d')} is {z_score:.1f}x higher than your " \
                                   f"typical {category} spending (avg AED {mean:,.2f}).",
                        data={
                            "transaction_id": txn.id,
                            "merchant": txn.merchant or txn.description,
                            "amount": round(amount, 2),
                            "date": txn.date.isoformat(),
                            "category": category,
                            "category_average": round(mean, 2),
                            "z_score": round(z_score, 2),
                        },
                        period_start=start_date,
                        period_end=end_date,
                    ))
        
        return insights
    
    @classmethod
    def _analyze_recurring(
        cls,
        db: Session,
        user_id: str,
        person_id: Optional[str],
        start_date: date,
        end_date: date,
    ) -> List[GeneratedInsight]:
        """Analyze recurring transactions for insights."""
        insights = []
        
        result = RecurringDetectionService.detect_patterns(db, user_id, person_id=person_id)
        
        if not result.recurring_groups:
            return insights
        
        # Monthly recurring total
        monthly_total = sum(
            g.estimated_amount for g in result.recurring_groups 
            if g.frequency.value == "monthly" and not g.forgotten
        )
        
        if monthly_total > 0:
            insights.append(GeneratedInsight(
                insight_type=InsightType.RECURRING_INSIGHT,
                severity=InsightSeverity.INFO,
                title="Monthly Recurring Expenses",
                description=f"You have AED {monthly_total:,.2f} in monthly recurring expenses " \
                           f"across {len(result.recurring_groups)} subscriptions/bills.",
                data={
                    "monthly_total": round(monthly_total, 2),
                    "subscription_count": len(result.recurring_groups),
                    "top_subscriptions": [
                        {"name": g.pattern_name, "amount": round(g.estimated_amount, 2)}
                        for g in sorted(result.recurring_groups, key=lambda x: x.estimated_amount, reverse=True)[:5]
                    ]
                },
                period_start=start_date,
                period_end=end_date,
            ))
        
        # Forgotten subscriptions
        forgotten = [g for g in result.recurring_groups if g.forgotten]
        if forgotten:
            potential_savings = sum(g.estimated_amount for g in forgotten)
            insights.append(GeneratedInsight(
                insight_type=InsightType.RECURRING_INSIGHT,
                severity=InsightSeverity.TIP,
                title="Potentially Unused Subscriptions",
                description=f"We found {len(forgotten)} subscriptions that haven't been charged recently. " \
                           f"If cancelled, you could save up to AED {potential_savings:,.2f}/month.",
                data={
                    "forgotten_count": len(forgotten),
                    "potential_savings": round(potential_savings, 2),
                    "subscriptions": [
                        {"name": g.pattern_name, "last_seen": g.last_seen.isoformat(), "amount": round(g.estimated_amount, 2)}
                        for g in forgotten
                    ]
                },
                period_start=start_date,
                period_end=end_date,
            ))
        
        return insights
    
    @classmethod
    def _find_savings_opportunities(
        cls,
        current_txns: List[Transaction],
        previous_txns: List[Transaction],
        start_date: date,
        end_date: date,
    ) -> List[GeneratedInsight]:
        """Identify potential savings opportunities."""
        insights = []
        
        current_by_cat = cls._group_by_category(current_txns)
        previous_by_cat = cls._group_by_category(previous_txns)
        
        # Look for categories where spending decreased - encourage continuation
        for category, prev_amount in previous_by_cat.items():
            current_amount = current_by_cat.get(category, 0)
            if prev_amount > 100 and current_amount < prev_amount * 0.7:  # 30%+ reduction
                savings = prev_amount - current_amount
                insights.append(GeneratedInsight(
                    insight_type=InsightType.SAVINGS_OPPORTUNITY,
                    severity=InsightSeverity.TIP,
                    title=f"Savings Progress in {category}",
                    description=f"You've reduced {category} spending by AED {savings:,.2f} this period. " \
                               f"Keep it up to save AED {savings * 12:,.0f}/year at this pace!",
                    data={
                        "category": category,
                        "current_spending": round(current_amount, 2),
                        "previous_spending": round(prev_amount, 2),
                        "monthly_savings": round(savings, 2),
                        "yearly_projection": round(savings * 12, 2),
                    },
                    period_start=start_date,
                    period_end=end_date,
                ))
        
        # Dining out tip if spending is high
        dining_categories = ["Restaurants", "Food & Drink", "Dining", "Cafes"]
        total_dining = sum(
            current_by_cat.get(cat, 0) for cat in dining_categories
        )
        total_spent = sum(current_by_cat.values())
        
        if total_spent > 0 and total_dining / total_spent > 0.2:  # >20% on dining
            potential_savings = total_dining * 0.3
            insights.append(GeneratedInsight(
                insight_type=InsightType.SAVINGS_OPPORTUNITY,
                severity=InsightSeverity.TIP,
                title="Dining Expenses Opportunity",
                description=f"Dining makes up {total_dining/total_spent*100:.0f}% of your spending. " \
                           f"Cooking at home more often could save you AED {potential_savings:,.0f}/month.",
                data={
                    "dining_total": round(total_dining, 2),
                    "percentage_of_total": round(total_dining/total_spent*100, 1),
                    "potential_monthly_savings": round(potential_savings, 2),
                },
                period_start=start_date,
                period_end=end_date,
            ))
        
        return insights
    
    @classmethod
    def _group_by_category(cls, transactions: List[Transaction]) -> Dict[str, float]:
        """Group transactions by category and sum amounts."""
        category_totals = defaultdict(float)
        for txn in transactions:
            category = txn.category or "Other"
            category_totals[category] += abs(float(txn.amount_signed))
        return dict(category_totals)
    
    @classmethod
    def save_insights(
        cls,
        db: Session,
        user_id: str,
        report: InsightsReport,
        person_id: Optional[str] = None,
    ) -> List[Insight]:
        """Save generated insights to the database."""
        saved = []
        
        for insight in report.insights:
            db_insight = Insight(
                user_id=user_id,
                person_id=int(person_id) if person_id else None,
                insight_type=insight.insight_type.value,
                severity=insight.severity.value,
                title=insight.title,
                description=insight.description,
                data_json=insight.data,
                period_start=insight.period_start,
                period_end=insight.period_end,
            )
            db.add(db_insight)
            saved.append(db_insight)
        
        db.commit()
        return saved
    
    @classmethod
    def get_saved_insights(
        cls,
        db: Session,
        user_id: str,
        include_dismissed: bool = False,
        limit: int = 50,
        person_id: Optional[str] = None,
    ) -> List[Insight]:
        """Get saved insights from database."""
        query = db.query(Insight).filter(Insight.user_id == user_id)
        
        if person_id:
            query = query.filter(Insight.person_id == int(person_id))
        
        if not include_dismissed:
            query = query.filter(Insight.is_dismissed == False)
        
        return query.order_by(Insight.created_at.desc()).limit(limit).all()
    
    @classmethod
    def dismiss_insight(cls, db: Session, user_id: str, insight_id: str) -> bool:
        """Mark an insight as dismissed."""
        import uuid as uuid_module
        insight = db.query(Insight).filter(
            Insight.id == uuid_module.UUID(insight_id),
            Insight.user_id == user_id
        ).first()
        
        if insight:
            insight.is_dismissed = True
            db.commit()
            return True
        return False

