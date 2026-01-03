"""Integration tests for Milestone 3: Background Jobs & WebSocket."""
import pytest
import time
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date
from decimal import Decimal
from app.main import app
from app.database import get_db, engine, Base
from app.services.job_service import JobService
from app.models import Transaction, Category, Rule, BackgroundJob

client = TestClient(app)


@pytest.fixture(scope="function")
def test_db():
    """Create a test database session."""
    Base.metadata.create_all(bind=engine)
    
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    # Clean up before test
    try:
        session.query(BackgroundJob).filter(BackgroundJob.user_id.like('%test%')).delete()
        session.query(Transaction).filter(Transaction.user_id.like('%test%')).delete()
        session.query(Rule).filter(Rule.user_id.like('%test%')).delete()
        session.query(Category).filter(Category.user_id.like('%test%')).delete()
        session.commit()
    except Exception as e:
        print(f"Pre-cleanup error: {e}")
        session.rollback()
    
    def override_get_db():
        try:
            yield session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield session
    
    # Cleanup after test
    try:
        session.rollback()
        session.query(BackgroundJob).filter(BackgroundJob.user_id.like('%test%')).delete()
        session.query(Transaction).filter(Transaction.user_id.like('%test%')).delete()
        session.query(Rule).filter(Rule.user_id.like('%test%')).delete()
        session.query(Category).filter(Category.user_id.like('%test%')).delete()
        session.commit()
    except Exception as e:
        print(f"Post-cleanup error: {e}")
        session.rollback()
    finally:
        session.close()
    
    app.dependency_overrides.clear()


def test_create_recategorization_job(test_db):
    """Test creating a recategorization background job."""
    response = client.post("/api/jobs/recategorize", headers={"X-User-Id": "test_user"})
    
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"
    
    # Verify job was created in database
    job = test_db.query(BackgroundJob).filter_by(id=data["job_id"]).first()
    assert job is not None
    assert job.user_id == "test_user"
    assert job.job_type == "recategorization"
    assert job.status in ["pending", "running", "completed"]


def test_get_job_status(test_db):
    """Test getting job status via API."""
    # Create a job
    create_response = client.post("/api/jobs/recategorize", headers={"X-User-Id": "test_user"})
    job_id = create_response.json()["job_id"]
    
    # Get job status
    status_response = client.get(f"/api/jobs/{job_id}", headers={"X-User-Id": "test_user"})
    assert status_response.status_code == 200
    
    data = status_response.json()
    assert data["job_id"] == job_id
    assert data["job_type"] == "recategorization"
    assert data["status"] in ["pending", "running", "completed"]
    assert "progress" in data


def test_job_runs_to_completion(test_db):
    """Test that a recategorization job completes successfully."""
    # Create test data - Category first, then Rule with keywords
    category = Category(
        user_id='test_user',
        name='Test Category'
    )
    test_db.add(category)
    test_db.commit()
    test_db.refresh(category)
    
    # Create rule with keywords
    rule = Rule(
        category_id=category.id,
        user_id='test_user',
        keywords=['TEST', 'EXAMPLE']
    )
    test_db.add(rule)
    
    # Create transactions
    for i in range(5):
        txn = Transaction(
            user_id='test_user',
            date=date(2024, 1, 1),
            account='Test Account',
            description=f'TEST Transaction {i}',
            details='Test details',
            search_text='TEST Transaction Test details',
            debit_credit='DR',
            amount=Decimal('100.00'),
            transaction_hash=f'test_hash_{i}'
        )
        test_db.add(txn)
    
    test_db.commit()
    
    # Trigger recategorization
    create_response = client.post("/api/jobs/recategorize", headers={"X-User-Id": "test_user"})
    job_id = create_response.json()["job_id"]
    
    # Wait for job to complete (max 10 seconds)
    for _ in range(20):
        status_response = client.get(f"/api/jobs/{job_id}", headers={"X-User-Id": "test_user"})
        status = status_response.json()["status"]
        if status in ["completed", "failed"]:
            break
        time.sleep(0.5)
    
    # Check final status
    final_response = client.get(f"/api/jobs/{job_id}", headers={"X-User-Id": "test_user"})
    final_data = final_response.json()
    
    assert final_data["status"] == "completed"
    assert final_data["progress"] == 100
    assert final_data["result"] is not None
    assert "transactions_updated" in final_data["result"]


def test_list_user_jobs(test_db):
    """Test listing jobs for a user."""
    # Create multiple jobs
    job_ids = []
    for _ in range(3):
        response = client.post("/api/jobs/recategorize", headers={"X-User-Id": "test_user"})
        job_ids.append(response.json()["job_id"])
    
    # List jobs
    list_response = client.get("/api/jobs/", headers={"X-User-Id": "test_user"})
    assert list_response.status_code == 200
    
    jobs = list_response.json()
    assert len(jobs) >= 3
    
    # Check that our jobs are in the list
    returned_ids = [j["job_id"] for j in jobs]
    for job_id in job_ids:
        assert job_id in returned_ids


def test_job_user_isolation(test_db):
    """Test that users can only see their own jobs."""
    # User 1 creates a job
    response1 = client.post("/api/jobs/recategorize", headers={"X-User-Id": "user1"})
    job_id1 = response1.json()["job_id"]
    
    # User 2 creates a job
    response2 = client.post("/api/jobs/recategorize", headers={"X-User-Id": "user2"})
    job_id2 = response2.json()["job_id"]
    
    # User 1 should not be able to access user 2's job
    access_response = client.get(f"/api/jobs/{job_id2}", headers={"X-User-Id": "user1"})
    assert access_response.status_code == 403
    
    # User 1 should be able to access their own job
    own_response = client.get(f"/api/jobs/{job_id1}", headers={"X-User-Id": "user1"})
    assert own_response.status_code == 200


def test_websocket_connection(test_db):
    """Test WebSocket connection establishment."""
    with client.websocket_connect("/ws?user_id=test_user") as websocket:
        # Connection should be accepted
        # Send ping
        websocket.send_text("ping")
        # Should receive pong
        data = websocket.receive_text()
        assert data == "pong"


def test_job_progress_tracking(test_db):
    """Test that job progress is tracked correctly."""
    # Create test data - Category first, then Rule with keywords
    category = Category(
        user_id='test_user',
        name='Test'
    )
    test_db.add(category)
    test_db.commit()
    test_db.refresh(category)
    
    # Create rule with keywords
    rule = Rule(
        category_id=category.id,
        user_id='test_user',
        keywords=['TEST']
    )
    test_db.add(rule)
    
    for i in range(10):
        txn = Transaction(
            user_id='test_user',
            date=date(2024, 1, 1),
            account='Test',
            description='TEST',
            details='test',
            search_text='TEST test',
            debit_credit='DR',
            amount=Decimal('10.00'),
            transaction_hash=f'hash_{i}'
        )
        test_db.add(txn)
    test_db.commit()
    
    # Create job
    job_id = JobService.create_recategorization_job(test_db, 'test_user')
    
    # Wait a bit for job to process
    time.sleep(2)
    
    # Check progress
    job = test_db.query(BackgroundJob).filter_by(id=job_id).first()
    assert job is not None
    assert job.total_items == 10
    assert job.processed_items >= 0


def test_job_not_found(test_db):
    """Test getting status for non-existent job returns 404."""
    response = client.get("/api/jobs/nonexistent-job-id", headers={"X-User-Id": "test_user"})
    assert response.status_code == 404
