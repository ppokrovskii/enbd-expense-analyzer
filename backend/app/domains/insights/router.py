"""Router for financial insights endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date
from pydantic import BaseModel

from app.shared.filtered_query import FilteredQueryContext, get_filtered_context
from .service import InsightsService
from .models import InsightType, InsightSeverity


router = APIRouter(prefix="/api/insights", tags=["insights"])


# Pydantic models for API responses
class InsightDataResponse(BaseModel):
    """Data associated with an insight."""
    pass  # Dynamic dict, handled by the dict response


class InsightResponse(BaseModel):
    """Response model for a single insight."""
    type: str
    severity: str
    title: str
    description: str
    data: dict
    period_start: Optional[date]
    period_end: Optional[date]


class InsightsSummaryResponse(BaseModel):
    """Summary of insights."""
    total_insights: int
    alerts: int
    warnings: int
    tips: int


class InsightsReportResponse(BaseModel):
    """Response model for insights report."""
    insights: List[InsightResponse]
    generated_at: str
    period_analyzed: str
    transaction_count: int
    total_spent: float
    summary: InsightsSummaryResponse


class SavedInsightResponse(BaseModel):
    """Response model for a saved insight."""
    id: str
    type: str
    severity: str
    title: str
    description: str
    created_at: str
    is_dismissed: bool


@router.get("/generate")
def generate_insights(
    period_days: int = Query(30, ge=7, le=365, description="Analysis period in days"),
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """
    Generate financial insights for the user.
    
    Analyzes spending patterns, detects anomalies, identifies recurring
    expenses, and finds savings opportunities.
    
    This endpoint uses algorithmic analysis for fast, cost-effective
    insight generation without requiring LLM calls.
    """
    report = InsightsService.generate_insights(
        db=ctx.db,
        user_id=ctx.user_id,
        period_days=period_days,
        workspace_id=str(ctx.workspace_id) if ctx.workspace_id else None,
    )
    
    return report.to_dict()


@router.get("/spending-trends")
def get_spending_trends(
    period_days: int = Query(30, ge=7, le=365),
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """
    Get spending trend analysis.
    
    Compares current period spending with the previous period
    and provides trend insights.
    """
    report = InsightsService.generate_insights(
        db=ctx.db,
        user_id=ctx.user_id,
        period_days=period_days,
        workspace_id=str(ctx.workspace_id) if ctx.workspace_id else None,
    )
    
    trend_insights = [
        i.to_dict() for i in report.insights 
        if i.insight_type == InsightType.SPENDING_TREND
    ]
    
    return {
        "trends": trend_insights,
        "period_analyzed": report.period_analyzed,
        "total_spent": round(report.total_spent, 2),
    }


@router.get("/categories")
def get_category_insights(
    period_days: int = Query(30, ge=7, le=365),
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """
    Get category-specific spending insights.
    
    Analyzes spending distribution across categories and
    identifies dominant spending areas.
    """
    report = InsightsService.generate_insights(
        db=ctx.db,
        user_id=ctx.user_id,
        period_days=period_days,
        workspace_id=str(ctx.workspace_id) if ctx.workspace_id else None,
    )
    
    category_insights = [
        i.to_dict() for i in report.insights 
        if i.insight_type == InsightType.CATEGORY_ANALYSIS
    ]
    
    return {
        "category_insights": category_insights,
        "period_analyzed": report.period_analyzed,
    }


@router.get("/anomalies")
def get_anomalies(
    period_days: int = Query(30, ge=7, le=365),
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """
    Get detected spending anomalies.
    
    Identifies unusual transactions that deviate significantly
    from normal spending patterns.
    """
    report = InsightsService.generate_insights(
        db=ctx.db,
        user_id=ctx.user_id,
        period_days=period_days,
        workspace_id=str(ctx.workspace_id) if ctx.workspace_id else None,
    )
    
    anomaly_insights = [
        i.to_dict() for i in report.insights 
        if i.insight_type == InsightType.ANOMALY_DETECTION
    ]
    
    return {
        "anomalies": anomaly_insights,
        "count": len(anomaly_insights),
    }


@router.get("/savings")
def get_savings_opportunities(
    period_days: int = Query(30, ge=7, le=365),
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """
    Get savings opportunities.
    
    Identifies areas where spending can be optimized and
    provides actionable recommendations.
    """
    report = InsightsService.generate_insights(
        db=ctx.db,
        user_id=ctx.user_id,
        period_days=period_days,
        workspace_id=str(ctx.workspace_id) if ctx.workspace_id else None,
    )
    
    savings_insights = [
        i.to_dict() for i in report.insights 
        if i.insight_type in [InsightType.SAVINGS_OPPORTUNITY, InsightType.RECURRING_INSIGHT]
    ]
    
    return {
        "opportunities": savings_insights,
        "count": len(savings_insights),
    }


@router.post("/save")
def save_current_insights(
    period_days: int = Query(30),
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """
    Save current insights to database.
    
    Persists the generated insights for historical tracking.
    """
    report = InsightsService.generate_insights(
        db=ctx.db,
        user_id=ctx.user_id,
        period_days=period_days,
        workspace_id=str(ctx.workspace_id) if ctx.workspace_id else None,
    )
    
    saved = InsightsService.save_insights(
        db=ctx.db,
        user_id=ctx.user_id,
        report=report,
        workspace_id=str(ctx.workspace_id) if ctx.workspace_id else None,
    )
    
    return {
        "saved_count": len(saved),
        "message": f"Saved {len(saved)} insights",
    }


@router.get("/history")
def get_saved_insights(
    include_dismissed: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """
    Get saved insights from database.
    
    Returns previously saved insights with their creation timestamps.
    """
    insights = InsightsService.get_saved_insights(
        db=ctx.db,
        user_id=ctx.user_id,
        include_dismissed=include_dismissed,
        limit=limit,
        workspace_id=str(ctx.workspace_id) if ctx.workspace_id else None,
    )
    
    return {
        "insights": [
            {
                "id": str(i.id),
                "type": i.insight_type,
                "severity": i.severity,
                "title": i.title,
                "description": i.description,
                "data": i.data_json,
                "created_at": i.created_at.isoformat(),
                "is_dismissed": i.is_dismissed,
            }
            for i in insights
        ],
        "count": len(insights),
    }


@router.post("/{insight_id}/dismiss")
def dismiss_insight(
    insight_id: str,
    ctx: FilteredQueryContext = Depends(get_filtered_context),
):
    """
    Dismiss an insight.
    
    Marks an insight as dismissed so it won't show up in future queries.
    """
    success = InsightsService.dismiss_insight(ctx.db, ctx.user_id, insight_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Insight not found")
    
    return {"message": "Insight dismissed"}
