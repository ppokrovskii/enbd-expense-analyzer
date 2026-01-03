"""Persons domain models."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.shared.database import Base


class Person(Base):
    """Person model for multi-person data isolation.
    
    A user can have multiple persons (e.g., managing finances for wife, friend).
    Each person has completely isolated data (transactions, categories, etc.).
    """
    __tablename__ = 'persons'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)  # Owner of this person
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=False)  # Currently active person for this user
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships can be added as needed
    # transactions = relationship("Transaction", back_populates="person")
    # categories = relationship("Category", back_populates="person")
    
    def __repr__(self):
        return f"<Person(id={self.id}, user_id={self.user_id}, name={self.name}, is_active={self.is_active})>"


# Note: We'll add person_id to other tables via migration
# This allows full data isolation per person while a single user
# can manage multiple persons

