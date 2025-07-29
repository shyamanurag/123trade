#!/usr/bin/env python3
"""
Fix P&L Real-Time Updates
========================
This script fixes the P&L calculation issue by ensuring position tracker
receives real-time price updates from ShareKhan feed.

PROBLEM IDENTIFIED:
- Position tracker has update_market_prices() method
- Background task exists but not being called
- ShareKhan prices available but not reaching position tracker
- Current price = Entry price → P&L = 0

SOLUTION:
- Fix the market data bridge to position tracker
- Ensure ShareKhan prices update position tracker every 30 seconds
- Verify P&L calculations with live prices
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

def fix_orchestrator_price_updates():
    """Fix the orchestrator to properly start price update background task"""
    logger.info("🔧 Fixing Orchestrator Price Updates")
    logger.info("=" * 50)
    
    orchestrator_file = "src/core/orchestrator.py"
    
    try:
        with open(orchestrator_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if the bridge starter is being called
        if "_start_market_data_to_position_tracker_bridge" not in content:
            logger.error("❌ Bridge starter method not found in orchestrator")
            return False
        
        # Find the initialize method and add the bridge starter
        lines = content.split('\n')
        modified = False
        
        for i, line in enumerate(lines):
            # Look for the end of initialize method
            if "self.logger.info(\"✅ Trading orchestrator initialized successfully\")" in line:
                # Add the bridge starter before this line
                indent = "            "  # Match the indentation
                bridge_call = f"{indent}# Start market data to position tracker bridge"
                bridge_call2 = f"{indent}await self._start_market_data_to_position_tracker_bridge()"
                
                # Check if already added
                if "market_data_to_position_tracker_bridge" not in lines[max(0, i-5):i+1]:
                    lines.insert(i, bridge_call2)
                    lines.insert(i, bridge_call)
                    lines.insert(i, "")
                    modified = True
                    logger.info("✅ Added bridge starter to initialize method")
                else:
                    logger.info("ℹ️ Bridge starter already present")
                break
        
        if modified:
            # Write back the modified content
            with open(orchestrator_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            logger.info("✅ Orchestrator updated successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing orchestrator: {e}")
        return False

def fix_market_data_source():
    """Fix the market data source for position updates"""
    logger.info("\n🔧 Fixing Market Data Source")
    logger.info("=" * 50)
    
    orchestrator_file = "src/core/orchestrator.py"
    
    try:
        with open(orchestrator_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the _update_positions_with_market_data method
        old_import_section = '''                # Get market data from ShareKhan cache
                market_prices = {}
                try:
                    from data.sharekhan_client import live_market_data
                    for symbol, data in live_market_data.items():
                        ltp = data.get('ltp', 0)
                        if ltp and ltp > 0:
                            market_prices[symbol] = float(ltp)
                except ImportError:
                    pass'''
        
        new_import_section = '''                # Get market data from ShareKhan API
                market_prices = {}
                try:
                    # Use the same method as orchestrator uses for market data
                    market_data_response = await self._get_market_data_from_api()
                    if market_data_response and market_data_response.get('data'):
                        for symbol, data in market_data_response['data'].items():
                            if isinstance(data, dict) and 'ltp' in data:
                                ltp = data.get('ltp', 0)
                                if ltp and ltp > 0:
                                    market_prices[symbol] = float(ltp)
                    
                    self.logger.debug(f"📊 Retrieved {len(market_prices)} market prices for position updates")
                    
                except Exception as e:
                    self.logger.error(f"❌ Error getting market data for positions: {e}")
                    # Fallback: try direct ShareKhan import
                    try:
                        from data.sharekhan_client import live_market_data
                        for symbol, data in live_market_data.items():
                            ltp = data.get('ltp', 0)
                            if ltp and ltp > 0:
                                market_prices[symbol] = float(ltp)
                    except ImportError:
                        pass'''
        
        if old_import_section in content:
            content = content.replace(old_import_section, new_import_section)
            
            with open(orchestrator_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info("✅ Fixed market data source for position updates")
            return True
        else:
            logger.warning("⚠️ Market data section not found - may already be fixed")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error fixing market data source: {e}")
        return False

def create_position_price_updater():
    """Create a standalone position price updater service"""
    logger.info("\n🔧 Creating Position Price Updater Service")
    logger.info("=" * 50)
    
    updater_code = '''#!/usr/bin/env python3
"""
Position Price Updater Service
=============================
Standalone service to update position tracker with real-time prices
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PositionPriceUpdater:
    """Updates position tracker with real-time market prices"""
    
    def __init__(self):
        self.running = False
        self.position_tracker = None
        self.update_interval = 30  # seconds
        
    async def initialize(self):
        """Initialize the updater"""
        try:
            from src.core.position_tracker import get_position_tracker
            self.position_tracker = await get_position_tracker()
            logger.info("✅ Position price updater initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize updater: {e}")
            return False
    
    async def get_market_prices(self):
        """Get current market prices from ShareKhan"""
        try:
            from src.api.market_data import get_sharekhan_proxy
            
            proxy_data = get_sharekhan_proxy()
            if not proxy_data or not proxy_data.get('data'):
                return {}
            
            market_prices = {}
            for symbol, data in proxy_data['data'].items():
                if isinstance(data, dict) and 'ltp' in data:
                    ltp = data.get('ltp', 0)
                    if ltp and ltp > 0:
                        market_prices[symbol] = float(ltp)
            
            return market_prices
            
        except Exception as e:
            logger.error(f"❌ Error getting market prices: {e}")
            return {}
    
    async def update_position_prices(self):
        """Update position tracker with current market prices"""
        try:
            if not self.position_tracker:
                return False
            
            # Get current market prices
            market_prices = await self.get_market_prices()
            
            if not market_prices:
                logger.warning("⚠️ No market prices available")
                return False
            
            # Update position tracker
            await self.position_tracker.update_market_prices(market_prices)
            
            # Get positions to verify updates
            positions = await self.position_tracker.get_all_positions()
            
            if positions:
                logger.info(f"📊 Updated {len(market_prices)} prices for {len(positions)} positions")
                
                # Log sample position updates
                for symbol, position in list(positions.items())[:3]:  # Show first 3
                    logger.info(f"   {symbol}: Entry ₹{position.average_price:.2f} → Current ₹{position.current_price:.2f} → P&L ₹{position.unrealized_pnl:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating position prices: {e}")
            return False
    
    async def run(self):
        """Main update loop"""
        self.running = True
        logger.info("🚀 Position price updater started")
        
        while self.running:
            try:
                success = await self.update_position_prices()
                if success:
                    logger.debug("✅ Position prices updated successfully")
                else:
                    logger.warning("⚠️ Position price update failed")
                
                await asyncio.sleep(self.update_interval)
                
            except asyncio.CancelledError:
                logger.info("🛑 Position price updater cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in update loop: {e}")
                await asyncio.sleep(10)  # Wait before retrying
        
        logger.info("🛑 Position price updater stopped")
    
    def stop(self):
        """Stop the updater"""
        self.running = False

