#!/usr/bin/env python3
"""
Test Price Updates - Check if live prices are updating
"""

import os
import sys
import asyncio
import logging

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_price_updates():
    """Test if prices are updating"""
    logger.info("🧪 Testing Price Updates")
    logger.info("=" * 40)
    
    try:
        from src.api.market_data import get_sharekhan_proxy
        
        # Get current ShareKhan prices
        proxy_data = get_sharekhan_proxy()
        live_prices = proxy_data.get('data', {})
        
        logger.info(f"📊 Live Prices Available: {len(live_prices)}")
        
        # Test symbols from your trades
        test_symbols = ['GODREJCP', 'JSWSTEEL', 'TVSMOTOR']
        
        # Entry prices from your trade data
        entry_prices = {
            'GODREJCP': 1255.30,
            'JSWSTEEL': 1029.90,
            'TVSMOTOR': 2853.00
        }
        
        logger.info("\n📈 Price Comparison:")
        logger.info("-" * 40)
        
        for symbol in test_symbols:
            if symbol in live_prices:
                price_data = live_prices[symbol]
                current_price = price_data.get('ltp', 0)  # Last Traded Price
                
                logger.info(f"\n{symbol}:")
                logger.info(f"  Current Price: Rs {current_price}")
                
                entry_price = entry_prices.get(symbol, 0)
                price_diff = current_price - entry_price
                
                logger.info(f"  Entry Price: Rs {entry_price}")
                logger.info(f"  Difference: Rs {price_diff:.2f}")
                
                # Calculate P&L for 50 shares (your trade quantity)
                pnl = price_diff * 50
                logger.info(f"  P&L for 50 shares: Rs {pnl:.2f}")
                
                # Check if price has moved
                if abs(price_diff) > 0.01:  # More than 1 paisa difference
                    logger.info(f"  ✅ Price has moved! P&L should be Rs {pnl:.2f}")
                else:
                    logger.warning(f"  ⚠️ Price hasn't moved from entry price")
                    
                # Show additional data
                change_percent = price_data.get('change_percent', 0)
                logger.info(f"  Change %: {change_percent:.2f}%")
                logger.info(f"  Volume: {price_data.get('volume', 0):,}")
                logger.info(f"  Timestamp: {price_data.get('timestamp', 'N/A')}")
                
            else:
                logger.warning(f"\n{symbol}: No live price data available")
        
        # Summary
        logger.info("\n" + "=" * 40)
        logger.info("📊 ANALYSIS SUMMARY:")
        
        if any(symbol in live_prices for symbol in test_symbols):
            logger.info("✅ Live price data is available")
            
            # Check if any prices have moved
            moved_prices = []
            for symbol in test_symbols:
                if symbol in live_prices:
                    current_price = live_prices[symbol].get('ltp', 0)
                    entry_price = entry_prices.get(symbol, 0)
                    if abs(current_price - entry_price) > 0.01:
                        moved_prices.append(symbol)
            
            if moved_prices:
                logger.info(f"✅ Prices have moved for: {', '.join(moved_prices)}")
                logger.info("   P&L should be calculated based on price differences")
            else:
                logger.warning("⚠️ No significant price movements detected")
                logger.warning("   This explains why P&L shows Rs 0.00")
        else:
            logger.error("❌ No live price data for your trade symbols")
            
    except Exception as e:
        logger.error(f"❌ Error testing price updates: {e}")
        import traceback
        traceback.print_exc()

def check_position_api():
    """Check if position API returns updated prices"""
    logger.info("\n🔍 Checking Position API")
    logger.info("=" * 40)
    
    try:
        import requests
        
        # Try to call the trades API (if running locally)
        api_url = "http://localhost:8000/api/trades/live"
        
        try:
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ API Response received: {len(data)} trades")
                
                # Check if trades have updated current_price
                for trade in data[:3]:  # Show first 3
                    symbol = trade.get('symbol', 'Unknown')
                    entry_price = trade.get('entry_price', 0)
                    current_price = trade.get('current_price', 0)
                    pnl = trade.get('pnl', 0)
                    
                    logger.info(f"\n{symbol}:")
                    logger.info(f"  Entry: Rs {entry_price}")
                    logger.info(f"  Current: Rs {current_price}")
                    logger.info(f"  P&L: Rs {pnl}")
                    
                    if current_price == entry_price:
                        logger.warning(f"  ⚠️ Current price same as entry price")
                    else:
                        logger.info(f"  ✅ Price difference detected")
            else:
                logger.warning(f"⚠️ API returned status {response.status_code}")
                
        except requests.exceptions.RequestException:
            logger.info("ℹ️ Local API not accessible (expected in production)")
            
    except Exception as e:
        logger.error(f"❌ Error checking position API: {e}")

def main():
    """Main test function"""
    logger.info("🚀 Price Update Test")
    logger.info("=" * 50)
    
    asyncio.run(test_price_updates())
    check_position_api()
    
    logger.info("\n" + "=" * 50)
    logger.info("🎯 CONCLUSION:")
    logger.info("If prices show movement but P&L is still Rs 0.00:")
    logger.info("1. Position tracker is not updating current_price")
    logger.info("2. Database positions table needs price updates")
    logger.info("3. API endpoints need to return live prices")
    logger.info("4. Frontend polling may need to be verified")

if __name__ == "__main__":
    main()