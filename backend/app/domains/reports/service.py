"""Service for managing reports and sections."""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import uuid

from app.domains.reports.models import (
    Report,
    ReportSection,
    SectionType,
    SectionFilters,
    SectionContent,
    MoveDirection,
)
from app.domains.persons.models import Person


class ReportService:
    """Service for managing reports and their sections."""

    # Section type display names
    SECTION_TYPE_NAMES = {
        SectionType.SUMMARY.value: "Summary",
        SectionType.EXPENSE_OVERVIEW.value: "Expense Overview",
        SectionType.TOP_CATEGORIES.value: "Top Spending Categories",
        SectionType.CATEGORY_DETAILS.value: "Category Details",
        SectionType.RECURRING.value: "Subscriptions & Recurring",
        SectionType.TRENDS.value: "Trends & Anomalies",
        SectionType.INSIGHTS.value: "Key Insights",
    }

    @classmethod
    def create_report(
        cls,
        db: Session,
        user_id: str,
        person_id: Optional[int] = None,
        name: Optional[str] = None,
    ) -> Report:
        """
        Create a new report with auto-generated name and default Summary section.
        
        Args:
            db: Database session
            user_id: User identifier
            person_id: Person ID (uses active person if not provided)
            name: Optional custom name
            
        Returns:
            Created Report with Summary section
        """
        # Get person for naming
        person = None
        if person_id:
            person = db.query(Person).filter(Person.id == person_id).first()
        
        # Auto-generate name if not provided
        if not name:
            name = cls._generate_report_name(db, user_id, person_id, person)
        
        # Create report
        report = Report(
            user_id=user_id,
            person_id=person_id,
            name=name,
        )
        db.add(report)
        db.flush()  # Get the ID
        
        # Create default Summary section with default filters
        default_filters = cls._get_default_filters()
        summary_section = ReportSection(
            report_id=report.id,
            section_type=SectionType.SUMMARY.value,
            position=0,
            filters_json=default_filters,
        )
        db.add(summary_section)
        db.commit()
        db.refresh(report)
        
        return report

    @classmethod
    def _generate_report_name(
        cls,
        db: Session,
        user_id: str,
        person_id: Optional[int],
        person: Optional[Person],
    ) -> str:
        """Generate auto-name for report: "{Person Name} Report" or "{Person Name} Report 2", etc."""
        person_name = person.name if person else "My"
        base_name = f"{person_name} Report"
        
        # Count existing reports for this person
        query = db.query(func.count(Report.id)).filter(Report.user_id == user_id)
        if person_id:
            query = query.filter(Report.person_id == person_id)
        else:
            query = query.filter(Report.person_id.is_(None))
        
        count = query.scalar() or 0
        
        if count == 0:
            return base_name
        else:
            return f"{base_name} {count + 1}"

    @classmethod
    def _get_default_filters(cls) -> Dict[str, Any]:
        """Get default filters (current month)."""
        today = date.today()
        first_day = date(today.year, today.month, 1)
        
        # Last day of current month
        if today.month == 12:
            last_day = date(today.year, 12, 31)
        else:
            last_day = date(today.year, today.month + 1, 1).replace(day=1)
            last_day = last_day.replace(day=1) - __import__('datetime').timedelta(days=1)
        
        return {
            "start_date": first_day.isoformat(),
            "end_date": last_day.isoformat(),
            "group_by": "month",
        }

    @classmethod
    def get_report(
        cls,
        db: Session,
        report_id: str,
        user_id: str,
    ) -> Optional[Report]:
        """Get a report by ID with all sections."""
        return db.query(Report).options(
            joinedload(Report.sections),
            joinedload(Report.person),
        ).filter(
            Report.id == uuid.UUID(report_id),
            Report.user_id == user_id,
        ).first()

    @classmethod
    def list_reports(
        cls,
        db: Session,
        user_id: str,
        person_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Report]:
        """
        List all reports for user (optionally filtered by person).
        Shows reports from ALL persons by default.
        """
        query = db.query(Report).options(
            joinedload(Report.person),
        ).filter(Report.user_id == user_id)
        
        if person_id is not None:
            query = query.filter(Report.person_id == person_id)
        
        return query.order_by(Report.updated_at.desc()).limit(limit).all()

    @classmethod
    def update_report(
        cls,
        db: Session,
        report_id: str,
        user_id: str,
        name: str,
    ) -> Optional[Report]:
        """Update report name."""
        report = cls.get_report(db, report_id, user_id)
        if not report:
            return None
        
        report.name = name
        report.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(report)
        return report

    @classmethod
    def delete_report(
        cls,
        db: Session,
        report_id: str,
        user_id: str,
    ) -> bool:
        """Delete a report and all its sections."""
        report = db.query(Report).filter(
            Report.id == uuid.UUID(report_id),
            Report.user_id == user_id,
        ).first()
        
        if not report:
            return False
        
        db.delete(report)
        db.commit()
        return True

    @classmethod
    def duplicate_report(
        cls,
        db: Session,
        report_id: str,
        user_id: str,
    ) -> Optional[Report]:
        """Duplicate a report with all its sections."""
        original = cls.get_report(db, report_id, user_id)
        if not original:
            return None
        
        # Create new report
        new_report = Report(
            user_id=user_id,
            person_id=original.person_id,
            name=f"{original.name} (Copy)",
        )
        db.add(new_report)
        db.flush()
        
        # Copy all sections
        for section in original.sections:
            new_section = ReportSection(
                report_id=new_report.id,
                section_type=section.section_type,
                position=section.position,
                custom_title=section.custom_title,
                filters_json=section.filters_json,
                content_json=section.content_json,
            )
            db.add(new_section)
        
        db.commit()
        db.refresh(new_report)
        return new_report

    # Section management

    @classmethod
    def add_section(
        cls,
        db: Session,
        report_id: str,
        user_id: str,
        section_type: SectionType,
        custom_title: Optional[str] = None,
        filters: Optional[SectionFilters] = None,
    ) -> Optional[ReportSection]:
        """Add a new section to a report."""
        report = db.query(Report).filter(
            Report.id == uuid.UUID(report_id),
            Report.user_id == user_id,
        ).first()
        
        if not report:
            return None
        
        # Get max position (handle 0 being falsy)
        max_pos_result = db.query(func.max(ReportSection.position)).filter(
            ReportSection.report_id == report.id
        ).scalar()
        max_pos = max_pos_result if max_pos_result is not None else -1
        
        # Get default filters from Summary section if available
        filters_json = None
        if filters:
            filters_json = filters.model_dump(exclude_none=True)
        else:
            # Inherit filters from Summary section
            summary = db.query(ReportSection).filter(
                ReportSection.report_id == report.id,
                ReportSection.section_type == SectionType.SUMMARY.value,
            ).first()
            if summary and summary.filters_json:
                filters_json = summary.filters_json.copy()
        
        section = ReportSection(
            report_id=report.id,
            section_type=section_type.value,
            position=max_pos + 1,
            custom_title=custom_title,
            filters_json=filters_json,
        )
        db.add(section)
        
        # Update report timestamp
        report.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(section)
        return section

    @classmethod
    def update_section(
        cls,
        db: Session,
        report_id: str,
        section_id: int,
        user_id: str,
        custom_title: Optional[str] = None,
        filters: Optional[SectionFilters] = None,
        content: Optional[SectionContent] = None,
    ) -> Optional[ReportSection]:
        """Update a section's title, filters, or content."""
        # Verify report ownership
        report = db.query(Report).filter(
            Report.id == uuid.UUID(report_id),
            Report.user_id == user_id,
        ).first()
        
        if not report:
            return None
        
        section = db.query(ReportSection).filter(
            ReportSection.id == section_id,
            ReportSection.report_id == report.id,
        ).first()
        
        if not section:
            return None
        
        if custom_title is not None:
            section.custom_title = custom_title if custom_title else None
        
        if filters is not None:
            section.filters_json = filters.model_dump(exclude_none=True)
        
        if content is not None:
            section.content_json = content.model_dump(exclude_none=True)
        
        section.updated_at = datetime.utcnow()
        report.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(section)
        return section

    @classmethod
    def delete_section(
        cls,
        db: Session,
        report_id: str,
        section_id: int,
        user_id: str,
    ) -> bool:
        """Delete a section (except Summary)."""
        # Verify report ownership
        report = db.query(Report).filter(
            Report.id == uuid.UUID(report_id),
            Report.user_id == user_id,
        ).first()
        
        if not report:
            return False
        
        section = db.query(ReportSection).filter(
            ReportSection.id == section_id,
            ReportSection.report_id == report.id,
        ).first()
        
        if not section:
            return False
        
        # Cannot delete Summary section
        if section.section_type == SectionType.SUMMARY.value:
            return False
        
        db.delete(section)
        
        # Re-order remaining sections
        remaining = db.query(ReportSection).filter(
            ReportSection.report_id == report.id,
        ).order_by(ReportSection.position).all()
        
        for i, s in enumerate(remaining):
            s.position = i
        
        report.updated_at = datetime.utcnow()
        db.commit()
        return True

    @classmethod
    def move_section(
        cls,
        db: Session,
        report_id: str,
        section_id: int,
        user_id: str,
        direction: MoveDirection,
    ) -> bool:
        """Move a section up or down."""
        # Verify report ownership
        report = db.query(Report).filter(
            Report.id == uuid.UUID(report_id),
            Report.user_id == user_id,
        ).first()
        
        if not report:
            return False
        
        section = db.query(ReportSection).filter(
            ReportSection.id == section_id,
            ReportSection.report_id == report.id,
        ).first()
        
        if not section:
            return False
        
        # Cannot move Summary section
        if section.section_type == SectionType.SUMMARY.value:
            return False
        
        # Get all sections ordered by position
        sections = db.query(ReportSection).filter(
            ReportSection.report_id == report.id,
        ).order_by(ReportSection.position).all()
        
        current_idx = next((i for i, s in enumerate(sections) if s.id == section_id), None)
        if current_idx is None:
            return False
        
        if direction == MoveDirection.UP:
            # Can't move above Summary (position 0)
            if current_idx <= 1:
                return False
            swap_idx = current_idx - 1
        else:  # DOWN
            if current_idx >= len(sections) - 1:
                return False
            swap_idx = current_idx + 1
        
        # Swap positions
        sections[current_idx].position, sections[swap_idx].position = \
            sections[swap_idx].position, sections[current_idx].position
        
        report.updated_at = datetime.utcnow()
        db.commit()
        return True

    @classmethod
    def generate_section_title(
        cls,
        section: ReportSection,
    ) -> str:
        """Generate display title for a section."""
        # Custom title takes precedence
        if section.custom_title:
            return section.custom_title
        
        base_name = cls.SECTION_TYPE_NAMES.get(
            section.section_type,
            section.section_type.replace("_", " ").title()
        )
        
        # Build date range string
        filters = section.filters_json or {}
        start_date = filters.get("start_date")
        end_date = filters.get("end_date")
        
        date_range = ""
        if start_date and end_date:
            try:
                start = datetime.fromisoformat(start_date)
                end = datetime.fromisoformat(end_date)
                date_range = f"{start.strftime('%b %d, %Y')} – {end.strftime('%b %d, %Y')}"
            except (ValueError, TypeError):
                pass
        
        # Add grouping prefix for expense_overview
        if section.section_type == SectionType.EXPENSE_OVERVIEW.value:
            group_by = filters.get("group_by", "month")
            grouping = "Monthly" if group_by == "month" else "Weekly"
            if date_range:
                return f"{grouping} {base_name} for {date_range}"
            return f"{grouping} {base_name}"
        
        if date_range:
            return f"{base_name} for {date_range}"
        return base_name

    @classmethod
    def to_response(cls, report: Report) -> Dict[str, Any]:
        """Convert Report to response dict."""
        return {
            "id": str(report.id),
            "name": report.name,
            "person_id": report.person_id,
            "person_name": report.person.name if report.person else None,
            "sections": [cls.section_to_response(s) for s in report.sections],
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "updated_at": report.updated_at.isoformat() if report.updated_at else None,
        }

    @classmethod
    def section_to_response(cls, section: ReportSection) -> Dict[str, Any]:
        """Convert ReportSection to response dict."""
        return {
            "id": section.id,
            "section_type": section.section_type,
            "position": section.position,
            "custom_title": section.custom_title,
            "display_title": cls.generate_section_title(section),
            "filters": section.filters_json,
            "content": section.content_json,
            "created_at": section.created_at.isoformat() if section.created_at else None,
            "updated_at": section.updated_at.isoformat() if section.updated_at else None,
        }

    @classmethod
    def to_list_item(cls, report: Report) -> Dict[str, Any]:
        """Convert Report to list item dict."""
        return {
            "id": str(report.id),
            "name": report.name,
            "person_id": report.person_id,
            "person_name": report.person.name if report.person else None,
            "section_count": len(report.sections) if report.sections else 0,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "updated_at": report.updated_at.isoformat() if report.updated_at else None,
        }
