"""
Pytest configuration and fixtures for the trading system tests
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from typing import Generator, AsyncGenerator
import httpx
import redis
from fastapi.testclient import TestClient

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Set test environment variables
os.environ["TESTING"] = "true"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["LOG_LEVEL"] = "DEBUG"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def app():
    """Create FastAPI application for testing."""
    # Import here to avoid circular imports
    try:
        from app import app as fastapi_app
        return fastapi_app
    except ImportError:
        # Create a minimal FastAPI app for testing
        from fastapi import FastAPI
        app = FastAPI(title="Test Trading System")
        
        @app.get("/health")
        async def health_check():
            return {"status": "healthy"}
        
        return app

@pytest.fixture(scope="session")
def client(app) -> Generator[TestClient, None, None]:
    """Create test client for API testing."""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture(scope="session")
async def async_client(app) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create async test client for API testing."""
    async with httpx.AsyncClient(
        app=app,
        base_url="http://testserver"
    ) as async_test_client:
        yield async_test_client

@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    mock_client = Mock()
    mock_client.ping = Mock(return_value=True)
    mock_client.get = Mock(return_value=None)
    mock_client.set = Mock(return_value=True)
    mock_client.delete = Mock(return_value=1)
    mock_client.exists = Mock(return_value=False)
    mock_client.close = Mock()
    return mock_client

@pytest.fixture
def mock_database():
    """Mock database connection for testing."""
    mock_db = Mock()
    mock_db.execute = AsyncMock()
    mock_db.fetch = AsyncMock(return_value=[])
    mock_db.fetchrow = AsyncMock(return_value=None)
    mock_db.fetchval = AsyncMock(return_value=None)
    mock_db.close = AsyncMock()
    return mock_db

@pytest.fixture
def mock_binance_client():
    """Mock Binance API client for testing."""
    mock_client = Mock()
    mock_client.get_symbol_ticker = Mock(return_value={"symbol": "BTCUSDT", "price": "50000.00"})
    mock_client.get_orderbook_ticker = Mock(return_value={
        "symbol": "BTCUSDT",
        "bidPrice": "49900.00",
        "bidQty": "1.00000000",
        "askPrice": "50100.00",
        "askQty": "1.00000000"
    })
    mock_client.get_historical_klines = Mock(return_value=[
        [1640995200000, "50000", "51000", "49000", "50500", "100", 1640995259999, "5000000", 1000, "50", "2500000", "0"]
    ])
    return mock_client

@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "is_active": True,
        "is_verified": True,
        "created_at": "2024-01-01T00:00:00Z"
    }

@pytest.fixture
def sample_trade_data():
    """Sample trade data for testing."""
    return {
        "id": 1,
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": 0.1,
        "price": 50000.0,
        "status": "FILLED",
        "timestamp": "2024-01-01T00:00:00Z"
    }

@pytest.fixture
def sample_market_data():
    """Sample market data for testing."""
    return {
        "symbol": "BTCUSDT",
        "price": 50000.0,
        "change_24h": 2.5,
        "volume_24h": 1000000.0,
        "high_24h": 51000.0,
        "low_24h": 49000.0,
        "timestamp": "2024-01-01T00:00:00Z"
    }

@pytest.fixture(autouse=True)
def clean_environment():
    """Clean environment before and after each test."""
    # Setup
    os.environ["TESTING"] = "true"
    
    yield
    
    # Teardown - clean up any test data
    test_files = ["test.db", "test.db-shm", "test.db-wal"]
    for file in test_files:
        if os.path.exists(file):
            try:
                os.remove(file)
            except OSError:
                pass

@pytest.fixture
def temp_config_file(tmp_path):
    """Create temporary configuration file for testing."""
    config_content = """
trading:
  mode: testing
  max_position_size: 1000
  risk_per_trade: 0.01
  
database:
  url: sqlite:///test.db
  
redis:
  url: redis://localhost:6379/15
  
apis:
  binance:
    testnet: true
"""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(config_content)
    return str(config_file)

# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "api: marks tests as API tests"
    )
    config.addinivalue_line(
        "markers", "database: marks tests that require database"
    )
    config.addinivalue_line(
        "markers", "redis: marks tests that require Redis"
    )

def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Mark integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Mark unit tests
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Mark API tests
        if "api" in str(item.fspath):
            item.add_marker(pytest.mark.api)
        
        # Mark slow tests
        if "slow" in item.name or "performance" in item.name:
            item.add_marker(pytest.mark.slow)