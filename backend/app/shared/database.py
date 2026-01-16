"""Database configuration and session management."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os

# Database URL from environment variable or default for local dev
# Using postgresql+psycopg for psycopg3 driver
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://enbd_user:enbd_password@localhost:5432/enbd_db"
)

# SQL echo: disabled by default, enable with SQL_ECHO=true for debugging
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() in ("true", "1", "yes")

# Create engine
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Disable connection pooling for testing
    echo=SQL_ECHO,  # Log SQL statements only when explicitly enabled
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

