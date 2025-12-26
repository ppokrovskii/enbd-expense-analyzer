"""API router for category management (CRUD + AI operations)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.models import Category, Transaction
from app.services.category_service import CategoryService
from app.services.llm_service import LLMCategorizationService


router = APIRouter(prefix="/api/categories", tags=["categories"])


class CategoryCreate(BaseModel):
    """Request model for creating a category."""
    name: str
    keywords: List[str]


class CategoryUpdate(BaseModel):
    """Request model for updating a category."""
    name: Optional[str] = None
    keywords: Optional[List[str]] = None


class CategoryResponse(BaseModel):
    """Response model for a category."""
    id: int
    name: str
    keywords: List[str]
    
    class Config:
        from_attributes = True


class CategoryStatsResponse(BaseModel):
    """Response with category and transaction count."""
    id: int
    name: str
    keywords: List[str]
    transaction_count: int


class AIRecategorizeRequest(BaseModel):
    """Request for AI recategorization."""
    category_name: Optional[str] = None  # If None, recategorize all "Other"
    force_recategorize: bool = False  # If True, recategorize even if already categorized


class AIRecategorizeResponse(BaseModel):
    """Response from AI recategorization."""
    processed: int
    cached: int
    llm_calls: int
    categorized: int
    estimated_cost_usd: float


@router.get("/", response_model=List[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    """
    Get all categories.
    
    Returns:
        List of all categories with their keywords
    """
    categories = db.query(Category).all()
    return categories


@router.get("/stats", response_model=List[CategoryStatsResponse])
def get_category_stats(db: Session = Depends(get_db)):
    """
    Get all categories with transaction counts.
    
    Returns:
        List of categories with their transaction counts
    """
    categories = db.query(Category).all()
    result = []
    
    for category in categories:
        count = db.query(Transaction).filter(Transaction.category == category.name).count()
        result.append(CategoryStatsResponse(
            id=category.id,
            name=category.name,
            keywords=category.keywords or [],
            transaction_count=count
        ))
    
    return result


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """
    Get a specific category by ID.
    
    Args:
        category_id: Category ID
    
    Returns:
        Category details
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.post("/", response_model=CategoryResponse, status_code=201)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    """
    Create a new category.
    
    Args:
        category: Category data (name and keywords)
    
    Returns:
        Created category
    """
    # Check if category with same name already exists
    existing = db.query(Category).filter(Category.name == category.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Category '{category.name}' already exists")
    
    new_category = Category(
        name=category.name,
        keywords=category.keywords
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    
    return new_category


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a category.
    
    Args:
        category_id: Category ID
        category_update: Updated category data
    
    Returns:
        Updated category
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Update fields if provided
    if category_update.name is not None:
        # Check if new name conflicts with existing category
        existing = db.query(Category).filter(
            Category.name == category_update.name,
            Category.id != category_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Category '{category_update.name}' already exists")
        category.name = category_update.name
    
    if category_update.keywords is not None:
        category.keywords = category_update.keywords
    
    db.commit()
    db.refresh(category)
    
    return category


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    """
    Delete a category.
    
    Args:
        category_id: Category ID
    
    Note:
        Transactions with this category will be set to "Other"
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Update transactions to "Other" category
    db.query(Transaction).filter(Transaction.category == category.name).update(
        {"category": "Other"}
    )
    
    db.delete(category)
    db.commit()
    
    return None


@router.post("/apply-rules")
def apply_category_rules(db: Session = Depends(get_db)):
    """
    Apply rule-based categorization to all uncategorized transactions.
    
    Returns:
        Number of transactions categorized
    """
    category_service = CategoryService()
    categorized_count = category_service.categorize_transactions(db)
    
    return {
        "success": True,
        "categorized": categorized_count,
        "message": f"Categorized {categorized_count} transaction(s) using rules"
    }


@router.post("/ai-recategorize", response_model=AIRecategorizeResponse)
def ai_recategorize(
    request: AIRecategorizeRequest,
    db: Session = Depends(get_db)
):
    """
    Use AI to recategorize transactions.
    
    Args:
        request: Recategorization parameters
            - category_name: Specific category to recategorize (default: "Other")
            - force_recategorize: Recategorize even if already categorized
    
    Returns:
        Statistics about the AI categorization process
    """
    try:
        llm_service = LLMCategorizationService()
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"LLM service initialization failed: {str(e)}. Make sure OPENAI_API_KEY is set."
        )
    
    # If specific category requested, update those transactions to "Other" first
    if request.category_name and request.force_recategorize:
        count = db.query(Transaction).filter(
            Transaction.category == request.category_name
        ).update({"category": "Other"})
        db.commit()
    
    # Run AI categorization
    stats = llm_service.categorize_uncategorized_transactions(db)
    
    # Estimate cost (rough estimate: $0.001 per LLM call for gpt-4o-mini, $0.015 for gpt-4o)
    cost_per_call = 0.015 if "gpt-4o" in llm_service.model else 0.001
    estimated_cost = stats['llm_calls'] * cost_per_call
    
    return AIRecategorizeResponse(
        processed=stats['processed'],
        cached=stats['cached'],
        llm_calls=stats['llm_calls'],
        categorized=stats['categorized'],
        estimated_cost_usd=round(estimated_cost, 4)
    )


@router.post("/seed-from-config")
def seed_categories_from_config(db: Session = Depends(get_db)):
    """
    Seed categories from config/categories.json file.
    Useful for initial setup or resetting to default categories.
    
    Returns:
        Number of categories inserted
    """
    category_service = CategoryService()
    
    try:
        inserted = category_service.seed_categories_from_json(db, "config/categories.json")
        return {
            "success": True,
            "inserted": inserted,
            "message": f"Inserted {inserted} new category(ies) from config"
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="config/categories.json not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to seed categories: {str(e)}")

