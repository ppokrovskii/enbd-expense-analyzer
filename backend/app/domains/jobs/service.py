"""Service for managing background jobs."""
import threading
import asyncio
from uuid import uuid4
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
from .models import BackgroundJob
from app.domains.transactions.models import Transaction
from app.domains.categories.models import Rule, Category
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
    def create_rule_apply_job(
        db: Session, 
        user_id: str, 
        rule_ids: List[int],
        run_sync: bool = False
    ) -> str:
        """
        Create a background job to apply specific rules to matching transactions.
        
        Only recategorizes transactions that:
        1. Are currently "Other" or uncategorized
        2. Match the keywords of the specified rules
        
        This is more efficient than full recategorization when applying new rules.
        
        Args:
            run_sync: If True, run synchronously (for testing). Default False for background.
        """
        job_id = str(uuid4())
        job = BackgroundJob(
            id=job_id,
            user_id=user_id,
            job_type="rule_apply",
            status="pending",
            progress=0,
            processed_items=0,
            job_params={"rule_ids": rule_ids}
        )
        db.add(job)
        db.commit()
        
        if run_sync:
            # Run synchronously (useful for testing)
            JobService._run_rule_apply_sync(db, job_id, user_id, rule_ids)
        else:
            # Run in background thread
            thread = threading.Thread(
                target=JobService._run_rule_apply,
                args=(job_id, user_id, rule_ids),
                daemon=True
            )
            thread.start()
        
        return job_id
    
    @staticmethod
    def _run_rule_apply_sync(db: Session, job_id: str, user_id: str, rule_ids: List[int]):
        """Synchronous version of rule apply for testing."""
        from app.domains.notifications.manager import ws_manager
        
        job = db.query(BackgroundJob).filter_by(id=job_id).first()
        if not job:
            return
        
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()
        
        # Load the specific rules
        rules = db.query(Rule).filter(
            Rule.id.in_(rule_ids),
            Rule.user_id == user_id
        ).all()
        
        if not rules:
            job.status = "completed"
            job.progress = 100
            job.result = {"transactions_updated": 0, "message": "No valid rules found"}
            job.completed_at = datetime.utcnow()
            db.commit()
            return
        
        # Build a map of rule -> category
        rule_category_map = {}
        for rule in rules:
            category = db.query(Category).filter_by(id=rule.category_id).first()
            if category:
                rule_category_map[rule.id] = {
                    "category_name": category.name,
                    "keywords": [kw.upper() for kw in rule.keywords],
                    "exclude_keywords": [kw.upper() for kw in (rule.exclude_keywords or [])],
                    "priority": rule.priority
                }
        
        # Load account variables
        account_vars = AccountService.get_account_variables(db, user_id)
        
        # Query uncategorized/Other transactions
        transactions = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            or_(
                Transaction.category.is_(None),
                Transaction.category == '',
                Transaction.category == 'Other'
            )
        ).all()
        
        total = len(transactions)
        job.total_items = total
        
        updated_count = 0
        rules_applied: Dict[str, int] = {}
        
        for txn in transactions:
            search_text = (txn.search_text or f"{txn.details or ''} {txn.description or ''}").upper()
            
            # Substitute account variables
            for var_name, var_value in account_vars.items():
                if var_value:
                    search_text = search_text.replace(var_value.upper(), f"${{{var_name}}}")
            
            # Check each rule (sorted by priority)
            matched_category = None
            for rule_id, rule_data in sorted(rule_category_map.items(), key=lambda x: x[1]["priority"], reverse=True):
                excluded = any(kw in search_text for kw in rule_data["exclude_keywords"])
                if excluded:
                    continue
                
                matched = any(kw in search_text for kw in rule_data["keywords"])
                if matched:
                    matched_category = rule_data["category_name"]
                    break
            
            if matched_category and txn.category != matched_category:
                txn.category = matched_category
                updated_count += 1
                rules_applied[matched_category] = rules_applied.get(matched_category, 0) + 1
        
        # Complete the job
        result = {
            "transactions_updated": updated_count,
            "transactions_scanned": total,
            "rules_applied": len(rule_ids),
            "by_category": rules_applied
        }
        
        job.status = "completed"
        job.progress = 100
        job.processed_items = total
        job.completed_at = datetime.utcnow()
        job.result = result
        db.commit()
    
    @staticmethod
    def _run_rule_apply(job_id: str, user_id: str, rule_ids: List[int]):
        """
        Background worker that applies specific rules to matching transactions.
        
        Sends WebSocket notification with results when complete.
        """
        from app.domains.notifications.manager import ws_manager
        
        db = SessionLocal()
        try:
            job = db.query(BackgroundJob).filter_by(id=job_id).first()
            if not job:
                return
            
            job.status = "running"
            job.started_at = datetime.utcnow()
            db.commit()
            
            # Load the specific rules
            rules = db.query(Rule).filter(
                Rule.id.in_(rule_ids),
                Rule.user_id == user_id
            ).all()
            
            if not rules:
                job.status = "completed"
                job.progress = 100
                job.result = {"transactions_updated": 0, "message": "No valid rules found"}
                job.completed_at = datetime.utcnow()
                db.commit()
                asyncio.run(ws_manager.send_job_complete(user_id, job_id, job.result))
                return
            
            # Build a map of rule -> category
            rule_category_map = {}
            for rule in rules:
                category = db.query(Category).filter_by(id=rule.category_id).first()
                if category:
                    rule_category_map[rule.id] = {
                        "category_name": category.name,
                        "keywords": [kw.upper() for kw in rule.keywords],
                        "exclude_keywords": [kw.upper() for kw in (rule.exclude_keywords or [])],
                        "priority": rule.priority
                    }
            
            # Load account variables for variable substitution
            account_vars = AccountService.get_account_variables(db, user_id)
            
            # Query uncategorized/Other transactions
            transactions = db.query(Transaction).filter(
                Transaction.user_id == user_id,
                or_(
                    Transaction.category.is_(None),
                    Transaction.category == '',
                    Transaction.category == 'Other'
                )
            ).all()
            
            total = len(transactions)
            job.total_items = total
            db.commit()
            
            updated_count = 0
            rules_applied: Dict[str, int] = {}  # category -> count
            
            for i, txn in enumerate(transactions):
                search_text = (txn.search_text or f"{txn.details or ''} {txn.description or ''}").upper()
                
                # Substitute account variables
                for var_name, var_value in account_vars.items():
                    if var_value:
                        search_text = search_text.replace(var_value.upper(), f"${{{var_name}}}")
                
                # Check each rule (sorted by priority)
                matched_category = None
                for rule_id, rule_data in sorted(rule_category_map.items(), key=lambda x: x[1]["priority"], reverse=True):
                    # Check exclude keywords first
                    excluded = any(kw in search_text for kw in rule_data["exclude_keywords"])
                    if excluded:
                        continue
                    
                    # Check match keywords
                    matched = any(kw in search_text for kw in rule_data["keywords"])
                    if matched:
                        matched_category = rule_data["category_name"]
                        break
                
                if matched_category and txn.category != matched_category:
                    txn.category = matched_category
                    updated_count += 1
                    rules_applied[matched_category] = rules_applied.get(matched_category, 0) + 1
                
                # Send progress every 50 transactions or at the end
                if (i + 1) % 50 == 0 or i == total - 1:
                    progress = int(((i + 1) / total) * 100) if total > 0 else 100
                    job.progress = progress
                    job.processed_items = i + 1
                    db.commit()
                    
                    # Send progress update
                    asyncio.run(ws_manager.send_job_progress(user_id, job_id, progress, i + 1, total))
            
            # Final commit
            db.commit()
            
            # Complete the job
            result = {
                "transactions_updated": updated_count,
                "transactions_scanned": total,
                "rules_applied": len(rule_ids),
                "by_category": rules_applied
            }
            
            job.status = "completed"
            job.progress = 100
            job.processed_items = total
            job.completed_at = datetime.utcnow()
            job.result = result
            db.commit()
            
            # Send completion notification (both generic and toast-friendly)
            asyncio.run(ws_manager.send_job_complete(user_id, job_id, result))
            asyncio.run(ws_manager.send_rules_applied(user_id, job_id, updated_count, rules_applied))
            
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

