"""SQLAlchemy models for the Transactions domain."""
from sqlalchemy import Column, Integer, String, Text, Date, Numeric, DateTime, Index, JSON, Boolean, ForeignKey
from datetime import datetime
from app.shared.database import Base


class Transaction(Base):
    """Transaction model representing a bank transaction."""
    
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, server_default='default_user', index=True)
    person_id = Column(Integer, ForeignKey('persons.id'), nullable=True, index=True)
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
    search_text = Column(Text)  # Combined details + description for enhanced matching
    
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
        Index('idx_transactions_user_date', 'user_id', 'date'),
        Index('idx_transactions_user_category', 'user_id', 'category'),
        Index('idx_transactions_user_merchant', 'user_id', 'merchant'),
    )
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, user_id={self.user_id}, date={self.date}, merchant={self.merchant}, amount={self.amount_signed})>"


class UnparsedFile(Base):
    """Storage for uploaded files that couldn't be automatically parsed."""
    
    __tablename__ = "unparsed_files"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100))
    bank_name = Column(String(100))  # User-provided if auto-detection fails
    detection_attempted = Column(Boolean, default=True)
    detection_result = Column(JSON)  # Store detection confidence scores
    status = Column(String(20), default='pending')  # pending, parsed, failed
    error_message = Column(Text)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    
    __table_args__ = (
        Index('idx_unparsed_files_user', 'user_id'),
        Index('idx_unparsed_files_status', 'status'),
    )
    
    def __repr__(self):
        return f"<UnparsedFile(id={self.id}, user_id={self.user_id}, filename={self.filename}, bank_name={self.bank_name})>"

