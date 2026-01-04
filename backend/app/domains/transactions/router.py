"""Transactions API router - upload and data query endpoints."""
from fastapi import APIRouter, UploadFile, File, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date
from pathlib import Path
from pydantic import BaseModel
from decimal import Decimal
import tempfile
import shutil

from app.shared.filtered_query import FilteredQueryContext, get_filtered_context
from app.shared.database import get_db
from app.shared.dependencies import get_user_id, get_person_id
from .models import Transaction
from .service import TransactionService
from .import_service import MultiBankImportService


router = APIRouter(prefix="/api", tags=["transactions"])


# ============================================================================
# Upload Endpoints (previously upload.py)
# ============================================================================

class UploadResponse(BaseModel):
    """Response model for file uploads."""
    success: bool
    files_processed: int
    transactions_added: int
    duplicates_skipped: int
    detected_banks: dict  # filename -> bank name
    unparsed_files: List[dict]  # Files that couldn't be parsed


@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    bank_name: Optional[str] = None,  # User can specify bank name
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """
    Upload bank statement files with automatic format detection.
    
    Supports:
    - Automatic bank detection
    - Multiple file formats (.xlsx, .xls, .csv)
    - Multiple banks (ENBD, FAB, WIO, etc.)
    - Fallback to unparsed files storage for unknown formats
    """
    # Validate files have allowed extensions
    allowed_extensions = ['.xlsx', '.xls', '.csv']
    for file in files:
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.filename}. Allowed: {', '.join(allowed_extensions)}"
            )
    
    # Save uploaded files to temporary directory
    temp_dir = Path(tempfile.mkdtemp())
    temp_files = []
    
    try:
        for file in files:
            temp_file_path = temp_dir / file.filename
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            temp_files.append(temp_file_path)
        
        # Import files
        total_added = 0
        total_skipped = 0
        detected_banks = {}
        unparsed_files = []
        
        for file_path in temp_files:
            result = MultiBankImportService.import_file(
                file_path, ctx.db, ctx.user_id, bank_name, ctx.person_id
            )
            
            if result['success']:
                total_added += result['transactions_added']
                total_skipped += result['duplicates_skipped']
                detected_banks[file_path.name] = {
                    'bank': result['detected_bank'],
                    'confidence': result['detection_confidence']
                }
            else:
                # File couldn't be parsed
                unparsed_files.append({
                    'filename': file_path.name,
                    'error': result['error'],
                    'unparsed_file_id': result.get('unparsed_file_id'),
                    'detected_bank': result.get('detected_bank'),
                    'requires_bank_name': result.get('requires_bank_name', False)
                })
        
        return UploadResponse(
            success=len(unparsed_files) == 0,  # Success if all files parsed
            files_processed=len(temp_files),
            transactions_added=total_added,
            duplicates_skipped=total_skipped,
            detected_banks=detected_banks,
            unparsed_files=unparsed_files
        )
    
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Upload error: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Cleanup temporary files
        shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# Data Query Endpoints (previously data.py)
