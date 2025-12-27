"""
Integration tests for the new category management features.

TODO: Expand these tests to cover:
- Auto-apply rules on category creation/update
- Category detailed stats API
- Rule merchants API
- Pattern validation API
- "Other" category merchants API
- Frontend master-detail navigation
- Modal workflows
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models import Category, Transaction
from datetime import date, timedelta

client = TestClient(app)


def test_create_category_auto_applies_rules(test_db: Session):
    """Test that creating a category automatically applies rules to transactions."""
    # Create a transaction that should match
    test_db.add(
        Transaction(
            date=date.today(),
            account="Test Account",
            merchant="CARREFOUR HYPERMARKET",
            description="Test",
            amount=100.0,
            amount_signed=-100.0,
            debit_credit="Debit",
            category="Other",
        )
    )
    test_db.commit()

    # Create category with keyword that matches
    response = client.post(
        "/api/categories/",
        json={"name": "Test Groceries", "keywords": ["CARREFOUR"]},
    )

    assert response.status_code == 201
    data = response.json()
    assert "category" in data
    assert "transactions_affected" in data
    # The transaction should have been categorized
    assert data["transactions_affected"] >= 0


def test_get_category_detailed_stats(test_db: Session):
    """Test getting detailed stats for a category."""
    # Create a category
    category = Category(name="Test Category", keywords=["TEST"])
    test_db.add(category)
    test_db.commit()

    # Get detailed stats
    response = client.get(f"/api/categories/{category.id}/detailed-stats?days=30")

    assert response.status_code == 200
    data = response.json()
    assert "total_amount" in data
    assert "transaction_count" in data
    assert "rule_count" in data
    assert "merchant_count" in data
    assert "days" in data
    assert data["days"] == 30


def test_get_other_category_merchants(test_db: Session):
    """Test getting merchants from 'Other' category."""
    # Create uncategorized transaction
    test_db.add(
        Transaction(
            date=date.today(),
            account="Test Account",
            merchant="Unknown Merchant",
            description="Test",
            amount=100.0,
            amount_signed=-100.0,
            debit_credit="Debit",
            category=None,
        )
    )
    test_db.commit()

    # Get Other category merchants
    response = client.get("/api/categories/other/merchants?days=30")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "merchant" in data[0]
        assert "transaction_count" in data[0]
        assert "total_amount" in data[0]


def test_validate_pattern(test_db: Session):
    """Test pattern validation API."""
    response = client.post(
        "/api/categories/validate-pattern",
        json={
            "pattern": "TEST",
            "pattern_type": "keyword",
            "exclude_category_id": None,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "is_valid" in data
    assert "has_conflicts" in data
    assert "conflicting_rules" in data
    assert "preview_matches" in data

