"""API router for category management (CRUD + AI operations)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
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


class CategoryCreateResponse(BaseModel):
    """Response model for category creation with auto-applied rules."""
    category: CategoryResponse
    transactions_affected: int


class CategoryStatsResponse(BaseModel):
    """Response with category and transaction count."""
    id: int
    name: str
    keywords: List[str]
    transaction_count: int


class UncategorizedMerchantGroup(BaseModel):
    """Group of uncategorized transactions by merchant."""
    merchant: str
    transaction_count: int
    total_amount: float


class MerchantSuggestionRequest(BaseModel):
    """Request for AI category suggestion for a merchant."""
    merchant: str


class MerchantSuggestionResponse(BaseModel):
    """AI suggested category for a merchant."""
    merchant: str
    suggested_category: str


class ApplyCategoryToMerchantRequest(BaseModel):
    """Request to apply a category to all transactions for a merchant."""
    merchant: str
    category_name: str


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


class CategoryDetailedStatsResponse(BaseModel):
    """Detailed stats for a category including rules and merchants."""
    id: int
    name: str
    total_amount: float
    transaction_count: int
    rule_count: int
    merchant_count: int
    days: int


class RuleMerchantGroup(BaseModel):
    """Merchant group matched by a specific rule."""
    merchant: str
    transaction_count: int
    total_amount: float


class ValidatePatternRequest(BaseModel):
    """Request to validate a rule pattern."""
    pattern: str
    pattern_type: str  # "keyword", "keyword_or", "regex"
    exclude_category_id: Optional[int] = None


class ValidatePatternResponse(BaseModel):
    """Response from pattern validation."""
    is_valid: bool
    has_conflicts: bool
    conflicting_rules: List[dict]
    preview_matches: List[str]  # Sample merchants that would match


class AIBulkSuggestion(BaseModel):
    """AI suggestion for a merchant."""
    merchant: str
    suggested_category: str
    suggested_pattern: str
    pattern_type: str  # keyword, keyword_or, regex
    transaction_count: int
    total_amount: float
    is_new_category: bool  # True if suggesting a new category from standard MCC list


class AIBulkApplyRequest(BaseModel):
    """Request to apply AI bulk suggestions."""
    suggestions: List[dict]  # {merchant, category, pattern, pattern_type, create_new_category}
    auto_create_rules: bool = True


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


@router.get("/all-merchants")
def get_all_merchants(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """Get all merchants across all categories with their category information."""
    from datetime import datetime, timedelta
    cutoff_date = datetime.now().date() - timedelta(days=days)
    
    # Query all merchants with their category
    merchants = db.query(
        Transaction.merchant,
        Transaction.category,
        func.count(Transaction.id).label('transaction_count'),
        func.sum(func.abs(Transaction.amount_signed)).label('total_amount')
    ).filter(
        Transaction.date >= cutoff_date
    ).group_by(
        Transaction.merchant,
        Transaction.category
    ).order_by(
        func.sum(func.abs(Transaction.amount_signed)).desc()
    ).all()
    
    return [
        {
            "merchant": m.merchant,
            "category": m.category,
            "transaction_count": m.transaction_count,
            "total_amount": float(m.total_amount) if m.total_amount else 0
        }
        for m in merchants
    ]


class AIBulkSuggestRequest(BaseModel):
    """Request body for AI bulk suggestions."""
    days: int = 30
    level: str = "global"
    category_id: Optional[int] = None
    rule_index: Optional[int] = None
    merchant: Optional[str] = None
    merchants: Optional[List[str]] = None  # List of specific merchants to categorize
    limit: int = 1000


@router.post("/ai-bulk-suggest", response_model=List[AIBulkSuggestion])
def ai_bulk_suggest(
    request: AIBulkSuggestRequest,
    db: Session = Depends(get_db)
):
    """
    Get AI suggestions for categorizing merchants in bulk.
    
    Request body:
        days: Look at transactions in last N days (30/60/90)
        level: Scope of suggestions (global, category, rule, merchant)
        category_id: Required if level is category or rule
        rule_index: Required if level is rule
        merchant: Required if level is merchant
        merchants: Optional list of specific merchants to categorize (overrides level logic)
        limit: Maximum number of merchants to analyze (1-1000, default 1000)
    
    Returns:
        List of AI suggestions with merchant, category, pattern, and stats
    """
    days = request.days
    level = request.level
    category_id = request.category_id
    rule_index = request.rule_index
    merchant = request.merchant
    merchants = request.merchants
    limit = request.limit
    try:
        llm_service = LLMCategorizationService(db)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"LLM service initialization failed: {str(e)}"
        )
    
    # Determine which merchants to analyze based on level
    from datetime import datetime, timedelta
    cutoff_date = datetime.now().date() - timedelta(days=days)
    
    # If specific merchants list is provided, use that directly
    if merchants:
        merchant_list = merchants
    elif level == "merchant" and merchant:
        # Single merchant
        merchant_list = [merchant]
    elif level == "rule" and category_id and rule_index is not None:
        # Merchants matched by a specific rule
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category or rule_index >= len(category.keywords):
            raise HTTPException(status_code=404, detail="Category or rule not found")
        
        rule = category.keywords[rule_index]
        merchants_query = db.query(Transaction.merchant.distinct()).filter(
            Transaction.merchant.ilike(f'%{rule}%'),
            Transaction.date >= cutoff_date
        ).all()
        merchant_list = [m[0] for m in merchants_query if m[0]]
    
    elif level == "category" and category_id:
        # Merchants in a specific category
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        merchants_query = db.query(Transaction.merchant.distinct()).filter(
            Transaction.category == category.name,
            Transaction.date >= cutoff_date
        ).all()
        merchant_list = [m[0] for m in merchants_query if m[0]]
    
    else:
        # Global: uncategorized (Other) merchants
        merchants_query = db.query(Transaction.merchant.distinct()).filter(
            Transaction.category.in_([None, 'Other', '']),
            Transaction.date >= cutoff_date
        ).all()
        merchant_list = [m[0] for m in merchants_query if m[0]]
    
    if not merchant_list:
        return []
    
    # Limit to maximum 1000 merchants
    merchant_list = merchant_list[:limit]
    
    # Get AI suggestions via function calling
    ai_suggestions = llm_service.bulk_suggest_categories(merchant_list)
    
    # Enhance with transaction stats
    result = []
    for suggestion in ai_suggestions:
        merchant_name = suggestion.get("merchant")
        if not merchant_name:
            continue
        
        stats = db.query(
            func.count(Transaction.id).label('count'),
            func.sum(Transaction.amount_signed).label('amount')
        ).filter(
            Transaction.merchant == merchant_name
            # Note: No date filter here - show all-time stats for the merchant
        ).first()
        
        result.append(AIBulkSuggestion(
            merchant=merchant_name,
            suggested_category=suggestion.get("category", "Other"),
            suggested_pattern=suggestion.get("pattern", merchant_name),
            pattern_type=suggestion.get("pattern_type", "keyword"),
            transaction_count=stats.count if stats else 0,
            total_amount=float(stats.amount) if stats and stats.amount else 0.0,
            is_new_category=suggestion.get("is_new_category", False)  # Pass through from LLM
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


@router.post("/", response_model=CategoryCreateResponse, status_code=201)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    """
    Create a new category and automatically apply rules to transactions.
    
    Args:
        category: Category data (name and keywords)
    
    Returns:
        Created category and count of transactions affected
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
    
    # Auto-apply rules
    category_service = CategoryService()
    affected_count = category_service.categorize_transactions(db)
    
    return CategoryCreateResponse(
        category=CategoryResponse.from_orm(new_category),
        transactions_affected=affected_count
    )


