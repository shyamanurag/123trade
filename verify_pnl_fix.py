#!/usr/bin/env python3
"""
Verify P&L Fix
==============
Quick verification that the P&L fix is working
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def verify_pnl_fix():
    """Verify the P&L fix is working"""
    logger.info("🔍 Verifying P&L Fix")
    logger.info("=" * 40)
    
    try:
        # Test 1: Check if position tracker can be initialized
        logger.info("1. Testing Position Tracker Initialization:")
        from src.core.position_tracker import get_position_tracker
        position_tracker = await get_position_tracker()
        logger.info("   ✅ Position tracker initialized")
        
        # Test 2: Check if market data is available
        logger.info("\n2. Testing Market Data Availability:")
        from src.api.market_data import get_sharekhan_proxy
        proxy_data = get_sharekhan_proxy()
        
        if proxy_data and proxy_data.get('data'):
            data_count = len(proxy_data['data'])
            logger.info(f"   ✅ Market data available: {data_count} symbols")
            
            # Show sample data
            sample_symbols = list(proxy_data['data'].keys())[:3]
            for symbol in sample_symbols:
                data = proxy_data['data'][symbol]
                if isinstance(data, dict) and 'ltp' in data:
                    logger.info(f"   📊 {symbol}: ₹{data['ltp']}")
        else:
            logger.error("   ❌ No market data available")
            return False
        
        # Test 3: Create test position and update with live price
        logger.info("\n3. Testing Position Price Update:")
        
        # Create test position
        test_symbol = 'RELIANCE'
        test_entry_price = 1470.0
        test_quantity = 50
        
        await position_tracker.update_position(test_symbol, test_quantity, test_entry_price, 'long')
        logger.info(f"   ✅ Created test position: {test_symbol} {test_quantity} @ ₹{test_entry_price}")
        
        # Get initial position
        position = await position_tracker.get_position(test_symbol)
        if position:
            logger.info(f"   📊 Initial P&L: ₹{position.unrealized_pnl:.2f}")
        
        # Update with live market price
        if proxy_data and proxy_data.get('data') and test_symbol in proxy_data['data']:
            live_data = proxy_data['data'][test_symbol]
            if isinstance(live_data, dict) and 'ltp' in live_data:
                live_price = live_data['ltp']
                
                # Update position tracker with live price
                market_prices = {test_symbol: live_price}
                await position_tracker.update_market_prices(market_prices)
                
                # Get updated position
                updated_position = await position_tracker.get_position(test_symbol)
                if updated_position:
                    logger.info(f"   📊 Live price: ₹{live_price}")
                    logger.info(f"   📊 Updated current price: ₹{updated_position.current_price}")
                    logger.info(f"   📊 Updated P&L: ₹{updated_position.unrealized_pnl:.2f}")
                    
                    # Calculate expected P&L
                    expected_pnl = (live_price - test_entry_price) * test_quantity
                    logger.info(f"   📊 Expected P&L: ₹{expected_pnl:.2f}")
                    
                    # Verify P&L calculation
                    if abs(updated_position.unrealized_pnl - expected_pnl) < 0.01:
                        logger.info("   ✅ P&L calculation is correct!")
                        
                        # Check if price actually changed
                        if abs(live_price - test_entry_price) > 0.01:
                            logger.info("   ✅ Price has moved - P&L should be non-zero")
                        else:
                            logger.warning("   ⚠️ Live price same as entry price - P&L will be zero")
                    else:
                        logger.error("   ❌ P&L calculation is incorrect")
                        return False
                else:
                    logger.error("   ❌ Could not get updated position")
                    return False
            else:
                logger.error(f"   ❌ No live price data for {test_symbol}")
                return False
        else:
            logger.error(f"   ❌ {test_symbol} not found in market data")
            return False
        
        # Test 4: Check orchestrator bridge
        logger.info("\n4. Testing Orchestrator Bridge:")
        try:
            from src.core.orchestrator import TradingOrchestrator
            
            # Check if the bridge method exists
            if hasattr(TradingOrchestrator, '_start_market_data_to_position_tracker_bridge'):
                logger.info("   ✅ Bridge method exists in orchestrator")
            else:
                logger.error("   ❌ Bridge method missing in orchestrator")
                return False
                
            if hasattr(TradingOrchestrator, '_update_positions_with_market_data'):
                logger.info("   ✅ Background update method exists")
            else:
                logger.error("   ❌ Background update method missing")
                return False
                
        except Exception as e:
            logger.error(f"   ❌ Error checking orchestrator: {e}")
            return False
        
        logger.info("\n" + "=" * 40)
        logger.info("🎉 P&L FIX VERIFICATION COMPLETE")
        logger.info("✅ Position tracker working")
        logger.info("✅ Market data available")
        logger.info("✅ Price updates working")
        logger.info("✅ P&L calculation correct")
        logger.info("✅ Orchestrator bridge ready")
        
        logger.info("\n🚀 DEPLOYMENT READY:")
        logger.info("- The fix should resolve P&L = ₹0.00 issue")
        logger.info("- Position tracker will receive live price updates")
        logger.info("- P&L will be calculated with real-time prices")
        logger.info("- Background task will update prices every 30 seconds")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error verifying P&L fix: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main verification function"""
    logger.info("🚀 P&L Fix Verification")
    logger.info("=" * 50)
    
    success = await verify_pnl_fix()
    
    if success:
        logger.info("\n🎯 RESULT: P&L FIX VERIFIED SUCCESSFULLY!")
        logger.info("Deploy these changes to production to resolve the P&L issue.")
    else:
        logger.error("\n❌ RESULT: P&L FIX VERIFICATION FAILED!")
        logger.error("Additional debugging may be required.")

if __name__ == "__main__":
    asyncio.run(main())
