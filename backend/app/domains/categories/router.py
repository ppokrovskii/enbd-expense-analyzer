"""Categories API router - Category CRUD, Rules, and AI operations."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.shared.database import get_db
from app.shared.dependencies import get_user_id
from .models import Category, Rule
from .service import CategoryService
from .llm_service import LLMCategorizationService
from app.domains.transactions.models import Transaction


router = APIRouter(prefix="/api", tags=["categories"])


# ============================================================================
# Pydantic Models
# ============================================================================

class CategoryCreate(BaseModel):
    name: str
    color: Optional[str] = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    color: Optional[str] = None
    
    class Config:
        from_attributes = True


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


class CategoryCreateResponse(BaseModel):
    category: CategoryResponse
    transactions_affected: int


class RuleCreate(BaseModel):
    category_id: int
    keywords: List[str]
    exclude_keywords: Optional[List[str]] = []
    priority: int = 0


class RuleUpdate(BaseModel):
    keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None
    priority: Optional[int] = None


class RuleResponse(BaseModel):
    id: int
    category_id: int
    keywords: List[str]
    exclude_keywords: List[str]
    priority: int
    
    class Config:
        from_attributes = True


class RuleWithCategoryResponse(BaseModel):
    id: int
    category_id: int
    category_name: str
    keywords: List[str]
    exclude_keywords: List[str]
    priority: int
    
    class Config:
        from_attributes = True


class PaginatedRulesResponse(BaseModel):
    items: List[RuleWithCategoryResponse]
    total: int
    offset: int
    limit: int
    has_more: bool


class RuleMerchantGroup(BaseModel):
    merchant: str
    transaction_count: int
    total_amount: float


class AIBulkSuggestion(BaseModel):
    merchant: str
    suggested_category: str
    suggested_pattern: str
    pattern_type: str
    transaction_count: int
    total_amount: float
    is_new_category: bool


class AIBulkSuggestRequest(BaseModel):
    days: int = 30
    level: str = "global"
    category_id: Optional[int] = None
    rule_index: Optional[int] = None
    merchant: Optional[str] = None
    merchants: Optional[List[str]] = None
    limit: int = 1000


class AIBulkApplyRequest(BaseModel):
    suggestions: List[dict]
    auto_create_rules: bool = True


# ============================================================================
# Category CRUD Endpoints
# ============================================================================

@router.get("/categories/", response_model=List[CategoryResponse])
def list_categories(db: Session = Depends(get_db), user_id: str = Depends(get_user_id)):
    """Get all categories."""
    categories = db.query(Category).filter(Category.user_id == user_id).all()
    return categories


class CategoryWithStats(BaseModel):
    id: int
    name: str
    color: Optional[str] = None
    transaction_count: int = 0
    total_amount: float = 0.0
    
    class Config:
        from_attributes = True


@router.get("/categories/stats", response_model=List[CategoryWithStats])
def get_categories_with_stats(db: Session = Depends(get_db), user_id: str = Depends(get_user_id)):
    """Get all categories with transaction statistics."""
    categories = db.query(Category).filter(Category.user_id == user_id).all()
    
    # Get transaction stats per category
    stats = db.query(
        Transaction.category,
        func.count(Transaction.id).label('count'),
        func.sum(func.abs(Transaction.amount_signed)).label('total')
    ).filter(
        Transaction.user_id == user_id,
        Transaction.category.isnot(None)
    ).group_by(Transaction.category).all()
    
    stats_map = {s.category: {'count': s.count, 'total': float(s.total) if s.total else 0} for s in stats}
    
    return [
        CategoryWithStats(
            id=cat.id,
            name=cat.name,
            color=cat.color,
            transaction_count=stats_map.get(cat.name, {}).get('count', 0),
            total_amount=stats_map.get(cat.name, {}).get('total', 0)
        )
        for cat in categories
    ]


@router.get("/categories/{category_id}", response_model=CategoryResponse)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """Get a specific category by ID."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.post("/categories/", response_model=CategoryCreateResponse, status_code=201)
def create_category(category: CategoryCreate, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)):
    """Create a new category."""
    existing = db.query(Category).filter(
        Category.name == category.name,
        Category.user_id == user_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Category '{category.name}' already exists")
    
    new_category = Category(name=category.name, color=category.color, user_id=user_id)
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    
    return CategoryCreateResponse(
        category=CategoryResponse.model_validate(new_category),
        transactions_affected=0
    )


@router.put("/categories/{category_id}", response_model=CategoryCreateResponse)
def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """Update a category's name or color."""
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == user_id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    if category_update.name is not None:
        existing = db.query(Category).filter(
            Category.name == category_update.name,
            Category.user_id == user_id,
            Category.id != category_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Category '{category_update.name}' already exists")
        
        old_name = category.name
        category.name = category_update.name
        db.query(Transaction).filter(
            Transaction.category == old_name,
            Transaction.user_id == user_id
        ).update({"category": category_update.name})
    
    if category_update.color is not None:
        category.color = category_update.color
    
    db.commit()
    db.refresh(category)
    
    return CategoryCreateResponse(
        category=CategoryResponse.model_validate(category),
        transactions_affected=0
    )


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)):
    """Delete a category."""
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == user_id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db.query(Transaction).filter(
        Transaction.category == category.name,
        Transaction.user_id == user_id
    ).update({"category": "Other"})
    
    db.delete(category)
    db.commit()
    return None