@router.put("/{category_id}", response_model=CategoryCreateResponse)
def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a category and automatically apply rules to transactions.
    
    Args:
        category_id: Category ID
        category_update: Updated category data
    
    Returns:
        Updated category and count of transactions affected
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    keywords_changed = False
    
    # Update fields if provided
    if category_update.name is not None:
        # Check if new name conflicts with existing category
        existing = db.query(Category).filter(
            Category.name == category_update.name,
            Category.id != category_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Category '{category_update.name}' already exists")
        
        # Update all transactions with old category name to new name
        old_name = category.name
        category.name = category_update.name
        db.query(Transaction).filter(Transaction.category == old_name).update({
            "category": category_update.name
        })
    
    if category_update.keywords is not None:
        category.keywords = category_update.keywords
        keywords_changed = True
    
    db.commit()
    db.refresh(category)
    
    # Auto-apply rules with force_recategorize_all if keywords changed
    category_service = CategoryService()
    affected_count = category_service.categorize_transactions(
        db, 
        force_recategorize_all=keywords_changed
    )
    
    return CategoryCreateResponse(
        category=CategoryResponse.from_orm(category),
        transactions_affected=affected_count
    )


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
def apply_category_rules(force_all: bool = False, db: Session = Depends(get_db)):
    """
    Apply rule-based categorization to transactions.
    
    Args:
        force_all: If true, recategorize ALL transactions. If false, only "Other" transactions.
    
    Returns:
        Number of transactions categorized
    """
    category_service = CategoryService()
    categorized_count = category_service.categorize_transactions(db, force_recategorize_all=force_all)
    
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
        llm_service = LLMCategorizationService(db)
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




@router.get("/uncategorized-merchants", response_model=List[UncategorizedMerchantGroup])
def get_uncategorized_merchants(
    db: Session = Depends(get_db)
):
    """
    Get uncategorized transactions grouped by merchant, ordered by total amount desc.
    
    Returns list of merchant groups with transaction counts and total amounts.
    """
    # Query uncategorized transactions grouped by merchant
    results = db.query(
        Transaction.merchant,
        func.count(Transaction.id).label('transaction_count'),
        func.sum(func.abs(Transaction.amount_signed)).label('total_amount')
    ).filter(
        (Transaction.category == None) | (Transaction.category == 'Other')
    ).group_by(
        Transaction.merchant
    ).order_by(
        func.sum(func.abs(Transaction.amount_signed)).desc()
    ).all()
    
    return [
        UncategorizedMerchantGroup(
            merchant=r.merchant,
            transaction_count=r.transaction_count,
            total_amount=float(r.total_amount)
        )
        for r in results
    ]


@router.post("/suggest-category", response_model=MerchantSuggestionResponse)
def suggest_category_for_merchant(
    request: MerchantSuggestionRequest,
    db: Session = Depends(get_db)
):
    """
    Get AI suggestion for categorizing a specific merchant.
    
    Args:
        request: Contains merchant name to categorize
    
    Returns:
        Suggested category name
    """
    try:
        llm_service = LLMCategorizationService(db)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"LLM service initialization failed: {str(e)}. Make sure OPENAI_API_KEY is set."
        )
    
    # Get category suggestion from LLM
    try:
        suggested_category = llm_service.categorize_merchant(request.merchant, db)
        return MerchantSuggestionResponse(
            merchant=request.merchant,
            suggested_category=suggested_category
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get category suggestion: {str(e)}"
        )


