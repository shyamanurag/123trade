"""
Integration tests for the risk management system
"""

import pytest
from datetime import datetime
from decimal import Decimal
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

from core.models import (
    OrderType,
    OrderSide,
    TimeFrame,
    MarketData,
    TradingSignal,
    SignalMetadata,
    Position
)
from core.exceptions import RiskManagementError
from risk.risk_manager import RiskManager

@pytest.fixture
def risk_config() -> Dict:
    """Create risk management configuration"""
    return {
        "max_position_size": Decimal("2.0"),
        "max_leverage": Decimal("3.0"),
        "max_drawdown": Decimal("0.15"),
        "max_daily_loss": Decimal("1000.0"),
        "max_open_positions": 5,
        "position_limits": {
            "BTC/USD": Decimal("1.0"),
            "ETH/USD": Decimal("5.0")
        },
        "correlation_limits": {
            "max_correlation": Decimal("0.7"),
            "lookback_period": 30
        },
        "volatility_limits": {
            "max_volatility": Decimal("0.05"),
            "lookback_period": 20
        }
    }

@pytest.fixture
def positions() -> List[Position]:
    """Create test positions"""
    return [
        Position(
            symbol="BTC/USD",
            quantity=Decimal("0.5"),
            average_entry_price=Decimal("50000.0"),
            current_price=Decimal("51000.0"),
            unrealized_pnl=Decimal("500.0"),
            margin_used=Decimal("25000.0")
        ),
        Position(
            symbol="ETH/USD",
            quantity=Decimal("2.0"),
            average_entry_price=Decimal("3000.0"),
            current_price=Decimal("3100.0"),
            unrealized_pnl=Decimal("200.0"),
            margin_used=Decimal("6000.0")
        )
    ]

@pytest.fixture
def market_data() -> Dict:
    """Create market data"""
    return {
        "BTC/USD": {
            "timestamp": datetime.utcnow(),
            "open": Decimal("50000.0"),
            "high": Decimal("51000.0"),
            "low": Decimal("49000.0"),
            "close": Decimal("50500.0"),
            "volume": Decimal("100.0"),
            "volatility": Decimal("0.02")
        },
        "ETH/USD": {
            "timestamp": datetime.utcnow(),
            "open": Decimal("3000.0"),
            "high": Decimal("3100.0"),
            "low": Decimal("2900.0"),
            "close": Decimal("3050.0"),
            "volume": Decimal("1000.0"),
            "volatility": Decimal("0.03")
        }
    }

@pytest.mark.asyncio
async def test_position_size_validation(risk_config: Dict):
    """Test position size validation"""
    manager = RiskManager(risk_config)
    
    # Test valid position size
    assert await manager.validate_position_size("BTC/USD", Decimal("0.5"))
    
    # Test exceeding position limit
    with pytest.raises(RiskManagementError):
        await manager.validate_position_size("BTC/USD", Decimal("2.0"))
    
    # Test exceeding max position size
    with pytest.raises(RiskManagementError):
        await manager.validate_position_size("BTC/USD", Decimal("3.0"))

@pytest.mark.asyncio
async def test_leverage_validation(risk_config: Dict):
    """Test leverage validation"""
    manager = RiskManager(risk_config)
    
    # Test valid leverage
    assert await manager.validate_leverage(Decimal("2.0"))
    
    # Test exceeding max leverage
    with pytest.raises(RiskManagementError):
        await manager.validate_leverage(Decimal("4.0"))

@pytest.mark.asyncio
async def test_drawdown_validation(risk_config: Dict, positions: List[Position]):
    """Test drawdown validation"""
    manager = RiskManager(risk_config)
    
    # Test valid drawdown
    assert await manager.validate_drawdown(positions, Decimal("0.1"))
    
    # Test exceeding max drawdown
    with pytest.raises(RiskManagementError):
        await manager.validate_drawdown(positions, Decimal("0.2"))

@pytest.mark.asyncio
async def test_daily_loss_validation(risk_config: Dict):
    """Test daily loss validation"""
    manager = RiskManager(risk_config)
    
    # Test valid daily loss
    assert await manager.validate_daily_loss(Decimal("500.0"))
    
    # Test exceeding max daily loss
    with pytest.raises(RiskManagementError):
        await manager.validate_daily_loss(Decimal("1500.0"))

