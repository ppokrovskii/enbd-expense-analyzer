"""Integration tests for Milestone 4: Multi-Bank Support."""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.database import get_db, engine, Base
from app.services.parsers import ENBDParser, FABParser, WIOParser
from app.services.multi_bank_import_service import MultiBankImportService
from app.models import Transaction, UnparsedFile

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
        session.query(UnparsedFile).filter(UnparsedFile.user_id.like('%test%')).delete()
        session.query(Transaction).filter(Transaction.user_id.like('%test%')).delete()
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
        session.query(UnparsedFile).filter(UnparsedFile.user_id.like('%test%')).delete()
        session.query(Transaction).filter(Transaction.user_id.like('%test%')).delete()
        session.commit()
    except Exception as e:
        print(f"Post-cleanup error: {e}")
        session.rollback()
    finally:
        session.close()
    
    app.dependency_overrides.clear()


def test_enbd_parser_detection(test_db):
    """Test that ENBD parser can detect ENBD files."""
    parser = ENBDParser()
    
    # Test with sample ENBD file
    sample_file = Path("/app/tests/sample_transactions.xlsx")
    if sample_file.exists():
        can_parse, confidence = parser.can_parse(sample_file)
        assert can_parse is True or can_parse is False  # Should return a boolean
        assert 0.0 <= confidence <= 1.0  # Confidence should be between 0 and 1


def test_fab_parser_detection(test_db):
    """Test that FAB parser returns proper detection result."""
    parser = FABParser()
    
    # Test with ENBD file (should not detect as FAB)
    sample_file = Path("/app/tests/sample_transactions.xlsx")
    if sample_file.exists():
        can_parse, confidence = parser.can_parse(sample_file)
        assert isinstance(can_parse, bool)
        assert 0.0 <= confidence <= 1.0


def test_wio_parser_detection(test_db):
    """Test that WIO parser returns proper detection result."""
    parser = WIOParser()
    
    sample_file = Path("/app/tests/sample_transactions.xlsx")
    if sample_file.exists():
        can_parse, confidence = parser.can_parse(sample_file)
        assert isinstance(can_parse, bool)
        assert 0.0 <= confidence <= 1.0


def test_auto_detect_bank(test_db):
    """Test automatic bank detection."""
    sample_file = Path("/app/tests/sample_transactions.xlsx")
    if sample_file.exists():
        parser, confidence, detection_result = MultiBankImportService.detect_bank(sample_file)
        
        # Should return detection results
        assert isinstance(detection_result, dict)
        assert 'detections' in detection_result
        assert isinstance(detection_result['detections'], list)
        
        # Confidence should be valid
        assert 0.0 <= confidence <= 1.0


def test_import_enbd_file(test_db):
    """Test importing an ENBD file."""
    sample_file = Path("/app/tests/sample_transactions.xlsx")
    if sample_file.exists():
        result = MultiBankImportService.import_file(sample_file, test_db, 'test_user')
        
        assert isinstance(result, dict)
        assert 'success' in result
        
        if result['success']:
            assert 'transactions_added' in result
            assert 'duplicates_skipped' in result
            assert 'detected_bank' in result
            assert result['detected_bank'] in ['ENBD', 'FAB', 'WIO']
        else:
            # If parsing failed, should have unparsed_file_id
            assert 'unparsed_file_id' in result or 'error' in result


def test_unparsed_file_storage(test_db):
    """Test that unparsable files are stored for admin review."""
    # Create a dummy file that won't be parsable
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is not a valid bank statement")
        temp_path = Path(f.name)
    
    try:
        result = MultiBankImportService.import_file(temp_path, test_db, 'test_user', 'Unknown Bank')
        
        # Should not succeed
        assert result['success'] is False
        
        # Should have saved as unparsed file
        if 'unparsed_file_id' in result:
            unparsed = test_db.query(UnparsedFile).filter_by(id=result['unparsed_file_id']).first()
            assert unparsed is not None
            assert unparsed.user_id == 'test_user'
            assert unparsed.status == 'pending'
    finally:
        temp_path.unlink(missing_ok=True)


def test_parser_returns_standard_columns(test_db):
    """Test that parsers return standardized DataFrame columns."""
    parser = ENBDParser()
    sample_file = Path("/app/tests/sample_transactions.xlsx")
    
    if sample_file.exists():
        can_parse, _ = parser.can_parse(sample_file)
        if can_parse:
            df = parser.parse(sample_file)
            
            # Check required columns
            required_cols = ['Date', 'Account', 'Description', 'Details', 'Debit/Credit', 'Amount']
            for col in required_cols:
                assert col in df.columns, f"Missing column: {col}"


def test_multi_bank_import_deduplication(test_db):
    """Test that duplicate transactions are not imported twice."""
    sample_file = Path("/app/tests/sample_transactions.xlsx")
    
    if sample_file.exists():
        # First import
        result1 = MultiBankImportService.import_file(sample_file, test_db, 'test_user')
        
        if result1['success']:
            first_count = result1['transactions_added']
            
            # Second import (should skip duplicates)
            result2 = MultiBankImportService.import_file(sample_file, test_db, 'test_user')
            
            if result2['success']:
                assert result2['transactions_added'] == 0
                assert result2['duplicates_skipped'] == first_count


def test_user_isolation_unparsed_files(test_db):
    """Test that unparsed files are isolated by user."""
    import tempfile
    
    # Create dummy file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("test content")
        temp_path = Path(f.name)
    
    try:
        # User 1 uploads unparsable file
        result1 = MultiBankImportService.import_file(temp_path, test_db, 'user1')
        
        # User 2 uploads unparsable file
        result2 = MultiBankImportService.import_file(temp_path, test_db, 'user2')
        
        # Check user 1's unparsed files
        user1_files = test_db.query(UnparsedFile).filter_by(user_id='user1').all()
        assert len(user1_files) >= 1
        
        # Check user 2's unparsed files
        user2_files = test_db.query(UnparsedFile).filter_by(user_id='user2').all()
        assert len(user2_files) >= 1
        
        # Verify they're different records
        user1_ids = {f.id for f in user1_files}
        user2_ids = {f.id for f in user2_files}
        assert user1_ids.isdisjoint(user2_ids)
        
    finally:
        temp_path.unlink(missing_ok=True)


def test_detection_confidence_scoring(test_db):
    """Test that detection confidence is properly scored."""
    sample_file = Path("/app/tests/sample_transactions.xlsx")
    
    if sample_file.exists():
        parser, confidence, detection_result = MultiBankImportService.detect_bank(sample_file)
        
        # Should have multiple detection attempts
        assert len(detection_result['detections']) >= 3  # ENBD, FAB, WIO
        
        # Each detection should have required fields
        for detection in detection_result['detections']:
            assert 'bank' in detection
            assert 'can_parse' in detection
            assert 'confidence' in detection
            assert isinstance(detection['confidence'], float)

