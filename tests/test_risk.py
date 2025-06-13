"""
Risk Management Test Script
Tests drawdown tracking, volatility sizing, and blacklist functionality
"""

import asyncio
import logging
from datetime import datetime, timedelta
import json
from pathlib import Path
import yaml
import redis.asyncio as redis
from typing import Dict, Optional, Tuple

from risk.risk_manager import RiskManager
from risk.drawdown_tracker import DrawdownTracker
from risk.volatility_sizing import VolatilitySizing
from risk.blacklist import Blacklist

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_CONFIG = {
    'risk': {
        'max_drawdown': 0.05,  # 5% max drawdown
        'position_size_limit': 0.1,  # 10% of capital per position
        'volatility_window': 20,  # 20 days for volatility calculation
        'blacklist_threshold': 3,  # 3 violations for blacklisting
        'blacklist_duration': 24  # 24 hours blacklist duration
    },
    'redis': {
        'url': 'redis://localhost:6379'
    }
}

async def setup_test_environment() -> tuple[Dict, redis.Redis]:
    """Set up test environment with config and Redis"""
    try:
        # Initialize Redis
        redis_client = redis.from_url(TEST_CONFIG['redis']['url'], decode_responses=True)
        await redis_client.ping()
        logger.info("✓ Redis connection successful")
        
        return TEST_CONFIG, redis_client
    except Exception as e:
        logger.error(f"Failed to set up test environment: {e}")
        raise

async def test_drawdown_tracker(risk_manager: RiskManager):
    """Test drawdown tracking functionality"""
    try:
        # Test initial status
        initial_status = risk_manager.drawdown_tracker.get_status()
        assert initial_status['current_drawdown'] == 0, "Initial drawdown should be 0"
        
        # Simulate portfolio value changes
        test_values = [
            (1000000, 0),  # Initial value
            (1050000, 0),  # 5% gain
            (980000, 0.02),  # 2% drawdown
            (950000, 0.05),  # 5% drawdown
            (900000, 0.10)  # 10% drawdown (should trigger warning)
        ]
        
        for value, expected_drawdown in test_values:
            risk_manager.drawdown_tracker.update_portfolio_value(value)
            status = risk_manager.drawdown_tracker.get_status()
            assert abs(status['current_drawdown'] - expected_drawdown) < 0.001, \
                f"Drawdown calculation error: expected {expected_drawdown}, got {status['current_drawdown']}"
        
        # Test drawdown alerts
        alerts = risk_manager.drawdown_tracker.get_alerts()
        assert len(alerts) > 0, "Should have generated drawdown alerts"
        
        logger.info("✓ Drawdown tracking tests passed")
        return True
    except Exception as e:
        logger.error(f"Drawdown tracking test failed: {e}")
        return False

async def test_volatility_sizing(risk_manager: RiskManager):
    """Test volatility-based position sizing"""
    try:
        # Test data
        test_signals = [
            {
                'symbol': 'NIFTY24500CE',
                'quantity': 100,
                'price': 100,
                'volatility': 0.15  # 15% volatility
            },
            {
                'symbol': 'BANKNIFTY45000CE',
                'quantity': 50,
                'price': 200,
                'volatility': 0.25  # 25% volatility
            }
        ]
        
        capital = 1000000  # 1M capital
        
        for signal in test_signals:
            # Calculate position size
            position_size = await risk_manager.vol_sizing.calculate_position_size(
                signal,
                capital=capital,
                market_data={'volatility': signal['volatility']}
            )
            
            # Verify position size limits
            assert position_size <= capital * TEST_CONFIG['risk']['position_size_limit'], \
                "Position size exceeds limit"
            
            # Verify volatility adjustment
            if signal['volatility'] > 0.2:  # High volatility
                assert position_size < capital * 0.05, \
                    "High volatility position should be reduced"
        
        logger.info("✓ Volatility sizing tests passed")
        return True
    except Exception as e:
        logger.error(f"Volatility sizing test failed: {e}")
        return False

async def test_blacklist(risk_manager: RiskManager):
    """Test blacklist functionality"""
    try:
        test_symbols = ['TEST1', 'TEST2', 'TEST3']
        
        # Test initial state
        for symbol in test_symbols:
            is_blacklisted, reason = await risk_manager.blacklist.is_blacklisted(symbol)
            assert not is_blacklisted, "Symbol should not be blacklisted initially"
        
        # Test violation tracking
        for symbol in test_symbols:
            for _ in range(TEST_CONFIG['risk']['blacklist_threshold']):
                await risk_manager.blacklist.record_violation(symbol, "Test violation")
        
        # Verify blacklisting
        for symbol in test_symbols:
            is_blacklisted, reason = await risk_manager.blacklist.is_blacklisted(symbol)
            assert is_blacklisted, "Symbol should be blacklisted after violations"
            assert reason is not None, "Should provide blacklist reason"
        
        # Test blacklist expiration
        # Simulate time passing
        await asyncio.sleep(1)  # In real test, would use time travel
        await risk_manager.blacklist.cleanup_expired()
        
        # Verify cleanup
        for symbol in test_symbols:
            is_blacklisted, _ = await risk_manager.blacklist.is_blacklisted(symbol)
            assert not is_blacklisted, "Blacklist should be expired"
        
        logger.info("✓ Blacklist tests passed")
        return True
    except Exception as e:
        logger.error(f"Blacklist test failed: {e}")
        return False

async def test_risk_limits(risk_manager: RiskManager):
    """Test risk limit enforcement"""
    try:
        # Test position limits
        test_positions = [
            {'symbol': 'NIFTY24500CE', 'quantity': 1000, 'price': 100},
            {'symbol': 'BANKNIFTY45000CE', 'quantity': 500, 'price': 200}
        ]
        
        for position in test_positions:
            is_allowed = await risk_manager.check_position_limit(position)
            total_exposure = position['quantity'] * position['price']
            assert is_allowed == (total_exposure <= TEST_CONFIG['risk']['position_size_limit'] * 1000000), \
                "Position limit check failed"
        
        # Test concentration limits
        portfolio = {
            'NIFTY24500CE': 0.3,  # 30% exposure
            'BANKNIFTY45000CE': 0.4,  # 40% exposure
            'RELIANCE': 0.2  # 20% exposure
        }
        
        is_concentrated = await risk_manager.check_concentration_risk(portfolio)
        assert is_concentrated, "Should detect concentration risk"
        
        logger.info("✓ Risk limits tests passed")
        return True
    except Exception as e:
        logger.error(f"Risk limits test failed: {e}")
        return False

async def run_tests():
    """Run all risk management tests"""
    try:
        # Set up test environment
        config, redis_client = await setup_test_environment()
        
        # Initialize risk manager
        risk_manager = RiskManager(config, redis_client)
        await risk_manager.start()
        
        # Run tests
        tests = [
            ("Drawdown Tracking", test_drawdown_tracker(risk_manager)),
            ("Volatility Sizing", test_volatility_sizing(risk_manager)),
            ("Blacklist", test_blacklist(risk_manager)),
            ("Risk Limits", test_risk_limits(risk_manager))
        ]
        
        # Print results
        print("\nRisk Management Test Results:")
        print("=" * 50)
        all_passed = True
        for name, result in tests:
            status = "✓ PASSED" if await result else "✗ FAILED"
            print(f"{name}: {status}")
            if not await result:
                all_passed = False
        
        print("=" * 50)
        print(f"Overall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
        
        # Cleanup
        await risk_manager.stop()
        await redis_client.close()
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(run_tests())
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        exit(1) 