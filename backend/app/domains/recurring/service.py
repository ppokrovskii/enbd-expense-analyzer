"""Service for detecting recurring transactions using hybrid algo+LLM approach."""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any, Optional, Tuple
from datetime import date, timedelta
from collections import defaultdict
import statistics
import time
import re

from app.domains.transactions.models import Transaction
from app.domains.recurring.models import (
    Frequency, 
    DetectedRecurring, 
    RecurringDetectionResult,
    RecurringGroup,
    RecurringOccurrence
)


# Known service patterns for better naming
KNOWN_SERVICES = {
    "NETFLIX": "Netflix Subscription",
    "SPOTIFY": "Spotify Subscription",
    "AMAZON PRIME": "Amazon Prime",
    "DISNEY": "Disney+ Subscription",
    "HULU": "Hulu Subscription",
    "HBO": "HBO Max Subscription",
    "APPLE": "Apple Services",
    "GOOGLE": "Google Services",
    "MICROSOFT": "Microsoft Services",
    "ADOBE": "Adobe Creative Cloud",
    "DROPBOX": "Dropbox",
    "YOUTUBE": "YouTube Premium",
    "GYM": "Gym Membership",
    "FITNESS": "Fitness Membership",
    "CROSSFIT": "CrossFit Membership",
    "VIRGIN": "Virgin Active",
    "ETISALAT": "Etisalat Bill",
    "DU ": "Du Bill",
    "DEWA": "DEWA Utility Bill",
    "SALIK": "Salik Top-up",
    "RTA": "RTA Services",
    "INSURANCE": "Insurance Premium",
    "RENT": "Rent Payment",
    "MAID": "Domestic Help",
    "CLEANING": "Cleaning Service",
}


