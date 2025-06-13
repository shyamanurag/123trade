"""
Test script for TrueData connection and functionality
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
import pandas as pd
from truedata_provider import TrueDataProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_connection(provider: TrueDataProvider) -> bool:
    """Test basic connection"""
    try:
        is_connected = await provider.connect()
        if is_connected:
            logger.info("✅ Connection test passed")
            return True
        else:
            logger.error("❌ Connection test failed")
            return False
    except Exception as e:
        logger.error(f"❌ Connection test failed with error: {e}")
        return False

async def test_symbol_subscription(provider: TrueDataProvider, symbols: list) -> bool:
    """Test symbol subscription"""
    try:
        req_ids = await provider.subscribe_symbols(symbols)
        if req_ids:
            logger.info(f"✅ Subscription test passed for symbols: {symbols}")
            return True
        else:
            logger.error("❌ Subscription test failed")
            return False
    except Exception as e:
        logger.error(f"❌ Subscription test failed with error: {e}")
        return False

async def test_market_data(provider: TrueDataProvider, symbol: str) -> bool:
    """Test market data retrieval"""
    try:
        data = await provider.get_market_data(symbol, '5min')
        if data and 'spot' in data:
            logger.info(f"✅ Market data test passed for {symbol}")
            logger.info(f"Current price: {data['spot']}")
            return True
        else:
            logger.error("❌ Market data test failed")
            return False
    except Exception as e:
        logger.error(f"❌ Market data test failed with error: {e}")
        return False

async def test_option_chain(provider: TrueDataProvider, underlying: str) -> bool:
    """Test option chain retrieval"""
    try:
        # Get next expiry date
        next_expiry = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        chain = await provider.get_option_chain(underlying, next_expiry)
        if not chain.empty:
            logger.info(f"✅ Option chain test passed for {underlying}")
            logger.info(f"Chain shape: {chain.shape}")
            return True
        else:
            logger.error("❌ Option chain test failed")
            return False
    except Exception as e:
        logger.error(f"❌ Option chain test failed with error: {e}")
        return False

async def test_real_time_data(provider: TrueDataProvider, symbol: str) -> bool:
    """Test real-time data callback"""
    try:
        data_received = False
        
        def callback(data):
            nonlocal data_received
            logger.info(f"Received real-time data for {symbol}: {data}")
            data_received = True
        
        await provider.subscribe_symbols([symbol], callback)
        
        # Wait for data
        for _ in range(10):  # Try for 10 seconds
            if data_received:
                logger.info(f"✅ Real-time data test passed for {symbol}")
                return True
            await asyncio.sleep(1)
        
        logger.error("❌ Real-time data test failed - no data received")
        return False
    except Exception as e:
        logger.error(f"❌ Real-time data test failed with error: {e}")
        return False

async def run_tests():
    """Run all tests"""
    # Configuration - using environment variables for security
    config = {
        'username': os.getenv('TRUEDATA_USERNAME', 'test_user'),
        'password': os.getenv('TRUEDATA_PASSWORD', 'test_password'),
        'live_port': int(os.getenv('TRUEDATA_PORT', '8086')),
        'log_level': logging.INFO,
        'url': os.getenv('TRUEDATA_URL', 'push.truedata.in'),
        'is_sandbox': os.getenv('TRUEDATA_SANDBOX', 'true').lower() == 'true',
        'sandbox_max_symbols': int(os.getenv('TRUEDATA_MAX_SYMBOLS', '5')),
        'sandbox_allowed_symbols': ['NIFTY-I', 'BANKNIFTY-I', 'RELIANCE', 'TCS', 'INFY'],
        'max_connection_attempts': 3,
        'reconnect_delay': 5,
        'heartbeat_interval': 30,
        'connection_timeout': 60
    }
    
    # Validate required environment variables
    if config['username'] == 'test_user' or config['password'] == 'test_password':
        logger.warning("⚠️ Using default test credentials. Set TRUEDATA_USERNAME and TRUEDATA_PASSWORD environment variables for actual testing.")
    
    # Initialize provider
    provider = TrueDataProvider(config)
    
    # Run tests
    tests = [
        ("Connection Test", test_connection(provider)),
        ("Symbol Subscription Test", test_symbol_subscription(provider, ['NIFTY-I', 'BANKNIFTY-I'])),
        ("Market Data Test", test_market_data(provider, 'NIFTY-I')),
        ("Option Chain Test", test_option_chain(provider, 'NIFTY')),
        ("Real-time Data Test", test_real_time_data(provider, 'NIFTY-I'))
    ]
    
    # Print results
    print("\n=== Test Results ===")
    for test_name, result in tests:
        status = "✅ PASSED" if await result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    # Cleanup
    await provider.disconnect()

if __name__ == "__main__":
    asyncio.run(run_tests()) 