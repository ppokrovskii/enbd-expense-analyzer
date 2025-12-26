"""Tests for Milestone 6: Data API with filtering."""
import pytest
from httpx import AsyncClient
from app.main import app
from app.models import Transaction
from sqlalchemy.orm import Session
from datetime import date
from decimal import Decimal


@pytest.mark.asyncio
async def test_get_transactions_no_filters(test_db: Session):
    """Test fetching all transactions without filters."""
    # Insert test transactions
    trans1 = Transaction(
        date=date(2025, 12, 1),
        account='Current Account',
        merchant='CARREFOUR',
        amount=Decimal('100.00'),
        amount_signed=Decimal('-100.00'),
        category='Groceries',
        transaction_hash='hash1'
    )
    trans2 = Transaction(
        date=date(2025, 12, 2),
        account='Savings Account',
        merchant='UBER',
        amount=Decimal('50.00'),
        amount_signed=Decimal('-50.00'),
        category='Transportation',
        transaction_hash='hash2'
    )
    test_db.add_all([trans1, trans2])
    test_db.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/transactions")
    
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 2
    assert len(data['transactions']) == 2


@pytest.mark.asyncio
async def test_get_transactions_with_date_filter(test_db: Session):
    """Test filtering transactions by date range."""
    # Insert transactions across different dates
    trans1 = Transaction(
        date=date(2025, 12, 1),
        account='Current Account',
        merchant='MERCHANT1',
        amount=Decimal('100.00'),
        transaction_hash='hash1',
        category='Other'
    )
    trans2 = Transaction(
        date=date(2025, 12, 15),
        account='Current Account',
        merchant='MERCHANT2',
        amount=Decimal('50.00'),
        transaction_hash='hash2',
        category='Other'
    )
    trans3 = Transaction(
        date=date(2025, 12, 30),
        account='Current Account',
        merchant='MERCHANT3',
        amount=Decimal('75.00'),
        transaction_hash='hash3',
        category='Other'
    )
    test_db.add_all([trans1, trans2, trans3])
    test_db.commit()
    
    # Test start_date filter
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/transactions?start_date=2025-12-10")
    
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 2  # trans2 and trans3
    
    # Test end_date filter
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/transactions?end_date=2025-12-10")
    
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 1  # trans1 only


@pytest.mark.asyncio
async def test_get_transactions_with_category_filter(test_db: Session):
    """Test filtering transactions by category."""
    trans1 = Transaction(
        date=date(2025, 12, 1),
        account='Current Account',
        merchant='CARREFOUR',
        amount=Decimal('100.00'),
        transaction_hash='hash1',
        category='Groceries'
    )
    trans2 = Transaction(
        date=date(2025, 12, 2),
        account='Current Account',
        merchant='UBER',
        amount=Decimal('50.00'),
        transaction_hash='hash2',
        category='Transportation'
    )
    test_db.add_all([trans1, trans2])
    test_db.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/transactions?categories=Groceries")
    
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 1
    assert data['transactions'][0]['category'] == 'Groceries'


@pytest.mark.asyncio
async def test_get_transactions_with_merchant_filter(test_db: Session):
    """Test filtering transactions by merchant substring."""
    trans1 = Transaction(
        date=date(2025, 12, 1),
        account='Current Account',
        merchant='CARREFOUR HYPERMARKET',
        amount=Decimal('100.00'),
        transaction_hash='hash1',
        category='Groceries'
    )
    trans2 = Transaction(
        date=date(2025, 12, 2),
        account='Current Account',
        merchant='UBER TRIP',
        amount=Decimal('50.00'),
        transaction_hash='hash2',
        category='Transportation'
    )
    test_db.add_all([trans1, trans2])
    test_db.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/transactions?merchant=CARRE")
    
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 1
    assert 'CARREFOUR' in data['transactions'][0]['merchant']


@pytest.mark.asyncio
async def test_get_transactions_pagination(test_db: Session):
    """Test transaction pagination."""
    # Insert 10 transactions
    for i in range(10):
        trans = Transaction(
            date=date(2025, 12, i+1),
            account='Current Account',
            merchant=f'MERCHANT{i}',
            amount=Decimal('100.00'),
            transaction_hash=f'hash{i}',
            category='Other'
        )
        test_db.add(trans)
    test_db.commit()
    
    # Get first page
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/transactions?page=1&page_size=5")
    
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 10
    assert len(data['transactions']) == 5
    assert data['page'] == 1
    
    # Get second page
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/transactions?page=2&page_size=5")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data['transactions']) == 5
    assert data['page'] == 2


@pytest.mark.asyncio
async def test_get_weekly_chart_data(test_db: Session):
    """Test getting weekly aggregated chart data."""
    # Insert transactions in same week
    trans1 = Transaction(
        date=date(2025, 12, 22),  # Monday
        account='Current Account',
        merchant='CARREFOUR',
        amount=Decimal('100.00'),
        amount_signed=Decimal('-100.00'),
        category='Groceries',
        week_start=date(2025, 12, 22),
        transaction_hash='hash1'
    )
    trans2 = Transaction(
        date=date(2025, 12, 24),  # Wednesday
        account='Current Account',
        merchant='UBER',
        amount=Decimal('50.00'),
        amount_signed=Decimal('-50.00'),
        category='Transportation',
        week_start=date(2025, 12, 22),
        transaction_hash='hash2'
    )
    test_db.add_all([trans1, trans2])
    test_db.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/chart/weekly")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data['data']) == 2  # 2 categories
    assert 'Groceries' in data['categories']
    assert 'Transportation' in data['categories']
    assert '2025-12-22' in data['periods']


@pytest.mark.asyncio
async def test_get_monthly_chart_data(test_db: Session):
    """Test getting monthly aggregated chart data."""
    trans1 = Transaction(
        date=date(2025, 12, 1),
        account='Current Account',
        merchant='CARREFOUR',
        amount=Decimal('100.00'),
        amount_signed=Decimal('-100.00'),
        category='Groceries',
        month='2025-12',
        transaction_hash='hash1'
    )
    trans2 = Transaction(
        date=date(2025, 12, 15),
        account='Current Account',
        merchant='UBER',
        amount=Decimal('50.00'),
        amount_signed=Decimal('-50.00'),
        category='Transportation',
        month='2025-12',
        transaction_hash='hash2'
    )
    test_db.add_all([trans1, trans2])
    test_db.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/chart/monthly")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data['data']) == 2
    assert '2025-12' in data['periods']


@pytest.mark.asyncio
async def test_get_summary_stats(test_db: Session):
    """Test getting summary statistics."""
    trans1 = Transaction(
        date=date(2025, 12, 1),
        account='Current Account',
        merchant='SALARY',
        amount=Decimal('5000.00'),
        amount_signed=Decimal('5000.00'),  # Income
        category='Salary',
        transaction_hash='hash1'
    )
    trans2 = Transaction(
        date=date(2025, 12, 2),
        account='Current Account',
        merchant='CARREFOUR',
        amount=Decimal('100.00'),
        amount_signed=Decimal('-100.00'),  # Expense
        category='Groceries',
        transaction_hash='hash2'
    )
    test_db.add_all([trans1, trans2])
    test_db.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/stats/summary")
    
    assert response.status_code == 200
    data = response.json()
    assert data['total_income'] == 5000.0
    assert data['total_expenses'] == 100.0
    assert data['net'] == 4900.0
    assert data['transaction_count'] == 2

