"""
Integration tests for the regime adaptive controller
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
    SignalMetadata
)
from core.exceptions import StrategyError
from strategies.regime_adaptive_controller import RegimeAdaptiveController

@pytest.fixture
def controller_config() -> Dict:
    """Create controller configuration"""
    return {
        "regime_thresholds": {
            "ULTRA_HIGH_VOL": {"vix": 25, "atr_ratio": 1.5},
            "TRENDING": {"adx": 30, "directional_movement": 0.7},
            "RANGE_BOUND": {"adx": 20, "atr_ratio": 0.5}
        },
        "allocation_adjustments": {
            "ULTRA_HIGH_VOL": {
                "volatility_explosion": 1.4,
                "momentum_surfer": 0.6,
                "volume_profile_scalper": 1.0,
                "news_impact_scalper": 1.0
            },
            "TRENDING": {
                "momentum_surfer": 1.4,
                "volume_profile_scalper": 1.2,
                "volatility_explosion": 0.7,
                "news_impact_scalper": 0.7
            },
            "RANGE_BOUND": {
                "volume_profile_scalper": 1.5,
                "volatility_explosion": 1.2,
                "momentum_surfer": 0.6,
                "news_impact_scalper": 0.7
            }
        }
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
async def test_regime_detection(controller_config: Dict, market_data: Dict):
    """Test regime detection"""
    controller = RegimeAdaptiveController(controller_config)
    
    # Test normal regime
    regime = await controller.detect_regime(market_data)
    assert regime == "NORMAL"
    
    # Test ultra high volatility regime
    market_data["vix"] = 30.0
    regime = await controller.detect_regime(market_data)
    assert regime == "ULTRA_HIGH_VOL"
    
    # Test trending regime
    market_data["vix"] = 20.0
    market_data["adx"] = 35.0
    regime = await controller.detect_regime(market_data)
    assert regime == "TRENDING"
    
    # Test range bound regime
    market_data["adx"] = 15.0
    regime = await controller.detect_regime(market_data)
    assert regime == "RANGE_BOUND"

@pytest.mark.asyncio
async def test_allocation_multipliers(controller_config: Dict):
    """Test allocation multipliers"""
    controller = RegimeAdaptiveController(controller_config)
    
    # Test ultra high volatility regime
    multiplier = controller.get_allocation_multiplier("volatility_explosion", "ULTRA_HIGH_VOL")
    assert multiplier == 1.4
    
    # Test trending regime
    multiplier = controller.get_allocation_multiplier("momentum_surfer", "TRENDING")
    assert multiplier == 1.4
    
    # Test range bound regime
    multiplier = controller.get_allocation_multiplier("volume_profile_scalper", "RANGE_BOUND")
    assert multiplier == 1.5
    
    # Test default multiplier
    multiplier = controller.get_allocation_multiplier("unknown_strategy", "NORMAL")
    assert multiplier == 1.0

@pytest.mark.asyncio
async def test_regime_history(controller_config: Dict, market_data: Dict):
    """Test regime history tracking"""
    controller = RegimeAdaptiveController(controller_config)
    
    # Initial state
    assert len(controller.regime_history) == 0
    
    # Change regime
    market_data["vix"] = 30.0
    await controller.detect_regime(market_data)
    assert len(controller.regime_history) == 1
    assert controller.regime_history[0]["regime"] == "ULTRA_HIGH_VOL"
    assert "timestamp" in controller.regime_history[0]
    assert "vix" in controller.regime_history[0]
    assert "adx" in controller.regime_history[0]
    
    # No change in regime
    await controller.detect_regime(market_data)
    assert len(controller.regime_history) == 1

@pytest.mark.asyncio
async def test_concurrent_regime_detection(controller_config: Dict, market_data: Dict):
    """Test concurrent regime detection"""
    controller = RegimeAdaptiveController(controller_config)
    
    async def detect_regime():
        return await controller.detect_regime(market_data)
    
    # Run multiple concurrent regime detections
    tasks = [detect_regime() for _ in range(5)]
    results = await asyncio.gather(*tasks)
    
    # All results should be the same
    assert all(r == results[0] for r in results)
    assert len(controller.regime_history) <= 1

@pytest.mark.asyncio
async def test_signal_generation(controller_config: Dict, market_data: Dict):
    """Test signal generation"""
    controller = RegimeAdaptiveController(controller_config)
    
    # Meta-strategy doesn't generate direct signals
    signals = await controller.generate_signals(market_data)
    assert len(signals) == 0

@pytest.mark.asyncio
async def test_invalid_market_data(controller_config: Dict):
    """Test handling of invalid market data"""
    controller = RegimeAdaptiveController(controller_config)
    
    # Missing required fields
    with pytest.raises(StrategyError):
        await controller.detect_regime({})
    
    # Invalid data types
    with pytest.raises(StrategyError):
        await controller.detect_regime({
            "vix": "invalid",
            "adx": "invalid",
            "atr_ratio": "invalid"
        })

@pytest.mark.asyncio
async def test_regime_transitions(controller_config: Dict, market_data: Dict):
    """Test regime transitions"""
    controller = RegimeAdaptiveController(controller_config)
    
    # Start in normal regime
    regime = await controller.detect_regime(market_data)
    assert regime == "NORMAL"
    
    # Transition to ultra high volatility
    market_data["vix"] = 30.0
    regime = await controller.detect_regime(market_data)
    assert regime == "ULTRA_HIGH_VOL"
    assert len(controller.regime_history) == 1
    
    # Transition to trending
    market_data["vix"] = 20.0
    market_data["adx"] = 35.0
    regime = await controller.detect_regime(market_data)
    assert regime == "TRENDING"
    assert len(controller.regime_history) == 2
    
    # Transition to range bound
    market_data["adx"] = 15.0
    regime = await controller.detect_regime(market_data)
    assert regime == "RANGE_BOUND"
    assert len(controller.regime_history) == 3
    
    # Back to normal
    market_data["adx"] = 25.0
    regime = await controller.detect_regime(market_data)
    assert regime == "NORMAL"
    assert len(controller.regime_history) == 4 