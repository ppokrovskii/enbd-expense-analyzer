"""Categories API router - Category CRUD, Rules, and AI operations."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, cast, String
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta, date

from app.shared.filtered_query import FilteredQueryContext, get_filtered_context
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
def list_categories(ctx: FilteredQueryContext = Depends(get_filtered_context)):
    """Get all categories for current user/person."""
    categories = ctx.query(Category).all()
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
def get_categories_with_stats(ctx: FilteredQueryContext = Depends(get_filtered_context)):
    """Get all categories with transaction statistics."""
    categories = ctx.query(Category).all()
    
    # Get transaction stats per category (filtered by user/person)
    stats_query = ctx.query(Transaction).with_entities(
        Transaction.category,
        func.count(Transaction.id).label('count'),
        func.sum(func.abs(Transaction.amount_signed)).label('total')
    ).filter(
        Transaction.category.isnot(None)
    ).group_by(Transaction.category)
    
    stats = stats_query.all()
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
def get_category(category_id: int, ctx: FilteredQueryContext = Depends(get_filtered_context)):
    """Get a specific category by ID (filtered by user/person)."""
    category = ctx.get_by_id(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.post("/categories/", response_model=CategoryCreateResponse, status_code=201)
def create_category(category: CategoryCreate, ctx: FilteredQueryContext = Depends(get_filtered_context)):
    """Create a new category."""
    existing = ctx.query(Category).filter(Category.name == category.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Category '{category.name}' already exists")
    
    new_category = Category(name=category.name, color=category.color)
    ctx.add(new_category)  # Automatically sets user_id and person_id
    ctx.commit()
    ctx.refresh(new_category)
    
    return CategoryCreateResponse(
        category=CategoryResponse.model_validate(new_category),
        transactions_affected=0
    )


@router.put("/categories/{category_id}", response_model=CategoryCreateResponse)
def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Update a category's name or color."""
    category = ctx.get_by_id(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    if category_update.name is not None:
        existing = ctx.query(Category).filter(
            Category.name == category_update.name,
            Category.id != category_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Category '{category_update.name}' already exists")
        
        old_name = category.name
        category.name = category_update.name
        # Update transactions with this category name
        ctx.query(Transaction).filter(
            Transaction.category == old_name
        ).update({"category": category_update.name})
    
    if category_update.color is not None:
        category.color = category_update.color
    
    ctx.commit()
    ctx.refresh(category)
    
    return CategoryCreateResponse(
        category=CategoryResponse.model_validate(category),
        transactions_affected=0
    )


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, ctx: FilteredQueryContext = Depends(get_filtered_context)):
    """Delete a category."""
    category = ctx.get_by_id(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Reset transactions with this category to "Other"
    ctx.query(Transaction).filter(
        Transaction.category == category.name
    ).update({"category": "Other"})
    
    ctx.delete(category)
    ctx.commit()
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
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Get all rules with pagination, optionally filtered by category or search query."""
    # Base query with category join (using raw_query for join)
    query = ctx.raw_query(Rule, Category.name.label('category_name')).join(
        Category, Rule.category_id == Category.id
    ).filter(Rule.user_id == ctx.user_id)
    
    # Add person_id filter if set
    if ctx.person_id is not None:
        query = query.filter(Rule.person_id == ctx.person_id)
    
    if category_id:
        query = query.filter(Rule.category_id == category_id)
    
    # Search in keywords (JSON array)
    if search:
        search_pattern = f"%{search}%"
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
def create_rule(rule: RuleCreate, ctx: FilteredQueryContext = Depends(get_filtered_context)):
    """Create a new categorization rule."""
    category = ctx.get_by_id(Category, rule.category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    new_rule = Rule(
        category_id=rule.category_id,
        keywords=rule.keywords,
        exclude_keywords=rule.exclude_keywords or [],
        priority=rule.priority
    )
    ctx.add(new_rule)  # Automatically sets user_id and person_id
    ctx.commit()
    ctx.refresh(new_rule)
    return new_rule


@router.put("/rules/{rule_id}", response_model=RuleResponse)
def update_rule(
    rule_id: int,
    rule_update: RuleUpdate,
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Update an existing rule."""
    rule = ctx.get_by_id(Rule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    if rule_update.keywords is not None:
        rule.keywords = rule_update.keywords
    if rule_update.exclude_keywords is not None:
        rule.exclude_keywords = rule_update.exclude_keywords
    if rule_update.priority is not None:
        rule.priority = rule_update.priority
    
    ctx.commit()
    ctx.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: int, ctx: FilteredQueryContext = Depends(get_filtered_context)):
    """Delete a rule."""
    rule = ctx.get_by_id(Rule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    ctx.delete(rule)
    ctx.commit()
    return None


# ============================================================================
# Categorization Endpoints
# ============================================================================

@router.post("/categories/apply-rules")
def apply_category_rules(
    force_all: bool = False,
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Apply rule-based categorization to transactions."""
    category_service = CategoryService()
    categorized_count = category_service.categorize_transactions(
        ctx.db, 
        user_id=ctx.user_id, 
        force_recategorize_all=force_all,
        person_id=ctx.person_id
    )
    
    return {
        "success": True,
        "categorized": categorized_count,
        "transactions_updated": categorized_count,  # Alias for tests
        "message": f"Categorized {categorized_count} transaction(s) using rules"
    }


@router.get("/categories/other/merchants", response_model=List[RuleMerchantGroup])
def get_other_category_merchants(
    days: int = Query(30, ge=7, le=90),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Get all merchants in the 'Other' category (uncategorized)."""
    # Build base filter with user/person
    base_filters = [Transaction.user_id == ctx.user_id]
    if ctx.person_id is not None:
        base_filters.append(Transaction.person_id == ctx.person_id)
    
    # Date filtering
    if start_date and end_date:
        base_filters.append(Transaction.date >= start_date)
        base_filters.append(Transaction.date <= end_date)
    else:
        date_threshold = datetime.now().date() - timedelta(days=days)
        base_filters.append(Transaction.date >= date_threshold)
    
    # Category filter (uncategorized)
    base_filters.append(or_(Transaction.category == None, Transaction.category == 'Other'))
    
    results = ctx.raw_query(
        Transaction.merchant,
        func.count(Transaction.id).label('transaction_count'),
        func.sum(func.abs(Transaction.amount_signed)).label('total_amount')
    ).filter(*base_filters).group_by(Transaction.merchant).order_by(
        func.sum(func.abs(Transaction.amount_signed)).desc()
    ).all()
    
    return [
        RuleMerchantGroup(
            merchant=r.merchant,
            transaction_count=r.transaction_count,
            total_amount=float(r.total_amount) if r.total_amount else 0
        )
        for r in results if r.merchant
    ]


@router.get("/categories/{category_id}/all-rule-merchants", response_model=List[RuleMerchantGroup])
def get_category_all_merchants(
    category_id: int,
    days: int = Query(30, ge=7, le=90),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Get ALL merchants in a specific category."""
    category = ctx.get_by_id(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Build base filter with user/person
    base_filters = [
        Transaction.user_id == ctx.user_id,
        Transaction.category == category.name
    ]
    if ctx.person_id is not None:
        base_filters.append(Transaction.person_id == ctx.person_id)
    
    # Date filtering
    if start_date and end_date:
        base_filters.append(Transaction.date >= start_date)
        base_filters.append(Transaction.date <= end_date)
    else:
        date_threshold = datetime.now().date() - timedelta(days=days)
        base_filters.append(Transaction.date >= date_threshold)
    
    results = ctx.raw_query(
        Transaction.merchant,
        func.count(Transaction.id).label('transaction_count'),
        func.sum(func.abs(Transaction.amount_signed)).label('total_amount')
    ).filter(*base_filters).group_by(Transaction.merchant).order_by(
        func.sum(func.abs(Transaction.amount_signed)).desc()
    ).all()
    
    return [
        RuleMerchantGroup(
            merchant=r.merchant,
            transaction_count=r.transaction_count,
            total_amount=float(r.total_amount) if r.total_amount else 0
        )
        for r in results if r.merchant
    ]


# ============================================================================
# AI Bulk Suggestion Endpoints
# ============================================================================

@router.post("/categories/ai-bulk-suggest", response_model=List[AIBulkSuggestion])
def ai_bulk_suggest(
    request: AIBulkSuggestRequest,
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Get AI suggestions for categorizing merchants in bulk."""
    try:
        llm_service = LLMCategorizationService(ctx.db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"LLM service initialization failed: {str(e)}")
    
    cutoff_date = datetime.now().date() - timedelta(days=request.days)
    
    if request.merchants:
        merchant_list = request.merchants
    elif request.level == "merchant" and request.merchant:
        merchant_list = [request.merchant]
    else:
        # Get uncategorized merchants for user/person
        merchants_query = ctx.query(Transaction).with_entities(
            Transaction.merchant.distinct()
        ).filter(
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
        
        # Get stats for this merchant (filtered by user/person)
        stats = ctx.query(Transaction).with_entities(
            func.count(Transaction.id).label('count'),
            func.sum(Transaction.amount_signed).label('amount')
        ).filter(
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
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Apply AI bulk suggestions to create/update rules and categorize transactions."""
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
        
        # Find or create category (filtered by user/person)
        category = ctx.query(Category).filter(Category.name == category_name).first()
        
        if not category:
            if create_new:
                category = Category(name=category_name, keywords=[])
                ctx.add(category)  # Automatically sets user_id and person_id
                ctx.commit()
                created_categories.append(category_name)
            else:
                continue
        
        # Update transactions (filtered by user/person)
        count = ctx.query(Transaction).filter(
            Transaction.merchant == merchant
        ).update({"category": category_name})
        
        transactions_affected += count
    
    ctx.commit()
    
    if request.auto_create_rules:
        category_service = CategoryService()
        additional_affected = category_service.categorize_transactions(
            ctx.db, 
            user_id=ctx.user_id, 
            force_recategorize_all=True, 
            person_id=ctx.person_id
        )
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

# ============================================================================
# Rule Test/Preview Endpoints
# ============================================================================

class RuleTestRequest(BaseModel):
    """Request model for testing a rule pattern."""
    keywords: List[str]
    exclude_keywords: Optional[List[str]] = []
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    limit: int = 50


class MatchingMerchant(BaseModel):
    """A merchant that matches the rule pattern."""
    merchant: str
    transaction_count: int
    total_amount: float
    matched_keyword: str


class SampleTransaction(BaseModel):
    """A sample transaction that matches the rule."""
    id: int
    date: date
    merchant: str
    description: str
    amount: float
    matched_text: str


class RuleTestResponse(BaseModel):
    """Response model for rule test endpoint."""
    matching_merchants: List[MatchingMerchant]
    match_count: int
    total_transactions: int
    sample_transactions: List[SampleTransaction]


@router.post("/rules/test", response_model=RuleTestResponse)
def test_rule_pattern(
    request: RuleTestRequest,
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """
    Test a rule pattern and preview which merchants it would match.
    
    This endpoint allows you to test keywords and exclude_keywords
    before creating or updating a rule.
    """
    if not request.keywords:
        return RuleTestResponse(
            matching_merchants=[],
            match_count=0,
            total_transactions=0,
            sample_transactions=[]
        )
    
    # Build date filter
    date_filters = []
    if request.start_date and request.end_date:
        date_filters.append(Transaction.date >= request.start_date)
        date_filters.append(Transaction.date <= request.end_date)
    else:
        # Default to last 90 days
        cutoff = datetime.now().date() - timedelta(days=90)
        date_filters.append(Transaction.date >= cutoff)
    
    # Get all transactions for the user/person
    base_query = ctx.query(Transaction).filter(*date_filters)
    all_transactions = base_query.all()
    
    # Apply pattern matching logic
    matching_txns = []
    for txn in all_transactions:
        search_text = (txn.search_text or txn.merchant or "").upper()
        if not search_text:
            continue
        
        # Check exclusions first
        excluded = False
        for exclude in (request.exclude_keywords or []):
            if exclude and exclude.upper() in search_text:
                excluded = True
                break
        
        if excluded:
            continue
        
        # Check keyword matches
        matched_kw = None
        for keyword in request.keywords:
            if '|' in keyword:
                # Pipe-separated alternatives (OR pattern)
                alternatives = [alt.strip().upper() for alt in keyword.split('|')]
                for alt in alternatives:
                    if alt and alt in search_text:
                        matched_kw = alt
                        break
            else:
                if keyword.upper() in search_text:
                    matched_kw = keyword
                    break
            if matched_kw:
                break
        
        if matched_kw:
            matching_txns.append((txn, matched_kw))
    
    # Group by merchant
    merchant_groups = {}
    for txn, matched_kw in matching_txns:
        merchant = txn.merchant or "Unknown"
        if merchant not in merchant_groups:
            merchant_groups[merchant] = {
                'count': 0,
                'total': 0.0,
                'matched_keyword': matched_kw,
                'transactions': []
            }
        merchant_groups[merchant]['count'] += 1
        merchant_groups[merchant]['total'] += abs(float(txn.amount_signed or 0))
        merchant_groups[merchant]['transactions'].append((txn, matched_kw))
    
    # Build matching merchants list
    matching_merchants = [
        MatchingMerchant(
            merchant=merchant,
            transaction_count=data['count'],
            total_amount=data['total'],
            matched_keyword=data['matched_keyword']
        )
        for merchant, data in sorted(
            merchant_groups.items(), 
            key=lambda x: x[1]['total'], 
            reverse=True
        )[:request.limit]
    ]
    
    # Build sample transactions (first 10)
    sample_transactions = []
    for txn, matched_kw in matching_txns[:10]:
        sample_transactions.append(SampleTransaction(
            id=txn.id,
            date=txn.date,
            merchant=txn.merchant or "Unknown",
            description=txn.description or "",
            amount=float(txn.amount_signed or 0),
            matched_text=matched_kw
        ))
    
    return RuleTestResponse(
        matching_merchants=matching_merchants,
        match_count=len(merchant_groups),
        total_transactions=len(matching_txns),
        sample_transactions=sample_transactions
    )


# ============================================================================
# Rule Conflict Detection Endpoints
# ============================================================================

class ConflictCheckRequest(BaseModel):
    """Request model for checking rule conflicts."""
    keywords: List[str]
    exclude_keywords: Optional[List[str]] = []
    rule_id: Optional[int] = None  # Exclude this rule from conflict check (for edit mode)


class RuleConflict(BaseModel):
    """A conflicting rule."""
    rule_id: int
    category_id: int
    category_name: str
    keywords: List[str]
    overlapping_keywords: List[str]  # Keywords that overlap
    severity: str  # "error" for exact duplicate, "warning" for partial overlap


class ConflictCheckResponse(BaseModel):
    """Response model for conflict check endpoint."""
    conflicts: List[RuleConflict]
    has_conflicts: bool


@router.post("/rules/check-conflicts", response_model=ConflictCheckResponse)
def check_rule_conflicts(
    request: ConflictCheckRequest,
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """
    Check if a rule pattern conflicts with existing rules.
    
    A conflict occurs when:
    - exact duplicate: same keyword exists in another rule (severity: error)
    - partial overlap: keyword is substring of or contains another keyword (severity: warning)
    """
    if not request.keywords:
        return ConflictCheckResponse(conflicts=[], has_conflicts=False)
    
    # Get all existing rules for user/person
    query = ctx.raw_query(Rule, Category.name.label('category_name')).join(
        Category, Rule.category_id == Category.id
    ).filter(Rule.user_id == ctx.user_id)
    
    if ctx.person_id is not None:
        query = query.filter(Rule.person_id == ctx.person_id)
    
    # Exclude current rule if editing
    if request.rule_id:
        query = query.filter(Rule.id != request.rule_id)
    
    existing_rules = query.all()
    
    conflicts = []
    input_keywords_upper = [kw.upper() for kw in request.keywords]
    
    for rule, category_name in existing_rules:
        overlapping = []
        severity = "warning"
        
        for existing_kw in (rule.keywords or []):
            existing_kw_upper = existing_kw.upper()
            
            for input_kw in request.keywords:
                input_kw_upper = input_kw.upper()
                
                # Handle OR patterns - split by pipe
                input_alternatives = [alt.strip() for alt in input_kw_upper.split('|')]
                existing_alternatives = [alt.strip() for alt in existing_kw_upper.split('|')]
                
                for input_alt in input_alternatives:
                    for existing_alt in existing_alternatives:
                        if not input_alt or not existing_alt:
                            continue
                        
                        # Exact match - error severity
                        if input_alt == existing_alt:
                            overlapping.append(existing_kw)
                            severity = "error"
                            break
                        
                        # Substring match - warning severity (but don't downgrade from error)
                        if input_alt in existing_alt or existing_alt in input_alt:
                            if existing_kw not in overlapping:
                                overlapping.append(existing_kw)
                            # Don't change severity if already error
                    
                    if severity == "error":
                        break
        
        if overlapping:
            conflicts.append(RuleConflict(
                rule_id=rule.id,
                category_id=rule.category_id,
                category_name=category_name,
                keywords=rule.keywords or [],
                overlapping_keywords=list(set(overlapping)),
                severity=severity
            ))
    
    return ConflictCheckResponse(
        conflicts=conflicts,
        has_conflicts=len(conflicts) > 0
    )


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
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Generate a categorization rule using LLM based on transaction details."""
    from .llm_rule_service import LLMRuleService
    
    try:
        llm_service = LLMRuleService()
        rule = await llm_service.generate_rule(
            db=ctx.db,
            user_id=ctx.user_id,
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
