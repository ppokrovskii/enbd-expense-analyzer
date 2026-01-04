"""Router for reports endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional, List

from app.shared.filtered_query import FilteredQueryContext, get_filtered_context
from .service import ReportService
from .models import (
    SectionType,
    SectionFilters,
    SectionContent,
    MoveDirection,
    ReportCreate,
    ReportUpdate,
    ReportSectionCreate,
    ReportSectionUpdate,
    MoveSectionRequest,
)


router = APIRouter(prefix="/api/reports", tags=["reports"])


# ============== Section Types (must be before /{report_id} routes) ==============

@router.get("/section-types")
def get_section_types():
    """Get available section types."""
    return {
        "section_types": [
            {
                "value": t.value,
                "label": ReportService.SECTION_TYPE_NAMES.get(t.value, t.value),
                "has_ai_generate": t.value in [
                    SectionType.EXPENSE_OVERVIEW.value,
                    SectionType.RECURRING.value,
                    SectionType.TRENDS.value,
                    SectionType.INSIGHTS.value,
                ],
                "has_grouping": t.value == SectionType.EXPENSE_OVERVIEW.value,
            }
            for t in SectionType
            if t != SectionType.SUMMARY  # Summary is auto-created
        ]
    }


# ============== Report Endpoints ==============

@router.get("/")
def list_reports(
    person_id: Optional[int] = Query(None, description="Filter by person ID"),
    limit: int = Query(50, ge=1, le=100),
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """
    List all reports for the current user.
    By default shows reports from ALL persons.
    Optionally filter by person_id.
    """
    reports = ReportService.list_reports(
        db=ctx.db,
        user_id=ctx.user_id,
        person_id=person_id,
        limit=limit,
    )
    
    return {
        "reports": [ReportService.to_list_item(r) for r in reports],
        "count": len(reports),
    }


@router.post("/")
def create_report(
    request: ReportCreate,
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """
    Create a new empty report with auto-generated name.
    Creates a default Summary section.
    """
    # Use provided person_id or active person
    person_id = request.person_id if request.person_id is not None else ctx.person_id
    
    report = ReportService.create_report(
        db=ctx.db,
        user_id=ctx.user_id,
        person_id=person_id,
        name=request.name,
    )
    
    return ReportService.to_response(report)


@router.get("/{report_id}")
def get_report(
    report_id: str,
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """Get a report with all its sections."""
    report = ReportService.get_report(ctx.db, report_id, ctx.user_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return ReportService.to_response(report)


@router.put("/{report_id}")
def update_report(
    report_id: str,
    request: ReportUpdate,
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """Update report name."""
    report = ReportService.update_report(
        db=ctx.db,
        report_id=report_id,
        user_id=ctx.user_id,
        name=request.name,
    )
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return ReportService.to_response(report)


@router.delete("/{report_id}")
def delete_report(
    report_id: str,
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """Delete a report and all its sections."""
    success = ReportService.delete_report(ctx.db, report_id, ctx.user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {"message": "Report deleted successfully"}


@router.post("/{report_id}/duplicate")
def duplicate_report(
    report_id: str,
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """Duplicate a report with all its sections."""
    report = ReportService.duplicate_report(ctx.db, report_id, ctx.user_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return ReportService.to_response(report)


# ============== Section Endpoints ==============

@router.post("/{report_id}/sections")
def add_section(
    report_id: str,
    request: ReportSectionCreate,
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """Add a new section to a report."""
    section = ReportService.add_section(
        db=ctx.db,
        report_id=report_id,
        user_id=ctx.user_id,
        section_type=request.section_type,
        custom_title=request.custom_title,
        filters=request.filters,
    )
    
    if not section:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return ReportService.section_to_response(section)


@router.put("/{report_id}/sections/{section_id}")
def update_section(
    report_id: str,
    section_id: int,
    request: ReportSectionUpdate,
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """Update a section's title, filters, or content."""
    section = ReportService.update_section(
        db=ctx.db,
        report_id=report_id,
        section_id=section_id,
        user_id=ctx.user_id,
        custom_title=request.custom_title,
        filters=request.filters,
        content=request.content,
    )
    
    if not section:
        raise HTTPException(status_code=404, detail="Report or section not found")
    
    return ReportService.section_to_response(section)


@router.delete("/{report_id}/sections/{section_id}")
def delete_section(
    report_id: str,
    section_id: int,
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """Delete a section (except Summary which cannot be deleted)."""
    success = ReportService.delete_section(
        db=ctx.db,
        report_id=report_id,
        section_id=section_id,
        user_id=ctx.user_id,
    )
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Section not found or cannot be deleted (Summary section cannot be removed)"
        )
    
    return {"message": "Section deleted successfully"}


@router.put("/{report_id}/sections/{section_id}/move")
def move_section(
    report_id: str,
    section_id: int,
    request: MoveSectionRequest,
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """Move a section up or down."""
    success = ReportService.move_section(
        db=ctx.db,
        report_id=report_id,
        section_id=section_id,
        user_id=ctx.user_id,
        direction=request.direction,
    )
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot move section (not found, is Summary, or at boundary)"
        )
    
    # Return updated report
    report = ReportService.get_report(ctx.db, report_id, ctx.user_id)
    return ReportService.to_response(report)


# ============== Export Endpoints ==============

@router.post("/{report_id}/export/pdf")
def export_pdf(
    report_id: str,
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """
    Export report as PDF.
    Returns a URL to trigger client-side PDF generation.
    For WYSIWYG export, the frontend will use html2pdf.js.
    """
    report = ReportService.get_report(ctx.db, report_id, ctx.user_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Return report data for client-side PDF generation
    return {
        "report_id": str(report.id),
        "report_name": report.name,
        "message": "Use client-side PDF generation for WYSIWYG export",
    }
