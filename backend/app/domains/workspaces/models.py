"""Workspaces domain models."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.shared.database import Base


class Workspace(Base):
    """Workspace model for multi-workspace data isolation.
    
    A user can have multiple workspaces (e.g., managing finances for wife, friend).
    Each workspace has completely isolated data (transactions, categories, etc.).
    """
    __tablename__ = 'workspaces'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)  # Owner of this workspace
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=False)  # Currently active workspace for this user
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships can be added as needed
    # transactions = relationship("Transaction", back_populates="workspace")
    # categories = relationship("Category", back_populates="workspace")
    
    def __repr__(self):
        return f"<Workspace(id={self.id}, user_id={self.user_id}, name={self.name}, is_active={self.is_active})>"


# Note: We'll add workspace_id to other tables via migration
# This allows full data isolation per workspace while a single user
# can manage multiple workspaces
