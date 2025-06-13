"""
Test configuration and fixtures
"""

import os
import pytest
from datetime import datetime
from decimal import Decimal
from typing import Dict, Generator

from core.models import (
    OrderType,
    OrderSide,
    OrderStatus,
    TimeFrame,
    Order,
    Position,
    MarketData,
    StrategyConfig,
    SignalMetadata,
    TradingSignal
)

@pytest.fixture
def test_order() -> Order:
    """Create a test order"""
    return Order(
        order_id="test-123",
        symbol="BTC/USD",
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=Decimal("1.0"),
        price=Decimal("50000.0")
    )

@pytest.fixture
def test_position() -> Position:
    """Create a test position"""
    return Position(
        symbol="BTC/USD",
        quantity=Decimal("1.0"),
        average_entry_price=Decimal("50000.0"),
        current_price=Decimal("51000.0"),
        unrealized_pnl=Decimal("1000.0"),
        margin_used=Decimal("5000.0")
    )

@pytest.fixture
def test_market_data() -> MarketData:
    """Create test market data"""
    return MarketData(
        symbol="BTC/USD",
        timestamp=datetime.utcnow(),
        open=Decimal("50000.0"),
        high=Decimal("51000.0"),
        low=Decimal("49000.0"),
        close=Decimal("50500.0"),
        volume=Decimal("100.0"),
        timeframe=TimeFrame.HOUR_1
    )

@pytest.fixture
def test_strategy_config() -> StrategyConfig:
    """Create test strategy configuration"""
    return StrategyConfig(
        name="Test Strategy",
        description="Test strategy description",
        timeframe=TimeFrame.HOUR_1,
        symbols=["BTC/USD", "ETH/USD"],
        parameters={
            "stop_loss": 0.02,
            "take_profit": 0.05
        },
        risk_limits={
            "max_position_size": 1.0,
            "max_drawdown": 0.1
        }
    )

@pytest.fixture
def test_signal_metadata() -> SignalMetadata:
    """Create test signal metadata"""
    return SignalMetadata(
        quality_score=0.8,
        timeframe=TimeFrame.HOUR_1,
        confidence=0.9,
        indicators={
            "rsi": 70.0,
            "macd": [0.1, 0.2, 0.3]
        },
        strategy_name="Test Strategy"
    )

@pytest.fixture
def test_trading_signal(test_signal_metadata: SignalMetadata) -> TradingSignal:
    """Create test trading signal"""
    return TradingSignal(
        symbol="BTC/USD",
        action=OrderSide.BUY,
        quantity=Decimal("1.0"),
        entry_price=Decimal("50000.0"),
        strategy_name="Test Strategy",
        signal_id="test-123",
        metadata=test_signal_metadata
    )

@pytest.fixture
def test_config() -> Dict:
    """Create test configuration"""
    return {
        "redis": {
            "url": "redis://localhost:6379",
            "decode_responses": True
        },
        "security": {
            "jwt_secret": "test-secret-key",
            "jwt_algorithm": "HS256",
            "token_expire_minutes": 60,
            "webhook_secret": "test-webhook-secret",
            "ip_whitelist": ["127.0.0.1"]
        },
        "webhooks": {
            "n8n": {
                "url": "https://test.n8n.cloud/webhook/test",
                "timeout": 5,
                "retry_attempts": 3,
                "retry_delay": 1
            }
        },
        "monitoring": {
            "health_check_interval": 30,
            "security_event_ttl": 2592000,
            "metrics_port": 9090
        },
        "backup": {
            "backup_dir": "test_backups",
            "retention_days": 7,
            "schedule": "0 0 * * *",
            "encryption_key": "test-backup-key"
        }
    }

@pytest.fixture
def test_log_dir(tmp_path) -> Generator[str, None, None]:
    """Create temporary log directory"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    yield str(log_dir)
    # Cleanup after tests
    for file in log_dir.glob("*"):
        file.unlink()
    log_dir.rmdir()

@pytest.fixture
def test_data_dir(tmp_path) -> Generator[str, None, None]:
    """Create temporary data directory"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    yield str(data_dir)
    # Cleanup after tests
    for file in data_dir.glob("*"):
        file.unlink()
    data_dir.rmdir()

@pytest.fixture
def test_backup_dir(tmp_path) -> Generator[str, None, None]:
    """Create temporary backup directory"""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    yield str(backup_dir)
    # Cleanup after tests
    for file in backup_dir.glob("*"):
        file.unlink()
    backup_dir.rmdir()

@pytest.fixture(autouse=True)
def setup_test_environment(
    test_log_dir: str,
    test_data_dir: str,
    test_backup_dir: str
) -> None:
    """Setup test environment"""
    # Set environment variables
    os.environ["LOG_DIR"] = test_log_dir
    os.environ["DATA_DIR"] = test_data_dir
    os.environ["BACKUP_DIR"] = test_backup_dir
    os.environ["TESTING"] = "true"
    
    yield
    
    # Cleanup environment variables
    for var in ["LOG_DIR", "DATA_DIR", "BACKUP_DIR", "TESTING"]:
        os.environ.pop(var, None) 