@router.post("/apply-to-merchant")
def apply_category_to_merchant(
    request: ApplyCategoryToMerchantRequest,
    db: Session = Depends(get_db)
):
    """
    Apply a category to all transactions for a specific merchant.
    
    Args:
        request: Contains merchant name and category to apply
    
    Returns:
        Number of transactions updated
    """
    # Validate category exists
    category = db.query(Category).filter(Category.name == request.category_name).first()
    if not category:
        raise HTTPException(
            status_code=404,
            detail=f"Category '{request.category_name}' not found"
        )
    
    # Update all transactions for this merchant
    count = db.query(Transaction).filter(
        Transaction.merchant == request.merchant
    ).update({
        "category": request.category_name
    })
    db.commit()
    
    return {
        "success": True,
        "updated_count": count,
        "merchant": request.merchant,
        "category": request.category_name
    }


@router.get("/{category_id}/detailed-stats", response_model=CategoryDetailedStatsResponse)
def get_category_detailed_stats(
    category_id: int,
    days: int = Query(30, ge=7, le=90, description="Time window in days"),
    db: Session = Depends(get_db)
):
    """
    Get detailed statistics for a specific category including rules and merchants.
    
    Args:
        category_id: Category ID
        days: Time window in days (7-90)
    
    Returns:
        Detailed category statistics
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Calculate date threshold
    date_threshold = datetime.now().date() - timedelta(days=days)
    
    # Get transactions for this category within time window
    transactions = db.query(Transaction).filter(
        Transaction.category == category.name,
        Transaction.date >= date_threshold
    ).all()
    
    # Calculate stats
    total_amount = sum(abs(float(t.amount_signed or 0)) for t in transactions)
    transaction_count = len(transactions)
    
    # Get unique merchants
    merchants = set(t.merchant for t in transactions)
    merchant_count = len(merchants)
    
    # Rule count is the number of keywords
    rule_count = len(category.keywords) if category.keywords else 0
    
    return CategoryDetailedStatsResponse(
        id=category.id,
        name=category.name,
        total_amount=total_amount,
        transaction_count=transaction_count,
        rule_count=rule_count,
        merchant_count=merchant_count,
        days=days
    )


@router.get("/{category_id}/rules/{rule_index}/merchants", response_model=List[RuleMerchantGroup])
def get_rule_merchants(
    category_id: int,
    rule_index: int,
    days: int = Query(30, ge=7, le=90, description="Time window in days"),
    db: Session = Depends(get_db)
):
    """
    Get merchants matched by a specific rule within a category.
    
    Args:
        category_id: Category ID
        rule_index: Index of the rule in the keywords array
        days: Time window in days (7-90)
    
    Returns:
        List of merchants matched by this rule, grouped and sorted by volume
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    if not category.keywords or rule_index >= len(category.keywords):
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule_pattern = category.keywords[rule_index]
    date_threshold = datetime.now().date() - timedelta(days=days)
    
    # Find transactions that match this specific rule pattern
    # Get transactions for this category and check which ones match the pattern
    transactions = db.query(Transaction).filter(
        Transaction.category == category.name,
        Transaction.date >= date_threshold
    ).all()
    
    # Filter transactions by rule pattern (case-insensitive substring match)
    matched_transactions = [
        t for t in transactions
        if rule_pattern.upper() in (t.merchant or "").upper()
    ]
    
    # Group by merchant
    merchant_groups = {}
    for t in matched_transactions:
        if t.merchant not in merchant_groups:
            merchant_groups[t.merchant] = {
                'count': 0,
                'total': 0
            }
        merchant_groups[t.merchant]['count'] += 1
        merchant_groups[t.merchant]['total'] += abs(float(t.amount_signed or 0))
    
    # Convert to response format and sort by volume
    result = [
        RuleMerchantGroup(
            merchant=merchant,
            transaction_count=data['count'],
            total_amount=data['total']
        )
        for merchant, data in merchant_groups.items()
    ]
    
    result.sort(key=lambda x: x.total_amount, reverse=True)
    
    return result


