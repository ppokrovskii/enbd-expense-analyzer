"""
PGQueuer task definitions for background jobs.

Uses PostgreSQL LISTEN/NOTIFY for efficient, event-driven job processing.
"""
import logging
import time
import asyncio
from typing import Dict, Optional, List
from datetime import datetime

import asyncpg
from pgqueuer import PgQueuer, AsyncpgDriver
from pgqueuer.models import Job

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.shared.database import SessionLocal
from app.domains.transactions.models import Transaction
from app.domains.categories.models import Rule, Category
from app.domains.categories.service import CategoryService
from app.domains.accounts.service import AccountService
from app.domains.jobs.models import BackgroundJob

logger = logging.getLogger("jobs")

# Global PgQueuer instance - initialized on startup
pgq: Optional[PgQueuer] = None


async def init_pgqueuer(database_url: str) -> PgQueuer:
    """Initialize PgQueuer with database connection."""
    global pgq
    
    # Convert SQLAlchemy URL to asyncpg format
    # postgresql+psycopg://user:pass@host:port/db -> postgresql://user:pass@host:port/db
    asyncpg_url = database_url.replace("postgresql+psycopg://", "postgresql://")
    
    logger.info(f"📦 Connecting to database for PgQueuer...")
    connection = await asyncpg.connect(asyncpg_url)
    
    # Install pgqueuer schema if not exists
    logger.info("📦 Installing PgQueuer schema (if needed)...")
    driver = AsyncpgDriver(connection)
    from pgqueuer.queries import Queries
    queries = Queries(driver)
    try:
        await queries.install()
        logger.info("📦 PgQueuer schema installed")
    except Exception as e:
        # Schema already exists, which is fine
        if "already exists" in str(e):
            logger.info("📦 PgQueuer schema already exists")
        else:
            raise
    
    # Create PgQueuer from connection
    pgq = PgQueuer.from_asyncpg_connection(connection)
    
    # Register task handlers using entrypoint decorator
    @pgq.entrypoint("recategorize")
    async def handle_recategorize(job: Job) -> None:
        """Process recategorization job."""
        import json
        payload = json.loads(job.payload) if job.payload else {}
        await run_recategorization_task(
            job_id=job.id,
            user_id=payload.get("user_id"),
            workspace_id=payload.get("workspace_id")
        )
    
    @pgq.entrypoint("apply_rules")
    async def handle_apply_rules(job: Job) -> None:
        """Process rule application job."""
        import json
        payload = json.loads(job.payload) if job.payload else {}
        await run_apply_rules_task(
            job_id=job.id,
            user_id=payload.get("user_id"),
            workspace_id=payload.get("workspace_id"),
            rule_ids=payload.get("rule_ids", [])
        )
    
    logger.info("✅ PgQueuer initialized with entrypoints: recategorize, apply_rules")
    return pgq


async def enqueue_recategorization(user_id: str, workspace_id: Optional[int] = None) -> str:
    """Enqueue a recategorization job."""
    global pgq
    if not pgq:
        raise RuntimeError("PgQueuer not initialized")
    
    import json
    payload = json.dumps({"user_id": user_id, "workspace_id": workspace_id}).encode()
    
    from pgqueuer.queries import Queries
    from pgqueuer import AsyncpgDriver
    # Get queries from pgqueuer's internal driver
    driver = pgq._driver
    queries = Queries(driver)
    
    job_ids = await queries.enqueue(
        "recategorize",
        payload=payload,
        priority=0
    )
    job_id = str(job_ids[0]) if job_ids else "unknown"
    
    logger.info(f"📋 Enqueued recategorization job | job_id={job_id} user_id={user_id} workspace_id={workspace_id}")
    return job_id


async def enqueue_apply_rules(
    user_id: str, 
    rule_ids: List[int], 
    workspace_id: Optional[int] = None
) -> str:
    """Enqueue a rule application job."""
    global pgq
    if not pgq:
        raise RuntimeError("PgQueuer not initialized")
    
    import json
    payload = json.dumps({"user_id": user_id, "workspace_id": workspace_id, "rule_ids": rule_ids}).encode()
    
    from pgqueuer.queries import Queries
    driver = pgq._driver
    queries = Queries(driver)
    
    job_ids = await queries.enqueue(
        "apply_rules",
        payload=payload,
        priority=0
    )
    job_id = str(job_ids[0]) if job_ids else "unknown"
    
    logger.info(f"📋 Enqueued apply_rules job | job_id={job_id} user_id={user_id} rule_ids={rule_ids}")
    return job_id


