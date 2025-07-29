#!/usr/bin/env python3
"""
Test Position Updates
====================
Test script to verify position tracker is receiving price updates
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_position_updates():
    """Test position tracker updates"""
    logger.info("🧪 Testing Position Updates")
    logger.info("=" * 40)
    
    try:
        from src.core.position_tracker import get_position_tracker
        from src.api.market_data import get_sharekhan_proxy
        
        # Get position tracker
        position_tracker = await get_position_tracker()
        
        # Get current positions
        positions = await position_tracker.get_all_positions()
        logger.info(f"📊 Current positions: {len(positions)}")
        
        if not positions:
            logger.warning("⚠️ No positions found - creating test position")
            # Create a test position
            await position_tracker.update_position('RELIANCE', 50, 1473.0, 'long')
            positions = await position_tracker.get_all_positions()
        
        # Show current state
        logger.info("\n📈 Current Position State:")
        for symbol, position in positions.items():
            logger.info(f"  {symbol}:")
            logger.info(f"    Entry Price: ₹{position.average_price:.2f}")
            logger.info(f"    Current Price: ₹{position.current_price:.2f}")
            logger.info(f"    P&L: ₹{position.unrealized_pnl:.2f}")
            logger.info(f"    Last Updated: {position.last_updated}")
        
        # Get live market data
        logger.info("\n📊 Getting Live Market Data:")
        proxy_data = get_sharekhan_proxy()
        
        if proxy_data and proxy_data.get('data'):
            market_prices = {}
            for symbol, data in proxy_data['data'].items():
                if isinstance(data, dict) and 'ltp' in data:
                    ltp = data.get('ltp', 0)
                    if ltp and ltp > 0:
                        market_prices[symbol] = float(ltp)
            
            logger.info(f"  Available live prices: {len(market_prices)}")
            
            # Show sample prices
            for symbol, price in list(market_prices.items())[:5]:
                logger.info(f"    {symbol}: ₹{price}")
            
            # Update position tracker with live prices
            logger.info("\n🔄 Updating Position Tracker:")
            await position_tracker.update_market_prices(market_prices)
            
            # Show updated state
            logger.info("\n📈 Updated Position State:")
            updated_positions = await position_tracker.get_all_positions()
            
            for symbol, position in updated_positions.items():
                logger.info(f"  {symbol}:")
                logger.info(f"    Entry Price: ₹{position.average_price:.2f}")
                logger.info(f"    Current Price: ₹{position.current_price:.2f}")
                logger.info(f"    P&L: ₹{position.unrealized_pnl:.2f}")
                logger.info(f"    Last Updated: {position.last_updated}")
                
                # Check if price changed
                if symbol in market_prices:
                    live_price = market_prices[symbol]
                    if abs(position.current_price - live_price) < 0.01:
                        logger.info(f"    ✅ Price updated to live price")
                    else:
                        logger.warning(f"    ⚠️ Price not updated (Live: ₹{live_price})")
                
                # Check if P&L calculated
                expected_pnl = (position.current_price - position.average_price) * position.quantity
                if abs(position.unrealized_pnl - expected_pnl) < 0.01:
                    logger.info(f"    ✅ P&L calculated correctly")
                else:
                    logger.warning(f"    ⚠️ P&L calculation issue (Expected: ₹{expected_pnl:.2f})")
        
        else:
            logger.error("❌ No live market data available")
        
        logger.info("\n" + "=" * 40)
        logger.info("🎯 TEST SUMMARY:")
        logger.info("If P&L is still zero after live price update:")
        logger.info("1. Check if ShareKhan feed is working")
        logger.info("2. Verify position tracker update_market_prices method")
        logger.info("3. Check if background price updater is running")
        logger.info("4. Verify API endpoints return updated positions")
        
    except Exception as e:
        logger.error(f"❌ Error testing position updates: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_position_updates())
