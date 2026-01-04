"""Tests for the refactored reports system with sections."""
import pytest
from datetime import date
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

from app.domains.reports.models import (
    Report,
    ReportSection,
    SectionType,
    SectionFilters,
    SectionContent,
    MoveDirection,
)
from app.domains.reports.service import ReportService
from app.domains.persons.models import Person


class TestReportServiceUnit:
    """Unit tests for ReportService."""

    def test_section_type_names_defined(self):
        """All section types have display names."""
        for section_type in SectionType:
            assert section_type.value in ReportService.SECTION_TYPE_NAMES

    def test_default_filters_structure(self):
        """Default filters have required fields."""
        filters = ReportService._get_default_filters()
        
        assert 'start_date' in filters
        assert 'end_date' in filters
        assert 'group_by' in filters
        assert filters['group_by'] == 'month'

    def test_generate_section_title_custom_title_priority(self):
        """Custom title should take precedence over auto-generated."""
        section = MagicMock(spec=ReportSection)
        section.custom_title = "My Custom Title"
        section.section_type = SectionType.EXPENSE_OVERVIEW.value
        section.filters_json = {"start_date": "2025-01-01", "end_date": "2025-12-31"}
        
        title = ReportService.generate_section_title(section)
        
        assert title == "My Custom Title"

    def test_generate_section_title_auto_summary(self):
        """Summary section auto-generates simple title."""
        section = MagicMock(spec=ReportSection)
        section.custom_title = None
        section.section_type = SectionType.SUMMARY.value
        section.filters_json = {"start_date": "2025-01-01", "end_date": "2025-12-31"}
        
        title = ReportService.generate_section_title(section)
        
        assert "Summary" in title

    def test_generate_section_title_expense_overview_monthly(self):
        """Expense overview section includes Monthly prefix."""
        section = MagicMock(spec=ReportSection)
        section.custom_title = None
        section.section_type = SectionType.EXPENSE_OVERVIEW.value
        section.filters_json = {
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "group_by": "month"
        }
        
        title = ReportService.generate_section_title(section)
        
        assert "Monthly" in title
        assert "Expense Overview" in title

    def test_generate_section_title_expense_overview_weekly(self):
        """Expense overview section includes Weekly prefix."""
        section = MagicMock(spec=ReportSection)
        section.custom_title = None
        section.section_type = SectionType.EXPENSE_OVERVIEW.value
        section.filters_json = {
            "start_date": "2025-01-01",
            "end_date": "2025-03-31",
            "group_by": "week"
        }
        
        title = ReportService.generate_section_title(section)
        
        assert "Weekly" in title
        assert "Expense Overview" in title


