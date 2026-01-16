"""Multi-bank import service with automatic format detection."""
import os
import pandas as pd
import hashlib
import shutil
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Any
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from .models import Transaction, UnparsedFile
from .service import TransactionService
from .parsers import ENBDParser, FABParser, WIOParser, BankParser


class MultiBankImportService:
    """Service for importing bank statements with automatic format detection."""
    
    # Registry of all available parsers
    PARSERS: List[BankParser] = [
        ENBDParser(),
        FABParser(),
        WIOParser(),
    ]
    
    # Directory for storing unparsed files - use env var or fallback to local path
    UNPARSED_FILES_DIR = Path(os.getenv("UNPARSED_FILES_DIR", "./unparsed_files"))
    
    @staticmethod
    def create_transaction_hash(row: pd.Series) -> str:
        """Create a unique hash for a transaction to detect duplicates."""
        composite_key = f"{row['Date']}|{row['Account']}|{row['Amount']}|{row['Description']}|{row['Debit/Credit']}"
        return hashlib.md5(composite_key.encode()).hexdigest()
    
    @staticmethod
    def detect_bank(file_path: Path) -> Tuple[Optional[BankParser], float, Dict]:
        """
        Auto-detect which bank parser can handle this file.
        
        Returns:
            (parser, confidence, detection_details)
        """
        detection_results = []
        
        for parser in MultiBankImportService.PARSERS:
            can_parse, confidence = parser.can_parse(file_path)
            detection_results.append({
                'bank': parser.BANK_NAME,
                'can_parse': can_parse,
                'confidence': confidence
            })
        
        # Sort by confidence
        detection_results.sort(key=lambda x: x['confidence'], reverse=True)
        best_match = detection_results[0]
        
        if best_match['can_parse']:
            # Find the parser instance
            parser = next(
                p for p in MultiBankImportService.PARSERS 
                if p.BANK_NAME == best_match['bank']
            )
            return (parser, best_match['confidence'], {'detections': detection_results})
        
        return (None, 0.0, {'detections': detection_results})
    
    @staticmethod
    def save_unparsed_file(
        db: Session,
        user_id: str,
        file_path: Path,
        bank_name: Optional[str],
        detection_result: Dict,
        error_message: str
    ) -> UnparsedFile:
        """
        Save an unparsed file for admin review.
        
        Args:
            db: Database session
            user_id: User ID
            file_path: Path to the uploaded file
            bank_name: User-provided bank name (if any)
            detection_result: Detection attempt results
            error_message: Error that occurred during parsing
            
        Returns:
            UnparsedFile instance
        """
        # Ensure storage directory exists
        MultiBankImportService.UNPARSED_FILES_DIR.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        stored_filename = f"{user_id}_{timestamp}_{file_path.name}"
        stored_path = MultiBankImportService.UNPARSED_FILES_DIR / stored_filename
        
        # Copy file to storage
        shutil.copy(file_path, stored_path)
        
        # Create database record
        unparsed_file = UnparsedFile(
            user_id=user_id,
            filename=file_path.name,
            file_path=str(stored_path),
            file_size=file_path.stat().st_size,
            mime_type=f"application/{file_path.suffix[1:]}" if file_path.suffix else None,
            bank_name=bank_name,
            detection_attempted=True,
            detection_result=detection_result,
            status='pending',
            error_message=error_message
        )
        
        db.add(unparsed_file)
        db.commit()
        db.refresh(unparsed_file)
        
        return unparsed_file
    
    @staticmethod
    def import_file(
        file_path: Path,
        db: Session,
        user_id: str = 'default_user',
        bank_name: Optional[str] = None,
        workspace_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Import a bank statement file with automatic format detection.
        
        Args:
            file_path: Path to the file
            db: Database session
            user_id: User ID for multi-tenant support
            bank_name: Optional user-provided bank name
            workspace_id: Optional person ID for person-level data isolation
            
        Returns:
            Dictionary with import results
        """
        try:
            # Auto-detect bank if not provided
            parser, confidence, detection_result = MultiBankImportService.detect_bank(file_path)
            
            if parser is None:
                # No parser found - save for admin review
                error_msg = f"Could not auto-detect bank format. Please specify the bank name."
                unparsed_file = MultiBankImportService.save_unparsed_file(
                    db, user_id, file_path, bank_name, detection_result, error_msg
                )
                return {
                    'success': False,
                    'error': error_msg,
                    'unparsed_file_id': unparsed_file.id,
                    'detection_result': detection_result,
                    'requires_bank_name': True
                }
            
            # Parse the file
            try:
                df = parser.parse(file_path)
            except ValueError as e:
                # Parser exists but failed to parse - save for admin
                error_msg = f"Parser failed: {str(e)}"
                unparsed_file = MultiBankImportService.save_unparsed_file(
                    db, user_id, file_path, bank_name or parser.BANK_NAME, 
                    detection_result, error_msg
                )
                return {
                    'success': False,
                    'error': error_msg,
                    'unparsed_file_id': unparsed_file.id,
                    'detected_bank': parser.BANK_NAME,
                    'detection_confidence': confidence
                }
            
            # Normalize and import transactions
            df_normalized = df.copy()
            df_normalized['transaction_hash'] = df_normalized.apply(
                MultiBankImportService.create_transaction_hash, axis=1
            )
            
            # Get existing transaction hashes (filter by workspace_id if provided)
            hash_query = db.query(Transaction.transaction_hash).filter(Transaction.user_id == user_id)
            if workspace_id is not None:
                hash_query = hash_query.filter(Transaction.workspace_id == workspace_id)
            existing_hashes = {t.transaction_hash for t in hash_query.all()}
            
            # Filter out duplicates
            new_transactions = df_normalized[~df_normalized['transaction_hash'].isin(existing_hashes)]
            
            # Insert new transactions
            transactions_added = 0
            
            for _, row in new_transactions.iterrows():
                # Parse balance
                balance_value = None
                if 'Balance' in row and pd.notna(row['Balance']):
                    balance_str = str(row['Balance']).replace(',', '').strip()
                    if balance_str and balance_str.lower() not in ['nan', 'none', '']:
                        try:
                            balance_value = Decimal(balance_str)
                        except:
                            balance_value = None
                
                transaction = Transaction(
                    user_id=user_id,
                    workspace_id=workspace_id,
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
                
                # Populate search_text
                details = str(row['Details']) if pd.notna(row['Details']) else ''
                description = str(row['Description']) if pd.notna(row['Description']) else ''
                transaction.search_text = f"{details} {description}".strip()
                
                # Apply transformations
                TransactionService.transform_transaction(transaction)
                
                db.add(transaction)
                transactions_added += 1
            
            db.commit()
            
            return {
                'success': True,
                'transactions_added': transactions_added,
                'duplicates_skipped': len(df_normalized) - transactions_added,
                'detected_bank': parser.BANK_NAME,
                'detection_confidence': confidence
            }
            
        except Exception as e:
            # Unexpected error - save file for admin
            error_msg = f"Unexpected error: {str(e)}"
            unparsed_file = MultiBankImportService.save_unparsed_file(
                db, user_id, file_path, bank_name, 
                {'error': 'unexpected'}, error_msg
            )
            return {
                'success': False,
                'error': error_msg,
                'unparsed_file_id': unparsed_file.id
            }

