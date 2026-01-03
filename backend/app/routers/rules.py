"""API router for categorization rules management."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.dependencies import get_user_id
from app.models import Rule, Category

router = APIRouter(prefix="/api/rules", tags=["rules"])


class RuleCreate(BaseModel):
    """Request model for creating a rule."""
    category_id: int
    keywords: List[str]
    exclude_keywords: Optional[List[str]] = []
    priority: int = 0


class RuleUpdate(BaseModel):
    """Request model for updating a rule."""
    keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None
    priority: Optional[int] = None


class RuleResponse(BaseModel):
    """Response model for a rule."""
    id: int
    category_id: int
    keywords: List[str]
    exclude_keywords: List[str]
    priority: int
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[RuleResponse])
def list_rules(
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """
    Get all rules, optionally filtered by category.
    
    Args:
        category_id: Optional category ID to filter rules
    
    Returns:
        List of rules
    """
    query = db.query(Rule).filter(Rule.user_id == user_id)
    if category_id:
        query = query.filter(Rule.category_id == category_id)
    
    rules = query.order_by(Rule.priority.desc(), Rule.id).all()
    return rules


@router.post("/", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(
    rule: RuleCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """
    Create a new categorization rule.
    
    Args:
        rule: Rule data (category_id, keywords, exclude_keywords, priority)
    
    Returns:
        Created rule
    """
    # Verify category exists and belongs to user
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


@router.put("/{rule_id}", response_model=RuleResponse)
def update_rule(
    rule_id: int,
    rule_update: RuleUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """
    Update an existing rule.
    
    Args:
        rule_id: Rule ID
        rule_update: Updated rule data
    
    Returns:
        Updated rule
    """
    rule = db.query(Rule).filter(
        Rule.id == rule_id,
        Rule.user_id == user_id
    ).first()
    
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


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """
    Delete a rule.
    
    Args:
        rule_id: Rule ID
    """
    rule = db.query(Rule).filter(
        Rule.id == rule_id,
        Rule.user_id == user_id
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    db.delete(rule)
    db.commit()
    
    return None

