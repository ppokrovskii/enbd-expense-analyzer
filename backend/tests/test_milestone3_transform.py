"""Tests for Milestone 3: Data cleaning + transformation."""
import pytest
from datetime import date, datetime
from decimal import Decimal
from app.services.transform_service import TransformService


def test_extract_merchant_from_description():
    """Test extracting merchant from description field."""
    service = TransformService()
    
    # Test with description
    merchant = service.extract_merchant("CARREFOUR  DUBAI", "")
    assert merchant == "CARREFOUR"
    
    # Test with details when description is empty
    merchant = service.extract_merchant("", "LULU HYPERMARKET  LOCATION")
    assert merchant == "LULU HYPERMARKET"
    
    # Test with unknown merchant
    merchant = service.extract_merchant("", "")
    assert merchant == "Unknown"


def test_calculate_signed_amount():
    """Test calculating signed amounts from debit/credit."""
    service = TransformService()
    
    # Debit should be negative
    signed = service.calculate_signed_amount(Decimal("100.00"), "Debit")
    assert signed == Decimal("-100.00")
    
    # Credit should be positive
    signed = service.calculate_signed_amount(Decimal("100.00"), "Credit")
    assert signed == Decimal("100.00")
    
    # Handle None
    signed = service.calculate_signed_amount(Decimal("100.00"), None)
    assert signed == Decimal("100.00")


def test_calculate_week_start():
    """Test calculating week start (Monday)."""
    service = TransformService()
    
    # Test with a Wednesday (2025-12-24)
    date_obj = date(2025, 12, 24)
    week_start = service.calculate_week_start(date_obj)
    assert week_start == date(2025, 12, 22)  # Monday
    assert week_start.weekday() == 0  # Monday is 0
    
    # Test with a Monday (already start of week)
    date_obj = date(2025, 12, 22)
    week_start = service.calculate_week_start(date_obj)
    assert week_start == date(2025, 12, 22)


def test_is_internal_transfer():
    """Test identifying internal transfers."""
    service = TransformService()
    
    # Should detect transfer
    is_transfer = service.is_internal_transfer(
        "Transfer", 
        "TRF TO OWN ACCOUNT",
        "Between accounts"
    )
    assert is_transfer is True
    
    # Should not detect regular transaction
    is_transfer = service.is_internal_transfer(
        "CARREFOUR",
        "SHOPPING",
        "GROCERIES"
    )
    assert is_transfer is False


def test_transform_transaction():
    """Test transforming a transaction object."""
    from app.models import Transaction
    
    service = TransformService()
    
    # Create a mock transaction
    transaction = Transaction(
        date=date(2025, 12, 26),
        account="Current Account",
        description="CARREFOUR  DUBAI",
        details="Shopping",
        debit_credit="Debit",
        amount=Decimal("250.50"),
        balance=Decimal("5000.00"),
        transaction_hash="abc123",
        created_at=datetime.utcnow()
    )
    
    # Transform it
    transformed = service.transform_transaction(transaction)
    
    # Check enriched fields
    assert transformed.merchant == "CARREFOUR"
    assert transformed.amount_signed == Decimal("-250.50")
    assert transformed.week_start == date(2025, 12, 22)  # Monday
    assert transformed.month == "2025-12"
    assert transformed.year == 2025

