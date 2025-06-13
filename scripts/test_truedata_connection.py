#!/usr/bin/env python3
"""
Test TrueData connectivity with Trial106 credentials
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.truedata_provider import TrueDataProvider
from config.truedata_config import TrueDataConfig

class TrueDataTester:
    def __init__(self):
        self.provider = None
        
    async def test_connection(self):
        """Test TrueData connection with Trial106 credentials"""
        try:
            print("🔌 Testing TrueData Connection...")
            print(f"Username: {TrueDataConfig.USERNAME}")
            print(f"Port: {TrueDataConfig.REALTIME_PORT}")
            print(f"Symbol Limit: {TrueDataConfig.SYMBOL_LIMIT}")
            print(f"Expiry: {TrueDataConfig.EXPIRY_DATE}")
            
            # Initialize provider with Trial106 config
            config = {
                'username': TrueDataConfig.USERNAME,
                'password': TrueDataConfig.PASSWORD,
                'live_port': TrueDataConfig.REALTIME_PORT,
                'url': 'push.truedata.in',
                'is_sandbox': False,  # Trial account but not sandbox
                'log_level': 'INFO',
                'max_connection_attempts': 3,
                'sandbox_max_symbols': TrueDataConfig.SYMBOL_LIMIT,
                'sandbox_allowed_symbols': TrueDataConfig.PRIMARY_SYMBOLS
            }
            
            self.provider = TrueDataProvider(config)
            
            # Test connection
            connected = await self.provider.connect()
            if connected:
                print("✅ TrueData connection successful!")
                return True
            else:
                print("❌ TrueData connection failed!")
                return False
                
        except Exception as e:
            print(f"❌ TrueData connection error: {e}")
            return False
    
    async def test_market_data(self):
        """Test historical market data retrieval"""
        try:
            print("\n📊 Testing Market Data...")
            
            # Test with NIFTY (should work even on holidays)
            data = await self.provider.get_market_data('NIFTY', '1day')
            
            if data and 'spot' in data:
                print(f"✅ NIFTY Data Retrieved:")
                print(f"   Spot Price: {data['spot']}")
                print(f"   ATR: {data.get('atr', 'N/A')}")
                print(f"   ADX: {data.get('adx', 'N/A')}")
                print(f"   VIX: {data.get('vix', 'N/A')}")
                print(f"   Candles Count: {len(data.get('candles', []))}")
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
            test_symbols = ['NIFTY', 'BANKNIFTY', 'RELIANCE']
            
            result = await self.provider.subscribe_symbols(test_symbols)
            
            if result:
                print(f"✅ Subscribed to symbols: {test_symbols}")
                
                # Check subscribed symbols
                subscribed = self.provider.get_subscribed_symbols()
                print(f"   Currently subscribed: {subscribed}")
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
            too_many_symbols = TrueDataConfig.PRIMARY_SYMBOLS[:55]  # More than 50
            
            try:
                result = await self.provider.subscribe_symbols(too_many_symbols)
                if not result:
                    print("✅ Symbol limit properly enforced")
                    return True
                else:
                    print("⚠️  Symbol limit not enforced - check validation")
                    return False
            except ValueError as e:
                print(f"✅ Symbol limit validation working: {e}")
                return True
                
        except Exception as e:
            print(f"❌ Trial limits test error: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup connections"""
        if self.provider:
            await self.provider.disconnect()
            print("🧹 Cleaned up TrueData connections")

async def main():
    """Main test function"""
    tester = TrueDataTester()
    
    try:
        print("🚀 TrueData Integration Test Starting...")
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
                print("\n🎉 All TrueData tests PASSED! System ready for trading.")
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
    result = asyncio.run(main())
    sys.exit(0 if result else 1) 