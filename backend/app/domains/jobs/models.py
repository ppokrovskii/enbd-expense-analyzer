"""SQLAlchemy models for the Jobs domain."""
from sqlalchemy import Column, Integer, String, DateTime, Index, JSON
from datetime import datetime
from app.shared.database import Base


class BackgroundJob(Base):
    """Background job model for tracking async operations."""
    
    __tablename__ = "background_jobs"
    
    id = Column(String(36), primary_key=True, index=True)  # UUID
    user_id = Column(String(50), nullable=False, index=True)
    job_type = Column(String(50), nullable=False)  # e.g., "recategorization"
    status = Column(String(20), nullable=False, default="pending")  # pending, running, completed, failed
    progress = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    total_items = Column(Integer, nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_jobs_user_created', 'user_id', 'created_at'),
        Index('idx_jobs_status', 'status'),
    )
    
    def __repr__(self):
        return f"<BackgroundJob(id={self.id}, user_id={self.user_id}, job_type={self.job_type}, status={self.status})>"

