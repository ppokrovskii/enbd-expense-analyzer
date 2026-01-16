"""
Transaction service combining import, transform, and query functionality.
"""
import re
import hashlib
import decimal
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, List, Tuple, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from .models import Transaction


class TransactionService:
    """Unified service for transaction import, transformation, and queries."""
    
    # ========================================================================
    # Query Methods (previously TransactionQueryService)
    # ========================================================================
    
    @staticmethod
    def get_category_expression():
        """
        Get the standardized category expression that treats NULL/empty as 'Uncategorized'.
        
        This ensures consistent category handling across all queries.
        'Uncategorized' = needs categorization (NULL or '')
        'Other' = intentionally marked as miscellaneous
        """
        return case(
            (Transaction.category.is_(None), 'Uncategorized'),
            (Transaction.category == '', 'Uncategorized'),
            else_=Transaction.category
        )
    
    @staticmethod
    def apply_base_filters(
        query,
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        categories: Optional[List[str]] = None,
        accounts: Optional[List[str]] = None,
        merchant: Optional[str] = None,
        exclude_transfers: bool = False,
        person_id: Optional[int] = None
    ):
        """
        Apply consistent base filters to any transaction query.
        
        Args:
            query: SQLAlchemy query object
            user_id: User ID for multi-tenant filtering
            start_date: Filter transactions >= this date
            end_date: Filter transactions <= this date
            categories: List of categories to include (supports "Other" for NULL)
            accounts: List of accounts to filter by
            merchant: Substring to search in merchant names
            exclude_transfers: Whether to exclude 'Transfer Between My Accounts'
            person_id: Person ID for person-level data isolation (if None, uses user_id only)
        
        Returns:
            Filtered query object
        """
        category_expr = TransactionService.get_category_expression()
        
        # ALWAYS filter by user_id for multi-tenant isolation
        query = query.filter(Transaction.user_id == user_id)
        
        # Filter by person_id if provided (for multi-person isolation)
        if person_id is not None:
            query = query.filter(Transaction.person_id == person_id)
        
        # Exclude internal transfers if requested
        if exclude_transfers:
            query = query.filter(category_expr != 'Transfer Between My Accounts')
        
        # Date filters
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)
        
        # Category filter (handles "Other" for NULL categories)
        if categories:
            query = query.filter(category_expr.in_(categories))
        
        # Account filter
        if accounts:
            query = query.filter(Transaction.account.in_(accounts))
        
        # Merchant substring search
        if merchant:
            query = query.filter(Transaction.merchant.ilike(f"%{merchant}%"))
        
        return query
    
    @staticmethod
    def get_filtered_transactions(
        db: Session,
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        categories: Optional[List[str]] = None,
        accounts: Optional[List[str]] = None,
        merchant: Optional[str] = None,
        exclude_transfers: bool = False,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = 'date',
        sort_order: str = 'desc',
        person_id: Optional[int] = None
    ) -> Tuple[List[Transaction], int]:
        """
        Get paginated transactions with consistent filtering.
        
        Returns: (transactions, total_count)
        """
        query = db.query(Transaction)
        
        # Apply consistent filters
        query = TransactionService.apply_base_filters(
            query,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            categories=categories,
            accounts=accounts,
            merchant=merchant,
            exclude_transfers=exclude_transfers,
            person_id=person_id
        )
        
        # Get total count
        total = query.count()
        
        # Determine sort field
        if sort_by == 'amount':
            sort_field = func.abs(Transaction.amount_signed)
        else:  # default to date
            sort_field = Transaction.date
        
        # Apply sort order
        if sort_order == 'asc':
            query = query.order_by(sort_field.asc())
        else:  # default to desc
            query = query.order_by(sort_field.desc())
        
        # Apply pagination
        transactions = query.offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        return transactions, total
    
    @staticmethod
    def get_weekly_aggregation(
        db: Session,
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        categories: Optional[List[str]] = None,
        accounts: Optional[List[str]] = None,
        merchant: Optional[str] = None,
        exclude_transfers: bool = False,
        person_id: Optional[int] = None
    ):
        """
        Get weekly aggregated data with consistent filtering.
        
        Returns: List of (period, category, total) tuples
        """
        category_expr = TransactionService.get_category_expression()
        
        query = db.query(
            Transaction.week_start.label('period'),
            category_expr.label('category'),
            func.sum(func.abs(Transaction.amount_signed)).label('total')
        )
        
        # Apply consistent filters
        query = TransactionService.apply_base_filters(
            query,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            categories=categories,
            accounts=accounts,
            merchant=merchant,
            exclude_transfers=exclude_transfers,
            person_id=person_id
        )
        
        # Group by week and category
        query = query.group_by(
            Transaction.week_start,
            category_expr
        ).order_by(Transaction.week_start)
        
        return query.all()
    
    @staticmethod
    def get_monthly_aggregation(
        db: Session,
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        categories: Optional[List[str]] = None,
        accounts: Optional[List[str]] = None,
        merchant: Optional[str] = None,
        exclude_transfers: bool = False,
        person_id: Optional[int] = None
    ):
        """
        Get monthly aggregated data with consistent filtering.
        
        Returns: List of (period, category, total) tuples
        """
        category_expr = TransactionService.get_category_expression()
        
        query = db.query(
            Transaction.month.label('period'),
            category_expr.label('category'),
            func.sum(func.abs(Transaction.amount_signed)).label('total')
        )
        
        # Apply consistent filters
        query = TransactionService.apply_base_filters(
            query,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            categories=categories,
            accounts=accounts,
            merchant=merchant,
            exclude_transfers=exclude_transfers,
            person_id=person_id
        )
        
        # Group by month and category
        query = query.group_by(
            Transaction.month,
            category_expr
        ).order_by(Transaction.month)
        
        return query.all()
    
    # ========================================================================
    # Transform Methods (previously TransformService)
    # ========================================================================
    
    @staticmethod
    def extract_merchant(description: str, details: str) -> str:
        """
        Extract merchant name from description or details.
        
        Priority: Description first, then Details if Description is empty.
        Extract the first part before double spaces.
        """
        source_text = None
        
        if description and str(description).strip() != '' and str(description).lower() != 'nan':
            source_text = str(description).strip()
        elif details and str(details).strip() != '' and str(details).lower() != 'nan':
            source_text = str(details).strip()
        
        if not source_text:
            return "Unknown"
        
        # Remove double spaces and everything after
        parts = re.split(r'\s{2,}', source_text)
        merchant = parts[0].strip()
        
        return merchant if merchant else "Unknown"
    
    @staticmethod
    def calculate_signed_amount(amount: Decimal, debit_credit: str) -> Decimal:
        """
        Calculate signed amount based on debit/credit indicator.
        
        Debit (outgoing) = negative
        Credit (incoming) = positive
        """
        if not debit_credit:
            return amount
        
        debit_credit_lower = str(debit_credit).lower()
        if 'debit' in debit_credit_lower:
            return -abs(amount)
        elif 'credit' in debit_credit_lower:
            return abs(amount)
        else:
            return amount
    
    @staticmethod
    def calculate_week_start(dt: date) -> date:
        """Calculate the start of the week (Monday) for a given date."""
        weekday = dt.weekday()
        week_start = dt - timedelta(days=weekday)
        return week_start
    
    @staticmethod
    def is_internal_transfer(description: str, details: str, merchant: str) -> bool:
        """
        Detect if a transaction is an internal transfer between accounts.
        
        Args:
            description: Transaction description
            details: Transaction details
            merchant: Extracted merchant name
            
        Returns:
            True if the transaction appears to be an internal transfer
        """
        # Combine all text to search
        combined = f"{description or ''} {details or ''} {merchant or ''}".upper()
        
        # Common patterns for internal transfers
        transfer_patterns = [
            'TRANSFER TO OWN',
            'TRF TO OWN',
            'TRANSFER FROM OWN',
            'TRF FROM OWN',
            'BETWEEN ACCOUNTS',
            'INTERNAL TRANSFER',
            'OWN ACCOUNT',
            'SELF TRANSFER'
        ]
        
        for pattern in transfer_patterns:
            if pattern in combined:
                return True
        
        return False
    
    @staticmethod
    def transform_transaction(transaction: Transaction) -> Transaction:
        """
        Apply all transformations to a single transaction.
        
        Enriches the transaction with:
        - Merchant name
        - Signed amount
        - Week start date
        - Month (YYYY-MM)
        - Year
        """
        # Extract merchant
        transaction.merchant = TransactionService.extract_merchant(
            transaction.description,
            transaction.details
        )
        
        # Calculate signed amount
        transaction.amount_signed = TransactionService.calculate_signed_amount(
            transaction.amount,
            transaction.debit_credit
        )
        
        # Add date dimensions
        transaction.week_start = TransactionService.calculate_week_start(transaction.date)
        transaction.month = transaction.date.strftime('%Y-%m')
        transaction.year = transaction.date.year
        
        return transaction
    
    # ========================================================================
    # Import Methods (previously ImportService)
    # ========================================================================
    
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
    
    @staticmethod
    def import_file(file_path: Path, db: Session, user_id: str = 'default_user') -> Dict[str, int]:
        """
        Import a single XLSX file into the database.
        
        Args:
            file_path: Path to the XLSX file
            db: Database session
            user_id: User ID for multi-tenant support
        
        Returns:
            Dictionary with statistics: {transactions_added: int, duplicates_skipped: int}
        """
        # Parse XLSX
        df = TransactionService.parse_xlsx(file_path)
        
        # Normalize for hashing
        df_normalized = TransactionService.normalize_data(df)
        
        # Create hashes
        df_normalized['transaction_hash'] = df_normalized.apply(TransactionService.create_transaction_hash, axis=1)
        
        # Get existing hashes from database for this user
        existing_hashes = {
            t.transaction_hash 
            for t in db.query(Transaction.transaction_hash).filter(Transaction.user_id == user_id).all()
        }
        
        # Filter out duplicates
        new_transactions = df_normalized[~df_normalized['transaction_hash'].isin(existing_hashes)]
        
        # Insert new transactions
        transactions_added = 0
        
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
                user_id=user_id,
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
            
            # Populate search_text for enhanced categorization
            details = str(row['Details']) if pd.notna(row['Details']) else ''
            description = str(row['Description']) if pd.notna(row['Description']) else ''
            transaction.search_text = f"{details} {description}".strip()
            
            # Apply transformations immediately
            TransactionService.transform_transaction(transaction)
            
            db.add(transaction)
            transactions_added += 1
        
        db.commit()
        
        return {
            'transactions_added': transactions_added,
            'duplicates_skipped': len(df_normalized) - transactions_added
        }

