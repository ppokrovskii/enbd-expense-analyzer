"""XLSX import service for parsing and inserting transactions."""
import pandas as pd
import hashlib
import decimal
from pathlib import Path
from typing import List, Tuple, Dict
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models import Transaction
from app.services.transform_service import TransformService


class ImportService:
    """Service for importing XLSX files and creating transactions."""
    
    @staticmethod
    def create_transaction_hash(row: pd.Series) -> str:
        """Create a unique hash for a transaction to detect duplicates."""
        composite_key = f"{row['Date']}|{row['Account']}|{row['Amount']}|{row['Description']}|{row['Debit/Credit']}"
        return hashlib.md5(composite_key.encode()).hexdigest()
    
    @staticmethod
    def parse_xlsx(file_path: Path) -> pd.DataFrame:
        """
        Parse ENBD XLSX file and extract transactions.
        
        The XLSX file has a variable number of metadata rows before the actual data.
        The header row contains: Date, Description, Details, Debit/Credit, Amount, Balance
        """
        # Read the file
        df = pd.read_excel(file_path, header=None)
        
        # Find the header row (contains "Date")
        header_row_idx = None
        for idx, row in df.iterrows():
            if row.astype(str).str.contains("Date", case=False, na=False).any():
                header_row_idx = idx
                break
        
        if header_row_idx is None:
            raise ValueError(f"Could not find header row in {file_path}")
        
        # Re-read with correct header
        df = pd.read_excel(file_path, header=header_row_idx)
        
        # Drop any rows that are all NaN
        df = df.dropna(how='all')
        
        # Extract account name from filename
        account_name = file_path.stem.replace(" Transactions", "")
        df['Account'] = account_name
        
        return df
    
    @staticmethod
    def normalize_data(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize data for consistent hashing."""
        df = df.copy()
        
        # Normalize date to string format YYYY-MM-DD
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        
        # Remove commas from amount and normalize to string with 2 decimal places
        df['Amount'] = df['Amount'].astype(str).str.replace(',', '')
        df['Amount'] = df['Amount'].apply(lambda x: f"{float(x):.2f}" if pd.notna(x) and x != '' else "0.00")
        
        # Remove commas from balance too
        df['Balance'] = df['Balance'].astype(str).str.replace(',', '')
        
        # Fill NaN values for hashing
        df['Description'] = df['Description'].fillna('')
        df['Debit/Credit'] = df['Debit/Credit'].fillna('')
        
        return df
    
    def import_file(self, file_path: Path, db: Session) -> Dict[str, int]:
        """
        Import a single XLSX file into the database.
        
        Returns:
            Dictionary with statistics: {transactions_added: int, duplicates_skipped: int}
        """
        # Parse XLSX
        df = self.parse_xlsx(file_path)
        
        # Normalize for hashing
        df_normalized = self.normalize_data(df)
        
        # Create hashes
        df_normalized['transaction_hash'] = df_normalized.apply(self.create_transaction_hash, axis=1)
        
        # Get existing hashes from database
        existing_hashes = {
            t.transaction_hash 
            for t in db.query(Transaction.transaction_hash).all()
        }
        
        # Filter out duplicates
        new_transactions = df_normalized[~df_normalized['transaction_hash'].isin(existing_hashes)]
        
        # Insert new transactions
        transactions_added = 0
        transform_service = TransformService()
        
        for _, row in new_transactions.iterrows():
            # Parse balance carefully
            balance_value = None
            if pd.notna(row['Balance']):
                balance_str = str(row['Balance']).replace(',', '').strip()
                if balance_str and balance_str.lower() not in ['nan', 'none', '']:
                    try:
                        balance_value = Decimal(balance_str)
                    except (ValueError, decimal.InvalidOperation):
                        balance_value = None
            
            transaction = Transaction(
                date=pd.to_datetime(row['Date']).date(),
                account=row['Account'],
                description=str(row['Description']) if pd.notna(row['Description']) else None,
                details=str(row['Details']) if pd.notna(row['Details']) else None,
                debit_credit=str(row['Debit/Credit']) if pd.notna(row['Debit/Credit']) else None,
                amount=Decimal(str(row['Amount'])),
                balance=balance_value,
                transaction_hash=row['transaction_hash'],
                created_at=datetime.utcnow()
            )
            
            # Apply transformations immediately
            transform_service.transform_transaction(transaction)
            
            db.add(transaction)
            transactions_added += 1
        
        db.commit()
        
        return {
            'transactions_added': transactions_added,
            'duplicates_skipped': len(df_normalized) - transactions_added
        }
    
    def import_multiple_files(self, file_paths: List[Path], db: Session) -> Dict[str, int]:
        """
        Import multiple XLSX files.
        
        Returns:
            Dictionary with cumulative statistics
        """
        total_added = 0
        total_skipped = 0
        files_processed = 0
        
        for file_path in file_paths:
            stats = self.import_file(file_path, db)
            total_added += stats['transactions_added']
            total_skipped += stats['duplicates_skipped']
            files_processed += 1
        
        return {
            'files_processed': files_processed,
            'transactions_added': total_added,
            'duplicates_skipped': total_skipped
        }

