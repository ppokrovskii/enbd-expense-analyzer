"""SQLAlchemy models for the Accounts domain."""
from sqlalchemy import Column, Integer, String, DateTime, Index, Boolean, UniqueConstraint
from datetime import datetime
from app.shared.database import Base


class UserAccount(Base):
    """User account configuration for bank accounts."""
    
    __tablename__ = "user_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    account_name = Column(String(100), nullable=False)  # e.g., "current_account"
    account_number = Column(String(50))
    account_number_masked = Column(String(50))
    bank = Column(String(50), nullable=False)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_user_accounts', 'user_id'),
        UniqueConstraint('user_id', 'account_name', name='uq_user_account_name')
    )
    
    def __repr__(self):
        return f"<UserAccount(id={self.id}, user_id={self.user_id}, account_name={self.account_name}, bank={self.bank})>"

