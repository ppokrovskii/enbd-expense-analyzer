"""Backward compatibility - re-export from transactions domain."""
from typing import List
from pathlib import Path
from sqlalchemy.orm import Session
from app.domains.transactions.service import TransactionService


class ImportService:
    """Backward compatible wrapper around TransactionService."""
    
    @staticmethod
    def create_transaction_hash(row):
        return TransactionService.create_transaction_hash(row)
    
    @staticmethod
    def parse_xlsx(file_path):
        return TransactionService.parse_xlsx(file_path)
    
    @staticmethod
    def normalize_data(df):
        return TransactionService.normalize_data(df)
    
    def import_file(self, file_path, db, user_id='default_user'):
        return TransactionService.import_file(file_path, db, user_id)
    
    def import_multiple_files(self, file_paths: List[Path], db: Session, user_id: str = 'default_user'):
        """Import multiple files and aggregate statistics."""
        total_added = 0
        total_skipped = 0
        
        for file_path in file_paths:
            stats = TransactionService.import_file(file_path, db, user_id)
            total_added += stats['transactions_added']
            total_skipped += stats['duplicates_skipped']
        
        return {
            'files_processed': len(file_paths),
            'transactions_added': total_added,
            'duplicates_skipped': total_skipped
        }


__all__ = ['ImportService']
