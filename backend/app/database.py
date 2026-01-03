"""Backward compatibility - re-export from shared.database."""
from app.shared.database import (
    Base,
    get_db,
    engine,
    SessionLocal,
    DATABASE_URL
)

__all__ = ['Base', 'get_db', 'engine', 'SessionLocal', 'DATABASE_URL']
