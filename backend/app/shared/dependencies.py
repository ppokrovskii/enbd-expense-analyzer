"""
FastAPI dependencies for request processing.

This module contains dependency functions that can be injected into route handlers.
"""
from fastapi import Header
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

