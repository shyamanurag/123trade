#!/usr/bin/env python3
"""
Test Production Deployment
==========================
Test the deployed app to verify P&L fixes and orchestrator status
WITHOUT touching ShareKhan
"""

import requests
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Production URL
PRODUCTION_URL = "https://trade123-l3zp7.ondigitalocean.app"

def test_app_health():
    """Test basic app health"""
    logger.info("🏥 Testing App Health")
    logger.info("=" * 40)
    
    try:
        # Test health endpoint
        response = requests.get(f"{PRODUCTION_URL}/ready", timeout=10)
        if response.status_code == 200:
            logger.info("✅ App is running and responding")
            return True
        else:
            logger.error(f"❌ App health check failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ App health check error: {e}")
        return False

def test_orchestrator_status():
    """Test orchestrator status"""
    logger.info("\n🎯 Testing Orchestrator Status")
    logger.info("=" * 40)
    
    try:
        # Test orchestrator debug endpoint
        response = requests.get(f"{PRODUCTION_URL}/api/v1/orchestrator/status", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            logger.info("✅ Orchestrator endpoint accessible")
            logger.info(f"📊 Response: {json.dumps(data, indent=2)}")
            
            # Check if orchestrator is running
            if data.get('status') == 'running':
                logger.info("✅ Orchestrator is running")
                return True
            else:
                logger.warning(f"⚠️ Orchestrator status: {data.get('status', 'unknown')}")
                return False
        else:
            logger.error(f"❌ Orchestrator status check failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Orchestrator status error: {e}")
        return False

def test_position_tracker():
    """Test position tracker and P&L"""
    logger.info("\n📊 Testing Position Tracker & P&L")
    logger.info("=" * 40)
    
    try:
        # Test positions endpoint
        response = requests.get(f"{PRODUCTION_URL}/api/v1/positions", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            logger.info("✅ Positions endpoint accessible")
            
            if isinstance(data, dict) and 'positions' in data:
                positions = data['positions']
                logger.info(f"📊 Found {len(positions)} positions")
                
                # Check for non-zero P&L
                for symbol, position in positions.items():
                    if isinstance(position, dict):
                        current_price = position.get('current_price', 0)
                        entry_price = position.get('average_price', 0)
                        pnl = position.get('unrealized_pnl', 0)
                        
                        logger.info(f"   {symbol}:")
                        logger.info(f"     Entry: ₹{entry_price}")
                        logger.info(f"     Current: ₹{current_price}")
                        logger.info(f"     P&L: ₹{pnl}")
                        
                        # Check if P&L is being calculated
                        if current_price != entry_price:
                            logger.info(f"     ✅ Price updated (not equal to entry)")
                        else:
                            logger.warning(f"     ⚠️ Current price equals entry price")
                        
                        if pnl != 0:
                            logger.info(f"     ✅ P&L is non-zero")
                        else:
                            logger.warning(f"     ⚠️ P&L is zero")
                
                return len(positions) > 0
            else:
                logger.info("ℹ️ No positions found")
                return True
        else:
            logger.error(f"❌ Positions endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Position tracker test error: {e}")
        return False

def test_market_data():
    """Test market data availability (without ShareKhan)"""
    logger.info("\n📈 Testing Market Data Availability")
    logger.info("=" * 40)
    
    try:
        # Test market data proxy endpoint
        response = requests.get(f"{PRODUCTION_URL}/api/market-data/proxy", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            logger.info("✅ Market data endpoint accessible")
            
            if isinstance(data, dict) and 'data' in data:
                market_data = data['data']
                logger.info(f"📊 Market data available for {len(market_data)} symbols")
                
                # Show sample data
                sample_symbols = list(market_data.keys())[:3]
                for symbol in sample_symbols:
                    symbol_data = market_data[symbol]
                    if isinstance(symbol_data, dict) and 'ltp' in symbol_data:
                        logger.info(f"   {symbol}: ₹{symbol_data['ltp']}")
                
                return len(market_data) > 0
            else:
                logger.warning("⚠️ No market data found")
                return False
        else:
            logger.error(f"❌ Market data endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Market data test error: {e}")
        return False

def test_trades_endpoint():
    """Test trades endpoint for live data"""
    logger.info("\n💼 Testing Trades Endpoint")
    logger.info("=" * 40)
    
    try:
        # Test live trades endpoint
        response = requests.get(f"{PRODUCTION_URL}/api/v1/trades/live", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            logger.info("✅ Trades endpoint accessible")
            
            if isinstance(data, list):
                logger.info(f"📊 Found {len(data)} trades")
                
                # Check recent trades for P&L
                for trade in data[:3]:  # Show first 3 trades
                    if isinstance(trade, dict):
                        symbol = trade.get('symbol', 'Unknown')
                        entry_price = trade.get('entry_price', 0)
                        current_price = trade.get('current_price', 0)
                        pnl = trade.get('unrealized_pnl', 0)
                        
                        logger.info(f"   {symbol}:")
                        logger.info(f"     Entry: ₹{entry_price}")
                        logger.info(f"     Current: ₹{current_price}")
                        logger.info(f"     P&L: ₹{pnl}")
                
                return True
            else:
                logger.info("ℹ️ No trades found")
                return True
        else:
            logger.error(f"❌ Trades endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Trades test error: {e}")
        return False

def main():
    """Main test function"""
    logger.info("🚀 TESTING PRODUCTION DEPLOYMENT")
    logger.info("=" * 60)
    logger.info(f"🌐 Production URL: {PRODUCTION_URL}")
    logger.info(f"⏰ Test Time: {datetime.now()}")
    
    # Run tests
    tests = [
        ("App Health", test_app_health),
        ("Orchestrator Status", test_orchestrator_status),
        ("Position Tracker & P&L", test_position_tracker),
        ("Market Data", test_market_data),
        ("Trades Endpoint", test_trades_endpoint)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*60}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ {test_name} test failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("📊 TEST RESULTS SUMMARY")
    logger.info("="*60)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} {test_name}")
        if result:
            passed += 1
    
    logger.info(f"\n🎯 OVERALL: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED - Deployment is working!")
    elif passed >= total * 0.8:
        logger.info("⚠️ MOSTLY WORKING - Some issues need attention")
    else:
        logger.error("❌ DEPLOYMENT ISSUES - Multiple failures detected")
    
    # Specific P&L guidance
    logger.info("\n🔍 P&L FIX STATUS:")
    if results.get("Orchestrator Status"):
        logger.info("✅ Orchestrator running - P&L fix should be active")
    else:
        logger.warning("⚠️ Orchestrator not running - P&L fix not active")
    
    if results.get("Position Tracker & P&L"):
        logger.info("✅ Position tracker accessible - check P&L values")
    else:
        logger.warning("⚠️ Position tracker issues - P&L may not update")
    
    if results.get("Market Data"):
        logger.info("✅ Market data available - prices should update")
    else:
        logger.warning("⚠️ Market data issues - prices may not update")

if __name__ == "__main__":
    main()
