"""Jobs API endpoints for managing background jobs."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.shared.database import get_db
from app.shared.dependencies import get_user_id
from .service import JobService
from .models import BackgroundJob


router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class JobResponse(BaseModel):
    job_id: str
    job_type: str
    status: str
    progress: int
    processed_items: Optional[int] = None
    total_items: Optional[int] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @classmethod
    def from_model(cls, job: BackgroundJob):
        return cls(
            job_id=job.id,
            job_type=job.job_type,
            status=job.status,
            progress=job.progress,
            processed_items=job.processed_items,
            total_items=job.total_items,
            result=job.result,
            error=job.error,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at
        )


class TriggerJobResponse(BaseModel):
    job_id: str
    status: str


@router.post("/recategorize", response_model=TriggerJobResponse)
def trigger_recategorization(db: Session = Depends(get_db), user_id: str = Depends(get_user_id)):
    """Trigger a background job to recategorize all transactions."""
    job_id = JobService.create_recategorization_job(db, user_id)
    return TriggerJobResponse(job_id=job_id, status="pending")


class ApplyRulesRequest(BaseModel):
    """Request body for applying specific rules."""
    rule_ids: List[int]


class ApplyRulesResponse(BaseModel):
    """Response for rule application job."""
    job_id: str
    status: str
    rule_count: int
    message: str


@router.post("/apply-rules", response_model=ApplyRulesResponse)
def apply_rules(
    request: ApplyRulesRequest,
    sync: bool = False,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """
    Apply specific rules to uncategorized transactions.
    
    This triggers a background job that:
    1. Finds all "Other" or uncategorized transactions
    2. Applies only the specified rules to matching transactions
    3. Sends WebSocket notifications with progress and results
    
    Use this when applying newly created rules instead of full recategorization.
    
    Args:
        sync: If True, run synchronously and return after completion. 
              Default False (background job with WebSocket notifications).
    
    WebSocket notifications sent (when sync=False):
    - job_progress: {type, job_id, progress, processed, total}
    - job_complete: {type, job_id, result: {transactions_updated, by_category}}
    """
    if not request.rule_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one rule_id is required"
        )
    
    job_id = JobService.create_rule_apply_job(db, user_id, request.rule_ids, run_sync=sync)
    
    # If sync, get the final status
    if sync:
        job = JobService.get_job_status(db, job_id)
        return ApplyRulesResponse(
            job_id=job_id,
            status=job.status if job else "unknown",
            rule_count=len(request.rule_ids),
            message=f"Applied {len(request.rule_ids)} rule(s): {job.result.get('transactions_updated', 0)} transactions updated" if job and job.result else "Completed"
        )
    
    return ApplyRulesResponse(
        job_id=job_id,
        status="pending",
        rule_count=len(request.rule_ids),
        message=f"Started applying {len(request.rule_ids)} rule(s) to uncategorized transactions"
    )


@router.get("/{job_id}", response_model=JobResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)):
    """Get the current status of a background job."""
    job = JobService.get_job_status(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return JobResponse.from_model(job)


@router.get("/", response_model=List[JobResponse])
def list_user_jobs(limit: int = 20, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)):
    """List recent background jobs for the current user."""
    jobs = JobService.get_user_jobs(db, user_id, limit=limit)
    return [JobResponse.from_model(job) for job in jobs]