@router.get("/{category_id}/all-rule-merchants", response_model=List[RuleMerchantGroup])
def get_category_all_merchants(
    category_id: int,
    days: int = Query(30, ge=7, le=90, description="Time window in days"),
    db: Session = Depends(get_db)
):
    """
    Get ALL merchants in a specific category (not filtered by any specific rule).
    
    Args:
        category_id: Category ID
        days: Time window in days (7-90)
    
    Returns:
        List of all merchants in this category, grouped and sorted by volume
    """
    # Get category
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    date_threshold = datetime.now().date() - timedelta(days=days)
    
    # Query all transactions in this category within time window
    results = db.query(
        Transaction.merchant,
        func.count(Transaction.id).label('transaction_count'),
        func.sum(func.abs(Transaction.amount_signed)).label('total_amount')
    ).filter(
        Transaction.category == category.name,
        Transaction.date >= date_threshold
    ).group_by(
        Transaction.merchant
    ).order_by(
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


@router.get("/other/merchants", response_model=List[RuleMerchantGroup])
def get_other_category_merchants(
    days: int = Query(30, ge=7, le=90, description="Time window in days"),
    db: Session = Depends(get_db)
):
    """
    Get all merchants in the 'Other' category (uncategorized).
    
    Args:
        days: Time window in days (7-90)
    
    Returns:
        List of uncategorized merchants, grouped and sorted by volume
    """
    date_threshold = datetime.now().date() - timedelta(days=days)
    
    # Query transactions with NULL category or 'Other' category within time window
    results = db.query(
        Transaction.merchant,
        func.count(Transaction.id).label('transaction_count'),
        func.sum(func.abs(Transaction.amount_signed)).label('total_amount')
    ).filter(
        ((Transaction.category == None) | (Transaction.category == 'Other')),
        Transaction.date >= date_threshold
    ).group_by(
        Transaction.merchant
    ).order_by(
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


@router.post("/validate-pattern", response_model=ValidatePatternResponse)
def validate_rule_pattern(
    request: ValidatePatternRequest,
    db: Session = Depends(get_db)
):
    """
    Validate a rule pattern and check for conflicts with existing rules.
    
    Args:
        request: Pattern validation request
    
    Returns:
        Validation result with conflict information
    """
    import re
    
    # Validate pattern syntax
    is_valid = True
    if request.pattern_type == "regex":
        try:
            re.compile(request.pattern)
        except re.error:
            is_valid = False
    
    # Check for conflicts with existing rules
    conflicting_rules = []
    categories = db.query(Category).all()
    
    for category in categories:
        if request.exclude_category_id and category.id == request.exclude_category_id:
            continue
        
        if not category.keywords:
            continue
        
        for keyword in category.keywords:
            # Check if patterns overlap
            # Simple heuristic: if one pattern contains the other (case-insensitive)
            pattern_upper = request.pattern.upper()
            keyword_upper = keyword.upper()
            
            if pattern_upper in keyword_upper or keyword_upper in pattern_upper:
                # Get sample merchants that would match both
                sample_merchants = db.query(Transaction.merchant).filter(
                    Transaction.merchant.ilike(f'%{keyword}%')
                ).limit(5).all()
                
                conflicting_rules.append({
                    'category': category.name,
                    'rule': keyword,
                    'overlap_count': len(sample_merchants)
                })
    
    # Get preview of merchants that would match this pattern
    preview_query = db.query(Transaction.merchant.distinct()).filter(
        Transaction.merchant.ilike(f'%{request.pattern}%')
    ).limit(10)
    
    preview_matches = [m[0] for m in preview_query.all() if m[0]]
    
    return ValidatePatternResponse(
        is_valid=is_valid,
        has_conflicts=len(conflicting_rules) > 0,
        conflicting_rules=conflicting_rules,
        preview_matches=preview_matches
    )


@router.put("/{category_id}/rules/{rule_index}/move")
def move_rule_to_category(
    category_id: int,
    rule_index: int,
    target_category_id: int,
    db: Session = Depends(get_db)
):
    """
    Move a rule from one category to another.
    
    Args:
        category_id: Source category ID
        rule_index: Index of the rule in the source category's keywords list
        target_category_id: Target category ID
        
    Returns:
        Success message with affected transaction counts
    """
    # Get source category
    source_category = db.query(Category).filter(Category.id == category_id).first()
    if not source_category:
        raise HTTPException(status_code=404, detail="Source category not found")
    
    # Validate rule index
    if rule_index < 0 or rule_index >= len(source_category.keywords):
        raise HTTPException(status_code=400, detail="Invalid rule index")
    
    # Get target category
    target_category = db.query(Category).filter(Category.id == target_category_id).first()
    if not target_category:
        raise HTTPException(status_code=404, detail="Target category not found")
    
    # Move the rule
    rule = source_category.keywords[rule_index]
    source_category.keywords = [
        kw for i, kw in enumerate(source_category.keywords) if i != rule_index
    ]
    target_category.keywords = target_category.keywords + [rule]
    
    db.commit()
    
    # Auto-apply rules to recategorize transactions
    category_service = CategoryService(db)
    affected_count = category_service.categorize_transactions()
    
    return {
        "message": f"Rule '{rule}' moved from '{source_category.name}' to '{target_category.name}'",
        "transactions_affected": affected_count
    }


# AI Bulk endpoints moved to before CRUD endpoints (lines 130-143)


@router.post("/ai-bulk-apply")
def ai_bulk_apply(
    request: AIBulkApplyRequest,
    db: Session = Depends(get_db)
):
    """
    Apply AI bulk suggestions to create/update rules and categorize transactions.
    
    Body:
        suggestions: List of {merchant, category, pattern, pattern_type, create_new_category}
        auto_create_rules: If true, add patterns as rules to categories
    
    Returns:
        Success message with counts
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
        
        # Find or create category
        category = db.query(Category).filter(Category.name == category_name).first()
        
        if not category:
            if create_new:
                category = Category(name=category_name, keywords=[])
                db.add(category)
                db.commit()
                created_categories.append(category_name)
            else:
                continue  # Skip if category doesn't exist and not creating
        
        # Add rule if auto_create_rules and pattern provided
        if request.auto_create_rules and pattern and pattern not in category.keywords:
            category.keywords = category.keywords + [pattern]
            if category_name not in updated_categories:
                updated_categories.append(category_name)
        
        # Categorize transactions with this merchant
        count = db.query(Transaction).filter(
            Transaction.merchant == merchant
        ).update({"category": category_name})
        
        transactions_affected += count
    
    db.commit()
    
    # Auto-apply all rules to recategorize ALL transactions when rules are involved
    # This ensures new patterns are applied to all matching transactions, not just the specific merchants
    if request.auto_create_rules:
        category_service = CategoryService()
        additional_affected = category_service.categorize_transactions(db, force_recategorize_all=True)
        transactions_affected += additional_affected
    
    return {
        "message": "AI suggestions applied successfully",
        "categories_created": len(created_categories),
        "categories_updated": len(updated_categories),
        "transactions_affected": transactions_affected,
        "created_categories": created_categories,
        "updated_categories": updated_categories
    }


