"""Router for financial insights endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date
from pydantic import BaseModel

from app.shared.database import get_db
from app.shared.dependencies import get_user_id
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
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
    period_days: int = Query(30, ge=7, le=365, description="Analysis period in days"),
    person_id: Optional[str] = Query(None, description="Filter by person ID"),
):
    """
    Generate financial insights for the user.
    
    Analyzes spending patterns, detects anomalies, identifies recurring
    expenses, and finds savings opportunities.
    
    This endpoint uses algorithmic analysis for fast, cost-effective
    insight generation without requiring LLM calls.
    """
    report = InsightsService.generate_insights(
        db=db,
        user_id=user_id,
        period_days=period_days,
        person_id=person_id,
    )
    
    return report.to_dict()


@router.get("/spending-trends")
def get_spending_trends(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
    period_days: int = Query(30, ge=7, le=365),
    person_id: Optional[str] = Query(None),
):
    """
    Get spending trend analysis.
    
    Compares current period spending with the previous period
    and provides trend insights.
    """
    report = InsightsService.generate_insights(
        db=db,
        user_id=user_id,
        period_days=period_days,
        person_id=person_id,
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
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
    period_days: int = Query(30, ge=7, le=365),
    person_id: Optional[str] = Query(None),
):
    """
    Get category-specific spending insights.
    
    Analyzes spending distribution across categories and
    identifies dominant spending areas.
    """
    report = InsightsService.generate_insights(
        db=db,
        user_id=user_id,
        period_days=period_days,
        person_id=person_id,
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
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
    period_days: int = Query(30, ge=7, le=365),
    person_id: Optional[str] = Query(None),
):
    """
    Get detected spending anomalies.
    
    Identifies unusual transactions that deviate significantly
    from normal spending patterns.
    """
    report = InsightsService.generate_insights(
        db=db,
        user_id=user_id,
        period_days=period_days,
        person_id=person_id,
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
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
    period_days: int = Query(30, ge=7, le=365),
    person_id: Optional[str] = Query(None),
):
    """
    Get savings opportunities.
    
    Identifies areas where spending can be optimized and
    provides actionable recommendations.
    """
    report = InsightsService.generate_insights(
        db=db,
        user_id=user_id,
        period_days=period_days,
        person_id=person_id,
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
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
    period_days: int = Query(30),
    person_id: Optional[str] = Query(None),
):
    """
    Save current insights to database.
    
    Persists the generated insights for historical tracking.
    """
    report = InsightsService.generate_insights(
        db=db,
        user_id=user_id,
        period_days=period_days,
        person_id=person_id,
    )
    
    saved = InsightsService.save_insights(
        db=db,
        user_id=user_id,
        report=report,
        person_id=person_id,
    )
    
    return {
        "saved_count": len(saved),
        "message": f"Saved {len(saved)} insights",
    }


@router.get("/history")
def get_saved_insights(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
    include_dismissed: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Get saved insights from database.
    
    Returns previously saved insights with their creation timestamps.
    """
    insights = InsightsService.get_saved_insights(
        db=db,
        user_id=user_id,
        include_dismissed=include_dismissed,
        limit=limit,
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
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """
    Dismiss an insight.
    
    Marks an insight as dismissed so it won't show up in future queries.
    """
    success = InsightsService.dismiss_insight(db, user_id, insight_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Insight not found")
    
    return {"message": "Insight dismissed"}