# ============================================================================
# Rules Endpoints
# ============================================================================

@router.get("/rules/", response_model=PaginatedRulesResponse)
def list_rules(
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """Get all rules with pagination, optionally filtered by category or search query."""
    # Base query with category join
    query = db.query(Rule, Category.name.label('category_name')).join(
        Category, Rule.category_id == Category.id
    ).filter(Rule.user_id == user_id)
    
    if category_id:
        query = query.filter(Rule.category_id == category_id)
    
    # Search in keywords (JSON array)
    if search:
        # Search for rules where any keyword contains the search term
        search_pattern = f"%{search}%"
        # For JSON array search, we cast to string and use LIKE
        from sqlalchemy import cast, String
        query = query.filter(cast(Rule.keywords, String).ilike(search_pattern))
    
    # Get total count before pagination
    total = query.count()
    
    # Apply pagination
    results = query.order_by(Rule.priority.desc(), Rule.id).offset(offset).limit(limit).all()
    
    items = [
        RuleWithCategoryResponse(
            id=rule.id,
            category_id=rule.category_id,
            category_name=category_name,
            keywords=rule.keywords,
            exclude_keywords=rule.exclude_keywords,
            priority=rule.priority
        )
        for rule, category_name in results
    ]
    
    return PaginatedRulesResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
        has_more=(offset + limit) < total
    )


