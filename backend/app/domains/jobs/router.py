"""Jobs API endpoints for managing background jobs.

Uses PgQueuer for event-driven job processing with PostgreSQL LISTEN/NOTIFY.
"""
import logging
import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.shared.filtered_query import FilteredQueryContext, get_filtered_context
from .service import JobService
from .models import BackgroundJob

# Configure logger for jobs module
logger = logging.getLogger("jobs")

# Check if pgqueuer is enabled (can fallback to threading for tests)
USE_PGQUEUER = os.environ.get("USE_PGQUEUER", "true").lower() == "true"

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
async def trigger_recategorization(ctx: FilteredQueryContext = Depends(get_filtered_context)):
    """
    Trigger a background job to recategorize all transactions.
    
    Uses PgQueuer with PostgreSQL LISTEN/NOTIFY for efficient event-driven processing.
    """
    logger.info(f"🔄 POST /recategorize | user_id={ctx.user_id} workspace_id={ctx.workspace_id}")
    
    if USE_PGQUEUER:
        from .tasks import enqueue_recategorization
        try:
            job_id = await enqueue_recategorization(ctx.user_id, ctx.workspace_id)
            logger.info(f"✅ Recategorization job enqueued (pgqueuer) | job_id={job_id}")
            return TriggerJobResponse(job_id=job_id, status="queued")
        except Exception as e:
            logger.warning(f"⚠️ PgQueuer unavailable, falling back to threading | error={e}")
    
    # Fallback to threading-based implementation
    job_id = JobService.create_recategorization_job(ctx.db, ctx.user_id)
    logger.info(f"✅ Recategorization job created (threading) | job_id={job_id}")
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
async def apply_rules(
    request: ApplyRulesRequest,
    sync: bool = False,
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """
    Apply specific rules to uncategorized transactions.
    
    Uses PgQueuer with PostgreSQL LISTEN/NOTIFY for efficient event-driven processing.
    
    This triggers a background job that:
    1. Finds all "Other" or uncategorized transactions
    2. Applies only the specified rules to matching transactions
    3. Sends WebSocket notifications with progress and results
    
    Args:
        sync: If True, run synchronously (fallback to threading). 
              Default False (async job via PgQueuer).
    
    WebSocket notifications sent:
    - job_progress: {type, job_id, progress, processed, total}
    - job_complete: {type, job_id, result: {transactions_updated, by_category}}
    """
    logger.info(f"🔄 POST /apply-rules | user_id={ctx.user_id} rule_ids={request.rule_ids} sync={sync}")
    
    if not request.rule_ids:
        logger.warning(f"⚠️ Apply-rules rejected: no rule_ids provided | user_id={ctx.user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one rule_id is required"
        )
    
    # Sync mode always uses threading (for tests)
    if sync:
        job_id = JobService.create_rule_apply_job(
            ctx.db, ctx.user_id, request.rule_ids, run_sync=True, workspace_id=ctx.workspace_id
        )
        job = JobService.get_job_status(ctx.db, job_id)
        result_msg = f"Applied {len(request.rule_ids)} rule(s): {job.result.get('transactions_updated', 0)} transactions updated" if job and job.result else "Completed"
        logger.info(f"✅ Apply-rules completed (sync) | job_id={job_id} result={result_msg}")
        return ApplyRulesResponse(
            job_id=job_id,
            status=job.status if job else "unknown",
            rule_count=len(request.rule_ids),
            message=result_msg
        )
    
    # Async mode uses PgQueuer
    if USE_PGQUEUER:
        from .tasks import enqueue_apply_rules
        try:
            job_id = await enqueue_apply_rules(ctx.user_id, request.rule_ids, ctx.workspace_id)
            logger.info(f"✅ Apply-rules job enqueued (pgqueuer) | job_id={job_id}")
            return ApplyRulesResponse(
                job_id=job_id,
                status="queued",
                rule_count=len(request.rule_ids),
                message=f"Queued {len(request.rule_ids)} rule(s) for application"
            )
        except Exception as e:
            logger.warning(f"⚠️ PgQueuer unavailable, falling back to threading | error={e}")
    
    # Fallback to threading
    job_id = JobService.create_rule_apply_job(
        ctx.db, ctx.user_id, request.rule_ids, run_sync=False, workspace_id=ctx.workspace_id
    )
    logger.info(f"✅ Apply-rules job created (threading) | job_id={job_id}")
    return ApplyRulesResponse(
        job_id=job_id,
        status="pending",
        rule_count=len(request.rule_ids),
        message=f"Started applying {len(request.rule_ids)} rule(s) to uncategorized transactions"
    )


@router.get("/{job_id}", response_model=JobResponse)
def get_job_status(job_id: str, ctx: FilteredQueryContext = Depends(get_filtered_context)):
    """Get the current status of a background job."""
    job = JobService.get_job_status(ctx.db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.user_id != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return JobResponse.from_model(job)


@router.get("/", response_model=List[JobResponse])
def list_user_jobs(limit: int = 20, ctx: FilteredQueryContext = Depends(get_filtered_context)):
    """List recent background jobs for the current user."""
    jobs = JobService.get_user_jobs(ctx.db, ctx.user_id, limit=limit)
    return [JobResponse.from_model(job) for job in jobs]
