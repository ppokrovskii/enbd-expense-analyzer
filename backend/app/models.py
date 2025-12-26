"""SQLAlchemy models for the ENBD Expense Analyzer."""
from sqlalchemy import Column, Integer, String, Text, Date, Numeric, DateTime, Index, JSON
from datetime import datetime
from .database import Base


class Transaction(Base):
    """Transaction model representing a bank transaction."""
    
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    account = Column(String(100), nullable=False)
    description = Column(Text)
    details = Column(Text)
    debit_credit = Column(String(10))
    amount = Column(Numeric(12, 2), nullable=False)
    balance = Column(Numeric(12, 2))
    
    # Enriched fields
    merchant = Column(String(200), index=True)
    amount_signed = Column(Numeric(12, 2))
    category = Column(String(100), index=True)
    
    # Date dimensions
    week_start = Column(Date)
    month = Column(String(7))  # YYYY-MM format
    year = Column(Integer)
    
    # Metadata
    transaction_hash = Column(String(32), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_date_category', 'date', 'category'),
        Index('idx_merchant_category', 'merchant', 'category'),
    )
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, date={self.date}, merchant={self.merchant}, amount={self.amount_signed})>"


class Category(Base):
    """Category model for transaction categorization rules."""
    
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    keywords = Column(JSON, nullable=False, default=list)  # List of keyword strings
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name})>"


class LLMCache(Base):
    """LLM categorization cache to avoid redundant API calls."""
    
    __tablename__ = "llm_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    merchant = Column(String(200), unique=True, nullable=False, index=True)
    category = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<LLMCache(merchant={self.merchant}, category={self.category})>"