class TestReportServiceIntegration:
    """Integration tests for ReportService with database."""

    @pytest.fixture
    def db_session(self, test_db):
        """Get test database session."""
        return test_db

    @pytest.fixture
    def test_user_id(self):
        return "test-user-reports"

    @pytest.fixture
    def test_person(self, db_session, test_user_id):
        """Create a test person."""
        person = Person(
            user_id=test_user_id,
            name="Test Person",
            is_active=True
        )
        db_session.add(person)
        db_session.commit()
        db_session.refresh(person)
        return person

    def test_create_report_auto_name(self, db_session, test_user_id, test_person):
        """Creating a report auto-generates name."""
        report = ReportService.create_report(
            db=db_session,
            user_id=test_user_id,
            person_id=test_person.id,
        )
        
        assert report is not None
        assert report.name == f"{test_person.name} Report"
        assert report.person_id == test_person.id

    def test_create_report_with_custom_name(self, db_session, test_user_id, test_person):
        """Creating a report with custom name uses it."""
        custom_name = "Q1 2025 Financial Report"
        report = ReportService.create_report(
            db=db_session,
            user_id=test_user_id,
            person_id=test_person.id,
            name=custom_name,
        )
        
        assert report.name == custom_name

    def test_create_report_has_summary_section(self, db_session, test_user_id, test_person):
        """New report automatically has a Summary section."""
        report = ReportService.create_report(
            db=db_session,
            user_id=test_user_id,
            person_id=test_person.id,
        )
        
        # Refresh to load sections
        db_session.refresh(report)
        
        assert len(report.sections) == 1
        assert report.sections[0].section_type == SectionType.SUMMARY.value
        assert report.sections[0].position == 0

    def test_create_report_sequential_naming(self, db_session, test_user_id, test_person):
        """Multiple reports get sequential naming."""
        report1 = ReportService.create_report(
            db=db_session,
            user_id=test_user_id,
            person_id=test_person.id,
        )
        
        report2 = ReportService.create_report(
            db=db_session,
            user_id=test_user_id,
            person_id=test_person.id,
        )
        
        assert report1.name == f"{test_person.name} Report"
        assert report2.name == f"{test_person.name} Report 2"

    def test_add_section(self, db_session, test_user_id, test_person):
        """Adding a section to a report."""
        report = ReportService.create_report(
            db=db_session,
            user_id=test_user_id,
            person_id=test_person.id,
        )
        
        section = ReportService.add_section(
            db=db_session,
            report_id=str(report.id),
            user_id=test_user_id,
            section_type=SectionType.EXPENSE_OVERVIEW,
        )
        
        assert section is not None
        assert section.section_type == SectionType.EXPENSE_OVERVIEW.value
        assert section.position == 1  # After Summary

    def test_add_multiple_same_section_type(self, db_session, test_user_id, test_person):
        """Can add multiple sections of same type."""
        report = ReportService.create_report(
            db=db_session,
            user_id=test_user_id,
            person_id=test_person.id,
        )
        
        section1 = ReportService.add_section(
            db=db_session,
            report_id=str(report.id),
            user_id=test_user_id,
            section_type=SectionType.INSIGHTS,
        )
        
        section2 = ReportService.add_section(
            db=db_session,
            report_id=str(report.id),
            user_id=test_user_id,
            section_type=SectionType.INSIGHTS,
        )
        
        assert section1.id != section2.id
        assert section1.position == 1
        assert section2.position == 2

    def test_update_section_custom_title(self, db_session, test_user_id, test_person):
        """Update section with custom title."""
        report = ReportService.create_report(
            db=db_session,
            user_id=test_user_id,
            person_id=test_person.id,
        )
        
        section = ReportService.add_section(
            db=db_session,
            report_id=str(report.id),
            user_id=test_user_id,
            section_type=SectionType.TOP_CATEGORIES,
        )
        
        updated = ReportService.update_section(
            db=db_session,
            report_id=str(report.id),
            section_id=section.id,
            user_id=test_user_id,
            custom_title="My Top Categories",
        )
        
        assert updated.custom_title == "My Top Categories"

    def test_delete_section_not_summary(self, db_session, test_user_id, test_person):
        """Can delete non-Summary sections."""
        report = ReportService.create_report(
            db=db_session,
            user_id=test_user_id,
            person_id=test_person.id,
        )
        
        section = ReportService.add_section(
            db=db_session,
            report_id=str(report.id),
            user_id=test_user_id,
            section_type=SectionType.TRENDS,
        )
        
        success = ReportService.delete_section(
            db=db_session,
            report_id=str(report.id),
            section_id=section.id,
            user_id=test_user_id,
        )
        
        assert success is True

    def test_cannot_delete_summary_section(self, db_session, test_user_id, test_person):
        """Cannot delete Summary section."""
        report = ReportService.create_report(
            db=db_session,
            user_id=test_user_id,
            person_id=test_person.id,
        )
        
        db_session.refresh(report)
        summary_section = report.sections[0]
        
        success = ReportService.delete_section(
            db=db_session,
            report_id=str(report.id),
            section_id=summary_section.id,
            user_id=test_user_id,
        )
        
        assert success is False

    def test_move_section_down(self, db_session, test_user_id, test_person):
        """Move section down."""
        report = ReportService.create_report(
            db=db_session,
            user_id=test_user_id,
            person_id=test_person.id,
        )
        
        section1 = ReportService.add_section(
            db=db_session,
            report_id=str(report.id),
            user_id=test_user_id,
            section_type=SectionType.EXPENSE_OVERVIEW,
        )
        
        section2 = ReportService.add_section(
            db=db_session,
            report_id=str(report.id),
            user_id=test_user_id,
            section_type=SectionType.TOP_CATEGORIES,
        )
        
        # Move section1 down
        success = ReportService.move_section(
            db=db_session,
            report_id=str(report.id),
            section_id=section1.id,
            user_id=test_user_id,
            direction=MoveDirection.DOWN,
        )
        
        assert success is True
        db_session.refresh(section1)
        db_session.refresh(section2)
        assert section1.position == 2
        assert section2.position == 1

    def test_move_section_up(self, db_session, test_user_id, test_person):
        """Move section up."""
        report = ReportService.create_report(
            db=db_session,
            user_id=test_user_id,
            person_id=test_person.id,
        )
        
        section1 = ReportService.add_section(
            db=db_session,
            report_id=str(report.id),
            user_id=test_user_id,
            section_type=SectionType.EXPENSE_OVERVIEW,
        )
        
        section2 = ReportService.add_section(
            db=db_session,
            report_id=str(report.id),
            user_id=test_user_id,
            section_type=SectionType.TOP_CATEGORIES,
        )
        
        # Move section2 up
        success = ReportService.move_section(
            db=db_session,
            report_id=str(report.id),
            section_id=section2.id,
            user_id=test_user_id,
            direction=MoveDirection.UP,
        )
        
        assert success is True
        db_session.refresh(section1)
        db_session.refresh(section2)
        assert section2.position == 1
        assert section1.position == 2

    def test_cannot_move_summary_section(self, db_session, test_user_id, test_person):
        """Cannot move Summary section."""
        report = ReportService.create_report(
            db=db_session,
            user_id=test_user_id,
            person_id=test_person.id,
        )
        
        db_session.refresh(report)
        summary_section = report.sections[0]
        
        success = ReportService.move_section(
            db=db_session,
            report_id=str(report.id),
            section_id=summary_section.id,
            user_id=test_user_id,
            direction=MoveDirection.DOWN,
        )
        
        assert success is False

    def test_list_reports_all_persons(self, db_session, test_user_id, test_person):
        """List reports shows all persons' reports."""
        # Create another person
        person2 = Person(
            user_id=test_user_id,
            name="Second Person",
            is_active=False
        )
        db_session.add(person2)
        db_session.commit()
        db_session.refresh(person2)
        
        # Create reports for both persons
        report1 = ReportService.create_report(
            db=db_session,
            user_id=test_user_id,
            person_id=test_person.id,
        )
        
        report2 = ReportService.create_report(
            db=db_session,
            user_id=test_user_id,
            person_id=person2.id,
        )
        
        # List all
        reports = ReportService.list_reports(
            db=db_session,
            user_id=test_user_id,
        )
        
        report_ids = [str(r.id) for r in reports]
        assert str(report1.id) in report_ids
        assert str(report2.id) in report_ids

    def test_list_reports_filter_by_person(self, db_session, test_user_id, test_person):
        """List reports can filter by person."""
        # Create another person
        person2 = Person(
            user_id=test_user_id,
            name="Another Person",
            is_active=False
        )
        db_session.add(person2)
        db_session.commit()
        db_session.refresh(person2)
        
        # Create reports
        report1 = ReportService.create_report(
            db=db_session,
            user_id=test_user_id,
            person_id=test_person.id,
        )
        
        report2 = ReportService.create_report(
            db=db_session,
            user_id=test_user_id,
            person_id=person2.id,
        )
        
        # Filter by first person
        reports = ReportService.list_reports(
            db=db_session,
            user_id=test_user_id,
            person_id=test_person.id,
        )
        
        assert len(reports) == 1
        assert str(reports[0].id) == str(report1.id)

    def test_duplicate_report(self, db_session, test_user_id, test_person):
        """Duplicate a report."""
        # Create original
        original = ReportService.create_report(
            db=db_session,
            user_id=test_user_id,
            person_id=test_person.id,
            name="Original Report",
        )
        
        # Add a section
        ReportService.add_section(
            db=db_session,
            report_id=str(original.id),
            user_id=test_user_id,
            section_type=SectionType.INSIGHTS,
        )
        
        # Duplicate
        duplicate = ReportService.duplicate_report(
            db=db_session,
            report_id=str(original.id),
            user_id=test_user_id,
        )
        
        assert duplicate is not None
        assert duplicate.id != original.id
        assert duplicate.name == "Original Report (Copy)"
        
        db_session.refresh(duplicate)
        # Should have 2 sections (Summary + Insights)
        assert len(duplicate.sections) == 2

    def test_update_report_name(self, db_session, test_user_id, test_person):
        """Update report name."""
        report = ReportService.create_report(
            db=db_session,
            user_id=test_user_id,
            person_id=test_person.id,
        )
        
        updated = ReportService.update_report(
            db=db_session,
            report_id=str(report.id),
            user_id=test_user_id,
            name="Updated Report Name",
        )
        
        assert updated.name == "Updated Report Name"

    def test_delete_report(self, db_session, test_user_id, test_person):
        """Delete a report."""
        report = ReportService.create_report(
            db=db_session,
            user_id=test_user_id,
            person_id=test_person.id,
        )
        report_id = str(report.id)
        
        success = ReportService.delete_report(
            db=db_session,
            report_id=report_id,
            user_id=test_user_id,
        )
        
        assert success is True
        
        # Verify deleted
        fetched = ReportService.get_report(db_session, report_id, test_user_id)
        assert fetched is None


