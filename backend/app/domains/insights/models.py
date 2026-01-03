"""Models for financial insights domain."""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Boolean, Date, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime, date
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid

from app.shared.database import Base


class InsightType(str, Enum):
    """Types of financial insights."""
    SPENDING_TREND = "spending_trend"
    CATEGORY_ANALYSIS = "category_analysis"
    ANOMALY_DETECTION = "anomaly_detection"
    BUDGET_ALERT = "budget_alert"
    SAVINGS_OPPORTUNITY = "savings_opportunity"
    RECURRING_INSIGHT = "recurring_insight"
    COMPARISON = "comparison"
    PREDICTION = "prediction"


class InsightSeverity(str, Enum):
    """Severity levels for insights."""
    INFO = "info"
    TIP = "tip"
    WARNING = "warning"
    ALERT = "alert"


class Insight(Base):
    """Database model for generated insights."""
    __tablename__ = "insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=True)
    insight_type = Column(String, nullable=False)
    severity = Column(String, default=InsightSeverity.INFO.value)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    data_json = Column(JSONB, nullable=True)  # Supporting data/metrics
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    is_dismissed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


# Data classes for insight generation (not persisted)

@dataclass
class SpendingTrend:
    """Spending trend analysis result."""
    period: str  # "weekly", "monthly"
    current_total: float
    previous_total: float
    change_percent: float
    trend_direction: str  # "up", "down", "stable"
    category_breakdown: Dict[str, float] = field(default_factory=dict)
    top_increase_category: Optional[str] = None
    top_decrease_category: Optional[str] = None


@dataclass
class CategoryInsight:
    """Category-specific insight."""
    category: str
    total_spent: float
    transaction_count: int
    avg_transaction: float
    percentage_of_total: float
    comparison_to_average: float  # vs historical average
    top_merchants: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AnomalyInsight:
    """Unusual spending pattern detected."""
    transaction_id: int
    merchant: str
    amount: float
    date: date
    anomaly_type: str  # "unusually_high", "unusual_merchant", "unusual_time"
    confidence: float
    explanation: str


@dataclass
class SavingsOpportunity:
    """Potential savings opportunity."""
    category: str
    current_monthly_avg: float
    suggested_target: float
    potential_savings: float
    recommendation: str


@dataclass 
class GeneratedInsight:
    """A generated insight with algorithm data and LLM description."""
    insight_type: InsightType
    severity: InsightSeverity
    title: str
    description: str  # LLM-generated natural language
    data: Dict[str, Any]
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "type": self.insight_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "data": self.data,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
        }


@dataclass
class InsightsReport:
    """Collection of insights for a user."""
    insights: List[GeneratedInsight]
    generated_at: datetime
    period_analyzed: str
    transaction_count: int
    total_spent: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "insights": [i.to_dict() for i in self.insights],
            "generated_at": self.generated_at.isoformat(),
            "period_analyzed": self.period_analyzed,
            "transaction_count": self.transaction_count,
            "total_spent": round(self.total_spent, 2),
            "summary": {
                "total_insights": len(self.insights),
                "alerts": sum(1 for i in self.insights if i.severity == InsightSeverity.ALERT),
                "warnings": sum(1 for i in self.insights if i.severity == InsightSeverity.WARNING),
                "tips": sum(1 for i in self.insights if i.severity == InsightSeverity.TIP),
            }
        }

