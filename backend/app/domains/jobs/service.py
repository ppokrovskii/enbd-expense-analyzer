"""Service for managing background jobs."""
import threading
import asyncio
from uuid import uuid4
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from .models import BackgroundJob
from app.domains.transactions.models import Transaction
from app.domains.categories.service import CategoryService
from app.domains.accounts.service import AccountService
from app.shared.database import SessionLocal


class JobService:
    """Service for creating and managing background jobs."""
    
    @staticmethod
    def create_recategorization_job(db: Session, user_id: str) -> str:
        """Create a background job to recategorize all user transactions."""
        job_id = str(uuid4())
        job = BackgroundJob(
            id=job_id,
            user_id=user_id,
            job_type="recategorization",
            status="pending",
            progress=0,
            processed_items=0
        )
        db.add(job)
        db.commit()
        
        thread = threading.Thread(
            target=JobService._run_recategorization,
            args=(job_id, user_id),
            daemon=True
        )
        thread.start()
        
        return job_id
    
    @staticmethod
    def _run_recategorization(job_id: str, user_id: str):
        """Background worker that recategorizes all transactions for a user."""
        from app.domains.notifications.manager import ws_manager
        
        db = SessionLocal()
        try:
            job = db.query(BackgroundJob).filter_by(id=job_id).first()
            if not job:
                return
            
            job.status = "running"
            job.started_at = datetime.utcnow()
            db.commit()
            
            account_vars = AccountService.get_account_variables(db, user_id)
            
            category_service = CategoryService()
            rules = category_service.load_categories(db, user_id)
            
            transactions = db.query(Transaction).filter_by(user_id=user_id).all()
            total = len(transactions)
            job.total_items = total
            db.commit()
            
            for i, txn in enumerate(transactions):
                new_category = category_service.categorize_with_variables(
                    txn.search_text or f"{txn.details or ''} {txn.description or ''}".strip(),
                    rules,
                    account_vars
                )
                txn.category = new_category
                
                if (i + 1) % 100 == 0 or i == total - 1:
                    progress = int(((i + 1) / total) * 100) if total > 0 else 100
                    job.progress = progress
                    job.processed_items = i + 1
                    db.commit()
                    
                    asyncio.run(ws_manager.send_job_progress(user_id, job_id, progress, i + 1, total))
            
            job.status = "completed"
            job.progress = 100
            job.processed_items = total
            job.completed_at = datetime.utcnow()
            job.result = {"transactions_updated": total}
            db.commit()
            
            asyncio.run(ws_manager.send_job_complete(user_id, job_id, {"transactions_updated": total}))
            
        except Exception as e:
            try:
                job = db.query(BackgroundJob).filter_by(id=job_id).first()
                if job:
                    job.status = "failed"
                    job.error = str(e)
                    job.completed_at = datetime.utcnow()
                    db.commit()
                    asyncio.run(ws_manager.send_job_failed(user_id, job_id, str(e)))
            except:
                pass
        finally:
            db.close()
    
    @staticmethod
    def get_job_status(db: Session, job_id: str) -> Optional[BackgroundJob]:
        """Get the current status of a background job."""
        return db.query(BackgroundJob).filter_by(id=job_id).first()
    
    @staticmethod
    def get_user_jobs(db: Session, user_id: str, limit: int = 20) -> List[BackgroundJob]:
        """Get recent jobs for a user."""
        return db.query(BackgroundJob).filter_by(user_id=user_id).order_by(
            BackgroundJob.created_at.desc()
        ).limit(limit).all()

