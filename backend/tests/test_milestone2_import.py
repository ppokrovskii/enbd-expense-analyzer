"""Integration tests for Milestone 2: XLSX upload + import pipeline."""
import pytest
from pathlib import Path
from app.models import Transaction
from app.services.import_service import ImportService


@pytest.fixture
def sample_xlsx():
    """Path to sample XLSX file."""
    return Path(__file__).parent / "sample_transactions.xlsx"


def test_parse_xlsx(sample_xlsx):
    """Test parsing ENBD XLSX file."""
    import_service = ImportService()
    df = import_service.parse_xlsx(sample_xlsx)
    
    # Check that we got data
    assert len(df) > 0
    
    # Check that required columns exist
    required_columns = ['Date', 'Description', 'Details', 'Debit/Credit', 'Amount', 'Balance', 'Account']
    for col in required_columns:
        assert col in df.columns
    
    # Check that account was extracted from filename
    assert df['Account'].iloc[0] in ["Current Account", "sample_transactions"]


def test_normalize_data(sample_xlsx):
    """Test data normalization for consistent hashing."""
    import_service = ImportService()
    df = import_service.parse_xlsx(sample_xlsx)
    df_normalized = import_service.normalize_data(df)
    
    # Check date format
    assert df_normalized['Date'].iloc[0].count('-') == 2  # YYYY-MM-DD format
    
    # Check amount format
    assert '.' in str(df_normalized['Amount'].iloc[0])
    assert len(str(df_normalized['Amount'].iloc[0]).split('.')[-1]) == 2  # 2 decimal places


def test_create_transaction_hash():
    """Test transaction hash creation."""
    import pandas as pd
    from app.services.import_service import ImportService
    
    row = pd.Series({
        'Date': '2025-12-26',
        'Account': 'Current Account',
        'Amount': '100.00',
        'Description': 'CARREFOUR',
        'Debit/Credit': 'Debit'
    })
    
    hash1 = ImportService.create_transaction_hash(row)
    hash2 = ImportService.create_transaction_hash(row)
    
    # Same data should produce same hash
    assert hash1 == hash2
    assert len(hash1) == 32  # MD5 hash length


def test_import_file(test_db, sample_xlsx):
    """Test importing a single XLSX file."""
    import_service = ImportService()
    stats = import_service.import_file(sample_xlsx, test_db)
    
    # Check stats
    assert stats['transactions_added'] > 0
    assert stats['duplicates_skipped'] == 0
    
    # Check database
    count = test_db.query(Transaction).count()
    assert count == stats['transactions_added']
    
    # Check first transaction
    first_transaction = test_db.query(Transaction).first()
    assert first_transaction is not None
    assert first_transaction.account in ["Current Account", "sample_transactions"]
    assert first_transaction.transaction_hash is not None


def test_import_duplicate_file(test_db, sample_xlsx):
    """Test that importing the same file twice doesn't create duplicates."""
    import_service = ImportService()
    
    # First import
    stats1 = import_service.import_file(sample_xlsx, test_db)
    initial_count = stats1['transactions_added']
    
    # Second import (same file)
    stats2 = import_service.import_file(sample_xlsx, test_db)
    
    # No new transactions should be added
    assert stats2['transactions_added'] == 0
    assert stats2['duplicates_skipped'] == initial_count
    
    # Database should have same count
    final_count = test_db.query(Transaction).count()
    assert final_count == initial_count


def test_import_multiple_files(test_db, sample_xlsx):
    """Test importing multiple files."""
    import_service = ImportService()
    stats = import_service.import_multiple_files([sample_xlsx], test_db)
    
    assert stats['files_processed'] == 1
    assert stats['transactions_added'] > 0
    assert stats['duplicates_skipped'] == 0

