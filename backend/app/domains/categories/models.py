"""SQLAlchemy models for the Categories domain."""
from sqlalchemy import Column, Integer, String, Text, DateTime, Index, JSON, ForeignKey
from datetime import datetime
from app.shared.database import Base


class Category(Base):
    """Category model for transaction categorization - name and color only."""
    
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, server_default='default_user', index=True)
    name = Column(String(100), nullable=False, index=True)
    color = Column(String(20))  # Color from 64-color palette
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_categories_user_name', 'user_id', 'name', unique=True),
    )
    
    def __repr__(self):
        return f"<Category(id={self.id}, user_id={self.user_id}, name={self.name})>"


class Rule(Base):
    """Rule model for categorization keywords - separate from Category."""
    
    __tablename__ = "rules"
    
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String(50), nullable=False, index=True)
    keywords = Column(JSON, nullable=False, default=list)  # List of keyword strings
    exclude_keywords = Column(JSON, default=list)  # Exclusion patterns
    priority = Column(Integer, default=0)  # For rule ordering
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_rules_category', 'category_id'),
        Index('idx_rules_user', 'user_id'),
    )
    
    def __repr__(self):
        return f"<Rule(id={self.id}, category_id={self.category_id}, keywords={self.keywords})>"


class LLMCache(Base):
    """LLM categorization cache to avoid redundant API calls."""
    
    __tablename__ = "llm_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, server_default='default_user', index=True)
    merchant = Column(String(200), nullable=False, index=True)
    category = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_llm_cache_user_merchant', 'user_id', 'merchant', unique=True),
    )
    
    def __repr__(self):
        return f"<LLMCache(user_id={self.user_id}, merchant={self.merchant}, category={self.category})>"

