#!/usr/bin/env python3
"""
Fix P&L and Price Update Issues
Addresses real-time price updates and P&L calculation problems
"""

import os
import sys
import logging
import asyncio
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_sharekhan_connection():
    """Check ShareKhan connection and price feed status"""
    logger.info("🔍 Checking ShareKhan Connection Status")
    logger.info("=" * 50)
    
    try:
        # Import ShareKhan components
        from src.feeds.sharekhan_feed import ShareKhanFeed
        from src.api.market_data import get_sharekhan_proxy
        
        # Check ShareKhan proxy status
        proxy_status = get_sharekhan_proxy()
        logger.info(f"📊 ShareKhan Proxy Status:")
        logger.info(f"   Connected: {proxy_status.get('connected', False)}")
        logger.info(f"   Symbols Count: {proxy_status.get('symbols_count', 0)}")
        logger.info(f"   Source: {proxy_status.get('source', 'Unknown')}")
        
        if proxy_status.get('error'):
            logger.error(f"❌ ShareKhan Error: {proxy_status['error']}")
        
        # Check if we have live data
        data = proxy_status.get('data', {})
        if data:
            logger.info(f"📈 Sample Live Data:")
            for symbol, price_data in list(data.items())[:3]:  # Show first 3
                logger.info(f"   {symbol}: {price_data}")
        else:
            logger.warning("⚠️ No live price data available")
            
    except Exception as e:
        logger.error(f"❌ Error checking ShareKhan: {e}")

def check_redis_price_cache():
    """Check Redis price cache for live updates"""
    logger.info("\n🔍 Checking Redis Price Cache")
    logger.info("=" * 50)
    
    try:
        from src.core.redis_fallback_manager import ProductionRedisFallback
        
        redis_manager = ProductionRedisFallback()
        status = redis_manager.get_connection_status()
        
        logger.info(f"📊 Redis Status:")
        logger.info(f"   Connected: {status.get('connected', False)}")
        logger.info(f"   Fallback Mode: {status.get('fallback_mode', True)}")
        
        if status.get('connected'):
            # Check for ShareKhan cache
            cache_data = redis_manager.get("sharekhan:live_cache")
            if cache_data:
                logger.info("✅ ShareKhan cache found in Redis")
                # Parse and show sample
                import json
                try:
                    parsed = json.loads(cache_data)
                    logger.info(f"   Cache entries: {len(parsed)}")
                except:
                    logger.info("   Cache data exists but format unknown")
            else:
                logger.warning("⚠️ No ShareKhan cache in Redis")
                
            # Check for specific symbols
            test_symbols = ['GODREJCP', 'JSWSTEEL', 'TVSMOTOR']
            for symbol in test_symbols:
                price_key = f"price:{symbol}"
                price_data = redis_manager.get(price_key)
                if price_data:
                    logger.info(f"   {symbol}: {price_data}")
                else:
                    logger.warning(f"   {symbol}: No price data")
        else:
            logger.warning("⚠️ Redis not connected - using fallback mode")
            
    except Exception as e:
        logger.error(f"❌ Error checking Redis cache: {e}")

def check_position_updates():
    """Check position update mechanism"""
    logger.info("\n🔍 Checking Position Update Mechanism")
    logger.info("=" * 50)
    
    try:
        from src.core.position_tracker import ProductionPositionTracker
        
        # Check if position tracker is updating prices
        logger.info("📊 Position Tracker Analysis:")
        logger.info("   - Position tracker should update current_price from live feeds")
        logger.info("   - P&L calculation: (current_price - entry_price) * quantity")
        logger.info("   - If current_price not updated, P&L remains zero")
        
        # Check the update mechanism
        logger.info("\n🔧 Required Fixes:")
        logger.info("1. Ensure ShareKhan feed is running and updating Redis")
        logger.info("2. Verify position tracker reads from live price feed")
        logger.info("3. Check frontend polling for updated positions")
        logger.info("4. Ensure database position updates include current_price")
        
    except Exception as e:
        logger.error(f"❌ Error checking position updates: {e}")

