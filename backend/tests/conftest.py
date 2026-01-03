"""Pytest configuration with Testcontainers for Postgres."""
import pytest
import os
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.shared.database import Base, get_db
from app.main import app as fastapi_app


# Ensure Docker client can connect (for both users)
if not os.getenv('DOCKER_HOST'):
    # Try to detect which user is running Docker
    possible_sockets = [
        '/Users/pavel_admin/.docker/run/docker.sock',
        '/Users/pavelp/.docker/run/docker.sock',
        '/var/run/docker.sock'
    ]
    for socket_path in possible_sockets:
        if os.path.exists(socket_path):
            os.environ['DOCKER_HOST'] = f'unix://{socket_path}'
            break


@pytest.fixture(scope="session")
def postgres_container():
    """Start a Postgres container for the entire test session."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def test_engine(postgres_container):
    """Create a test database engine using the container."""
    # Get connection URL from container (format: postgresql+psycopg2://user:pass@host:port/db)
    connection_url = postgres_container.get_connection_url()
    
    # Force psycopg3 driver by replacing the dialect
    # From: postgresql+psycopg2:// or postgresql://
    # To: postgresql+psycopg://
    connection_url = connection_url.replace("postgresql+psycopg2://", "postgresql+psycopg://")
    connection_url = connection_url.replace("postgresql://", "postgresql+psycopg://")
    
    # Create engine
    engine = create_engine(connection_url, echo=False)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create a test database session for each test."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = SessionLocal()
    
    # Override FastAPI dependency to use test database
    def override_get_db():
        try:
            yield session
        finally:
            pass
    
    fastapi_app.dependency_overrides[get_db] = override_get_db
    
    yield session
    
    # Rollback any uncommitted changes
    session.rollback()
    
    # Clean up tables for next test
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    
    session.close()
    
    # Clear dependency overrides
    fastapi_app.dependency_overrides.clear()