@router.post("/rules/", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(
    rule: RuleCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """Create a new categorization rule."""
    category = db.query(Category).filter(
        Category.id == rule.category_id,
        Category.user_id == user_id
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    new_rule = Rule(
        category_id=rule.category_id,
        user_id=user_id,
        keywords=rule.keywords,
        exclude_keywords=rule.exclude_keywords or [],
        priority=rule.priority
    )
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)
    return new_rule


@router.put("/rules/{rule_id}", response_model=RuleResponse)
def update_rule(
    rule_id: int,
    rule_update: RuleUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """Update an existing rule."""
    rule = db.query(Rule).filter(Rule.id == rule_id, Rule.user_id == user_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    if rule_update.keywords is not None:
        rule.keywords = rule_update.keywords
    if rule_update.exclude_keywords is not None:
        rule.exclude_keywords = rule_update.exclude_keywords
    if rule_update.priority is not None:
        rule.priority = rule_update.priority
    
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """Delete a rule."""
    rule = db.query(Rule).filter(Rule.id == rule_id, Rule.user_id == user_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    db.delete(rule)
    db.commit()
    return None


# ============================================================================
# Categorization Endpoints
# ============================================================================

@router.post("/categories/apply-rules")
def apply_category_rules(
    force_all: bool = False,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """Apply rule-based categorization to transactions."""
    category_service = CategoryService()
    categorized_count = category_service.categorize_transactions(db, user_id=user_id, force_recategorize_all=force_all)
    
    return {
        "success": True,
        "categorized": categorized_count,
        "transactions_updated": categorized_count,  # Alias for tests
        "message": f"Categorized {categorized_count} transaction(s) using rules"
    }


@router.get("/categories/other/merchants", response_model=List[RuleMerchantGroup])
def get_other_category_merchants(
    days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db)
):
    """Get all merchants in the 'Other' category (uncategorized)."""
    date_threshold = datetime.now().date() - timedelta(days=days)
    
    results = db.query(
        Transaction.merchant,
        func.count(Transaction.id).label('transaction_count'),
        func.sum(func.abs(Transaction.amount_signed)).label('total_amount')
    ).filter(
        ((Transaction.category == None) | (Transaction.category == 'Other')),
        Transaction.date >= date_threshold
    ).group_by(Transaction.merchant).order_by(
        func.sum(func.abs(Transaction.amount_signed)).desc()
    ).all()
    
    return [
        RuleMerchantGroup(
            merchant=r.merchant,
            transaction_count=r.transaction_count,
            total_amount=float(r.total_amount)
        )
        for r in results
    ]


@router.get("/categories/{category_id}/all-rule-merchants", response_model=List[RuleMerchantGroup])
def get_category_all_merchants(
    category_id: int,
    days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db)
):
    """Get ALL merchants in a specific category."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    date_threshold = datetime.now().date() - timedelta(days=days)
    
    results = db.query(
        Transaction.merchant,
        func.count(Transaction.id).label('transaction_count'),
        func.sum(func.abs(Transaction.amount_signed)).label('total_amount')
    ).filter(
        Transaction.category == category.name,
        Transaction.date >= date_threshold
    ).group_by(Transaction.merchant).order_by(
        func.sum(func.abs(Transaction.amount_signed)).desc()
    ).all()
    
    return [
        RuleMerchantGroup(
            merchant=r.merchant,
            transaction_count=r.transaction_count,
            total_amount=float(r.total_amount)
        )
        for r in results
    ]


# ============================================================================
# AI Bulk Suggestion Endpoints
# ============================================================================

@router.post("/categories/ai-bulk-suggest", response_model=List[AIBulkSuggestion])
def ai_bulk_suggest(
    request: AIBulkSuggestRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """Get AI suggestions for categorizing merchants in bulk.
    
    SECURITY: All queries are filtered by user_id to ensure data isolation.
    """
    try:
        llm_service = LLMCategorizationService(db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"LLM service initialization failed: {str(e)}")
    
    cutoff_date = datetime.now().date() - timedelta(days=request.days)
    
    if request.merchants:
        merchant_list = request.merchants
    elif request.level == "merchant" and request.merchant:
        merchant_list = [request.merchant]
    else:
        # SECURITY: Filter by user_id
        merchants_query = db.query(Transaction.merchant.distinct()).filter(
            Transaction.user_id == user_id,
            Transaction.category.in_([None, 'Other', '']),
            Transaction.date >= cutoff_date
        ).all()
        merchant_list = [m[0] for m in merchants_query if m[0]]
    
    if not merchant_list:
        return []
    
    merchant_list = merchant_list[:request.limit]
    ai_suggestions = llm_service.bulk_suggest_categories(merchant_list)
    
    result = []
    for suggestion in ai_suggestions:
        merchant_name = suggestion.get("merchant")
        if not merchant_name:
            continue
        
        # SECURITY: Filter stats by user_id, date range, AND only uncategorized transactions
        stats = db.query(
            func.count(Transaction.id).label('count'),
            func.sum(Transaction.amount_signed).label('amount')
        ).filter(
            Transaction.user_id == user_id,
            Transaction.merchant == merchant_name,
            Transaction.date >= cutoff_date,
            or_(
                Transaction.category.is_(None),
                Transaction.category == '',
                Transaction.category == 'Other'
            )
        ).first()
        
        result.append(AIBulkSuggestion(
            merchant=merchant_name,
            suggested_category=suggestion.get("category", "Other"),
            suggested_pattern=suggestion.get("pattern", merchant_name),
            pattern_type=suggestion.get("pattern_type", "keyword"),
            transaction_count=stats.count if stats else 0,
            total_amount=float(stats.amount) if stats and stats.amount else 0.0,
            is_new_category=suggestion.get("is_new_category", False)
        ))
    
    return result


@router.post("/categories/ai-bulk-apply")
def ai_bulk_apply(
    request: AIBulkApplyRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """Apply AI bulk suggestions to create/update rules and categorize transactions.
    
    SECURITY: All queries are filtered by user_id to ensure data isolation.
    """
    if not request.suggestions:
        return {"message": "No suggestions to apply"}
    
    created_categories = []
    updated_categories = []
    transactions_affected = 0
    
    for suggestion in request.suggestions:
        merchant = suggestion.get("merchant")
        category_name = suggestion.get("category")
        pattern = suggestion.get("pattern")
        create_new = suggestion.get("create_new_category", False)
        
        if not merchant or not category_name:
            continue
        
        # SECURITY: Filter category by user_id
        category = db.query(Category).filter(
            Category.name == category_name,
            Category.user_id == user_id
        ).first()
        
        if not category:
            if create_new:
                # SECURITY: Create category with user_id
                category = Category(name=category_name, user_id=user_id, keywords=[])
                db.add(category)
                db.commit()
                created_categories.append(category_name)
            else:
                continue
        
        # SECURITY: Only update transactions belonging to this user
        count = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.merchant == merchant
        ).update({"category": category_name})
        
        transactions_affected += count
    
    db.commit()
    
    if request.auto_create_rules:
        category_service = CategoryService()
        # SECURITY: Pass user_id to ensure only user's transactions are processed
        additional_affected = category_service.categorize_transactions(db, user_id=user_id, force_recategorize_all=True)
        transactions_affected += additional_affected
    
    return {
        "message": "AI suggestions applied successfully",
        "categories_created": len(created_categories),
        "categories_updated": len(updated_categories),
        "transactions_affected": transactions_affected
    }


# ============================================================================
# LLM Rule Generation Endpoints
# ============================================================================

class GenerateRuleRequest(BaseModel):
    merchant: str
    description: str
    details: str
    suggested_category: Optional[str] = None
    context: Optional[str] = None


class GenerateRuleResponse(BaseModel):
    category: str
    keywords: List[str]
    exclude_keywords: List[str]
    confidence: float
    reasoning: str
    is_new_category: bool


@router.post("/categories/generate-rule", response_model=GenerateRuleResponse)
async def generate_categorization_rule(
    request: GenerateRuleRequest,
    db: Session = Depends(get_db),
    user_id: str = Query("default_user")
):
    """Generate a categorization rule using LLM based on transaction details."""
    from .llm_rule_service import LLMRuleService
    
    try:
        llm_service = LLMRuleService()
        rule = await llm_service.generate_rule(
            db=db,
            user_id=user_id,
            merchant=request.merchant,
            description=request.description,
            details=request.details,
            suggested_category=request.suggested_category,
            context=request.context
        )
        
        return GenerateRuleResponse(**rule)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rule generation failed: {str(e)}")

