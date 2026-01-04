"""Router for reports endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel
from pathlib import Path

from app.shared.filtered_query import FilteredQueryContext, get_filtered_context
from .service import ReportService
from .models import ReportFormat, ReportType, ReportStatus


router = APIRouter(prefix="/api/reports", tags=["reports"])


# Pydantic models
class GenerateReportRequest(BaseModel):
    """Request model for generating a report."""
    report_type: str
    report_format: str
    period_start: date
    period_end: date
    title: Optional[str] = None


class ReportResponse(BaseModel):
    """Response model for a report."""
    id: str
    title: str
    report_type: str
    report_format: str
    status: str
    period_start: date
    period_end: date
    file_size: Optional[int]
    created_at: str
    completed_at: Optional[str]


class ReportListResponse(BaseModel):
    """Response model for list of reports."""
    reports: List[ReportResponse]
    count: int


@router.post("/generate", response_model=ReportResponse)
def generate_report(
    request: GenerateReportRequest,
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """
    Generate a financial report.
    
    Supports PDF, Excel, and JSON formats with various report types:
    - monthly_summary: Monthly financial summary
    - quarterly_summary: Quarterly financial summary
    - annual_summary: Annual financial summary
    - category_breakdown: Detailed category analysis
    - custom_period: Custom date range report
    """
    try:
        report_type = ReportType(request.report_type)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid report_type. Must be one of: {[t.value for t in ReportType]}"
        )
    
    try:
        report_format = ReportFormat(request.report_format)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid report_format. Must be one of: {[f.value for f in ReportFormat]}"
        )
    
    if request.period_start > request.period_end:
        raise HTTPException(status_code=400, detail="period_start must be before period_end")
    
    report = ReportService.generate_report(
        db=ctx.db,
        user_id=ctx.user_id,
        report_type=report_type,
        report_format=report_format,
        period_start=request.period_start,
        period_end=request.period_end,
        person_id=str(ctx.person_id) if ctx.person_id else None,
        title=request.title,
    )
    
    return ReportResponse(
        id=str(report.id),
        title=report.title,
        report_type=report.report_type,
        report_format=report.report_format,
        status=report.status,
        period_start=report.period_start,
        period_end=report.period_end,
        file_size=report.file_size,
        created_at=report.created_at.isoformat(),
        completed_at=report.completed_at.isoformat() if report.completed_at else None,
    )


@router.get("/", response_model=ReportListResponse)
def list_reports(
    limit: int = Query(20, ge=1, le=100),
    include_failed: bool = Query(False),
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """List all reports for the user."""
    reports = ReportService.get_user_reports(
        db=ctx.db,
        user_id=ctx.user_id,
        limit=limit,
        include_failed=include_failed,
        person_id=str(ctx.person_id) if ctx.person_id else None,
    )
    
    return ReportListResponse(
        reports=[
            ReportResponse(
                id=str(r.id),
                title=r.title,
                report_type=r.report_type,
                report_format=r.report_format,
                status=r.status,
                period_start=r.period_start,
                period_end=r.period_end,
                file_size=r.file_size,
                created_at=r.created_at.isoformat(),
                completed_at=r.completed_at.isoformat() if r.completed_at else None,
            )
            for r in reports
        ],
        count=len(reports),
    )


@router.get("/{report_id}")
def get_report(
    report_id: str,
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """Get report details by ID."""
    report = ReportService.get_report(ctx.db, report_id, ctx.user_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {
        "id": str(report.id),
        "title": report.title,
        "report_type": report.report_type,
        "report_format": report.report_format,
        "status": report.status,
        "period_start": report.period_start.isoformat(),
        "period_end": report.period_end.isoformat(),
        "file_path": report.file_path,
        "file_size": report.file_size,
        "metadata": report.metadata_json,
        "created_at": report.created_at.isoformat(),
        "completed_at": report.completed_at.isoformat() if report.completed_at else None,
        "error_message": report.error_message,
    }


@router.get("/{report_id}/download")
def download_report(
    report_id: str,
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """Download a generated report file."""
    report = ReportService.get_report(ctx.db, report_id, ctx.user_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.status != ReportStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Report is not ready for download")
    
    if not report.file_path or not Path(report.file_path).exists():
        raise HTTPException(status_code=404, detail="Report file not found")
    
    # Determine media type
    file_ext = Path(report.file_path).suffix.lower()
    media_types = {
        ".pdf": "application/pdf",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".json": "application/json",
        ".csv": "text/csv",
        ".txt": "text/plain",
    }
    media_type = media_types.get(file_ext, "application/octet-stream")
    
    filename = f"{report.title.replace(' ', '_')}{file_ext}"
    
    return FileResponse(
        path=report.file_path,
        media_type=media_type,
        filename=filename,
    )


@router.delete("/{report_id}")
def delete_report(
    report_id: str,
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """Delete a report and its file."""
    success = ReportService.delete_report(ctx.db, report_id, ctx.user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {"message": "Report deleted successfully"}


@router.get("/types/available")
def get_available_report_types():
    """Get available report types and formats."""
    return {
        "report_types": [
            {"value": t.value, "label": t.value.replace("_", " ").title()}
            for t in ReportType
        ],
        "report_formats": [
            {"value": f.value, "label": f.value.upper()}
            for f in ReportFormat
        ],
    }


@router.post("/generate/monthly")
def generate_monthly_report(
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    year: int = Query(..., ge=2000, le=2100, description="Year"),
    report_format: str = Query("pdf", description="Output format"),
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """Quick endpoint to generate a monthly report."""
    from calendar import monthrange
    
    period_start = date(year, month, 1)
    _, last_day = monthrange(year, month)
    period_end = date(year, month, last_day)
    
    try:
        fmt = ReportFormat(report_format)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid format")
    
    report = ReportService.generate_report(
        db=ctx.db,
        user_id=ctx.user_id,
        report_type=ReportType.MONTHLY_SUMMARY,
        report_format=fmt,
        period_start=period_start,
        period_end=period_end,
        person_id=str(ctx.person_id) if ctx.person_id else None,
    )
    
    return {
        "id": str(report.id),
        "title": report.title,
        "status": report.status,
        "download_url": f"/api/reports/{report.id}/download",
    }


@router.post("/generate/custom")
def generate_custom_report(
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    report_format: str = Query("pdf", description="Output format"),
    include_insights: bool = Query(True, description="Include insights section"),
    include_recurring: bool = Query(True, description="Include recurring patterns"),
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """Generate a custom period report with configurable sections."""
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")
    
    try:
        fmt = ReportFormat(report_format)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid format")
    
    report = ReportService.generate_report(
        db=ctx.db,
        user_id=ctx.user_id,
        report_type=ReportType.CUSTOM_PERIOD,
        report_format=fmt,
        period_start=start_date,
        period_end=end_date,
        person_id=str(ctx.person_id) if ctx.person_id else None,
    )
    
    return {
        "id": str(report.id),
        "title": report.title,
        "status": report.status,
        "download_url": f"/api/reports/{report.id}/download",
    }