class TestReportSectionFilters:
    """Tests for section filter handling."""

    def test_section_inherits_summary_filters(self, test_db, test_user):
        """New sections inherit filters from Summary."""
        from app.domains.persons.models import Person
        
        # Create person
        person = Person(user_id=test_user, name="Filter Test Person", is_active=True)
        test_db.add(person)
        test_db.commit()
        test_db.refresh(person)
        
        # Create report (gets Summary with default filters)
        report = ReportService.create_report(
            db=test_db,
            user_id=test_user,
            person_id=person.id,
        )
        
        # Update Summary filters
        test_db.refresh(report)
        summary = report.sections[0]
        ReportService.update_section(
            db=test_db,
            report_id=str(report.id),
            section_id=summary.id,
            user_id=test_user,
            filters=SectionFilters(
                start_date="2025-06-01",
                end_date="2025-06-30",
            ),
        )
        
        # Add new section - should inherit Summary filters
        new_section = ReportService.add_section(
            db=test_db,
            report_id=str(report.id),
            user_id=test_user,
            section_type=SectionType.TOP_CATEGORIES,
        )
        
        assert new_section.filters_json is not None
        assert new_section.filters_json.get('start_date') == "2025-06-01"
        assert new_section.filters_json.get('end_date') == "2025-06-30"

