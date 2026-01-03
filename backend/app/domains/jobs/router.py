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