# ============================================================================

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
    start_date: Optional[date] = Query(None, description="Filter by start date (inclusive)"),
    end_date: Optional[date] = Query(None, description="Filter by end date (inclusive)"),
    categories: Optional[List[str]] = Query(None, description="Filter by categories"),
    accounts: Optional[List[str]] = Query(None, description="Filter by accounts"),
    merchant: Optional[str] = Query(None, description="Filter by merchant substring"),
    exclude_transfers: bool = Query(False, description="Exclude internal transfers"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Number of items per page"),
    sort_by: str = Query('date', description="Sort by field: 'date' or 'amount'"),
    sort_order: str = Query('desc', description="Sort order: 'asc' or 'desc'"),
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Get transactions with optional filtering, pagination, and sorting."""
    transactions, total = TransactionService.get_filtered_transactions(
        db=ctx.db,
        user_id=ctx.user_id,
        start_date=start_date,
        end_date=end_date,
        categories=categories,
        accounts=accounts,
        merchant=merchant,
        exclude_transfers=exclude_transfers,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        person_id=ctx.person_id
    )
    
    # Calculate total amount for ALL filtered transactions (not just current page)
    all_transactions, _ = TransactionService.get_filtered_transactions(
        db=ctx.db,
        user_id=ctx.user_id,
        start_date=start_date,
        end_date=end_date,
        categories=categories,
        accounts=accounts,
        merchant=merchant,
        exclude_transfers=exclude_transfers,
        page=1,
        page_size=total,
        sort_by=sort_by,
        sort_order=sort_order,
        person_id=ctx.person_id
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
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    categories: Optional[List[str]] = Query(None, description="Filter by categories"),
    accounts: Optional[List[str]] = Query(None, description="Filter by accounts"),
    merchant: Optional[str] = Query(None, description="Filter by merchant substring"),
    exclude_transfers: bool = Query(True, description="Exclude internal transfers"),
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Get aggregated data for weekly stacked column chart."""
    results = TransactionService.get_weekly_aggregation(
        db=ctx.db,
        user_id=ctx.user_id,
        start_date=start_date,
        end_date=end_date,
        categories=categories,
        accounts=accounts,
        merchant=merchant,
        exclude_transfers=exclude_transfers,
        person_id=ctx.person_id
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
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    categories: Optional[List[str]] = Query(None, description="Filter by categories"),
    accounts: Optional[List[str]] = Query(None, description="Filter by accounts"),
    merchant: Optional[str] = Query(None, description="Filter by merchant substring"),
    exclude_transfers: bool = Query(True, description="Exclude internal transfers"),
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Get aggregated data for monthly stacked column chart."""
    results = TransactionService.get_monthly_aggregation(
        db=ctx.db,
        user_id=ctx.user_id,
        start_date=start_date,
        end_date=end_date,
        categories=categories,
        accounts=accounts,
        merchant=merchant,
        exclude_transfers=exclude_transfers,
        person_id=ctx.person_id
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
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Get summary statistics for transactions."""
    query = ctx.query(Transaction)
    
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
def get_filter_options(ctx: FilteredQueryContext = Depends(get_filtered_context)):
    """Get available filter options (categories, accounts, date range)."""
    # Get unique categories (excluding None) - filtered by user/person
    categories = ctx.query(Transaction).with_entities(
        Transaction.category
    ).filter(
        Transaction.category.isnot(None)
    ).distinct().order_by(Transaction.category).all()
    categories_list = [c[0] for c in categories]
    
    # Get unique accounts
    accounts = ctx.query(Transaction).with_entities(
        Transaction.account
    ).distinct().order_by(Transaction.account).all()
    accounts_list = [a[0] for a in accounts]
    
    # Get date range
    min_date = ctx.query(Transaction).with_entities(
        func.min(Transaction.date)
    ).scalar()
    max_date = ctx.query(Transaction).with_entities(
        func.max(Transaction.date)
    ).scalar()
    
    return {
        "categories": categories_list,
        "accounts": accounts_list,
        "min_date": min_date.isoformat() if min_date else None,
        "max_date": max_date.isoformat() if max_date else None
    }


class MerchantSummary(BaseModel):
    """Summary of transactions grouped by merchant."""
    merchant: str
    category: Optional[str]
    transaction_count: int
    total_amount: Decimal
    first_date: date
    last_date: date


class MerchantListResponse(BaseModel):
    """Response model for paginated merchant list."""
    merchants: List[MerchantSummary]
    total: int
    total_amount: float
    page: int
    page_size: int


@router.get("/merchants", response_model=MerchantListResponse)
def get_merchants(
    start_date: Optional[date] = Query(None, description="Filter by start date (inclusive)"),
    end_date: Optional[date] = Query(None, description="Filter by end date (inclusive)"),
    categories: Optional[List[str]] = Query(None, description="Filter by categories"),
    accounts: Optional[List[str]] = Query(None, description="Filter by accounts"),
    merchant: Optional[str] = Query(None, description="Filter by merchant substring"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Number of items per page"),
    sort_by: str = Query('total_amount', description="Sort by: 'merchant', 'total_amount', 'transaction_count', 'last_date'"),
    sort_order: str = Query('desc', description="Sort order: 'asc' or 'desc'"),
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Get transactions grouped by merchant with aggregated stats."""
    # Build base query with filters
    base_filter = [Transaction.user_id == ctx.user_id]
    
    if ctx.person_id is not None:
        base_filter.append(Transaction.person_id == ctx.person_id)
    if start_date:
        base_filter.append(Transaction.date >= start_date)
    if end_date:
        base_filter.append(Transaction.date <= end_date)
    if categories:
        base_filter.append(Transaction.category.in_(categories))
    if accounts:
        base_filter.append(Transaction.account.in_(accounts))
    if merchant:
        base_filter.append(Transaction.merchant.ilike(f"%{merchant}%"))
    
    # Exclude null/empty merchants
    base_filter.append(Transaction.merchant.isnot(None))
    base_filter.append(Transaction.merchant != '')
    
    # Aggregate by merchant
    query = ctx.raw_query(
        Transaction.merchant,
        func.min(Transaction.category).label('category'),  # Get most common category (simplified)
        func.count(Transaction.id).label('transaction_count'),
        func.sum(func.abs(Transaction.amount_signed)).label('total_amount'),
        func.min(Transaction.date).label('first_date'),
        func.max(Transaction.date).label('last_date')
    ).filter(
        *base_filter
    ).group_by(
        Transaction.merchant
    )
    
    # Get total count for pagination
    count_subquery = query.subquery()
    total = ctx.raw_query(func.count()).select_from(count_subquery).scalar() or 0
    
    # Apply sorting
    sort_column_map = {
        'merchant': Transaction.merchant,
        'total_amount': func.sum(func.abs(Transaction.amount_signed)),
        'transaction_count': func.count(Transaction.id),
        'last_date': func.max(Transaction.date)
    }
    sort_column = sort_column_map.get(sort_by, func.sum(func.abs(Transaction.amount_signed)))
    
    if sort_order == 'asc':
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    
    # Apply pagination
    offset = (page - 1) * page_size
    results = query.offset(offset).limit(page_size).all()
    
    # Calculate grand total (all merchants matching filter)
    total_amount_query = ctx.raw_query(
        func.sum(func.abs(Transaction.amount_signed))
    ).filter(*base_filter).scalar() or 0
    
    # Transform results
    merchants = [
        MerchantSummary(
            merchant=row.merchant,
            category=row.category,
            transaction_count=row.transaction_count,
            total_amount=row.total_amount or 0,
            first_date=row.first_date,
            last_date=row.last_date
        )
        for row in results
    ]
    
    return MerchantListResponse(
        merchants=merchants,
        total=total,
        total_amount=float(total_amount_query),
        page=page,
        page_size=page_size
    )


class UpdateTransactionCategoryRequest(BaseModel):
    """Request model for updating a transaction's category."""
    category: str


@router.patch("/transactions/{transaction_id}/category")
def update_transaction_category(
    transaction_id: int,
    request: UpdateTransactionCategoryRequest,
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Update the category of a specific transaction."""
    # Find the transaction (filtered by user/person)
    transaction = ctx.get_by_id(Transaction, transaction_id)
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Update the category
    transaction.category = request.category
    ctx.commit()
    ctx.refresh(transaction)
    
    return {
        "id": transaction.id,
        "merchant": transaction.merchant,
        "category": transaction.category,
        "message": "Category updated successfully"
    }
