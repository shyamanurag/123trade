#!/usr/bin/env python3
"""
Analyze P&L and Price Update Issues
Identifies why current prices aren't updating and P&L shows zero
"""

import os
import sys
import logging

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_trade_data():
    """Analyze the trade execution data"""
    logger.info("🔍 Analyzing Trade Execution Issues")
    logger.info("=" * 50)
    
    # Trade data from user
    trades = [
        {
            'symbol': 'GODREJCP',
            'side': 'sell',
            'quantity': 50,
            'entry_price': 1255.30,
            'current_price': 1255.30,
            'pnl': 0.00,
            'status': 'EXECUTED_FALLBACK',
            'strategy': 'momentum_surfer',
            'time': '06:29:07'
        },
        {
            'symbol': 'JSWSTEEL',
            'side': 'sell',
            'quantity': 50,
            'entry_price': 1029.90,
            'current_price': 1029.90,
            'pnl': 0.00,
            'status': 'EXECUTED_FALLBACK',
            'strategy': 'volume_profile_scalper',
            'time': '06:07:36'
        },
        {
            'symbol': 'TVSMOTOR',
            'side': 'sell',
            'quantity': 50,
            'entry_price': 2853.00,
            'current_price': 2853.00,
            'pnl': 0.00,
            'status': 'EXECUTED_FALLBACK',
            'strategy': 'volume_profile_scalper',
            'time': '05:59:23'
        }
    ]
    
    logger.info("📊 Trade Analysis:")
    for i, trade in enumerate(trades, 1):
        logger.info(f"\n{i}. {trade['symbol']} ({trade['strategy']}):")
        logger.info(f"   Entry: ₹{trade['entry_price']}")
        logger.info(f"   Current: ₹{trade['current_price']}")
        logger.info(f"   P&L: ₹{trade['pnl']}")
        logger.info(f"   Status: {trade['status']}")
        logger.info(f"   Time: {trade['time']}")
    
    # Identify issues
    logger.info("\n🔍 IDENTIFIED ISSUES:")
    logger.info("=" * 30)
    
    # Issue 1: Same entry and current prices
    logger.info("❌ ISSUE 1: Current Price Not Updating")
    logger.info("   - All trades show entry_price = current_price")
    logger.info("   - This indicates real-time price feed is not working")
    logger.info("   - P&L calculation depends on current price updates")
    
    # Issue 2: EXECUTED_FALLBACK status
    logger.info("\n❌ ISSUE 2: Fallback Execution Mode")
    logger.info("   - All trades show EXECUTED_FALLBACK status")
    logger.info("   - This means real broker connection failed")
    logger.info("   - System used paper trading fallback")
    
    # Issue 3: Zero P&L
    logger.info("\n❌ ISSUE 3: Zero P&L Calculation")
    logger.info("   - P&L = (current_price - entry_price) * quantity")
    logger.info("   - Since current_price = entry_price, P&L = 0")
    logger.info("   - Real-time price updates needed for accurate P&L")

def identify_root_causes():
    """Identify root causes of the issues"""
    logger.info("\n🔍 ROOT CAUSE ANALYSIS:")
    logger.info("=" * 30)
    
    logger.info("1. REAL-TIME PRICE FEED ISSUE:")
    logger.info("   - ShareKhan WebSocket connection may not be updating prices")
    logger.info("   - Price update mechanism not working in production")
    logger.info("   - Database price updates may be failing")
    
    logger.info("\n2. BROKER CONNECTION ISSUE:")
    logger.info("   - ShareKhan authentication still failing")
    logger.info("   - System falling back to paper trading mode")
    logger.info("   - Real broker API not accessible")
    
    logger.info("\n3. P&L CALCULATION DEPENDENCY:")
    logger.info("   - P&L calculation requires live price updates")
    logger.info("   - Without current price changes, P&L remains zero")
    logger.info("   - Frontend may not be receiving price updates")

def suggest_fixes():
    """Suggest fixes for the identified issues"""
    logger.info("\n🔧 SUGGESTED FIXES:")
    logger.info("=" * 30)
    
    logger.info("1. FIX REAL-TIME PRICE UPDATES:")
    logger.info("   - Check ShareKhan WebSocket connection status")
    logger.info("   - Verify price update mechanism in database")
    logger.info("   - Ensure frontend receives live price feeds")
    
    logger.info("\n2. FIX BROKER CONNECTION:")
    logger.info("   - Wait for Redis deployment to complete")
    logger.info("   - Verify ShareKhan token retrieval from Redis")
    logger.info("   - Check broker authentication in logs")
    
    logger.info("\n3. VERIFY P&L CALCULATION:")
    logger.info("   - Test P&L calculation with mock price changes")
    logger.info("   - Ensure P&L updates when prices change")
    logger.info("   - Check frontend P&L display logic")

def check_system_components():
    """Check which system components to investigate"""
    logger.info("\n📋 COMPONENTS TO CHECK:")
    logger.info("=" * 30)
    
    logger.info("1. SHAREKHAN CONNECTION:")
    logger.info("   - WebSocket connection status")
    logger.info("   - Price feed subscription")
    logger.info("   - Data flow to database")
    
    logger.info("\n2. DATABASE UPDATES:")
    logger.info("   - Price update queries")
    logger.info("   - Trade position updates")
    logger.info("   - P&L calculation triggers")
    
    logger.info("\n3. FRONTEND UPDATES:")
    logger.info("   - WebSocket connection to backend")
    logger.info("   - Real-time price display")
    logger.info("   - P&L calculation and display")
    
    logger.info("\n4. BROKER INTEGRATION:")
    logger.info("   - ShareKhan authentication status")
    logger.info("   - Real vs fallback execution")
    logger.info("   - Position synchronization")

def main():
    """Main analysis function"""
    logger.info("🚀 P&L and Price Update Analysis")
    logger.info("=" * 50)
    
    analyze_trade_data()
    identify_root_causes()
    suggest_fixes()
    check_system_components()
    
    logger.info("\n" + "=" * 50)
    logger.info("📊 SUMMARY:")
    logger.info("✅ Trades are executing (system is working)")
    logger.info("❌ Real-time price updates not working")
    logger.info("❌ P&L calculation stuck at zero")
    logger.info("❌ Using fallback mode instead of real broker")
    
    logger.info("\n🎯 PRIORITY FIXES:")
    logger.info("1. Fix ShareKhan real-time price feed")
    logger.info("2. Wait for Redis deployment completion")
    logger.info("3. Verify ShareKhan authentication")
    logger.info("4. Test P&L calculation with live prices")

if __name__ == "__main__":
    main()
