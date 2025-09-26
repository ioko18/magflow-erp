"""
Test client fixtures for FastAPI application testing.

This module provides test client fixtures that can be used across test modules
for testing FastAPI endpoints.
"""
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.database import engine, Base
from app.main import app
from app.core.database import get_db

# Create test database tables
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def test_db():
    """Create a fresh test database and drop it after tests."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop all tables
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="module")
def client(test_db) -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application.
    
    This fixture creates a FastAPI test client that can be used to make HTTP requests
    to the application during testing. The client is configured with a test database
    that is created fresh for each test module.
    """
    # Override the get_db dependency to use our test database
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up overrides
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """Get authentication headers for testing protected endpoints.
    
    This fixture logs in a test user and returns the authorization headers
    that can be used to make authenticated requests.
    """
    # TODO: Implement actual authentication when auth is set up
    return {"Authorization": "Bearer test-token"}
