"""Models for recurring transaction detection."""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Boolean, Date
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime, date
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid

from app.shared.database import Base


class Frequency(str, Enum):
    """Recurring transaction frequency types."""
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class RecurringGroup(Base):
    """Database model for recurring transaction groups."""
    __tablename__ = "recurring_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=True)
    pattern_name = Column(String, nullable=False)
    merchant = Column(String, nullable=False)
    estimated_amount = Column(Float, nullable=False)
    frequency = Column(String, nullable=False)  # Store as string from Frequency enum
    occurrences_count = Column(Integer, nullable=False, default=0)
    last_seen_date = Column(Date, nullable=True)
    next_expected_date = Column(Date, nullable=True)
    forgotten = Column(Boolean, default=False)
    confidence = Column(Float, default=0.0)  # 0.0 to 1.0
    metadata_json = Column(JSONB, nullable=True)  # Store additional algo/LLM details
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    occurrences = relationship("RecurringOccurrence", back_populates="recurring_group", cascade="all, delete-orphan")


class RecurringOccurrence(Base):
    """Database model for individual occurrences in a recurring pattern."""
    __tablename__ = "recurring_occurrences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recurring_group_id = Column(UUID(as_uuid=True), ForeignKey("recurring_groups.id"), nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    recurring_group = relationship("RecurringGroup", back_populates="occurrences")


# Data classes for detection results (not stored in DB)

@dataclass
class DetectedRecurring:
    """A detected recurring pattern (in-memory result)."""
    merchant: str
    pattern_name: str
    frequency: Frequency
    estimated_amount: float
    occurrences: int
    first_seen: date
    last_seen: date
    next_expected: Optional[date]
    confidence: float
    forgotten: bool
    transaction_ids: List[int] = field(default_factory=list)
    amount_variance: float = 0.0
    interval_variance: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "merchant": self.merchant,
            "pattern_name": self.pattern_name,
            "frequency": self.frequency.value,
            "estimated_amount": round(self.estimated_amount, 2),
            "occurrences": self.occurrences,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "next_expected": self.next_expected.isoformat() if self.next_expected else None,
            "confidence": round(self.confidence, 2),
            "forgotten": self.forgotten,
            "transaction_ids": self.transaction_ids,
        }


@dataclass
class RecurringDetectionResult:
    """Result of recurring pattern detection."""
    recurring_groups: List[DetectedRecurring]
    total_transactions_analyzed: int
    detection_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        monthly_total = sum(
            g.estimated_amount 
            for g in self.recurring_groups 
            if g.frequency == Frequency.MONTHLY and not g.forgotten
        )
        weekly_total = sum(
            g.estimated_amount 
            for g in self.recurring_groups 
            if g.frequency == Frequency.WEEKLY and not g.forgotten
        )
        forgotten_count = sum(1 for g in self.recurring_groups if g.forgotten)
        
        return {
            "recurring_groups": [g.to_dict() for g in self.recurring_groups],
            "total_transactions_analyzed": self.total_transactions_analyzed,
            "detection_time_ms": round(self.detection_time_ms, 2),
            "summary": {
                "total_recurring_patterns": len(self.recurring_groups),
                "active_patterns": len(self.recurring_groups) - forgotten_count,
                "forgotten_subscriptions": forgotten_count,
                "monthly_recurring_total": round(monthly_total + weekly_total * 4.33, 2),
                "weekly_recurring_total": round(weekly_total, 2),
            }
        }