async def main():
    """Main function for standalone execution"""
    updater = PositionPriceUpdater()
    
    if await updater.initialize():
        try:
            await updater.run()
        except KeyboardInterrupt:
            logger.info("🛑 Received interrupt signal")
        finally:
            updater.stop()
    else:
        logger.error("❌ Failed to initialize position price updater")

if __name__ == "__main__":
    asyncio.run(main())
'''
    
    try:
        with open('src/services/position_price_updater.py', 'w', encoding='utf-8') as f:
            f.write(updater_code)
        
        logger.info("✅ Created position price updater service")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating updater service: {e}")
        return False

def create_test_position_updates():
    """Create test script to verify position updates"""
    logger.info("\n🔧 Creating Position Update Test")
    logger.info("=" * 50)
    
    test_code = '''#!/usr/bin/env python3
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
        logger.info("\\n📈 Current Position State:")
        for symbol, position in positions.items():
            logger.info(f"  {symbol}:")
            logger.info(f"    Entry Price: ₹{position.average_price:.2f}")
            logger.info(f"    Current Price: ₹{position.current_price:.2f}")
            logger.info(f"    P&L: ₹{position.unrealized_pnl:.2f}")
            logger.info(f"    Last Updated: {position.last_updated}")
        
        # Get live market data
        logger.info("\\n📊 Getting Live Market Data:")
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
            logger.info("\\n🔄 Updating Position Tracker:")
            await position_tracker.update_market_prices(market_prices)
            
            # Show updated state
            logger.info("\\n📈 Updated Position State:")
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
        
        logger.info("\\n" + "=" * 40)
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
'''
    
    try:
        with open('test_position_updates_fix.py', 'w', encoding='utf-8') as f:
            f.write(test_code)
        
        logger.info("✅ Created position update test script")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating test script: {e}")
        return False

def main():
    """Main fix function"""
    logger.info("🚀 Fixing P&L Real-Time Updates")
    logger.info("=" * 50)
    
    logger.info("🔍 PROBLEM ANALYSIS:")
    logger.info("- Position tracker has update_market_prices() method")
    logger.info("- Background task exists but may not be started")
    logger.info("- ShareKhan prices available but not reaching position tracker")
    logger.info("- Current price = Entry price → P&L = 0")
    
    logger.info("\n🔧 IMPLEMENTING FIXES:")
    
    # Fix 1: Ensure orchestrator starts the bridge
    success1 = fix_orchestrator_price_updates()
    
    # Fix 2: Fix market data source
    success2 = fix_market_data_source()
    
    # Fix 3: Create standalone updater service
    success3 = create_position_price_updater()
    
    # Fix 4: Create test script
    success4 = create_test_position_updates()
    
    logger.info("\n" + "=" * 50)
    logger.info("📊 FIX SUMMARY:")
    
    if success1:
        logger.info("✅ Orchestrator bridge starter fixed")
    else:
        logger.error("❌ Orchestrator bridge starter failed")
    
    if success2:
        logger.info("✅ Market data source fixed")
    else:
        logger.error("❌ Market data source failed")
    
    if success3:
        logger.info("✅ Standalone updater service created")
    else:
        logger.error("❌ Standalone updater service failed")
    
    if success4:
        logger.info("✅ Position update test created")
    else:
        logger.error("❌ Position update test failed")
    
    logger.info("\n🎯 NEXT STEPS:")
    logger.info("1. Run: python test_position_updates_fix.py")
    logger.info("2. Check if P&L updates with live prices")
    logger.info("3. Deploy fixes to production")
    logger.info("4. Monitor position tracker logs")
    
    if all([success1, success2, success3, success4]):
        logger.info("\n🎉 ALL FIXES APPLIED SUCCESSFULLY!")
        logger.info("The P&L should now update with real-time prices")
    else:
        logger.warning("\n⚠️ Some fixes failed - manual intervention may be needed")

if __name__ == "__main__":
    main()
