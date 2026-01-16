"""Integration tests for PgQueuer-based job processing.

Tests the event-driven job queue using PostgreSQL LISTEN/NOTIFY.
"""
import pytest
import asyncio
import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.domains.transactions.models import Transaction
from app.domains.categories.models import Category, Rule
from app.domains.jobs.models import BackgroundJob
from app.domains.workspaces.models import Workspace


client = TestClient(app)


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_workspace(db: Session, user_id: str, name: str = "Test Workspace") -> Workspace:
    """Create a test workspace."""
    workspace = Workspace(user_id=user_id, name=name, is_active=True)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


def create_test_category(
    db: Session, 
    user_id: str, 
    name: str, 
    workspace_id: int = None,
    color: str = "#000000"
) -> Category:
    """Create a test category."""
    category = Category(user_id=user_id, workspace_id=workspace_id, name=name, color=color)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def create_test_rule(
    db: Session, 
    user_id: str, 
    category_id: int, 
    keywords: list,
    workspace_id: int = None,
    priority: int = 1,
    exclude_keywords: list = None
) -> Rule:
    """Create a test rule."""
    rule = Rule(
        user_id=user_id,
        workspace_id=workspace_id,
        category_id=category_id,
        keywords=keywords,
        exclude_keywords=exclude_keywords or [],
        priority=priority
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def create_test_transactions(
    db: Session,
    user_id: str,
    merchant: str,
    category: str = "Other",
    count: int = 5,
    workspace_id: int = None
) -> list:
    """Create test transactions."""
    transactions = []
    start_date = date.today() - timedelta(days=30)
    
    for i in range(count):
        hash_val = hashlib.md5(f"pgq_test_{user_id}_{merchant}_{i}".encode()).hexdigest()[:30]
        txn = Transaction(
            user_id=user_id,
            workspace_id=workspace_id,
            date=start_date + timedelta(days=i),
            account="Credit Card",
            description=f"{merchant} PAYMENT",
            merchant=merchant,
            category=category,
            debit_credit="D",
            amount=Decimal("50.00"),
            amount_signed=Decimal("-50.00"),
            transaction_hash=hash_val,
            search_text=f"{merchant} PAYMENT"
        )
        db.add(txn)
        transactions.append(txn)
    
    db.commit()
    return transactions


# ============================================================================
# API Endpoint Tests (sync mode - uses threading fallback)
# ============================================================================

class TestRecategorizeEndpoint:
    """Tests for POST /api/jobs/recategorize endpoint."""
    
    def test_recategorize_creates_job(self, test_db: Session):
        """Test that recategorize endpoint creates a job."""
        user_id = "recategorize_test_user"
        
        # Create some transactions
        category = create_test_category(test_db, user_id, "Shopping")
        create_test_rule(test_db, user_id, category.id, ["MALL", "STORE"])
        create_test_transactions(test_db, user_id, "MALL STORE", category="Other", count=3)
        
        response = client.post(
            "/api/jobs/recategorize",
            headers={"X-User-Id": user_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] in ["pending", "queued"]
    
    def test_recategorize_with_workspace_id(self, test_db: Session):
        """Test recategorize respects workspace_id filter."""
        user_id = "recat_workspace_user"
        
        # Create workspace
        workspace = create_test_workspace(test_db, user_id, "Test Workspace")
        
        response = client.post(
            "/api/jobs/recategorize",
            headers={"X-User-Id": user_id, "X-Workspace-Id": str(workspace.id)}
        )
        
        assert response.status_code == 200
        assert "job_id" in response.json()


class TestApplyRulesEndpoint:
    """Tests for POST /api/jobs/apply-rules endpoint."""
    
    def test_apply_rules_sync_mode(self, test_db: Session):
        """Test apply-rules with sync=true uses threading fallback."""
        user_id = "apply_rules_sync_user"
        
        category = create_test_category(test_db, user_id, "Groceries")
        rule = create_test_rule(test_db, user_id, category.id, ["CARREFOUR"])
        create_test_transactions(test_db, user_id, "CARREFOUR MARKET", count=5)
        
        response = client.post(
            "/api/jobs/apply-rules?sync=true",
            json={"rule_ids": [rule.id]},
            headers={"X-User-Id": user_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "5 transactions updated" in data["message"]
    
    def test_apply_rules_async_mode(self, test_db: Session):
        """Test apply-rules async mode creates job."""
        user_id = "apply_rules_async_user"
        
        category = create_test_category(test_db, user_id, "Transport")
        rule = create_test_rule(test_db, user_id, category.id, ["UBER", "CAREEM"])
        
        response = client.post(
            "/api/jobs/apply-rules",
            json={"rule_ids": [rule.id]},
            headers={"X-User-Id": user_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["pending", "queued"]
        assert "job_id" in data
    
    def test_apply_rules_empty_list_rejected(self, test_db: Session):
        """Test that empty rule_ids list returns 400."""
        response = client.post(
            "/api/jobs/apply-rules",
            json={"rule_ids": []},
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 400
        assert "rule_id" in response.json()["detail"].lower()


# ============================================================================
# Job Processing Logic Tests
# ============================================================================

class TestRecategorizationLogic:
    """Tests for recategorization job processing logic."""
    
    def test_recategorization_applies_all_rules(self, test_db: Session):
        """Test that recategorization applies all matching rules."""
        user_id = "recat_logic_user"
        
        # Create categories and rules
        groceries = create_test_category(test_db, user_id, "Groceries")
        transport = create_test_category(test_db, user_id, "Transport")
        
        create_test_rule(test_db, user_id, groceries.id, ["CARREFOUR", "SPINNEYS"])
        create_test_rule(test_db, user_id, transport.id, ["UBER", "RTA", "SALIK"])
        
        # Create transactions
        create_test_transactions(test_db, user_id, "CARREFOUR", count=3)
        create_test_transactions(test_db, user_id, "UBER", count=2)
        create_test_transactions(test_db, user_id, "RANDOM", count=4)
        
        # Use apply-rules sync to test categorization
        rules = test_db.query(Rule).filter_by(user_id=user_id).all()
        rule_ids = [r.id for r in rules]
        
        response = client.post(
            "/api/jobs/apply-rules?sync=true",
            json={"rule_ids": rule_ids},
            headers={"X-User-Id": user_id}
        )
        
        assert response.status_code == 200
        
        # Verify categorization
        groceries_txns = test_db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.category == "Groceries"
        ).count()
        transport_txns = test_db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.category == "Transport"
        ).count()
        
        assert groceries_txns == 3
        assert transport_txns == 2
    
    def test_recategorization_respects_exclude_keywords(self, test_db: Session):
        """Test that exclude_keywords prevent categorization."""
        user_id = "exclude_kw_user"
        
        category = create_test_category(test_db, user_id, "Shopping")
        rule = create_test_rule(
            test_db, user_id, category.id,
            keywords=["MALL"],
            exclude_keywords=["REFUND", "RETURN"]
        )
        
        # Create transactions - some with refund text
        create_test_transactions(test_db, user_id, "MALL PURCHASE", count=3)
        
        # Create refund transaction
        hash_val = hashlib.md5(f"refund_{user_id}".encode()).hexdigest()[:30]
        refund_txn = Transaction(
            user_id=user_id,
            date=date.today(),
            account="Card",
            description="MALL REFUND",
            merchant="MALL",
            category="Other",
            debit_credit="C",
            amount=Decimal("50.00"),
            amount_signed=Decimal("50.00"),
            transaction_hash=hash_val,
            search_text="MALL REFUND"
        )
        test_db.add(refund_txn)
        test_db.commit()
        
        response = client.post(
            "/api/jobs/apply-rules?sync=true",
            json={"rule_ids": [rule.id]},
            headers={"X-User-Id": user_id}
        )
        
        assert response.status_code == 200
        
        # Refund should remain "Other"
        test_db.refresh(refund_txn)
        assert refund_txn.category == "Other"
        
        # Regular transactions should be categorized
        shopping_count = test_db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.category == "Shopping"
        ).count()
        assert shopping_count == 3
    
    def test_recategorization_rule_priority(self, test_db: Session):
        """Test that higher priority rules win."""
        user_id = "priority_logic_user"
        
        generic = create_test_category(test_db, user_id, "Generic")
        specific = create_test_category(test_db, user_id, "Specific")
        
        # Low priority rule
        low_rule = create_test_rule(
            test_db, user_id, generic.id, ["STORE"], priority=1
        )
        # High priority rule
        high_rule = create_test_rule(
            test_db, user_id, specific.id, ["ELECTRONICS"], priority=10
        )
        
        # Transaction matches both
        hash_val = hashlib.md5(f"priority_{user_id}".encode()).hexdigest()[:30]
        txn = Transaction(
            user_id=user_id,
            date=date.today(),
            account="Card",
            description="ELECTRONICS STORE",
            merchant="ELECTRONICS STORE",
            category="Other",
            debit_credit="D",
            amount=Decimal("100.00"),
            amount_signed=Decimal("-100.00"),
            transaction_hash=hash_val,
            search_text="ELECTRONICS STORE"
        )
        test_db.add(txn)
        test_db.commit()
        
        response = client.post(
            "/api/jobs/apply-rules?sync=true",
            json={"rule_ids": [low_rule.id, high_rule.id]},
            headers={"X-User-Id": user_id}
        )
        
        test_db.refresh(txn)
        assert txn.category == "Specific"  # High priority wins


class TestApplyRulesLogic:
    """Tests for apply-rules job processing logic."""
    
    def test_apply_rules_only_affects_uncategorized(self, test_db: Session):
        """Test that only Other/uncategorized transactions are affected."""
        user_id = "uncategorized_only_user"
        
        category = create_test_category(test_db, user_id, "New Category")
        rule = create_test_rule(test_db, user_id, category.id, ["SHOP"])
        
        # Create uncategorized transactions
        create_test_transactions(test_db, user_id, "SHOP A", category="Other", count=3)
        # Create already-categorized transactions
        create_test_transactions(test_db, user_id, "SHOP B", category="Existing", count=2)
        
        response = client.post(
            "/api/jobs/apply-rules?sync=true",
            json={"rule_ids": [rule.id]},
            headers={"X-User-Id": user_id}
        )
        
        data = response.json()
        job_id = data["job_id"]
        job = test_db.query(BackgroundJob).filter_by(id=job_id).first()
        
        # Only 3 uncategorized should be updated
        assert job.result["transactions_updated"] == 3
        
        # Existing category unchanged
        existing_count = test_db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.category == "Existing"
        ).count()
        assert existing_count == 2
    
    def test_apply_rules_with_multiple_rules(self, test_db: Session):
        """Test applying multiple rules in one job."""
        user_id = "multi_rules_user"
        
        cat1 = create_test_category(test_db, user_id, "Category 1")
        cat2 = create_test_category(test_db, user_id, "Category 2")
        
        rule1 = create_test_rule(test_db, user_id, cat1.id, ["MERCHANT_A"])
        rule2 = create_test_rule(test_db, user_id, cat2.id, ["MERCHANT_B"])
        
        create_test_transactions(test_db, user_id, "MERCHANT_A SHOP", count=4)
        create_test_transactions(test_db, user_id, "MERCHANT_B STORE", count=3)
        create_test_transactions(test_db, user_id, "MERCHANT_C OTHER", count=2)
        
        response = client.post(
            "/api/jobs/apply-rules?sync=true",
            json={"rule_ids": [rule1.id, rule2.id]},
            headers={"X-User-Id": user_id}
        )
        
        job_id = response.json()["job_id"]
        job = test_db.query(BackgroundJob).filter_by(id=job_id).first()
        
        assert job.result["transactions_updated"] == 7  # 4 + 3
        assert job.result["by_category"]["Category 1"] == 4
        assert job.result["by_category"]["Category 2"] == 3
    
    def test_apply_rules_with_invalid_rule_ids(self, test_db: Session):
        """Test that invalid rule IDs are handled gracefully."""
        user_id = "invalid_rules_user"
        
        create_test_transactions(test_db, user_id, "MERCHANT", count=5)
        
        response = client.post(
            "/api/jobs/apply-rules?sync=true",
            json={"rule_ids": [99999, 99998]},
            headers={"X-User-Id": user_id}
        )
        
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        job = test_db.query(BackgroundJob).filter_by(id=job_id).first()
        
        assert job.status == "completed"
        assert job.result["transactions_updated"] == 0
        assert "No valid rules" in job.result.get("message", "")


# ============================================================================
# Workspace Isolation Tests
# ============================================================================

class TestWorkspaceIsolation:
    """Tests for workspace-based data isolation in jobs."""
    
    def test_apply_rules_respects_workspace_id(self, test_db: Session):
        """Test that jobs only affect transactions for the specified workspace."""
        user_id = "workspace_isolation_user"
        
        # Create two workspaces
        workspace1 = create_test_workspace(test_db, user_id, "Workspace 1")
        workspace2 = create_test_workspace(test_db, user_id, "Workspace 2")
        
        # Create category and rule for workspace 1
        category = create_test_category(test_db, user_id, "Workspace1 Cat", workspace_id=workspace1.id)
        rule = create_test_rule(test_db, user_id, category.id, ["SHOP"], workspace_id=workspace1.id)
        
        # Create transactions for both workspaces
        create_test_transactions(test_db, user_id, "SHOP A", workspace_id=workspace1.id, count=3)
        create_test_transactions(test_db, user_id, "SHOP B", workspace_id=workspace2.id, count=4)
        
        # Apply rules for workspace 1 only
        response = client.post(
            "/api/jobs/apply-rules?sync=true",
            json={"rule_ids": [rule.id]},
            headers={"X-User-Id": user_id, "X-Workspace-Id": str(workspace1.id)}
        )
        
        job_id = response.json()["job_id"]
        job = test_db.query(BackgroundJob).filter_by(id=job_id).first()
        
        # Only workspace 1's transactions should be updated
        assert job.result["transactions_updated"] == 3
        
        # Workspace 2's transactions should remain "Other"
        workspace2_other = test_db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.workspace_id == workspace2.id,
            Transaction.category == "Other"
        ).count()
        assert workspace2_other == 4


# ============================================================================
# Job Status and History Tests
# ============================================================================

class TestJobStatusAndHistory:
    """Tests for job status tracking and history."""
    
    def test_get_job_status(self, test_db: Session):
        """Test GET /api/jobs/{job_id} returns correct status."""
        user_id = "job_status_user"
        
        category = create_test_category(test_db, user_id, "Test")
        rule = create_test_rule(test_db, user_id, category.id, ["TEST"])
        
        # Create a job
        response = client.post(
            "/api/jobs/apply-rules?sync=true",
            json={"rule_ids": [rule.id]},
            headers={"X-User-Id": user_id}
        )
        job_id = response.json()["job_id"]
        
        # Get status
        status_response = client.get(
            f"/api/jobs/{job_id}",
            headers={"X-User-Id": user_id}
        )
        
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "completed"
        assert data["job_type"] == "rule_apply"
    
    def test_list_user_jobs(self, test_db: Session):
        """Test GET /api/jobs/ returns user's jobs."""
        user_id = "list_jobs_user"
        
        category = create_test_category(test_db, user_id, "Test")
        rule = create_test_rule(test_db, user_id, category.id, ["TEST"])
        
        # Create multiple jobs
        for _ in range(3):
            client.post(
                "/api/jobs/apply-rules?sync=true",
                json={"rule_ids": [rule.id]},
                headers={"X-User-Id": user_id}
            )
        
        # List jobs
        response = client.get(
            "/api/jobs/",
            headers={"X-User-Id": user_id}
        )
        
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 3
        assert all(j["job_type"] == "rule_apply" for j in jobs)
    
    def test_job_user_isolation(self, test_db: Session):
        """Test that users can only see their own jobs."""
        user1 = "jobs_user_1"
        user2 = "jobs_user_2"
        
        # Create jobs for user1
        cat1 = create_test_category(test_db, user1, "User1 Cat")
        rule1 = create_test_rule(test_db, user1, cat1.id, ["TEST"])
        response1 = client.post(
            "/api/jobs/apply-rules?sync=true",
            json={"rule_ids": [rule1.id]},
            headers={"X-User-Id": user1}
        )
        job1_id = response1.json()["job_id"]
        
        # User2 should not be able to access user1's job
        response = client.get(
            f"/api/jobs/{job1_id}",
            headers={"X-User-Id": user2}
        )
        assert response.status_code == 403
        
        # User2's job list should be empty
        list_response = client.get(
            "/api/jobs/",
            headers={"X-User-Id": user2}
        )
        assert len(list_response.json()) == 0


# ============================================================================
# PgQueuer Module Tests
# ============================================================================

class TestPgQueuerModule:
    """Tests for PgQueuer tasks module functionality."""
    
    def test_enqueue_functions_require_initialization(self):
        """Test that enqueue functions raise error if pgqueuer not initialized."""
        import asyncio
        from app.domains.jobs.tasks import enqueue_recategorization, pgq
        
        # Save original pgq value
        import app.domains.jobs.tasks as tasks_module
        original_pgq = tasks_module.pgq
        
        try:
            # Set pgq to None to simulate uninitialized state
            tasks_module.pgq = None
            
            with pytest.raises(RuntimeError, match="PgQueuer not initialized"):
                asyncio.run(enqueue_recategorization("test_user"))
        finally:
            # Restore original value
            tasks_module.pgq = original_pgq
    
    def test_payload_serialization(self):
        """Test that job payloads are correctly serialized/deserialized."""
        import json
        
        # Test payload creation
        payload_data = {"user_id": "test", "workspace_id": 1, "rule_ids": [1, 2, 3]}
        serialized = json.dumps(payload_data).encode()
        deserialized = json.loads(serialized)
        
        assert deserialized == payload_data
        assert deserialized["user_id"] == "test"
        assert deserialized["rule_ids"] == [1, 2, 3]


# ============================================================================
# Environment Variable Tests
# ============================================================================

class TestEnvironmentConfiguration:
    """Tests for environment-based configuration."""
    
    def test_use_pgqueuer_env_variable(self, test_db: Session):
        """Test that USE_PGQUEUER env variable is respected."""
        import os
        from app.domains.jobs.router import USE_PGQUEUER
        
        # Default should be True (or based on env)
        expected = os.environ.get("USE_PGQUEUER", "true").lower() == "true"
        assert USE_PGQUEUER == expected
    
    def test_fallback_to_threading_works(self, test_db: Session):
        """Test that threading fallback works when pgqueuer disabled."""
        user_id = "fallback_test_user"
        
        category = create_test_category(test_db, user_id, "Fallback Cat")
        rule = create_test_rule(test_db, user_id, category.id, ["FALLBACK_TEST"])
        create_test_transactions(test_db, user_id, "FALLBACK_TEST STORE", count=2)
        
        # sync=true always uses threading fallback
        response = client.post(
            "/api/jobs/apply-rules?sync=true",
            json={"rule_ids": [rule.id]},
            headers={"X-User-Id": user_id}
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "completed"
