#!/usr/bin/env python3
"""
Test ShareKhan connectivity with subscription credentials
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.sharekhan_provider import ShareKhanProvider
from config.sharekhan_config import ShareKhanConfig
from datetime import datetime, timedelta

class ShareKhanTester:
    def __init__(self):
        self.provider = None
        
    async def test_connection(self):
        """Test ShareKhan connection with subscription credentials"""
        try:
            print("🔌 Testing ShareKhan Connection...")
            config = ShareKhanConfig.get_connection_config()
            print(f"Username: {config['username']}")
            print(f"Port: {config['port']}")
            print(f"Symbol Limit: {config['symbol_limit']}")
            
            # Initialize provider with config
            self.provider = ShareKhanProvider(config)
            
            # Test connection
            connected = await self.provider.connect()
            if connected:
                print("✅ ShareKhan connection successful!")
                return True
            else:
                print("❌ ShareKhan connection failed!")
                return False
                
        except Exception as e:
            print(f"❌ ShareKhan connection error: {e}")
            return False
    
    async def test_market_data(self):
        """Test historical market data retrieval"""
        try:
            print("\n📊 Testing Market Data...")
            
            # Test with NIFTY (should work even on holidays)
            data = await self.provider.get_historical_data(
                symbol='NIFTY-I',
                start_time=datetime.now() - timedelta(days=1),
                end_time=datetime.now(),
                bar_size='1 day'
            )
            
            if not data.empty:
                print(f"✅ NIFTY Data Retrieved:")
                print(f"   Latest Close: {data['close'].iloc[-1]}")
                print(f"   Latest Volume: {data['volume'].iloc[-1]}")
                print(f"   Data Points: {len(data)}")
                return True
            else:
                print("❌ No market data received")
                return False
                
        except Exception as e:
            print(f"❌ Market data error: {e}")
            return False
    
    async def test_symbol_subscription(self):
        """Test symbol subscription within 50 symbol limit"""
        try:
            print("\n📡 Testing Symbol Subscription...")
            
            # Test with a few symbols within limit
            test_symbols = ['NIFTY-I', 'BANKNIFTY-I', 'RELIANCE-EQ']
            
            result = await self.provider.subscribe_market_data(test_symbols)
            
            if result:
                print(f"✅ Subscribed to symbols: {test_symbols}")
                return True
            else:
                print("❌ Symbol subscription failed")
                return False
                
        except Exception as e:
            print(f"❌ Symbol subscription error: {e}")
            return False
    
    async def test_trial_limits(self):
        """Test trial account limits"""
        try:
            print("\n🚧 Testing Trial Account Limits...")
            
            # Test symbol limit validation
            too_many_symbols = ['SYMBOL' + str(i) for i in range(55)]  # More than 50
            
            if not ShareKhanConfig.validate_symbol_limit(too_many_symbols):
                print("✅ Symbol limit properly enforced")
                return True
            else:
                print("⚠️  Symbol limit not enforced - check validation")
                return False
                
        except Exception as e:
            print(f"❌ Trial limits test error: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup connections"""
        if self.provider:
            await self.provider.disconnect()
            print("🧹 Cleaned up ShareKhan connections")

async def main():
    """Main test function"""
    tester = ShareKhanTester()
    
    try:
        print("🚀 ShareKhan Integration Test Starting...")
        print("=" * 50)
        
        # Test connection
        connection_ok = await tester.test_connection()
        
        if connection_ok:
            # Test market data
            market_data_ok = await tester.test_market_data()
            
            # Test subscriptions
            subscription_ok = await tester.test_symbol_subscription()
            
            # Test trial limits
            limits_ok = await tester.test_trial_limits()
            
            # Summary
            print("\n" + "=" * 50)
            print("📋 Test Results Summary:")
            print(f"   Connection: {'✅ PASS' if connection_ok else '❌ FAIL'}")
            print(f"   Market Data: {'✅ PASS' if market_data_ok else '❌ FAIL'}")
            print(f"   Subscriptions: {'✅ PASS' if subscription_ok else '❌ FAIL'}")
            print(f"   Trial Limits: {'✅ PASS' if limits_ok else '❌ FAIL'}")
            
            if all([connection_ok, market_data_ok, subscription_ok, limits_ok]):
                print("\n🎉 All ShareKhan tests PASSED! System ready for trading.")
                return True
            else:
                print("\n⚠️  Some tests failed. Check configuration.")
                return False
        else:
            print("\n❌ Connection failed. Cannot proceed with other tests.")
            return False
            
    except Exception as e:
        print(f"\n💥 Test suite error: {e}")
        return False
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 