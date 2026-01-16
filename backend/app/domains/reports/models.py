"""Models for the reports domain."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import uuid

from app.shared.database import Base


class SectionType(str, Enum):
    """Types of report sections."""
    SUMMARY = "summary"
    EXPENSE_OVERVIEW = "expense_overview"
    TOP_CATEGORIES = "top_categories"
    CATEGORY_DETAILS = "category_details"
    RECURRING = "recurring"
    TRENDS = "trends"
    INSIGHTS = "insights"


# SQLAlchemy Models

class Report(Base):
    """Database model for reports."""
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sections = relationship("ReportSection", back_populates="report", cascade="all, delete-orphan", order_by="ReportSection.position")
    workspace = relationship("Workspace", backref="reports")


class ReportSection(Base):
    """Database model for report sections."""
    __tablename__ = "report_sections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    section_type = Column(String(50), nullable=False)
    position = Column(Integer, nullable=False, default=0, index=True)
    custom_title = Column(String(255), nullable=True)
    filters_json = Column(JSONB, nullable=True)
    content_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    report = relationship("Report", back_populates="sections")


# Pydantic Schemas for API

class SectionFilters(BaseModel):
    """Filters for a report section."""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    group_by: Optional[str] = None  # 'week' or 'month', only for expense_overview


class SectionContent(BaseModel):
    """Content for a report section (AI-generated or user-edited)."""
    takeaway: Optional[str] = None  # For summary section
    bullets: Optional[List[str]] = None  # For trends/insights sections
    # Additional content fields can be added as needed


class ReportSectionCreate(BaseModel):
    """Schema for creating a new section."""
    section_type: SectionType
    custom_title: Optional[str] = None
    filters: Optional[SectionFilters] = None


class ReportSectionUpdate(BaseModel):
    """Schema for updating a section."""
    custom_title: Optional[str] = None
    filters: Optional[SectionFilters] = None
    content: Optional[SectionContent] = None


class ReportSectionResponse(BaseModel):
    """Schema for section response."""
    id: int
    section_type: str
    position: int
    custom_title: Optional[str] = None
    display_title: str  # Auto-generated or custom
    filters: Optional[Dict[str, Any]] = None
    content: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ReportCreate(BaseModel):
    """Schema for creating a new report."""
    name: Optional[str] = None  # Auto-generated if not provided
    workspace_id: Optional[int] = None  # Uses active workspace if not provided


class ReportUpdate(BaseModel):
    """Schema for updating a report."""
    name: str = Field(..., min_length=1, max_length=255)


class ReportResponse(BaseModel):
    """Schema for report response."""
    id: str
    name: str
    workspace_id: Optional[int] = None
    workspace_name: Optional[str] = None
    sections: List[ReportSectionResponse] = []
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ReportListItem(BaseModel):
    """Schema for report in list view."""
    id: str
    name: str
    workspace_id: Optional[int] = None
    workspace_name: Optional[str] = None
    section_count: int = 0
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    """Schema for list of reports."""
    reports: List[ReportListItem]
    count: int


class MoveDirection(str, Enum):
    """Direction for moving a section."""
    UP = "up"
    DOWN = "down"


class MoveSectionRequest(BaseModel):
    """Schema for moving a section."""
    direction: MoveDirection
