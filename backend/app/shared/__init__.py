"""Shared modules used across all domains."""
from .database import Base, get_db, engine, SessionLocal
from .dependencies import get_user_id

__all__ = [
    'Base',
    'get_db',
    'engine',
    'SessionLocal',
    'get_user_id',
]

