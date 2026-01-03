"""
FastAPI dependencies for request processing.

This module contains dependency functions that can be injected into route handlers.
"""
from fastapi import Header, Depends
from sqlalchemy.orm import Session
from typing import Optional


def get_user_id(x_user_id: Optional[str] = Header(default='default_user')) -> str:
    """
    Extract user_id from request headers or use default.
    
    For MVP, we default to 'default_user' for all requests.
    In production, this will extract user_id from JWT token.
    
    Args:
        x_user_id: User ID from X-User-Id header
        
    Returns:
        User ID string
    """
    return x_user_id or 'default_user'


def get_person_id(x_person_id: Optional[str] = Header(default=None)) -> Optional[int]:
    """
    Extract person_id from request headers.
    
    The X-Person-Id header should be set by the frontend when a person is active.
    Returns None if no person_id is provided (for backward compatibility).
    
    Args:
        x_person_id: Person ID from X-Person-Id header
        
    Returns:
        Person ID integer or None
    """
    if x_person_id is not None and x_person_id != '':
        try:
            return int(x_person_id)
        except ValueError:
            return None
    return None

