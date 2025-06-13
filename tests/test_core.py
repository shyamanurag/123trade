"""
Unit tests for core components
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from core.exceptions import (
    TradingSystemError,
    ConnectionError,
    AuthenticationError,
    ValidationError,
    StrategyError,
    RiskManagementError,
    OrderError,
    DataError,
    ConfigurationError,
    WebhookError,
    RecoveryError
)
from core.logging import setup_logging, get_logger, LoggerAdapter, create_logger_adapter
from core.recovery import RetryConfig, RecoveryManager, with_recovery
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

# Test Exceptions
def test_exception_hierarchy():
    """Test exception hierarchy"""
    assert issubclass(ConnectionError, TradingSystemError)
    assert issubclass(AuthenticationError, TradingSystemError)
    assert issubclass(ValidationError, TradingSystemError)
    assert issubclass(StrategyError, TradingSystemError)
    assert issubclass(RiskManagementError, TradingSystemError)
    assert issubclass(OrderError, TradingSystemError)
    assert issubclass(DataError, TradingSystemError)
    assert issubclass(ConfigurationError, TradingSystemError)
    assert issubclass(WebhookError, TradingSystemError)
    assert issubclass(RecoveryError, TradingSystemError)

def test_exception_attributes():
    """Test exception attributes"""
    error = ConnectionError("Connection failed", {"host": "localhost", "port": 8080})
    assert error.message == "Connection failed"
    assert error.details == {"host": "localhost", "port": 8080}
    assert error.error_code == 1000

# Test Logging
def test_setup_logging(tmp_path):
    """Test logging setup"""
    log_dir = tmp_path / "logs"
    setup_logging(log_dir=str(log_dir))
    logger = get_logger("test")
    assert logger.name == "test"
    assert logger.level == 20  # INFO

def test_logger_adapter():
    """Test logger adapter"""
    logger = get_logger("test")
    adapter = LoggerAdapter(logger, {"request_id": "123"})
    assert adapter.extra == {"request_id": "123"}

def test_create_logger_adapter():
    """Test logger adapter creation"""
    logger = get_logger("test")
    adapter = create_logger_adapter(logger, request_id="123", user_id="456")
    assert adapter.extra == {"request_id": "123", "user_id": "456"}

# Test Recovery
@pytest.mark.asyncio
async def test_retry_config():
    """Test retry configuration"""
    config = RetryConfig(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=30.0,
        exponential_base=2.0,
        jitter=True
    )
    assert config.max_attempts == 3
    assert config.initial_delay == 1.0
    assert config.max_delay == 30.0
    assert config.exponential_base == 2.0
    assert config.jitter is True

@pytest.mark.asyncio
async def test_recovery_manager():
    """Test recovery manager"""
    manager = RecoveryManager()
    
    # Test recovery strategy registration
    async def mock_recovery(error):
        return "recovered"
    
    manager.register_recovery_strategy(ConnectionError, mock_recovery)
    assert ConnectionError in manager._recovery_strategies
    
    # Test fallback strategy registration
    async def mock_fallback(error):
        return "fallback"
    
    manager.register_fallback_strategy(ConnectionError, mock_fallback)
    assert ConnectionError in manager._fallback_strategies

@pytest.mark.asyncio
async def test_with_recovery_decorator():
    """Test recovery decorator"""
    @with_recovery(retry_config=RetryConfig(max_attempts=2))
    async def mock_function():
        raise ConnectionError("Connection failed")
    
    with pytest.raises(RecoveryError):
        await mock_function()

# Test Models
def test_order_model():
    """Test order model"""
    order = Order(
        order_id="123",
        symbol="BTC/USD",
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=Decimal("1.0"),
        price=Decimal("50000.0")
    )
    assert order.order_id == "123"
    assert order.symbol == "BTC/USD"
    assert order.order_type == OrderType.LIMIT
    assert order.side == OrderSide.BUY
    assert order.quantity == Decimal("1.0")
    assert order.price == Decimal("50000.0")
    assert order.status == OrderStatus.PENDING

def test_position_model():
    """Test position model"""
    position = Position(
        symbol="BTC/USD",
        quantity=Decimal("1.0"),
        average_entry_price=Decimal("50000.0"),
        current_price=Decimal("51000.0"),
        unrealized_pnl=Decimal("1000.0"),
        margin_used=Decimal("5000.0")
    )
    assert position.symbol == "BTC/USD"
    assert position.quantity == Decimal("1.0")
    assert position.average_entry_price == Decimal("50000.0")
    assert position.current_price == Decimal("51000.0")
    assert position.unrealized_pnl == Decimal("1000.0")
    assert position.total_pnl == Decimal("1000.0")
    assert position.pnl_percentage == Decimal("2.0")

def test_market_data_model():
    """Test market data model"""
    market_data = MarketData(
        symbol="BTC/USD",
        timestamp=datetime.utcnow(),
        open=Decimal("50000.0"),
        high=Decimal("51000.0"),
        low=Decimal("49000.0"),
        close=Decimal("50500.0"),
        volume=Decimal("100.0"),
        timeframe=TimeFrame.HOUR_1
    )
    assert market_data.symbol == "BTC/USD"
    assert market_data.open == Decimal("50000.0")
    assert market_data.high == Decimal("51000.0")
    assert market_data.low == Decimal("49000.0")
    assert market_data.close == Decimal("50500.0")
    assert market_data.volume == Decimal("100.0")
    assert market_data.timeframe == TimeFrame.HOUR_1

def test_strategy_config_model():
    """Test strategy configuration model"""
    config = StrategyConfig(
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
    assert config.name == "Test Strategy"
    assert config.description == "Test strategy description"
    assert config.timeframe == TimeFrame.HOUR_1
    assert config.symbols == ["BTC/USD", "ETH/USD"]
    assert config.parameters["stop_loss"] == 0.02
    assert config.parameters["take_profit"] == 0.05
    assert config.risk_limits["max_position_size"] == 1.0
    assert config.risk_limits["max_drawdown"] == 0.1

def test_signal_metadata_model():
    """Test signal metadata model"""
    metadata = SignalMetadata(
        quality_score=0.8,
        timeframe=TimeFrame.HOUR_1,
        confidence=0.9,
        indicators={
            "rsi": 70.0,
            "macd": [0.1, 0.2, 0.3]
        },
        strategy_name="Test Strategy"
    )
    assert metadata.quality_score == 0.8
    assert metadata.timeframe == TimeFrame.HOUR_1
    assert metadata.confidence == 0.9
    assert metadata.indicators["rsi"] == 70.0
    assert metadata.indicators["macd"] == [0.1, 0.2, 0.3]
    assert metadata.strategy_name == "Test Strategy"

def test_trading_signal_model():
    """Test trading signal model"""
    signal = TradingSignal(
        symbol="BTC/USD",
        action=OrderSide.BUY,
        quantity=Decimal("1.0"),
        entry_price=Decimal("50000.0"),
        strategy_name="Test Strategy",
        signal_id="123",
        metadata=SignalMetadata(
            quality_score=0.8,
            timeframe=TimeFrame.HOUR_1,
            confidence=0.9,
            indicators={"rsi": 70.0},
            strategy_name="Test Strategy"
        )
    )
    assert signal.symbol == "BTC/USD"
    assert signal.action == OrderSide.BUY
    assert signal.quantity == Decimal("1.0")
    assert signal.entry_price == Decimal("50000.0")
    assert signal.strategy_name == "Test Strategy"
    assert signal.signal_id == "123"
    assert signal.metadata.quality_score == 0.8
    assert signal.status == "PENDING"

def test_model_validation():
    """Test model validation"""
    # Test invalid order type
    with pytest.raises(ValidationError):
        Order(
            order_id="123",
            symbol="BTC/USD",
            order_type="INVALID",
            side=OrderSide.BUY,
            quantity=Decimal("1.0"),
            price=Decimal("50000.0")
        )
    
    # Test invalid price for limit order
    with pytest.raises(ValidationError):
        Order(
            order_id="123",
            symbol="BTC/USD",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=Decimal("1.0")
        )
    
    # Test invalid high/low prices
    with pytest.raises(ValidationError):
        MarketData(
            symbol="BTC/USD",
            timestamp=datetime.utcnow(),
            open=Decimal("50000.0"),
            high=Decimal("49000.0"),
            low=Decimal("51000.0"),
            close=Decimal("50500.0"),
            volume=Decimal("100.0"),
            timeframe=TimeFrame.HOUR_1
        )
    
    # Test missing required strategy parameters
    with pytest.raises(ValidationError):
        StrategyConfig(
            name="Test Strategy",
            description="Test strategy description",
            timeframe=TimeFrame.HOUR_1,
            symbols=["BTC/USD"],
            parameters={}
        )
    
    # Test invalid signal expiration
    with pytest.raises(ValidationError):
        TradingSignal(
            symbol="BTC/USD",
            action=OrderSide.BUY,
            quantity=Decimal("1.0"),
            entry_price=Decimal("50000.0"),
            strategy_name="Test Strategy",
            signal_id="123",
            metadata=SignalMetadata(
                quality_score=0.8,
                timeframe=TimeFrame.HOUR_1,
                confidence=0.9,
                indicators={"rsi": 70.0},
                strategy_name="Test Strategy"
            ),
            expires_at=datetime.utcnow() - timedelta(hours=1)
        ) 