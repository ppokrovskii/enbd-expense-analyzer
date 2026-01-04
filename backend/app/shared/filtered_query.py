"""
FilteredQueryContext - Centralized user/person filtering for all database queries.

This module provides a systematic solution for applying user_id and person_id
filters to all database operations, ensuring data isolation without manual
filtering in every endpoint.

Usage in endpoints:
    @router.get("/categories/")
    def list_categories(ctx: FilteredQueryContext = Depends(get_filtered_context)):
        categories = ctx.query(Category).all()
        return categories
"""
from fastapi import Depends, Header
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, TypeVar, Type, List, Any

from app.shared.database import get_db

# Generic type for model classes
T = TypeVar('T')


class FilteredQueryContext:
    """
    Provides filtered database queries based on user/person context.
    
    All queries automatically include user_id filtering, and optionally
    person_id filtering when a person is active.
    
    Attributes:
        db: SQLAlchemy database session
        user_id: Current user identifier
        person_id: Optional person identifier (for multi-person support)
    """
    
    def __init__(self, db: Session, user_id: str, person_id: Optional[int] = None):
        self.db = db
        self.user_id = user_id
        self.person_id = person_id
    
    def query(self, model: Type[T]):
        """
        Create a query that's automatically filtered by user_id and optionally person_id.
        
        Args:
            model: SQLAlchemy model class to query
            
        Returns:
            Filtered SQLAlchemy Query object
            
        Example:
            categories = ctx.query(Category).all()
            transactions = ctx.query(Transaction).filter(Transaction.amount > 100).all()
        """
        q = self.db.query(model)
        
        # Filter by user_id if the model has it
        if hasattr(model, 'user_id'):
            q = q.filter(model.user_id == self.user_id)
        
        # Filter by person_id if provided and model supports it
        if self.person_id is not None and hasattr(model, 'person_id'):
            q = q.filter(model.person_id == self.person_id)
        
        return q
    
    def query_no_person_filter(self, model: Type[T]):
        """
        Create a query filtered only by user_id (no person_id filter).
        
        Use this for entities that are user-level, not person-level
        (e.g., accounts, user settings).
        
        Args:
            model: SQLAlchemy model class to query
            
        Returns:
            Filtered SQLAlchemy Query object (user_id only)
        """
        q = self.db.query(model)
        
        if hasattr(model, 'user_id'):
            q = q.filter(model.user_id == self.user_id)
        
        return q
    
    def raw_query(self, *args, **kwargs):
        """
        Create an unfiltered query (for special cases like joins).
        
        WARNING: Use with caution! You must manually apply filters.
        
        Returns:
            Unfiltered SQLAlchemy Query object
        """
        return self.db.query(*args, **kwargs)
    
    def add(self, obj: T) -> T:
        """
        Add object with automatic user_id/person_id assignment.
        
        Automatically sets user_id and person_id on the object if:
        - The object has those attributes
        - The attributes are not already set
        
        Args:
            obj: SQLAlchemy model instance to add
            
        Returns:
            The same object (for method chaining)
        """
        if hasattr(obj, 'user_id') and not getattr(obj, 'user_id', None):
            obj.user_id = self.user_id
        if hasattr(obj, 'person_id') and self.person_id is not None and not getattr(obj, 'person_id', None):
            obj.person_id = self.person_id
        self.db.add(obj)
        return obj
    
    def add_all(self, objects: List[T]) -> List[T]:
        """
        Add multiple objects with automatic user_id/person_id assignment.
        
        Args:
            objects: List of SQLAlchemy model instances to add
            
        Returns:
            The same list of objects
        """
        for obj in objects:
            self.add(obj)
        return objects
    
    def delete(self, obj: T) -> None:
        """Delete an object from the database."""
        self.db.delete(obj)
    
    def commit(self) -> None:
        """Commit the current transaction."""
        self.db.commit()
    
    def refresh(self, obj: T) -> T:
        """Refresh an object from the database."""
        self.db.refresh(obj)
        return obj
    
    def rollback(self) -> None:
        """Rollback the current transaction."""
        self.db.rollback()
    
    def get_by_id(self, model: Type[T], id: Any) -> Optional[T]:
        """
        Get an entity by ID, with automatic user/person filtering.
        
        Args:
            model: SQLAlchemy model class
            id: Primary key value
            
        Returns:
            The entity if found and belongs to user/person, None otherwise
        """
        return self.query(model).filter(model.id == id).first()
    
    def get_by_id_user_only(self, model: Type[T], id: Any) -> Optional[T]:
        """
        Get an entity by ID, filtered by user_id only (no person_id).
        
        Use for user-level entities like accounts.
        
        Args:
            model: SQLAlchemy model class
            id: Primary key value
            
        Returns:
            The entity if found and belongs to user, None otherwise
        """
        return self.query_no_person_filter(model).filter(model.id == id).first()
    
    def update_filtered(self, model: Type[T], filters: dict, values: dict) -> int:
        """
        Update records matching filters (with automatic user/person filtering).
        
        Args:
            model: SQLAlchemy model class
            filters: Additional filters to apply (as dict)
            values: Values to update (as dict)
            
        Returns:
            Number of rows updated
        """
        q = self.query(model)
        for key, value in filters.items():
            q = q.filter(getattr(model, key) == value)
        count = q.update(values)
        return count


def get_filtered_context(
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(default='default_user', alias='X-User-Id'),
    x_person_id: Optional[str] = Header(default=None, alias='X-Person-Id')
) -> FilteredQueryContext:
    """
    FastAPI dependency that provides filtered query context.
    
    Extracts user_id and person_id from request headers and creates
    a FilteredQueryContext for the request.
    
    Usage:
        @router.get("/items")
        def get_items(ctx: FilteredQueryContext = Depends(get_filtered_context)):
            return ctx.query(Item).all()
    """
    user_id = x_user_id or 'default_user'
    person_id = int(x_person_id) if x_person_id else None
    return FilteredQueryContext(db, user_id, person_id)


# Alias for shorter import
Ctx = FilteredQueryContext
get_ctx = get_filtered_context

