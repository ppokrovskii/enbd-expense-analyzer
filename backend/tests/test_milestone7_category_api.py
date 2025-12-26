"""Tests for Milestone 7: Category Management API."""
import pytest
from httpx import AsyncClient
from app.main import app
from app.models import Category, Transaction
from sqlalchemy.orm import Session
from datetime import date
from decimal import Decimal


@pytest.mark.asyncio
async def test_list_categories(test_db: Session):
    """Test listing all categories."""
    # Create test categories
    cat1 = Category(name="Groceries", keywords=["CARREFOUR", "SPINNEYS"])
    cat2 = Category(name="Transportation", keywords=["UBER", "CAREEM"])
    test_db.add_all([cat1, cat2])
    test_db.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/categories/")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] in ["Groceries", "Transportation"]


@pytest.mark.asyncio
async def test_get_category_stats(test_db: Session):
    """Test getting categories with transaction counts."""
    # Create category and transactions
    cat = Category(name="Groceries", keywords=["CARREFOUR"])
    test_db.add(cat)
    test_db.commit()
    
    # Add transactions
    for i in range(3):
        trans = Transaction(
            date=date(2025, 12, i+1),
            account="Current",
            merchant="CARREFOUR",
            amount=Decimal("100.00"),
            category="Groceries",
            transaction_hash=f"hash{i}"
        )
        test_db.add(trans)
    test_db.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/categories/stats")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Groceries"
    assert data[0]["transaction_count"] == 3


@pytest.mark.asyncio
async def test_get_category_by_id(test_db: Session):
    """Test getting a specific category."""
    cat = Category(name="Groceries", keywords=["CARREFOUR"])
    test_db.add(cat)
    test_db.commit()
    test_db.refresh(cat)
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/api/categories/{cat.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Groceries"
    assert "CARREFOUR" in data["keywords"]


@pytest.mark.asyncio
async def test_get_category_not_found(test_db: Session):
    """Test getting non-existent category returns 404."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/categories/9999")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_category(test_db: Session):
    """Test creating a new category."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/categories/",
            json={"name": "Entertainment", "keywords": ["NETFLIX", "CINEMA"]}
        )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Entertainment"
    assert "NETFLIX" in data["keywords"]
    
    # Verify in database
    cat = test_db.query(Category).filter_by(name="Entertainment").first()
    assert cat is not None
    assert "CINEMA" in cat.keywords


@pytest.mark.asyncio
async def test_create_duplicate_category(test_db: Session):
    """Test creating duplicate category returns error."""
    cat = Category(name="Groceries", keywords=["CARREFOUR"])
    test_db.add(cat)
    test_db.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/categories/",
            json={"name": "Groceries", "keywords": ["SPINNEYS"]}
        )
    
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_category(test_db: Session):
    """Test updating a category."""
    cat = Category(name="Groceries", keywords=["CARREFOUR"])
    test_db.add(cat)
    test_db.commit()
    test_db.refresh(cat)
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.put(
            f"/api/categories/{cat.id}",
            json={"keywords": ["CARREFOUR", "SPINNEYS", "LULU"]}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["keywords"]) == 3
    assert "LULU" in data["keywords"]


@pytest.mark.asyncio
async def test_update_category_name(test_db: Session):
    """Test updating category name."""
    cat = Category(name="Groceries", keywords=["CARREFOUR"])
    test_db.add(cat)
    test_db.commit()
    test_db.refresh(cat)
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.put(
            f"/api/categories/{cat.id}",
            json={"name": "Food & Groceries"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Food & Groceries"


@pytest.mark.asyncio
async def test_delete_category(test_db: Session):
    """Test deleting a category."""
    cat = Category(name="Groceries", keywords=["CARREFOUR"])
    test_db.add(cat)
    test_db.commit()
    test_db.refresh(cat)
    
    # Add a transaction with this category
    trans = Transaction(
        date=date(2025, 12, 1),
        account="Current",
        merchant="CARREFOUR",
        amount=Decimal("100.00"),
        category="Groceries",
        transaction_hash="hash1"
    )
    test_db.add(trans)
    test_db.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.delete(f"/api/categories/{cat.id}")
    
    assert response.status_code == 204
    
    # Verify category is deleted
    assert test_db.query(Category).filter_by(id=cat.id).first() is None
    
    # Verify transaction category is set to "Other"
    test_db.refresh(trans)
    assert trans.category == "Other"


@pytest.mark.asyncio
async def test_apply_category_rules(test_db: Session):
    """Test applying rule-based categorization."""
    # Create category
    cat = Category(name="Groceries", keywords=["CARREFOUR"])
    test_db.add(cat)
    test_db.commit()
    
    # Create uncategorized transaction
    trans = Transaction(
        date=date(2025, 12, 1),
        account="Current",
        merchant="CARREFOUR HYPERMARKET",
        amount=Decimal("100.00"),
        category="Other",
        transaction_hash="hash1"
    )
    test_db.add(trans)
    test_db.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/categories/apply-rules")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["categorized"] == 1
    
    # Verify transaction is categorized
    test_db.refresh(trans)
    assert trans.category == "Groceries"


@pytest.mark.asyncio
async def test_seed_categories_from_config(test_db: Session, tmp_path):
    """Test seeding categories from config file."""
    # Create a temporary config file
    config_content = '''{
  "categories": [
    {
      "name": "Groceries",
      "keywords": ["CARREFOUR", "SPINNEYS"]
    },
    {
      "name": "Transportation",
      "keywords": ["UBER", "CAREEM"]
    }
  ]
}'''
    config_file = tmp_path / "categories.json"
    config_file.write_text(config_content)
    
    # Note: This test won't work with the actual endpoint since it looks for
    # config/categories.json, but we can test the service directly
    from app.services.category_service import CategoryService
    service = CategoryService()
    inserted = service.seed_categories_from_json(test_db, str(config_file))
    
    assert inserted == 2
    assert test_db.query(Category).count() == 2


@pytest.mark.asyncio
async def test_ai_recategorize_endpoint_without_api_key(test_db: Session):
    """Test AI recategorization fails gracefully without API key."""
    import os
    
    # Temporarily remove API key
    old_key = os.environ.get('OPENAI_API_KEY')
    if 'OPENAI_API_KEY' in os.environ:
        del os.environ['OPENAI_API_KEY']
    
    try:
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/api/categories/ai-recategorize",
                json={"category_name": None, "force_recategorize": False}
            )
        
        assert response.status_code == 400
        assert "OPENAI_API_KEY" in response.json()["detail"]
    finally:
        # Restore API key
        if old_key:
            os.environ['OPENAI_API_KEY'] = old_key

