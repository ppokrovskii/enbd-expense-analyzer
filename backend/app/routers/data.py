"""API router for transaction data queries and filtering."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, datetime
from app.database import get_db
from app.models import Transaction
from app.services.transaction_query_service import TransactionQueryService
from pydantic import BaseModel
from decimal import Decimal


router = APIRouter(prefix="/api", tags=["data"])


class TransactionResponse(BaseModel):
    """Response model for a single transaction."""
    id: int
    date: date
    account: str
    description: Optional[str]
    details: Optional[str]
    debit_credit: Optional[str]
    amount: Decimal
    balance: Optional[Decimal]
    merchant: Optional[str]
    amount_signed: Optional[Decimal]
    category: Optional[str]
    week_start: Optional[date]
    month: Optional[str]
    year: Optional[int]
    
    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    """Response model for paginated transaction list."""
    transactions: List[TransactionResponse]
    total: int
    total_amount: float  # Total amount of ALL filtered transactions
    page: int
    page_size: int


class AggregatedData(BaseModel):
    """Aggregated data for charting."""
    period: str  # e.g., "2025-12-22" for week or "2025-12" for month
    category: str
    total: Decimal


class ChartDataResponse(BaseModel):
    """Response model for chart data."""
    data: List[AggregatedData]
    categories: List[str]  # Unique categories
    periods: List[str]  # Unique periods


@router.get("/transactions", response_model=TransactionListResponse)
def get_transactions(
    db: Session = Depends(get_db),
    start_date: Optional[date] = Query(None, description="Filter by start date (inclusive)"),
    end_date: Optional[date] = Query(None, description="Filter by end date (inclusive)"),
    categories: Optional[List[str]] = Query(None, description="Filter by categories"),
    accounts: Optional[List[str]] = Query(None, description="Filter by accounts"),
    merchant: Optional[str] = Query(None, description="Filter by merchant substring"),
    exclude_transfers: bool = Query(True, description="Exclude internal transfers"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Number of items per page")
):
    """
    Get transactions with optional filtering and pagination.
    
    Uses TransactionQueryService for consistent filtering logic.
    """
    transactions, total = TransactionQueryService.get_filtered_transactions(
        db=db,
        start_date=start_date,
        end_date=end_date,
        categories=categories,
        accounts=accounts,
        merchant=merchant,
        exclude_transfers=exclude_transfers,
        page=page,
        page_size=page_size
    )
    
    # Calculate total amount for ALL filtered transactions (not just current page)
    all_transactions, _ = TransactionQueryService.get_filtered_transactions(
        db=db,
        start_date=start_date,
        end_date=end_date,
        categories=categories,
        accounts=accounts,
        merchant=merchant,
        exclude_transfers=exclude_transfers,
        page=1,
        page_size=total  # Get all transactions to calculate total amount
    )
    
    total_amount = sum(abs(float(t.amount_signed or 0)) for t in all_transactions)
    
    return TransactionListResponse(
        transactions=transactions,
        total=total,
        total_amount=total_amount,
        page=page,
        page_size=page_size
    )


@router.get("/chart/weekly", response_model=ChartDataResponse)
def get_weekly_chart_data(
    db: Session = Depends(get_db),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    categories: Optional[List[str]] = Query(None, description="Filter by categories"),
    accounts: Optional[List[str]] = Query(None, description="Filter by accounts"),
    merchant: Optional[str] = Query(None, description="Filter by merchant substring"),
    exclude_transfers: bool = Query(True, description="Exclude internal transfers")
):
    """
    Get aggregated data for weekly stacked column chart.
    
    Uses TransactionQueryService for consistent filtering logic.
    """
    results = TransactionQueryService.get_weekly_aggregation(
        db=db,
        start_date=start_date,
        end_date=end_date,
        categories=categories,
        accounts=accounts,
        merchant=merchant,
        exclude_transfers=exclude_transfers
    )
    
    # Transform results to response format
    categories_set = set()
    periods_set = set()
    data = []
    
    for row in results:
        period_str = row.period.strftime('%Y-%m-%d') if row.period else 'Unknown'
        categories_set.add(row.category)
        periods_set.add(period_str)
        data.append(AggregatedData(
            period=period_str,
            category=row.category,
            total=row.total
        ))
    
    return ChartDataResponse(
        data=data,
        categories=sorted(list(categories_set)),
        periods=sorted(list(periods_set))
    )


@router.get("/chart/monthly", response_model=ChartDataResponse)
def get_monthly_chart_data(
    db: Session = Depends(get_db),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    categories: Optional[List[str]] = Query(None, description="Filter by categories"),
    accounts: Optional[List[str]] = Query(None, description="Filter by accounts"),
    merchant: Optional[str] = Query(None, description="Filter by merchant substring"),
    exclude_transfers: bool = Query(True, description="Exclude internal transfers")
):
    """
    Get aggregated data for monthly stacked column chart.
    
    Uses TransactionQueryService for consistent filtering logic.
    """
    results = TransactionQueryService.get_monthly_aggregation(
        db=db,
        start_date=start_date,
        end_date=end_date,
        categories=categories,
        accounts=accounts,
        merchant=merchant,
        exclude_transfers=exclude_transfers
    )
    
    # Transform results to response format
    categories_set = set()
    periods_set = set()
    data = []
    
    for row in results:
        categories_set.add(row.category)
        periods_set.add(row.period)
        data.append(AggregatedData(
            period=row.period,
            category=row.category,
            total=row.total
        ))
    
    return ChartDataResponse(
        data=data,
        categories=sorted(list(categories_set)),
        periods=sorted(list(periods_set))
    )


@router.get("/stats/summary")
def get_summary_stats(
    db: Session = Depends(get_db),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
):
    """
    Get summary statistics for transactions.
    
    Args:
        start_date: Start date for filtering
        end_date: End date for filtering
    
    Returns:
        Summary statistics including total income, expenses, and net
    """
    query = db.query(Transaction)
    
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    
    transactions = query.all()
    
    total_income = sum(
        t.amount_signed for t in transactions 
        if t.amount_signed and t.amount_signed > 0 and t.category in ['Salary', 'Incoming Transfer']
    )
    
    total_expenses = sum(
        abs(t.amount_signed) for t in transactions 
        if t.amount_signed and t.amount_signed < 0 
        and t.category not in ['Transfer Between My Accounts', 'Outgoing Transfer']
    )
    
    return {
        "total_income": float(total_income),
        "total_expenses": float(total_expenses),
        "net": float(total_income - total_expenses),
        "transaction_count": len(transactions)
    }


@router.get("/filters/options")
def get_filter_options(db: Session = Depends(get_db)):
    """
    Get available filter options (categories, accounts, date range).
    
    Returns:
        Dictionary with available categories, accounts, and date range
    """
    # Get unique categories (excluding None)
    categories = db.query(Transaction.category).distinct().filter(Transaction.category.isnot(None)).order_by(Transaction.category).all()
    categories_list = [c[0] for c in categories]
    
    # Get unique accounts
    accounts = db.query(Transaction.account).distinct().order_by(Transaction.account).all()
    accounts_list = [a[0] for a in accounts]
    
    # Get date range
    min_date = db.query(func.min(Transaction.date)).scalar()
    max_date = db.query(func.max(Transaction.date)).scalar()
    
    return {
        "categories": categories_list,
        "accounts": accounts_list,
        "min_date": min_date.isoformat() if min_date else None,
        "max_date": max_date.isoformat() if max_date else None
    }

