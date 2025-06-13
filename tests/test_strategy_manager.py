"""
Integration tests for the strategy manager
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
    StrategyConfig
)
from core.exceptions import StrategyError
from strategies.regime_adaptive_controller import RegimeAdaptiveController
from strategies.strategy_manager import StrategyManager

@pytest.fixture
def strategy_configs() -> Dict[str, StrategyConfig]:
    """Create strategy configurations"""
    return {
        "volatility_explosion": StrategyConfig(
            name="Volatility Explosion",
            description="Strategy for high volatility periods",
            timeframe=TimeFrame.MINUTE_15,
            symbols=["BTC/USD", "ETH/USD"],
            parameters={
                "stop_loss": 0.02,
                "take_profit": 0.05,
                "volatility_threshold": 0.03
            },
            risk_limits={
                "max_position_size": 1.0,
                "max_drawdown": 0.1
            }
        ),
        "momentum_surfer": StrategyConfig(
            name="Momentum Surfer",
            description="Strategy for trending markets",
            timeframe=TimeFrame.HOUR_1,
            symbols=["BTC/USD", "ETH/USD"],
            parameters={
                "stop_loss": 0.03,
                "take_profit": 0.06,
                "momentum_threshold": 0.02
            },
            risk_limits={
                "max_position_size": 1.5,
                "max_drawdown": 0.15
            }
        ),
        "volume_profile_scalper": StrategyConfig(
            name="Volume Profile Scalper",
            description="Strategy for range-bound markets",
            timeframe=TimeFrame.MINUTE_5,
            symbols=["BTC/USD", "ETH/USD"],
            parameters={
                "stop_loss": 0.01,
                "take_profit": 0.03,
                "volume_threshold": 1000
            },
            risk_limits={
                "max_position_size": 0.5,
                "max_drawdown": 0.05
            }
        )
    }

@pytest.fixture
def market_data() -> Dict:
    """Create market data"""
    return {
        "vix": 20.0,
        "adx": 25.0,
        "atr_ratio": 1.2,
        "directional_movement": 0.6,
        "symbol": "BTC/USD",
        "timestamp": datetime.utcnow(),
        "open": Decimal("50000.0"),
        "high": Decimal("51000.0"),
        "low": Decimal("49000.0"),
        "close": Decimal("50500.0"),
        "volume": Decimal("100.0")
    }

@pytest.mark.asyncio
async def test_strategy_initialization(strategy_configs: Dict[str, StrategyConfig]):
    """Test strategy initialization"""
    manager = StrategyManager()
    
    # Add strategies
    for name, config in strategy_configs.items():
        await manager.add_strategy(name, config)
    
    # Verify strategies were added
    assert len(manager.strategies) == len(strategy_configs)
    for name in strategy_configs:
        assert name in manager.strategies

@pytest.mark.asyncio
async def test_strategy_enabling_disabling(strategy_configs: Dict[str, StrategyConfig]):
    """Test enabling and disabling strategies"""
    manager = StrategyManager()
    
    # Add strategy
    name = "volatility_explosion"
    await manager.add_strategy(name, strategy_configs[name])
    
    # Disable strategy
    await manager.disable_strategy(name)
    assert not manager.strategies[name].enabled
    
    # Enable strategy
    await manager.enable_strategy(name)
    assert manager.strategies[name].enabled

@pytest.mark.asyncio
async def test_signal_generation(
    strategy_configs: Dict[str, StrategyConfig],
    market_data: Dict
):
    """Test signal generation from multiple strategies"""
    manager = StrategyManager()
    
    # Add strategies
    for name, config in strategy_configs.items():
        await manager.add_strategy(name, config)
    
    # Generate signals
    signals = await manager.generate_signals(market_data)
    
    # Verify signals
    assert isinstance(signals, list)
    for signal in signals:
        assert isinstance(signal, TradingSignal)
        assert signal.symbol in strategy_configs[signal.strategy_name].symbols

@pytest.mark.asyncio
async def test_strategy_allocation(
    strategy_configs: Dict[str, StrategyConfig],
    market_data: Dict
):
    """Test strategy allocation based on market regime"""
    manager = StrategyManager()
    
    # Add strategies
    for name, config in strategy_configs.items():
        await manager.add_strategy(name, config)
    
    # Test allocation in different regimes
    market_data["vix"] = 30.0  # Ultra high volatility
    allocations = await manager.get_strategy_allocations(market_data)
    assert allocations["volatility_explosion"] > allocations["momentum_surfer"]
    
    market_data["vix"] = 20.0
    market_data["adx"] = 35.0  # Trending
    allocations = await manager.get_strategy_allocations(market_data)
    assert allocations["momentum_surfer"] > allocations["volatility_explosion"]
    
    market_data["adx"] = 15.0  # Range bound
    allocations = await manager.get_strategy_allocations(market_data)
    assert allocations["volume_profile_scalper"] > allocations["momentum_surfer"]

@pytest.mark.asyncio
async def test_concurrent_signal_generation(
    strategy_configs: Dict[str, StrategyConfig],
    market_data: Dict
):
    """Test concurrent signal generation"""
    manager = StrategyManager()
    
    # Add strategies
    for name, config in strategy_configs.items():
        await manager.add_strategy(name, config)
    
    async def generate_signals():
        return await manager.generate_signals(market_data)
    
    # Run multiple concurrent signal generations
    tasks = [generate_signals() for _ in range(5)]
    results = await asyncio.gather(*tasks)
    
    # Verify results
    for signals in results:
        assert isinstance(signals, list)
        for signal in signals:
            assert isinstance(signal, TradingSignal)

@pytest.mark.asyncio
async def test_strategy_removal(strategy_configs: Dict[str, StrategyConfig]):
    """Test strategy removal"""
    manager = StrategyManager()
    
    # Add strategy
    name = "volatility_explosion"
    await manager.add_strategy(name, strategy_configs[name])
    assert name in manager.strategies
    
    # Remove strategy
    await manager.remove_strategy(name)
    assert name not in manager.strategies

@pytest.mark.asyncio
async def test_invalid_strategy_operations(strategy_configs: Dict[str, StrategyConfig]):
    """Test invalid strategy operations"""
    manager = StrategyManager()
    
    # Test adding invalid strategy
    with pytest.raises(StrategyError):
        await manager.add_strategy("invalid", None)
    
    # Test enabling non-existent strategy
    with pytest.raises(StrategyError):
        await manager.enable_strategy("non_existent")
    
    # Test disabling non-existent strategy
    with pytest.raises(StrategyError):
        await manager.disable_strategy("non_existent")
    
    # Test removing non-existent strategy
    with pytest.raises(StrategyError):
        await manager.remove_strategy("non_existent")

@pytest.mark.asyncio
async def test_strategy_performance_tracking(
    strategy_configs: Dict[str, StrategyConfig],
    market_data: Dict
):
    """Test strategy performance tracking"""
    manager = StrategyManager()
    
    # Add strategy
    name = "volatility_explosion"
    await manager.add_strategy(name, strategy_configs[name])
    
    # Generate signals
    signals = await manager.generate_signals(market_data)
    
    # Update performance metrics
    for signal in signals:
        await manager.update_strategy_performance(
            name,
            signal.symbol,
            Decimal("100.0"),  # PnL
            Decimal("0.02")    # Return
        )
    
    # Verify performance metrics
    performance = await manager.get_strategy_performance(name)
    assert isinstance(performance, dict)
    assert "total_pnl" in performance
    assert "total_return" in performance
    assert "win_rate" in performance 