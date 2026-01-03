"""Models for the reports domain."""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Boolean, Date, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime, date
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid

from app.shared.database import Base


class ReportFormat(str, Enum):
    """Supported report formats."""
    PDF = "pdf"
    EXCEL = "excel"
    JSON = "json"


class ReportType(str, Enum):
    """Types of reports."""
    MONTHLY_SUMMARY = "monthly_summary"
    QUARTERLY_SUMMARY = "quarterly_summary"
    ANNUAL_SUMMARY = "annual_summary"
    CATEGORY_BREAKDOWN = "category_breakdown"
    CUSTOM_PERIOD = "custom_period"


class ReportStatus(str, Enum):
    """Report generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class Report(Base):
    """Database model for generated reports."""
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=True)
    report_type = Column(String, nullable=False)
    report_format = Column(String, nullable=False)
    title = Column(String(200), nullable=False)
    status = Column(String, default=ReportStatus.PENDING.value)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    file_path = Column(String, nullable=True)  # Path to generated file
    file_size = Column(Integer, nullable=True)  # Size in bytes
    metadata_json = Column(JSONB, nullable=True)  # Report metadata/config
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


# Data classes for report generation

@dataclass
class ReportSection:
    """A section in a report."""
    title: str
    content: str  # Markdown/text content
    data: Dict[str, Any] = field(default_factory=dict)
    charts: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CategorySummary:
    """Summary for a single category."""
    name: str
    total: float
    transaction_count: int
    percentage: float
    average_transaction: float
    top_merchants: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PeriodSummary:
    """Summary for a period (day/week/month)."""
    label: str
    total: float
    transaction_count: int
    start_date: date
    end_date: date
    category_breakdown: Dict[str, float] = field(default_factory=dict)


@dataclass
class ReportData:
    """Complete data for generating a report."""
    title: str
    subtitle: str
    period_start: date
    period_end: date
    generated_at: datetime
    
    # Summary stats
    total_income: float
    total_expenses: float
    net_change: float
    transaction_count: int
    
    # Breakdowns
    categories: List[CategorySummary] = field(default_factory=list)
    monthly_trends: List[PeriodSummary] = field(default_factory=list)
    weekly_trends: List[PeriodSummary] = field(default_factory=list)
    
    # Insights
    insights: List[Dict[str, Any]] = field(default_factory=list)
    recurring: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    currency: str = "AED"
    account_names: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat(),
            },
            "generated_at": self.generated_at.isoformat(),
            "summary": {
                "total_income": round(self.total_income, 2),
                "total_expenses": round(self.total_expenses, 2),
                "net_change": round(self.net_change, 2),
                "transaction_count": self.transaction_count,
            },
            "categories": [
                {
                    "name": c.name,
                    "total": round(c.total, 2),
                    "transaction_count": c.transaction_count,
                    "percentage": round(c.percentage, 1),
                    "average_transaction": round(c.average_transaction, 2),
                    "top_merchants": c.top_merchants[:5],
                }
                for c in self.categories
            ],
            "monthly_trends": [
                {
                    "label": m.label,
                    "total": round(m.total, 2),
                    "transaction_count": m.transaction_count,
                }
                for m in self.monthly_trends
            ],
            "weekly_trends": [
                {
                    "label": w.label,
                    "total": round(w.total, 2),
                    "transaction_count": w.transaction_count,
                }
                for w in self.weekly_trends
            ],
            "insights": self.insights,
            "recurring": self.recurring,
            "currency": self.currency,
            "accounts": self.account_names,
        }

