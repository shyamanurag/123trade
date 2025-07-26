#!/usr/bin/env python3
"""
Test Production Deployment - Fixed Endpoints
============================================
Test with correct API endpoints based on the production logs
"""

import requests
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Production URL
PRODUCTION_URL = "https://trade123-l3zp7.ondigitalocean.app"

def test_system_status():
    """Test system status endpoint"""
    logger.info("🔍 Testing System Status")
    logger.info("=" * 40)
    
    try:
        response = requests.get(f"{PRODUCTION_URL}/api/system/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            logger.info("✅ System status accessible")
            logger.info(f"📊 Status: {json.dumps(data, indent=2)}")
            return True
        else:
            logger.warning(f"⚠️ System status returned: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ System status error: {e}")
        return False

def test_trading_control():
    """Test trading control endpoints"""
    logger.info("\n🎯 Testing Trading Control")
    logger.info("=" * 40)
    
    try:
        # Test trading control status
        response = requests.get(f"{PRODUCTION_URL}/api/v1/control/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            logger.info("✅ Trading control accessible")
            logger.info(f"📊 Control Status: {json.dumps(data, indent=2)}")
            return True
        else:
            logger.warning(f"⚠️ Trading control returned: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Trading control error: {e}")
        return False

def test_market_data_correct():
    """Test market data with correct endpoint"""
    logger.info("\n📈 Testing Market Data (Correct Endpoint)")
    logger.info("=" * 40)
    
    endpoints_to_try = [
        "/api/market-data/proxy",
        "/api/v1/market-data/proxy", 
        "/api/truedata/proxy",
        "/api/v1/truedata/proxy"
    ]
    
    for endpoint in endpoints_to_try:
        try:
            response = requests.get(f"{PRODUCTION_URL}{endpoint}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Market data found at: {endpoint}")
                
                if isinstance(data, dict) and 'data' in data:
                    market_data = data['data']
                    logger.info(f"📊 Market data for {len(market_data)} symbols")
                    
                    # Show sample data
                    sample_symbols = list(market_data.keys())[:3]
                    for symbol in sample_symbols:
                        symbol_data = market_data[symbol]
                        if isinstance(symbol_data, dict) and 'ltp' in symbol_data:
                            logger.info(f"   {symbol}: ₹{symbol_data['ltp']}")
                    
                    return True
                else:
                    logger.info(f"📊 Response: {json.dumps(data, indent=2)}")
                    return True
            else:
                logger.debug(f"❌ {endpoint}: {response.status_code}")
        except Exception as e:
            logger.debug(f"❌ {endpoint}: {e}")
    
    logger.warning("⚠️ No working market data endpoint found")
    return False

def test_positions_correct():
    """Test positions with correct format"""
    logger.info("\n📊 Testing Positions (Fixed Format)")
    logger.info("=" * 40)
    
    try:
        response = requests.get(f"{PRODUCTION_URL}/api/v1/positions", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            logger.info("✅ Positions endpoint accessible")
            
            # Handle different response formats
            if isinstance(data, list):
                logger.info(f"📊 Found {len(data)} positions (list format)")
                
                for position in data[:3]:  # Show first 3
                    if isinstance(position, dict):
                        symbol = position.get('symbol', 'Unknown')
                        entry_price = position.get('entry_price', 0)
                        current_price = position.get('current_price', 0)
                        pnl = position.get('unrealized_pnl', 0)
                        
                        logger.info(f"   {symbol}:")
                        logger.info(f"     Entry: ₹{entry_price}")
                        logger.info(f"     Current: ₹{current_price}")
                        logger.info(f"     P&L: ₹{pnl}")
                        
                        # Check P&L status
                        if current_price != entry_price:
                            logger.info(f"     ✅ Price updated")
                        else:
                            logger.warning(f"     ⚠️ Price = Entry price")
                        
                        if pnl != 0:
                            logger.info(f"     ✅ P&L non-zero")
                        else:
                            logger.warning(f"     ⚠️ P&L is zero")
                
                return True
                
            elif isinstance(data, dict):
                logger.info(f"📊 Positions response: {json.dumps(data, indent=2)}")
                return True
            else:
                logger.info(f"📊 Unexpected format: {type(data)}")
                return False
        else:
            logger.error(f"❌ Positions endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Positions test error: {e}")
        return False

def test_orchestrator_health():
    """Test if orchestrator is running via indirect methods"""
    logger.info("\n🎯 Testing Orchestrator Health (Indirect)")
    logger.info("=" * 40)
    
    # Try different orchestrator-related endpoints
    endpoints_to_try = [
        "/api/v1/strategies",
        "/api/v1/autonomous/status", 
        "/api/v1/control/orchestrator",
        "/api/system/orchestrator"
    ]
    
    orchestrator_working = False
    
    for endpoint in endpoints_to_try:
        try:
            response = requests.get(f"{PRODUCTION_URL}{endpoint}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Orchestrator-related endpoint working: {endpoint}")
                logger.info(f"📊 Response: {json.dumps(data, indent=2)}")
                orchestrator_working = True
                break
            else:
                logger.debug(f"❌ {endpoint}: {response.status_code}")
        except Exception as e:
            logger.debug(f"❌ {endpoint}: {e}")
    
    if not orchestrator_working:
        logger.warning("⚠️ No orchestrator endpoints responding")
    
    return orchestrator_working

def check_pnl_fix_status():
    """Check if P&L fix is working by looking for signs"""
    logger.info("\n🔍 Checking P&L Fix Status")
    logger.info("=" * 40)
    
    # Check if we can find any evidence of the fix working
    try:
        # Test if trades show updated prices
        response = requests.get(f"{PRODUCTION_URL}/api/v1/trades/live", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                logger.info(f"📊 Found {len(data)} trades")
                
                # Look for trades with non-zero P&L
                pnl_working = False
                price_updates = False
                
                for trade in data[:5]:  # Check first 5 trades
                    if isinstance(trade, dict):
                        symbol = trade.get('symbol', 'Unknown')
                        entry_price = trade.get('entry_price', 0)
                        current_price = trade.get('current_price', 0)
                        pnl = trade.get('unrealized_pnl', 0)
                        
                        logger.info(f"   {symbol}: Entry ₹{entry_price} → Current ₹{current_price} → P&L ₹{pnl}")
                        
                        if current_price != entry_price:
                            price_updates = True
                        
                        if pnl != 0:
                            pnl_working = True
                
                if price_updates:
                    logger.info("✅ Price updates detected")
                else:
                    logger.warning("⚠️ No price updates detected")
                
                if pnl_working:
                    logger.info("✅ P&L calculations working")
                else:
                    logger.warning("⚠️ All P&L values are zero")
                
                return price_updates and pnl_working
            else:
                logger.info("ℹ️ No trades found to check P&L")
                return True
        else:
            logger.error(f"❌ Trades endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ P&L check error: {e}")
        return False

def main():
    """Main test function"""
    logger.info("🚀 TESTING PRODUCTION DEPLOYMENT - FIXED")
    logger.info("=" * 60)
    logger.info(f"🌐 Production URL: {PRODUCTION_URL}")
    logger.info(f"⏰ Test Time: {datetime.now()}")
    
    # Run tests
    tests = [
        ("System Status", test_system_status),
        ("Trading Control", test_trading_control),
        ("Market Data", test_market_data_correct),
        ("Positions", test_positions_correct),
        ("Orchestrator Health", test_orchestrator_health),
        ("P&L Fix Status", check_pnl_fix_status)
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
    logger.info("📊 PRODUCTION TEST RESULTS")
    logger.info("="*60)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} {test_name}")
        if result:
            passed += 1
    
    logger.info(f"\n🎯 OVERALL: {passed}/{total} tests passed")
    
    # Analysis
    logger.info("\n🔍 ANALYSIS:")
    
    if results.get("System Status"):
        logger.info("✅ System is responding")
    else:
        logger.warning("⚠️ System status issues")
    
    if results.get("Trading Control"):
        logger.info("✅ Trading control working")
    else:
        logger.warning("⚠️ Trading control issues")
    
    if results.get("Orchestrator Health"):
        logger.info("✅ Orchestrator appears to be working")
    else:
        logger.warning("⚠️ Orchestrator may not be running")
    
    if results.get("P&L Fix Status"):
        logger.info("✅ P&L fix appears to be working")
    else:
        logger.warning("⚠️ P&L fix may not be active")
    
    # Final verdict
    if passed >= 4:
        logger.info("\n🎉 PRODUCTION DEPLOYMENT LOOKS GOOD!")
    elif passed >= 2:
        logger.info("\n⚠️ PRODUCTION DEPLOYMENT PARTIALLY WORKING")
    else:
        logger.error("\n❌ PRODUCTION DEPLOYMENT HAS ISSUES")

if __name__ == "__main__":
    main()