@pytest.mark.asyncio
async def test_open_positions_validation(risk_config: Dict, positions: List[Position]):
    """Test open positions validation"""
    manager = RiskManager(risk_config)
    
    # Test valid number of positions
    assert await manager.validate_open_positions(positions)
    
    # Test exceeding max open positions
    with pytest.raises(RiskManagementError):
        await manager.validate_open_positions(positions * 3)

@pytest.mark.asyncio
async def test_correlation_validation(risk_config: Dict, market_data: Dict):
    """Test correlation validation"""
    manager = RiskManager(risk_config)
    
    # Test valid correlation
    assert await manager.validate_correlation(
        "BTC/USD",
        "ETH/USD",
        Decimal("0.5")
    )
    
    # Test exceeding max correlation
    with pytest.raises(RiskManagementError):
        await manager.validate_correlation(
            "BTC/USD",
            "ETH/USD",
            Decimal("0.8")
        )

@pytest.mark.asyncio
async def test_volatility_validation(risk_config: Dict, market_data: Dict):
    """Test volatility validation"""
    manager = RiskManager(risk_config)
    
    # Test valid volatility
    assert await manager.validate_volatility(
        "BTC/USD",
        Decimal("0.02")
    )
    
    # Test exceeding max volatility
    with pytest.raises(RiskManagementError):
        await manager.validate_volatility(
            "BTC/USD",
            Decimal("0.06")
        )

@pytest.mark.asyncio
async def test_position_risk_calculation(risk_config: Dict, positions: List[Position]):
    """Test position risk calculation"""
    manager = RiskManager(risk_config)
    
    # Calculate position risk
    risk = await manager.calculate_position_risk(positions[0])
    
    # Verify risk metrics
    assert isinstance(risk, dict)
    assert "value_at_risk" in risk
    assert "expected_shortfall" in risk
    assert "sharpe_ratio" in risk
    assert "sortino_ratio" in risk

@pytest.mark.asyncio
async def test_portfolio_risk_calculation(risk_config: Dict, positions: List[Position]):
    """Test portfolio risk calculation"""
    manager = RiskManager(risk_config)
    
    # Calculate portfolio risk
    risk = await manager.calculate_portfolio_risk(positions)
    
    # Verify risk metrics
    assert isinstance(risk, dict)
    assert "total_value_at_risk" in risk
    assert "portfolio_volatility" in risk
    assert "portfolio_beta" in risk
    assert "correlation_matrix" in risk

@pytest.mark.asyncio
async def test_risk_limits_update(risk_config: Dict):
    """Test risk limits update"""
    manager = RiskManager(risk_config)
    
    # Update risk limits
    new_limits = {
        "max_position_size": Decimal("3.0"),
        "max_leverage": Decimal("4.0")
    }
    await manager.update_risk_limits(new_limits)
    
    # Verify updated limits
    assert manager.config["max_position_size"] == Decimal("3.0")
    assert manager.config["max_leverage"] == Decimal("4.0")

@pytest.mark.asyncio
async def test_risk_monitoring(risk_config: Dict, positions: List[Position], market_data: Dict):
    """Test risk monitoring"""
    manager = RiskManager(risk_config)
    
    # Start risk monitoring
    await manager.start_monitoring(positions, market_data)
    
    # Verify monitoring state
    assert manager.is_monitoring
    
    # Stop risk monitoring
    await manager.stop_monitoring()
    assert not manager.is_monitoring

@pytest.mark.asyncio
async def test_risk_alerts(risk_config: Dict, positions: List[Position]):
    """Test risk alerts"""
    manager = RiskManager(risk_config)
    
    # Register alert callback
    alert_received = False
    async def alert_callback(alert):
        nonlocal alert_received
        alert_received = True
    
    manager.register_alert_callback(alert_callback)
    
    # Trigger alert
    await manager.trigger_alert(
        "HIGH_RISK",
        "Portfolio risk exceeds threshold",
        {"risk_level": "high"}
    )
    
    # Verify alert was received
    assert alert_received 