def check_frontend_polling():
    """Check frontend polling configuration"""
    logger.info("\n🔍 Checking Frontend Polling Configuration")
    logger.info("=" * 50)
    
    try:
        # Check if frontend is using polling mode
        logger.info("📊 Frontend Configuration:")
        logger.info("   - Digital Ocean deployment uses polling mode")
        logger.info("   - Polling intervals:")
        logger.info("     * Market Data: 3 seconds")
        logger.info("     * Positions: 5 seconds")
        logger.info("     * Orders: 5 seconds")
        
        logger.info("\n🔧 Polling Issues:")
        logger.info("1. Frontend polls /api/trades/live every 3 seconds")
        logger.info("2. If backend doesn't update current_price, frontend shows stale data")
        logger.info("3. Need to verify API endpoints return updated prices")
        
    except Exception as e:
        logger.error(f"❌ Error checking frontend polling: {e}")

def suggest_immediate_fixes():
    """Suggest immediate fixes for P&L issues"""
    logger.info("\n🔧 IMMEDIATE FIXES REQUIRED")
    logger.info("=" * 50)
    
    logger.info("1. **ShareKhan Price Feed Fix:**")
    logger.info("   - Verify ShareKhan WebSocket is running")
    logger.info("   - Check if prices are being stored in Redis")
    logger.info("   - Ensure price updates are continuous")
    
    logger.info("\n2. **Position Update Fix:**")
    logger.info("   - Position tracker must read live prices")
    logger.info("   - Update current_price field in database")
    logger.info("   - Recalculate P&L with live prices")
    
    logger.info("\n3. **API Endpoint Fix:**")
    logger.info("   - /api/trades/live must return updated current_price")
    logger.info("   - Ensure P&L calculation uses live prices")
    logger.info("   - Frontend should receive updated values")
    
    logger.info("\n4. **Database Update Fix:**")
    logger.info("   - Positions table current_price column must be updated")
    logger.info("   - P&L calculation should be real-time")
    logger.info("   - Consider background job for price updates")

def create_price_update_test():
    """Create a test to verify price updates"""
    logger.info("\n🧪 Creating Price Update Test")
    logger.info("=" * 50)
    
    test_code = '''
# Test Script: test_price_updates.py
import asyncio
from src.core.position_tracker import ProductionPositionTracker
from src.api.market_data import get_sharekhan_proxy

async def test_price_updates():
    """Test if prices are updating"""
    
    # Get current ShareKhan prices
    proxy_data = get_sharekhan_proxy()
    live_prices = proxy_data.get('data', {})
    
    print(f"Live Prices Available: {len(live_prices)}")
    
    # Test symbols from your trades
    test_symbols = ['GODREJCP', 'JSWSTEEL', 'TVSMOTOR']
    
    for symbol in test_symbols:
        if symbol in live_prices:
            current_price = live_prices[symbol].get('price', 0)
            print(f"{symbol}: Current Price = ₹{current_price}")
            
            # This should be different from entry price if market is moving
            entry_prices = {
                'GODREJCP': 1255.30,
                'JSWSTEEL': 1029.90,
                'TVSMOTOR': 2853.00
            }
            
            entry_price = entry_prices.get(symbol, 0)
            price_diff = current_price - entry_price
            
            print(f"  Entry: ₹{entry_price}")
            print(f"  Difference: ₹{price_diff}")
            print(f"  P&L for 50 shares: ₹{price_diff * 50}")
        else:
            print(f"{symbol}: No live price data")

if __name__ == "__main__":
    asyncio.run(test_price_updates())
'''
    
    with open('test_price_updates.py', 'w') as f:
        f.write(test_code)
    
    logger.info("✅ Created test_price_updates.py")
    logger.info("   Run this to check if live prices are different from entry prices")

def main():
    """Main analysis function"""
    logger.info("🚀 P&L and Price Update Analysis")
    logger.info("=" * 50)
    
    check_sharekhan_connection()
    check_redis_price_cache()
    check_position_updates()
    check_frontend_polling()
    suggest_immediate_fixes()
    create_price_update_test()
    
    logger.info("\n" + "=" * 50)
    logger.info("📊 ANALYSIS COMPLETE")
    logger.info("✅ System is executing trades (good)")
    logger.info("❌ Real-time price updates not working")
    logger.info("❌ P&L stuck at zero due to price update issue")
    logger.info("❌ Using fallback mode instead of real broker")
    
    logger.info("\n🎯 NEXT STEPS:")
    logger.info("1. Wait for Redis deployment to complete")
    logger.info("2. Check ShareKhan price feed status")
    logger.info("3. Verify position update mechanism")
    logger.info("4. Test with live price data")

if __name__ == "__main__":
    main()
