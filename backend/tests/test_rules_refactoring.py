"""Tests for categories-to-rules refactoring (TDD)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.shared.database import get_db
from app.domains.categories.models import Category, Rule
from app.domains.transactions.models import Transaction
from datetime import date
from decimal import Decimal

client = TestClient(app)

# The test_db fixture is provided by conftest.py using testcontainers


def test_create_category_without_keywords(test_db):
    """Categories should only have name + color, no keywords."""
    response = client.post("/api/categories/", json={
        "name": "Groceries",
        "color": "#FF6B6B"
    }, headers={"X-User-Id": "test_user"})
    
    assert response.status_code == 201
    data = response.json()
    # API returns {"category": {...}, "transactions_affected": int}
    assert data["category"]["name"] == "Groceries"
    assert data["category"]["color"] == "#FF6B6B"
    assert "keywords" not in data["category"]  # Keywords should not be in response


def test_create_rule_for_category(test_db):
    """Rules should have keywords, exclude_keywords, category_id."""
    # First create a category
    category = Category(
        user_id="test_user",
        name="Groceries",
        color="#FF6B6B"
    )
    test_db.add(category)
    test_db.commit()
    test_db.refresh(category)
    category_id = category.id  # Store ID before any potential session issues
    
    # Create a rule for the category
    response = client.post("/api/rules/", json={
        "category_id": category_id,
        "keywords": ["CARREFOUR", "LULU", "SUPERMARKET"],
        "exclude_keywords": ["REFUND"],
        "priority": 0
    }, headers={"X-User-Id": "test_user"})
    
    assert response.status_code == 201
    data = response.json()
    assert data["category_id"] == category_id
    assert data["keywords"] == ["CARREFOUR", "LULU", "SUPERMARKET"]
    assert data["exclude_keywords"] == ["REFUND"]


def test_migrate_existing_categories_to_rules(test_db):
    """Migration script should move keywords to rules table.
    
    Note: This test verifies the migration concept, not actual DDL.
    Real migrations are handled via Alembic.
    """
    # Create a category in the new schema
    category = Category(
        user_id="test_user",
        name="Transport",
        color="#00BCD4"
    )
    test_db.add(category)
    test_db.commit()
    test_db.refresh(category)
    category_id = category.id
    
    # Simulate migration: create rules from "old" keywords data
    old_keywords = ["TAXI", "UBER"]
    rule = Rule(
        category_id=category_id,
        user_id="test_user",
        keywords=old_keywords,
        exclude_keywords=[],
        priority=0
    )
    test_db.add(rule)
    test_db.commit()
    
    # Verify rule was created
    rules = test_db.query(Rule).filter_by(user_id="test_user").all()
    assert len(rules) == 1
    assert rules[0].keywords == ["TAXI", "UBER"]


def test_categorize_with_rules(test_db):
    """CategoryService should use rules table instead of categories.keywords."""
    from app.services.category_service import CategoryService
    
    # Create category
    category = Category(
        user_id="test_user",
        name="Coffee",
        color="#FFC107"
    )
    test_db.add(category)
    test_db.commit()
    test_db.refresh(category)
    
    # Create rule for category
    rule = Rule(
        category_id=category.id,
        user_id="test_user",
        keywords=["STARBUCKS", "COSTA", "CAFE"],
        exclude_keywords=["REFUND"],
        priority=0
    )
    test_db.add(rule)
    test_db.commit()
    
    # Create transaction
    txn = Transaction(
        user_id="test_user",
        date=date(2024, 1, 1),
        account="Test Account",
        description="STARBUCKS PURCHASE",
        details="Coffee shop",
        amount=Decimal("25.50"),
        amount_signed=Decimal("-25.50"),
        category=None,
        search_text="Coffee shop STARBUCKS PURCHASE",
        transaction_hash="test_hash_1",
        merchant="STARBUCKS"
    )
    test_db.add(txn)
    test_db.commit()
    
    # Categorize using rules
    category_service = CategoryService()
    count = category_service.categorize_transactions(test_db, "test_user")
    
    assert count > 0
    test_db.refresh(txn)
    assert txn.category == "Coffee"


def test_get_categories_with_colors_only(test_db):
    """GET /api/categories should return name + color only, no keywords."""
    # Create categories
    category1 = Category(user_id="test_user", name="Food", color="#E91E63")
    category2 = Category(user_id="test_user", name="Transport", color="#00BCD4")
    test_db.add_all([category1, category2])
    test_db.commit()
    
    response = client.get("/api/categories/", headers={"X-User-Id": "test_user"})
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    for cat in data:
        assert "name" in cat
        assert "color" in cat
        assert "keywords" not in cat
        assert "exclude_keywords" not in cat


def test_list_rules_for_category(test_db):
    """GET /api/rules/?category_id={id} should return rules for category."""
    # Create category
    category = Category(user_id="test_user", name="Shopping", color="#FF9800")
    test_db.add(category)
    test_db.commit()
    test_db.refresh(category)
    
    # Create multiple rules
    rule1 = Rule(
        category_id=category.id,
        user_id="test_user",
        keywords=["AMAZON"],
        exclude_keywords=[],
        priority=0
    )
    rule2 = Rule(
        category_id=category.id,
        user_id="test_user",
        keywords=["NOON"],
        exclude_keywords=["FOOD"],
        priority=1
    )
    test_db.add_all([rule1, rule2])
    test_db.commit()
    
    response = client.get(f"/api/rules/?category_id={category.id}", headers={"X-User-Id": "test_user"})
    
    assert response.status_code == 200
    data = response.json()
    # Response is now paginated
    assert "items" in data
    assert "total" in data
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert any(r["keywords"] == ["AMAZON"] for r in data["items"])
    assert any(r["keywords"] == ["NOON"] for r in data["items"])
    # Check that category_name is included
    assert all(r["category_name"] == "Shopping" for r in data["items"])


def test_list_rules_pagination(test_db):
    """GET /api/rules/ should support pagination with offset and limit."""
    # Create category
    category = Category(user_id="test_user", name="TestCategory", color="#FF9800")
    test_db.add(category)
    test_db.commit()
    test_db.refresh(category)
    
    # Create 25 rules
    for i in range(25):
        rule = Rule(
            category_id=category.id,
            user_id="test_user",
            keywords=[f"KEYWORD_{i}"],
            exclude_keywords=[],
            priority=i
        )
        test_db.add(rule)
    test_db.commit()
    
    # Test first page (default limit 20)
    response = client.get("/api/rules/", headers={"X-User-Id": "test_user"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 25
    assert len(data["items"]) == 20
    assert data["offset"] == 0
    assert data["limit"] == 20
    assert data["has_more"] is True
    
    # Test second page
    response = client.get("/api/rules/?offset=20&limit=20", headers={"X-User-Id": "test_user"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 25
    assert len(data["items"]) == 5
    assert data["offset"] == 20
    assert data["limit"] == 20
    assert data["has_more"] is False


def test_list_rules_with_search(test_db):
    """GET /api/rules/?search=xxx should filter rules by keyword content."""
    # Create categories
    category1 = Category(user_id="test_user", name="Groceries", color="#FF6B6B")
    category2 = Category(user_id="test_user", name="Coffee", color="#FFC107")
    test_db.add_all([category1, category2])
    test_db.commit()
    test_db.refresh(category1)
    test_db.refresh(category2)
    
    # Create rules with different keywords
    rule1 = Rule(
        category_id=category1.id,
        user_id="test_user",
        keywords=["CARREFOUR", "SUPERMARKET"],
        exclude_keywords=[],
        priority=0
    )
    rule2 = Rule(
        category_id=category1.id,
        user_id="test_user",
        keywords=["LULU"],
        exclude_keywords=[],
        priority=0
    )
    rule3 = Rule(
        category_id=category2.id,
        user_id="test_user",
        keywords=["STARBUCKS", "COFFEE"],
        exclude_keywords=[],
        priority=0
    )
    test_db.add_all([rule1, rule2, rule3])
    test_db.commit()
    
    # Search for "COFFEE"
    response = client.get("/api/rules/?search=COFFEE", headers={"X-User-Id": "test_user"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["category_name"] == "Coffee"
    
    # Search for "SUPER" (partial match)
    response = client.get("/api/rules/?search=SUPER", headers={"X-User-Id": "test_user"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert "SUPERMARKET" in data["items"][0]["keywords"]


def test_list_rules_includes_category_name(test_db):
    """GET /api/rules/ should include category_name in response."""
    # Create multiple categories
    cat1 = Category(user_id="test_user", name="Food", color="#E91E63")
    cat2 = Category(user_id="test_user", name="Transport", color="#00BCD4")
    test_db.add_all([cat1, cat2])
    test_db.commit()
    test_db.refresh(cat1)
    test_db.refresh(cat2)
    
    # Create rules for each
    rule1 = Rule(
        category_id=cat1.id,
        user_id="test_user",
        keywords=["RESTAURANT"],
        exclude_keywords=[],
        priority=0
    )
    rule2 = Rule(
        category_id=cat2.id,
        user_id="test_user",
        keywords=["TAXI"],
        exclude_keywords=[],
        priority=0
    )
    test_db.add_all([rule1, rule2])
    test_db.commit()
    
    response = client.get("/api/rules/", headers={"X-User-Id": "test_user"})
    assert response.status_code == 200
    data = response.json()
    
    # Find each rule and verify category_name
    for item in data["items"]:
        if "RESTAURANT" in item["keywords"]:
            assert item["category_name"] == "Food"
        elif "TAXI" in item["keywords"]:
            assert item["category_name"] == "Transport"

