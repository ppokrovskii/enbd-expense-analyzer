"""Transformation service for enriching transaction data."""
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List
import pandas as pd
from sqlalchemy.orm import Session
from app.models import Transaction


class TransformService:
    """Service for transforming and enriching transaction data."""
    
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
    def calculate_week_start(date) -> datetime:
        """Calculate the start of the week (Monday) for a given date."""
        weekday = date.weekday()
        week_start = date - timedelta(days=weekday)
        return week_start
    
    @staticmethod
    def is_internal_transfer(merchant: str, description: str, details: str) -> bool:
        """Check if a transaction is an internal transfer between accounts."""
        transfer_keywords = [
            'transfer',
            'trf',
            'to own account',
            'from own account',
            'between accounts'
        ]
        
        combined_text = f"{merchant} {description} {details}".lower()
        return any(keyword in combined_text for keyword in transfer_keywords)
    
    def transform_transaction(self, transaction: Transaction) -> Transaction:
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
        transaction.merchant = self.extract_merchant(
            transaction.description,
            transaction.details
        )
        
        # Calculate signed amount
        transaction.amount_signed = self.calculate_signed_amount(
            transaction.amount,
            transaction.debit_credit
        )
        
        # Add date dimensions
        transaction.week_start = self.calculate_week_start(transaction.date)
        transaction.month = transaction.date.strftime('%Y-%m')
        transaction.year = transaction.date.year
        
        return transaction
    
    def transform_all(self, db: Session) -> int:
        """
        Transform all transactions in the database that haven't been transformed yet.
        
        Returns:
            Number of transactions transformed
        """
        # Get transactions that don't have merchant set yet
        transactions = db.query(Transaction).filter(
            Transaction.merchant.is_(None)
        ).all()
        
        count = 0
        for transaction in transactions:
            self.transform_transaction(transaction)
            count += 1
        
        if count > 0:
            db.commit()
        
        return count

