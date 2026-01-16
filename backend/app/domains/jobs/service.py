"""Service for managing background jobs."""
import logging
import threading
import asyncio
import time
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

# Configure logger for jobs module
logger = logging.getLogger("jobs")


class JobService:
    """Service for creating and managing background jobs."""
    
    @staticmethod
    def create_recategorization_job(db: Session, user_id: str) -> str:
        """Create a background job to recategorize all user transactions."""
        job_id = str(uuid4())
        logger.info(f"📋 Creating recategorization job | job_id={job_id} user_id={user_id}")
        
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
        logger.info(f"🚀 Recategorization job started in background thread | job_id={job_id}")
        
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
        logger.info(f"📋 Creating rule-apply job | job_id={job_id} user_id={user_id} rule_ids={rule_ids} sync={run_sync}")
        
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
            logger.debug(f"🔄 Running rule-apply synchronously | job_id={job_id}")
            JobService._run_rule_apply_sync(db, job_id, user_id, rule_ids)
        else:
            # Run in background thread
            thread = threading.Thread(
                target=JobService._run_rule_apply,
                args=(job_id, user_id, rule_ids),
                daemon=True
            )
            thread.start()
            logger.info(f"🚀 Rule-apply job started in background thread | job_id={job_id}")
        
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
        
        start_time = time.time()
        logger.info(f"🔄 [RuleApply] Starting job | job_id={job_id} user_id={user_id} rule_ids={rule_ids}")
        
        db = SessionLocal()
        try:
            job = db.query(BackgroundJob).filter_by(id=job_id).first()
            if not job:
                logger.error(f"❌ [RuleApply] Job not found | job_id={job_id}")
                return
            
            job.status = "running"
            job.started_at = datetime.utcnow()
            db.commit()
            
            # Load the specific rules
            rules = db.query(Rule).filter(
                Rule.id.in_(rule_ids),
                Rule.user_id == user_id
            ).all()
            
            logger.info(f"📋 [RuleApply] Loaded {len(rules)} rules to apply | job_id={job_id}")
            
            if not rules:
                logger.warning(f"⚠️ [RuleApply] No valid rules found | job_id={job_id} rule_ids={rule_ids}")
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
                    logger.debug(f"   Rule #{rule.id}: {category.name} | keywords={rule.keywords} priority={rule.priority}")
            
            # Load account variables for variable substitution
            account_vars = AccountService.get_account_variables(db, user_id)
            logger.debug(f"📦 [RuleApply] Loaded {len(account_vars)} account variables | job_id={job_id}")
            
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
            
            logger.info(f"📊 [RuleApply] Found {total} uncategorized transactions to process | job_id={job_id}")
            
            updated_count = 0
            rules_applied: Dict[str, int] = {}  # category -> count
            last_progress_log = 0
            
            for i, txn in enumerate(transactions):
                search_text = (txn.search_text or f"{txn.details or ''} {txn.description or ''}").upper()
                
                # Substitute account variables
                for var_name, var_value in account_vars.items():
                    if var_value:
                        search_text = search_text.replace(var_value.upper(), f"${{{var_name}}}")
                
                # Check each rule (sorted by priority)
                matched_category = None
                matched_rule_id = None
                for rule_id, rule_data in sorted(rule_category_map.items(), key=lambda x: x[1]["priority"], reverse=True):
                    # Check exclude keywords first
                    excluded = any(kw in search_text for kw in rule_data["exclude_keywords"])
                    if excluded:
                        continue
                    
                    # Check match keywords
                    matched = any(kw in search_text for kw in rule_data["keywords"])
                    if matched:
                        matched_category = rule_data["category_name"]
                        matched_rule_id = rule_id
                        break
                
                if matched_category and txn.category != matched_category:
                    logger.debug(f"   ✓ Match: txn_id={txn.id} rule_id={matched_rule_id} '{txn.merchant or txn.details[:30] if txn.details else '?'}...' → {matched_category}")
                    txn.category = matched_category
                    updated_count += 1
                    rules_applied[matched_category] = rules_applied.get(matched_category, 0) + 1
                
                # Send progress every 50 transactions or at the end
                progress = int(((i + 1) / total) * 100) if total > 0 else 100
                if (i + 1) % 50 == 0 or i == total - 1:
                    job.progress = progress
                    job.processed_items = i + 1
                    db.commit()
                    asyncio.run(ws_manager.send_job_progress(user_id, job_id, progress, i + 1, total))
                
                # Log at key milestones (every 25%)
                if progress >= last_progress_log + 25 or i == total - 1:
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed if elapsed > 0 else 0
                    logger.info(f"⏳ [RuleApply] Progress: {progress}% ({i + 1}/{total}) | matches={updated_count} rate={rate:.0f} txn/s | job_id={job_id}")
                    last_progress_log = (progress // 25) * 25
            
            # Final commit
            db.commit()
            
            elapsed_total = time.time() - start_time
            
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
            
            # Log summary
            logger.info(f"✅ [RuleApply] Completed | job_id={job_id} duration={elapsed_total:.2f}s")
            logger.info(f"   📈 Summary: {total} scanned, {updated_count} updated, {len(rule_ids)} rules applied")
            if rules_applied:
                logger.info(f"   📂 Updates by category:")
                for cat, count in sorted(rules_applied.items(), key=lambda x: -x[1]):
                    logger.info(f"      {cat}: {count} transactions")
            
            # Send completion notification (both generic and toast-friendly)
            asyncio.run(ws_manager.send_job_complete(user_id, job_id, result))
            asyncio.run(ws_manager.send_rules_applied(user_id, job_id, updated_count, rules_applied))
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ [RuleApply] Failed | job_id={job_id} duration={elapsed:.2f}s error={str(e)}", exc_info=True)
            try:
                job = db.query(BackgroundJob).filter_by(id=job_id).first()
                if job:
                    job.status = "failed"
                    job.error = str(e)
                    job.completed_at = datetime.utcnow()
                    db.commit()
                    asyncio.run(ws_manager.send_job_failed(user_id, job_id, str(e)))
            except Exception as inner_e:
                logger.error(f"❌ [RuleApply] Failed to update job status | job_id={job_id} error={str(inner_e)}")
        finally:
            db.close()
    
    @staticmethod
    def _run_recategorization(job_id: str, user_id: str):
        """Background worker that recategorizes all transactions for a user."""
        from app.domains.notifications.manager import ws_manager
        
        start_time = time.time()
        logger.info(f"🔄 [Recategorize] Starting job | job_id={job_id} user_id={user_id}")
        
        db = SessionLocal()
        try:
            job = db.query(BackgroundJob).filter_by(id=job_id).first()
            if not job:
                logger.error(f"❌ [Recategorize] Job not found | job_id={job_id}")
                return
            
            job.status = "running"
            job.started_at = datetime.utcnow()
            db.commit()
            
            # Load account variables for substitution
            account_vars = AccountService.get_account_variables(db, user_id)
            logger.debug(f"📦 [Recategorize] Loaded {len(account_vars)} account variables | job_id={job_id}")
            
            # Load categorization rules
            category_service = CategoryService()
            rules = category_service.load_categories(db, user_id)
            logger.info(f"📋 [Recategorize] Loaded {len(rules)} categorization rules | job_id={job_id}")
            
            # Log rule details at debug level
            for category_name, rule_config in rules.items():
                logger.debug(f"   Rule: {category_name} | keywords={len(rule_config.get('keywords', []))}")
            
            # Load all transactions for user
            transactions = db.query(Transaction).filter_by(user_id=user_id).all()
            total = len(transactions)
            job.total_items = total
            db.commit()
            
            logger.info(f"📊 [Recategorize] Processing {total} transactions | job_id={job_id}")
            
            # Track changes for summary
            category_changes: Dict[str, Dict[str, int]] = {}  # old_cat -> new_cat -> count
            unchanged_count = 0
            last_progress_log = 0
            
            for i, txn in enumerate(transactions):
                old_category = txn.category or "Uncategorized"
                new_category = category_service.categorize_with_variables(
                    txn.search_text or f"{txn.details or ''} {txn.description or ''}".strip(),
                    rules,
                    account_vars
                )
                
                if old_category != new_category:
                    if old_category not in category_changes:
                        category_changes[old_category] = {}
                    category_changes[old_category][new_category] = category_changes[old_category].get(new_category, 0) + 1
                else:
                    unchanged_count += 1
                
                txn.category = new_category
                
                # Log and send progress updates at 10%, 25%, 50%, 75%, 90%, 100%
                progress = int(((i + 1) / total) * 100) if total > 0 else 100
                if (i + 1) % 100 == 0 or i == total - 1:
                    job.progress = progress
                    job.processed_items = i + 1
                    db.commit()
                    asyncio.run(ws_manager.send_job_progress(user_id, job_id, progress, i + 1, total))
                
                # Log at key milestones
                if progress >= last_progress_log + 25 or i == total - 1:
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed if elapsed > 0 else 0
                    logger.info(f"⏳ [Recategorize] Progress: {progress}% ({i + 1}/{total}) | rate={rate:.0f} txn/s | job_id={job_id}")
                    last_progress_log = (progress // 25) * 25
            
            # Calculate summary
            total_changed = sum(sum(v.values()) for v in category_changes.values())
            elapsed_total = time.time() - start_time
            
            job.status = "completed"
            job.progress = 100
            job.processed_items = total
            job.completed_at = datetime.utcnow()
            job.result = {"transactions_updated": total, "transactions_changed": total_changed}
            db.commit()
            
            # Log detailed summary
            logger.info(f"✅ [Recategorize] Completed | job_id={job_id} duration={elapsed_total:.2f}s")
            logger.info(f"   📈 Summary: {total} processed, {total_changed} changed, {unchanged_count} unchanged")
            
            if category_changes:
                logger.info(f"   📂 Category transitions:")
                for old_cat, transitions in sorted(category_changes.items()):
                    for new_cat, count in sorted(transitions.items(), key=lambda x: -x[1]):
                        logger.info(f"      {old_cat} → {new_cat}: {count} transactions")
            
            asyncio.run(ws_manager.send_job_complete(user_id, job_id, {"transactions_updated": total, "transactions_changed": total_changed}))
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ [Recategorize] Failed | job_id={job_id} duration={elapsed:.2f}s error={str(e)}", exc_info=True)
            try:
                job = db.query(BackgroundJob).filter_by(id=job_id).first()
                if job:
                    job.status = "failed"
                    job.error = str(e)
                    job.completed_at = datetime.utcnow()
                    db.commit()
                    asyncio.run(ws_manager.send_job_failed(user_id, job_id, str(e)))
            except Exception as inner_e:
                logger.error(f"❌ [Recategorize] Failed to update job status | job_id={job_id} error={str(inner_e)}")
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