async def run_recategorization_task(
    job_id: int,
    user_id: str,
    workspace_id: Optional[int] = None
) -> None:
    """
    Execute recategorization task.
    
    Applies all rules to all transactions for a user/workspace.
    """
    from app.domains.notifications.manager import ws_manager
    
    start_time = time.time()
    logger.info(f"🔄 [Recategorize] Starting | job_id={job_id} user_id={user_id} workspace_id={workspace_id}")
    
    db = SessionLocal()
    try:
        # Load account variables
        account_vars = AccountService.get_account_variables(db, user_id)
        logger.debug(f"📦 [Recategorize] Loaded {len(account_vars)} account variables | job_id={job_id}")
        
        # Load categorization rules
        category_service = CategoryService()
        rules = category_service.load_categories(db, user_id, workspace_id=workspace_id)
        logger.info(f"📋 [Recategorize] Loaded {len(rules)} categorization rules | job_id={job_id}")
        
        # Load transactions
        query = db.query(Transaction).filter(Transaction.user_id == user_id)
        if workspace_id:
            query = query.filter(Transaction.workspace_id == workspace_id)
        transactions = query.all()
        total = len(transactions)
        
        logger.info(f"📊 [Recategorize] Processing {total} transactions | job_id={job_id}")
        
        # Track changes
        category_changes: Dict[str, Dict[str, int]] = {}
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
            
            # Progress logging at milestones
            progress = int(((i + 1) / total) * 100) if total > 0 else 100
            if progress >= last_progress_log + 25 or i == total - 1:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                logger.info(f"⏳ [Recategorize] Progress: {progress}% ({i + 1}/{total}) | rate={rate:.0f} txn/s | job_id={job_id}")
                last_progress_log = (progress // 25) * 25
                
                # Send WebSocket progress
                await ws_manager.send_job_progress(user_id, str(job_id), progress, i + 1, total)
        
        db.commit()
        
        # Summary
        total_changed = sum(sum(v.values()) for v in category_changes.values())
        elapsed_total = time.time() - start_time
        
        logger.info(f"✅ [Recategorize] Completed | job_id={job_id} duration={elapsed_total:.2f}s")
        logger.info(f"   📈 Summary: {total} processed, {total_changed} changed, {unchanged_count} unchanged")
        
        if category_changes:
            logger.info(f"   📂 Category transitions:")
            for old_cat, transitions in sorted(category_changes.items()):
                for new_cat, count in sorted(transitions.items(), key=lambda x: -x[1]):
                    logger.info(f"      {old_cat} → {new_cat}: {count} transactions")
        
        # Send completion notification
        result = {"transactions_updated": total, "transactions_changed": total_changed}
        await ws_manager.send_job_complete(user_id, str(job_id), result)
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ [Recategorize] Failed | job_id={job_id} duration={elapsed:.2f}s error={str(e)}", exc_info=True)
        raise  # Re-raise for pgqueuer retry handling
    finally:
        db.close()


async def run_apply_rules_task(
    job_id: int,
    user_id: str,
    workspace_id: Optional[int],
    rule_ids: List[int]
) -> None:
    """
    Execute rule application task.
    
    Applies specific rules to uncategorized transactions only.
    """
    from app.domains.notifications.manager import ws_manager
    
    start_time = time.time()
    logger.info(f"🔄 [ApplyRules] Starting | job_id={job_id} user_id={user_id} rule_ids={rule_ids}")
    
    db = SessionLocal()
    try:
        # Load the specific rules
        rules = db.query(Rule).filter(
            Rule.id.in_(rule_ids),
            Rule.user_id == user_id
        ).all()
        
        logger.info(f"📋 [ApplyRules] Loaded {len(rules)} rules to apply | job_id={job_id}")
        
        if not rules:
            logger.warning(f"⚠️ [ApplyRules] No valid rules found | job_id={job_id}")
            await ws_manager.send_job_complete(user_id, str(job_id), {"transactions_updated": 0})
            return
        
        # Build rule -> category map
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
                logger.debug(f"   Rule #{rule.id}: {category.name} | keywords={rule.keywords}")
        
        # Load account variables
        account_vars = AccountService.get_account_variables(db, user_id)
        
        # Query uncategorized transactions
        query = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            or_(
                Transaction.category.is_(None),
                Transaction.category == '',
                Transaction.category == 'Other'
            )
        )
        if workspace_id:
            query = query.filter(Transaction.workspace_id == workspace_id)
        transactions = query.all()
        
        total = len(transactions)
        logger.info(f"📊 [ApplyRules] Found {total} uncategorized transactions | job_id={job_id}")
        
        updated_count = 0
        rules_applied: Dict[str, int] = {}
        last_progress_log = 0
        
        for i, txn in enumerate(transactions):
            search_text = (txn.search_text or f"{txn.details or ''} {txn.description or ''}").upper()
            
            # Substitute account variables
            for var_name, var_value in account_vars.items():
                if var_value:
                    search_text = search_text.replace(var_value.upper(), f"${{{var_name}}}")
            
            # Check each rule
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
                logger.debug(f"   ✓ Match: txn_id={txn.id} '{txn.merchant or '?'}' → {matched_category}")
                txn.category = matched_category
                updated_count += 1
                rules_applied[matched_category] = rules_applied.get(matched_category, 0) + 1
            
            # Progress logging
            progress = int(((i + 1) / total) * 100) if total > 0 else 100
            if progress >= last_progress_log + 25 or i == total - 1:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                logger.info(f"⏳ [ApplyRules] Progress: {progress}% ({i + 1}/{total}) | matches={updated_count} rate={rate:.0f} txn/s | job_id={job_id}")
                last_progress_log = (progress // 25) * 25
                
                await ws_manager.send_job_progress(user_id, str(job_id), progress, i + 1, total)
        
        db.commit()
        
        elapsed_total = time.time() - start_time
        
        logger.info(f"✅ [ApplyRules] Completed | job_id={job_id} duration={elapsed_total:.2f}s")
        logger.info(f"   📈 Summary: {total} scanned, {updated_count} updated")
        if rules_applied:
            logger.info(f"   📂 Updates by category:")
            for cat, count in sorted(rules_applied.items(), key=lambda x: -x[1]):
                logger.info(f"      {cat}: {count} transactions")
        
        # Send notifications
        result = {
            "transactions_updated": updated_count,
            "transactions_scanned": total,
            "by_category": rules_applied
        }
        await ws_manager.send_job_complete(user_id, str(job_id), result)
        await ws_manager.send_rules_applied(user_id, str(job_id), updated_count, rules_applied)
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ [ApplyRules] Failed | job_id={job_id} duration={elapsed:.2f}s error={str(e)}", exc_info=True)
        raise
    finally:
        db.close()
