"""Router for recurring transaction detection endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date
from pydantic import BaseModel

from app.shared.database import get_db
from app.shared.dependencies import get_user_id
from .service import RecurringDetectionService
from .models import Frequency, RecurringGroup


router = APIRouter(prefix="/api/recurring", tags=["recurring"])


# Pydantic models for API responses
class RecurringPatternResponse(BaseModel):
    """Response model for a single recurring pattern."""
    merchant: str
    pattern_name: str
    frequency: str
    estimated_amount: float
    occurrences: int
    first_seen: date
    last_seen: date
    next_expected: Optional[date]
    confidence: float
    forgotten: bool
    transaction_ids: List[int]
    
    class Config:
        from_attributes = True


class RecurringSummaryResponse(BaseModel):
    """Summary statistics for recurring patterns."""
    total_recurring_patterns: int
    active_patterns: int
    forgotten_subscriptions: int
    monthly_recurring_total: float
    weekly_recurring_total: float


class RecurringDetectionResponse(BaseModel):
    """Response model for recurring detection."""
    recurring_groups: List[RecurringPatternResponse]
    total_transactions_analyzed: int
    detection_time_ms: float
    summary: RecurringSummaryResponse


class MonthlyTotalResponse(BaseModel):
    """Response model for monthly recurring total."""
    monthly_total: float
    currency: str = "AED"


@router.get("/detect", response_model=RecurringDetectionResponse)
def detect_recurring_patterns(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
    date_from: Optional[date] = Query(None, description="Start date for analysis"),
    date_to: Optional[date] = Query(None, description="End date for analysis"),
    person_id: Optional[str] = Query(None, description="Filter by person ID"),
):
    """
    Detect recurring transaction patterns.
    
    This endpoint analyzes transactions to find recurring patterns like
    subscriptions, bills, and regular payments. Uses a hybrid algorithm
    approach for fast, accurate detection.
    
    Returns detected patterns with:
    - Merchant name and pattern classification
    - Frequency (weekly, monthly, etc.)
    - Estimated amount and variance
    - Confidence score
    - Whether the subscription might be "forgotten"
    """
    result = RecurringDetectionService.detect_patterns(
        db=db,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        person_id=person_id
    )
    
    return result.to_dict()


@router.get("/monthly-total", response_model=MonthlyTotalResponse)
def get_monthly_recurring_total(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
    person_id: Optional[str] = Query(None, description="Filter by person ID"),
):
    """
    Get the total estimated monthly recurring expenses.
    
    This calculates the monthly equivalent of all detected recurring
    patterns, adjusting weekly/quarterly/yearly amounts to monthly.
    """
    total = RecurringDetectionService.get_monthly_recurring_total(
        db=db,
        user_id=user_id,
        person_id=person_id
    )
    
    return {"monthly_total": total, "currency": "AED"}


@router.get("/forgotten")
def get_forgotten_subscriptions(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
    person_id: Optional[str] = Query(None, description="Filter by person ID"),
):
    """
    Get potentially forgotten subscriptions.
    
    Returns recurring patterns that haven't been seen in over 60 days,
    which might indicate cancelled subscriptions or billing issues.
    """
    result = RecurringDetectionService.detect_patterns(
        db=db,
        user_id=user_id,
        person_id=person_id
    )
    
    forgotten = [g.to_dict() for g in result.recurring_groups if g.forgotten]
    
    return {
        "forgotten_subscriptions": forgotten,
        "count": len(forgotten),
        "potential_monthly_savings": sum(g.estimated_amount for g in result.recurring_groups if g.forgotten)
    }


@router.post("/save")
def save_detected_patterns(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
    person_id: Optional[str] = Query(None, description="Associate with person ID"),
):
    """
    Save detected recurring patterns to database.
    
    This persists the current detection results for tracking over time.
    Useful for monitoring changes in recurring expenses.
    """
    result = RecurringDetectionService.detect_patterns(
        db=db,
        user_id=user_id,
        person_id=person_id
    )
    
    saved = RecurringDetectionService.save_recurring_groups(
        db=db,
        user_id=user_id,
        result=result,
        person_id=person_id
    )
    
    return {
        "saved_count": len(saved),
        "message": f"Saved {len(saved)} recurring patterns"
    }


@router.get("/history")
def get_saved_recurring_patterns(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
    include_forgotten: bool = Query(True, description="Include forgotten patterns"),
):
    """
    Get saved recurring patterns from database.
    
    Returns previously saved recurring patterns with their historical data.
    """
    query = db.query(RecurringGroup).filter(RecurringGroup.user_id == user_id)
    
    if not include_forgotten:
        query = query.filter(RecurringGroup.forgotten == False)
    
    groups = query.order_by(RecurringGroup.estimated_amount.desc()).all()
    
    return {
        "patterns": [
            {
                "id": str(g.id),
                "merchant": g.merchant,
                "pattern_name": g.pattern_name,
                "frequency": g.frequency,
                "estimated_amount": g.estimated_amount,
                "occurrences": g.occurrences_count,
                "last_seen": g.last_seen_date.isoformat() if g.last_seen_date else None,
                "next_expected": g.next_expected_date.isoformat() if g.next_expected_date else None,
                "forgotten": g.forgotten,
                "confidence": g.confidence,
            }
            for g in groups
        ],
        "count": len(groups)
    }