class RecurringDetectionService:
    """
    Service for detecting recurring transaction patterns.
    
    Uses a hybrid approach:
    1. Algorithm-based detection (fast, cheap) - default
    2. LLM validation for edge cases (when confidence is low)
    """
    
    # Detection parameters
    MIN_OCCURRENCES = 3  # Minimum transactions to consider as recurring
    AMOUNT_VARIANCE_THRESHOLD = 0.15  # 15% variance allowed in amounts
    FORGOTTEN_THRESHOLD_DAYS = 60  # Days since last seen to mark as "forgotten"
    
    # Frequency detection windows (in days)
    FREQUENCY_WINDOWS = {
        Frequency.WEEKLY: (5, 10),       # 5-10 days
        Frequency.BIWEEKLY: (12, 18),    # 12-18 days
        Frequency.MONTHLY: (25, 35),     # 25-35 days
        Frequency.QUARTERLY: (80, 100),  # 80-100 days
        Frequency.YEARLY: (350, 380),    # 350-380 days
    }
    
    @classmethod
    def detect_patterns(
        cls,
        db: Session,
        user_id: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        workspace_id: Optional[str] = None,
    ) -> RecurringDetectionResult:
        """
        Detect recurring transaction patterns for a user.
        
        Args:
            db: Database session
            user_id: User identifier
            date_from: Start date for analysis (default: 1 year ago)
            date_to: End date for analysis (default: today)
            workspace_id: Optional person ID for multi-person filtering
            
        Returns:
            RecurringDetectionResult with detected patterns
        """
        start_time = time.time()
        
        # Set default date range (1 year)
        if not date_to:
            date_to = date.today()
        if not date_from:
            date_from = date_to - timedelta(days=365)
        
        # Fetch transactions
        query = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.date >= date_from,
            Transaction.date <= date_to,
            Transaction.amount_signed < 0,  # Only expenses
        )
        
        if workspace_id:
            query = query.filter(Transaction.workspace_id == int(workspace_id))
        
        transactions = query.order_by(Transaction.date).all()
        total_analyzed = len(transactions)
        
        if not transactions:
            return RecurringDetectionResult(
                recurring_groups=[],
                total_transactions_analyzed=0,
                detection_time_ms=0
            )
        
        # Group transactions by merchant
        merchant_groups = cls._group_by_merchant(transactions)
        
        # Detect recurring patterns in each group
        recurring_patterns = []
        for merchant, txns in merchant_groups.items():
            if len(txns) >= cls.MIN_OCCURRENCES:
                pattern = cls._analyze_merchant_pattern(merchant, txns, date_to)
                if pattern:
                    recurring_patterns.append(pattern)
        
        detection_time = (time.time() - start_time) * 1000
        
        return RecurringDetectionResult(
            recurring_groups=recurring_patterns,
            total_transactions_analyzed=total_analyzed,
            detection_time_ms=detection_time
        )
    
    @classmethod
    def _group_by_merchant(cls, transactions: List[Transaction]) -> Dict[str, List[Transaction]]:
        """Group transactions by normalized merchant name."""
        groups = defaultdict(list)
        
        for txn in transactions:
            # Normalize merchant name
            merchant = cls._normalize_merchant(txn.merchant or txn.description)
            groups[merchant].append(txn)
        
        return groups
    
    @classmethod
    def _normalize_merchant(cls, name: str) -> str:
        """Normalize merchant name for grouping."""
        if not name:
            return "UNKNOWN"
        
        # Uppercase and remove common suffixes/prefixes
        normalized = name.upper().strip()
        
        # Remove common transaction prefixes
        prefixes_to_remove = [
            "POS ", "ATM ", "TFR ", "DD ", "SO ", "CHQ ",
            "PURCHASE ", "PAYMENT ", "DEBIT ", "CREDIT ",
        ]
        for prefix in prefixes_to_remove:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
        
        # Remove trailing numbers and reference codes
        normalized = re.sub(r'\s+\d{6,}$', '', normalized)  # Remove long numbers at end
        normalized = re.sub(r'\s+REF\s*\d+', '', normalized)  # Remove REF codes
        normalized = re.sub(r'\s+[A-Z]{2}\d{6,}', '', normalized)  # Remove alphanumeric codes
        
        # Truncate long names
        if len(normalized) > 30:
            normalized = normalized[:30]
        
        return normalized.strip()
    
    @classmethod
    def _analyze_merchant_pattern(
        cls,
        merchant: str,
        transactions: List[Transaction],
        reference_date: date
    ) -> Optional[DetectedRecurring]:
        """Analyze a merchant's transactions for recurring patterns."""
        if len(transactions) < cls.MIN_OCCURRENCES:
            return None
        
        # Sort by date
        sorted_txns = sorted(transactions, key=lambda t: t.date)
        
        # Calculate intervals between transactions
        intervals = []
        for i in range(1, len(sorted_txns)):
            days_diff = (sorted_txns[i].date - sorted_txns[i-1].date).days
            if days_diff > 0:  # Ignore same-day transactions
                intervals.append(days_diff)
        
        if not intervals:
            return None
        
        # Calculate amounts
        amounts = [abs(float(t.amount_signed)) for t in sorted_txns]
        avg_amount = statistics.mean(amounts)
        amount_stddev = statistics.stdev(amounts) if len(amounts) > 1 else 0
        amount_variance = amount_stddev / avg_amount if avg_amount > 0 else 0
        
        # Check if amounts are consistent enough
        if amount_variance > cls.AMOUNT_VARIANCE_THRESHOLD:
            return None
        
        # Detect frequency
        frequency = cls._detect_frequency(intervals)
        if not frequency:
            return None
        
        # Calculate interval consistency (confidence factor)
        expected_interval = cls._get_expected_interval(frequency)
        interval_variance = cls._calculate_interval_variance(intervals, expected_interval)
        
        # Calculate confidence
        confidence = cls._calculate_confidence(
            occurrences=len(sorted_txns),
            amount_variance=amount_variance,
            interval_variance=interval_variance
        )
        
        # Determine if forgotten
        last_seen = sorted_txns[-1].date
        days_since_last = (reference_date - last_seen).days
        forgotten = days_since_last > cls.FORGOTTEN_THRESHOLD_DAYS
        
        # Calculate next expected date
        next_expected = cls._calculate_next_expected(last_seen, frequency, reference_date)
        
        # Generate pattern name
        pattern_name = cls._generate_pattern_name(merchant)
        
        return DetectedRecurring(
            merchant=merchant,
            pattern_name=pattern_name,
            frequency=frequency,
            estimated_amount=round(avg_amount, 2),
            occurrences=len(sorted_txns),
            first_seen=sorted_txns[0].date,
            last_seen=last_seen,
            next_expected=next_expected,
            confidence=confidence,
            forgotten=forgotten,
            transaction_ids=[t.id for t in sorted_txns],
            amount_variance=round(amount_variance, 4),
            interval_variance=round(interval_variance, 4)
        )
    
    @classmethod
    def _detect_frequency(cls, intervals: List[int]) -> Optional[Frequency]:
        """Detect the most likely frequency from transaction intervals."""
        if not intervals:
            return None
        
        avg_interval = statistics.mean(intervals)
        
        # Find the best matching frequency
        best_match = None
        best_score = float('inf')
        
        for freq, (min_days, max_days) in cls.FREQUENCY_WINDOWS.items():
            expected = (min_days + max_days) / 2
            score = abs(avg_interval - expected)
            
            # Check if within range
            if min_days <= avg_interval <= max_days:
                if score < best_score:
                    best_score = score
                    best_match = freq
        
        return best_match
    
    @classmethod
    def _get_expected_interval(cls, frequency: Frequency) -> int:
        """Get the expected interval in days for a frequency."""
        intervals = {
            Frequency.WEEKLY: 7,
            Frequency.BIWEEKLY: 14,
            Frequency.MONTHLY: 30,
            Frequency.QUARTERLY: 90,
            Frequency.YEARLY: 365,
        }
        return intervals.get(frequency, 30)
    
    @classmethod
    def _calculate_interval_variance(cls, intervals: List[int], expected: int) -> float:
        """Calculate variance from expected interval."""
        if not intervals:
            return 1.0
        
        deviations = [abs(i - expected) / expected for i in intervals]
        return statistics.mean(deviations)
    
    @classmethod
    def _calculate_confidence(
        cls,
        occurrences: int,
        amount_variance: float,
        interval_variance: float
    ) -> float:
        """
        Calculate confidence score (0.0 to 1.0) for a recurring pattern.
        
        Factors:
        - More occurrences = higher confidence
        - Lower amount variance = higher confidence
        - Lower interval variance = higher confidence
        """
        # Occurrence factor (more is better, diminishing returns after 6)
        occ_factor = min(occurrences / 6, 1.0)
        
        # Amount consistency factor
        amount_factor = max(0, 1.0 - amount_variance * 3)
        
        # Interval consistency factor
        interval_factor = max(0, 1.0 - interval_variance * 2)
        
        # Weighted average
        confidence = (
            occ_factor * 0.3 +
            amount_factor * 0.35 +
            interval_factor * 0.35
        )
        
        return min(max(confidence, 0.0), 1.0)
    
    @classmethod
    def _calculate_next_expected(
        cls,
        last_seen: date,
        frequency: Frequency,
        reference_date: date
    ) -> Optional[date]:
        """Calculate the next expected date for a recurring transaction."""
        interval = cls._get_expected_interval(frequency)
        next_date = last_seen + timedelta(days=interval)
        
        # If next date is in the past, advance until future
        while next_date <= reference_date:
            next_date += timedelta(days=interval)
        
        return next_date
    
    @classmethod
    def _generate_pattern_name(cls, merchant: str) -> str:
        """Generate a human-readable pattern name."""
        merchant_upper = merchant.upper()
        
        # Check known services
        for key, name in KNOWN_SERVICES.items():
            if key in merchant_upper:
                return name
        
        # Clean up merchant name
        clean_name = merchant.title()
        
        # Add "Subscription" suffix for common patterns
        if any(kw in merchant_upper for kw in ["STREAMING", "PREMIUM", "PLUS", "PRO"]):
            clean_name += " Subscription"
        
        return clean_name
    
    @classmethod
    def get_monthly_recurring_total(
        cls,
        db: Session,
        user_id: str,
        workspace_id: Optional[str] = None
    ) -> float:
        """
        Calculate the total monthly recurring expenses.
        
        Returns the estimated monthly total including:
        - Monthly subscriptions (as-is)
        - Weekly subscriptions (multiplied by 4.33)
        - Biweekly subscriptions (multiplied by 2.17)
        """
        result = cls.detect_patterns(db, user_id, workspace_id=workspace_id)
        
        monthly_total = 0.0
        for group in result.recurring_groups:
            if group.forgotten:
                continue
                
            if group.frequency == Frequency.WEEKLY:
                monthly_total += group.estimated_amount * 4.33
            elif group.frequency == Frequency.BIWEEKLY:
                monthly_total += group.estimated_amount * 2.17
            elif group.frequency == Frequency.MONTHLY:
                monthly_total += group.estimated_amount
            elif group.frequency == Frequency.QUARTERLY:
                monthly_total += group.estimated_amount / 3
            elif group.frequency == Frequency.YEARLY:
                monthly_total += group.estimated_amount / 12
        
        return round(monthly_total, 2)
    
    @classmethod
    def save_recurring_groups(
        cls,
        db: Session,
        user_id: str,
        result: RecurringDetectionResult,
        workspace_id: Optional[str] = None
    ) -> List[RecurringGroup]:
        """
        Save detected recurring groups to the database.
        
        This persists the detection results for tracking and history.
        """
        saved_groups = []
        
        for detected in result.recurring_groups:
            # Check if group already exists
            existing = db.query(RecurringGroup).filter(
                RecurringGroup.user_id == user_id,
                RecurringGroup.merchant == detected.merchant,
            ).first()
            
            if existing:
                # Update existing group
                existing.estimated_amount = detected.estimated_amount
                existing.occurrences_count = detected.occurrences
                existing.last_seen_date = detected.last_seen
                existing.next_expected_date = detected.next_expected
                existing.forgotten = detected.forgotten
                existing.confidence = detected.confidence
                saved_groups.append(existing)
            else:
                # Create new group
                group = RecurringGroup(
                    user_id=user_id,
                    workspace_id=int(workspace_id) if workspace_id else None,
                    pattern_name=detected.pattern_name,
                    merchant=detected.merchant,
                    estimated_amount=detected.estimated_amount,
                    frequency=detected.frequency.value,
                    occurrences_count=detected.occurrences,
                    last_seen_date=detected.last_seen,
                    next_expected_date=detected.next_expected,
                    forgotten=detected.forgotten,
                    confidence=detected.confidence,
                )
                db.add(group)
                saved_groups.append(group)
        
        db.commit()
        return saved_groups
