"""
Connection Monitoring Test Script
Tests broker and data feed connections, health checks, and reconnection logic
"""

import asyncio
import logging
from datetime import datetime, timedelta
import json
from pathlib import Path
import yaml
import redis.asyncio as redis
from typing import Dict, Optional, Tuple
import time

from core.orchestrator import TradingOrchestrator
from core.connection_manager import ConnectionState, ConnectionHealth
from brokers.zerodha import ZerodhaConnection
from data.truedata import TrueDataConnection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_CONFIG = {
    'broker': {
        'zerodha': {
            'api_key': 'sylcoq492qz6f7ej',
            'api_secret': 'test_api_secret',
            'max_reconnect_attempts': 3,
            'reconnect_delay': 1,
            'health_check_interval': 5
        }
    },
    'data': {
        'truedata': {
            'api_key': 'test_api_key',
            'max_reconnect_attempts': 3,
            'reconnect_delay': 1,
            'health_check_interval': 5
        }
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

async def test_zerodha_connection(orchestrator: TradingOrchestrator):
    """Test Zerodha connection and health monitoring"""
    try:
        # Get initial health
        health = orchestrator.broker_connection.get_health()
        assert health.state == ConnectionState.CONNECTED, "Should be connected initially"
        
        # Test connection metrics
        assert health.uptime_seconds >= 0, "Uptime should be non-negative"
        assert health.latency_ms >= 0, "Latency should be non-negative"
        assert health.last_error is None, "Should have no errors initially"
        
        # Test reconnection
        await orchestrator.broker_connection.disconnect()
        assert orchestrator.broker_connection.get_health().state == ConnectionState.DISCONNECTED, \
            "Should be disconnected after disconnect()"
        
        await orchestrator.broker_connection.connect()
        assert orchestrator.broker_connection.get_health().state == ConnectionState.CONNECTED, \
            "Should be connected after connect()"
        
        # Test error handling
        await orchestrator.broker_connection._simulate_error("Test error")
        health = orchestrator.broker_connection.get_health()
        assert health.last_error == "Test error", "Should record error"
        assert health.state == ConnectionState.RECONNECTING, "Should be reconnecting after error"
        
        logger.info("✓ Zerodha connection tests passed")
        return True
    except Exception as e:
        logger.error(f"Zerodha connection test failed: {e}")
        return False

async def test_truedata_connection(orchestrator: TradingOrchestrator):
    """Test TrueData connection and health monitoring"""
    try:
        # Get initial health
        health = orchestrator.data_connection.get_health()
        assert health.state == ConnectionState.CONNECTED, "Should be connected initially"
        
        # Test connection metrics
        assert health.uptime_seconds >= 0, "Uptime should be non-negative"
        assert health.latency_ms >= 0, "Latency should be non-negative"
        assert health.last_error is None, "Should have no errors initially"
        
        # Test reconnection
        await orchestrator.data_connection.disconnect()
        assert orchestrator.data_connection.get_health().state == ConnectionState.DISCONNECTED, \
            "Should be disconnected after disconnect()"
        
        await orchestrator.data_connection.connect()
        assert orchestrator.data_connection.get_health().state == ConnectionState.CONNECTED, \
            "Should be connected after connect()"
        
        # Test error handling
        await orchestrator.data_connection._simulate_error("Test error")
        health = orchestrator.data_connection.get_health()
        assert health.last_error == "Test error", "Should record error"
        assert health.state == ConnectionState.RECONNECTING, "Should be reconnecting after error"
        
        logger.info("✓ TrueData connection tests passed")
        return True
    except Exception as e:
        logger.error(f"TrueData connection test failed: {e}")
        return False

async def test_connection_resilience(orchestrator: TradingOrchestrator):
    """Test connection resilience and recovery"""
    try:
        # Test broker connection resilience
        await orchestrator.broker_connection.disconnect()
        await asyncio.sleep(1)
        await orchestrator.broker_connection.ensure_connection()
        assert orchestrator.broker_connection.get_health().state == ConnectionState.CONNECTED, \
            "Should recover broker connection"
        
        # Test data connection resilience
        await orchestrator.data_connection.disconnect()
        await asyncio.sleep(1)
        await orchestrator.data_connection.ensure_connection()
        assert orchestrator.data_connection.get_health().state == ConnectionState.CONNECTED, \
            "Should recover data connection"
        
        # Test simultaneous disconnection
        await orchestrator.broker_connection.disconnect()
        await orchestrator.data_connection.disconnect()
        await asyncio.sleep(1)
        await orchestrator.ensure_all_connections()
        
        broker_health = orchestrator.broker_connection.get_health()
        data_health = orchestrator.data_connection.get_health()
        
        assert broker_health.state == ConnectionState.CONNECTED, "Should recover broker connection"
        assert data_health.state == ConnectionState.CONNECTED, "Should recover data connection"
        
        logger.info("✓ Connection resilience tests passed")
        return True
    except Exception as e:
        logger.error(f"Connection resilience test failed: {e}")
        return False

async def test_health_monitoring(orchestrator: TradingOrchestrator):
    """Test health monitoring and metrics"""
    try:
        # Start health monitoring
        await orchestrator.start_health_monitoring()
        await asyncio.sleep(2)  # Wait for some metrics to be collected
        
        # Check broker health metrics
        broker_health = orchestrator.broker_connection.get_health()
        assert broker_health.uptime_seconds > 0, "Should track uptime"
        assert broker_health.latency_ms >= 0, "Should track latency"
        assert broker_health.reconnect_attempts >= 0, "Should track reconnect attempts"
        
        # Check data health metrics
        data_health = orchestrator.data_connection.get_health()
        assert data_health.uptime_seconds > 0, "Should track uptime"
        assert data_health.latency_ms >= 0, "Should track latency"
        assert data_health.reconnect_attempts >= 0, "Should track reconnect attempts"
        
        # Test health status aggregation
        overall_health = await orchestrator.get_system_health()
        assert 'broker' in overall_health, "Should include broker health"
        assert 'data' in overall_health, "Should include data health"
        assert overall_health['status'] in ['healthy', 'degraded', 'critical'], \
            "Should have valid health status"
        
        logger.info("✓ Health monitoring tests passed")
        return True
    except Exception as e:
        logger.error(f"Health monitoring test failed: {e}")
        return False

async def run_tests():
    """Run all connection tests"""
    try:
        # Set up test environment
        config, redis_client = await setup_test_environment()
        
        # Initialize orchestrator
        orchestrator = TradingOrchestrator(config)
        await orchestrator.initialize()
        
        # Run tests
        tests = [
            ("Zerodha Connection", test_zerodha_connection(orchestrator)),
            ("TrueData Connection", test_truedata_connection(orchestrator)),
            ("Connection Resilience", test_connection_resilience(orchestrator)),
            ("Health Monitoring", test_health_monitoring(orchestrator))
        ]
        
        # Print results
        print("\nConnection Test Results:")
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
        await orchestrator.shutdown()
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