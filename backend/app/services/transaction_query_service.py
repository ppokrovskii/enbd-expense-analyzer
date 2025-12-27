"""
Service layer for transaction queries with consistent filtering logic.

This ensures that chart aggregations and transaction lists use the same filtering rules.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.models import Transaction
from typing import Optional, List
from datetime import date


class TransactionQueryService:
    """Centralized service for building consistent transaction queries."""
    
    @staticmethod
    def get_category_expression():
        """
        Get the standardized category expression that treats NULL as 'Other'.
        
        This ensures consistent category handling across all queries.
        """
        return case((Transaction.category.is_(None), 'Other'), else_=Transaction.category)
    
    @staticmethod
    def apply_base_filters(
        query,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        categories: Optional[List[str]] = None,
        accounts: Optional[List[str]] = None,
        merchant: Optional[str] = None,
        exclude_transfers: bool = False
    ):
        """
        Apply consistent base filters to any transaction query.
        
        Args:
            query: SQLAlchemy query object
            start_date: Filter transactions >= this date
            end_date: Filter transactions <= this date
            categories: List of categories to include (supports "Other" for NULL)
            accounts: List of accounts to filter by
            merchant: Substring to search in merchant names
            exclude_transfers: Whether to exclude 'Transfer Between My Accounts'
        
        Returns:
            Filtered query object
        """
        category_expr = TransactionQueryService.get_category_expression()
        
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
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        categories: Optional[List[str]] = None,
        accounts: Optional[List[str]] = None,
        merchant: Optional[str] = None,
        exclude_transfers: bool = False,
        page: int = 1,
        page_size: int = 50
    ):
        """
        Get paginated transactions with consistent filtering.
        
        Returns: (transactions, total_count)
        """
        query = db.query(Transaction)
        
        # Apply consistent filters
        query = TransactionQueryService.apply_base_filters(
            query,
            start_date=start_date,
            end_date=end_date,
            categories=categories,
            accounts=accounts,
            merchant=merchant,
            exclude_transfers=exclude_transfers
        )
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        transactions = query.order_by(
            Transaction.date.desc()
        ).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        return transactions, total
    
    @staticmethod
    def get_weekly_aggregation(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        categories: Optional[List[str]] = None,
        accounts: Optional[List[str]] = None,
        merchant: Optional[str] = None,
        exclude_transfers: bool = False
    ):
        """
        Get weekly aggregated data with consistent filtering.
        
        Returns: List of (period, category, total) tuples
        """
        category_expr = TransactionQueryService.get_category_expression()
        
        query = db.query(
            Transaction.week_start.label('period'),
            category_expr.label('category'),
            func.sum(func.abs(Transaction.amount_signed)).label('total')
        )
        
        # Apply consistent filters
        query = TransactionQueryService.apply_base_filters(
            query,
            start_date=start_date,
            end_date=end_date,
            categories=categories,
            accounts=accounts,
            merchant=merchant,
            exclude_transfers=exclude_transfers
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
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        categories: Optional[List[str]] = None,
        accounts: Optional[List[str]] = None,
        merchant: Optional[str] = None,
        exclude_transfers: bool = False
    ):
        """
        Get monthly aggregated data with consistent filtering.
        
        Returns: List of (period, category, total) tuples
        """
        category_expr = TransactionQueryService.get_category_expression()
        
        query = db.query(
            Transaction.month.label('period'),
            category_expr.label('category'),
            func.sum(func.abs(Transaction.amount_signed)).label('total')
        )
        
        # Apply consistent filters
        query = TransactionQueryService.apply_base_filters(
            query,
            start_date=start_date,
            end_date=end_date,
            categories=categories,
            accounts=accounts,
            merchant=merchant,
            exclude_transfers=exclude_transfers
        )
        
        # Group by month and category
        query = query.group_by(
            Transaction.month,
            category_expr
        ).order_by(Transaction.month)
        
        return query.all()

