#!/usr/bin/env python3
"""
Setup Default Zerodha Broker User
Creates a pre-configured Zerodha broker user that only needs daily auth token updates
"""

import requests
import json
import os
from datetime import datetime

BASE_URL = "https://algoauto-9gx56.ondigitalocean.app"

# Default Zerodha broker configuration (hardcoded in system)
DEFAULT_ZERODHA_BROKER = {
    "user_id": "ZERODHA_MAIN",
    "name": "Main Zerodha Trading Account",
    "broker": "zerodha",
    "api_key": "sylcoq492qz6f7ej",  # Your actual API key
    "api_secret": "jm3h4iejwnxr4ngmma2qxccpkhevo8sy",  # Your actual API secret
    "client_id": "QSW899",  # Your actual client ID
    "initial_capital": 100000.0,
    "risk_tolerance": "medium",
    "paper_trading": False,  # Set to False for live trading
    "is_default": True,
    "requires_daily_auth": True
}

def setup_default_broker():
    """Set up the default Zerodha broker user"""
    print("🏦 SETTING UP DEFAULT ZERODHA BROKER")
    print("=" * 60)
    
    try:
        # Remove existing default user if exists
        print("🗑️  Removing existing default user...")
        try:
            delete_response = requests.delete(
                f"{BASE_URL}/api/v1/control/users/broker/ZERODHA_MAIN",
                timeout=10
            )
            if delete_response.status_code == 200:
                print("   ✅ Existing user removed")
            else:
                print("   ℹ️  No existing user to remove")
        except:
            print("   ℹ️  No existing user to remove")
        
        # Add the default broker user
        print("\n📤 Adding default Zerodha broker...")
        response = requests.post(
            f"{BASE_URL}/api/v1/control/users/broker",
            json=DEFAULT_ZERODHA_BROKER,
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("   ✅ Default Zerodha broker added successfully!")
            print(f"   📊 User ID: {DEFAULT_ZERODHA_BROKER['user_id']}")
            print(f"   💰 Capital: ₹{DEFAULT_ZERODHA_BROKER['initial_capital']:,.2f}")
            print(f"   🔴 Live Trading: {not DEFAULT_ZERODHA_BROKER['paper_trading']}")
            print(f"   🔑 API Key: {DEFAULT_ZERODHA_BROKER['api_key']}")
            return True
        else:
            print(f"   ❌ Failed: {response.text[:300]}")
            return False
            
    except Exception as e:
        print(f"❌ Error setting up broker: {e}")
        return False

def create_daily_auth_endpoint():
    """Information about the daily auth process"""
    print("\n🔐 DAILY AUTHENTICATION PROCESS")
    print("=" * 60)
    print("📋 From now on, you only need to:")
    print("   1. Visit: https://algoauto-9gx56.ondigitalocean.app/zerodha")
    print("   2. Click 'Login to Zerodha'")
    print("   3. Enter your Zerodha PIN")
    print("   4. System will automatically get the daily token")
    print("   5. Trading will start automatically")
    print()
    print("🚫 NO MORE NEED TO:")
    print("   ❌ Add broker credentials every time")
    print("   ❌ Configure API keys daily")
    print("   ❌ Set up capital allocation")
    print()
    print("✅ STREAMLINED DAILY WORKFLOW:")
    print("   1. Daily Auth (30 seconds)")
    print("   2. Autonomous trading starts")
    print("   3. Monitor & profit!")

def test_broker_setup():
    """Test if the broker setup is working"""
    print("\n🧪 TESTING BROKER SETUP")
    print("=" * 50)
    
    try:
        # Check if broker user exists
        response = requests.get(
            f"{BASE_URL}/api/v1/control/users/broker",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            users = data.get('users', [])
            
            if users:
                print(f"   ✅ Found {len(users)} broker user(s)")
                for user in users:
                    print(f"   📊 User: {user.get('user_id')} ({user.get('name')})")
                    print(f"   💰 Capital: ₹{user.get('initial_capital', 0):,.2f}")
                    print(f"   🔴 Live Trading: {not user.get('paper_trading', True)}")
                return True
            else:
                print("   ❌ No broker users found")
                return False
        else:
            print(f"   ❌ Failed to check users: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing setup: {e}")
        return False

def main():
    """Main setup process"""
    print("🚀 DEFAULT ZERODHA BROKER SETUP")
    print("=" * 70)
    print(f"Target: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Setup default broker
    if setup_default_broker():
        # Step 2: Test setup
        if test_broker_setup():
            # Step 3: Explain daily process
            create_daily_auth_endpoint()
            
            print("\n" + "=" * 70)
            print("🎉 SETUP COMPLETE!")
            print("✅ Default Zerodha broker is now configured")
            print("📱 Ready for daily auth token workflow")
            print("🚀 Autonomous trading system ready!")
            print("=" * 70)
        else:
            print("\n❌ Setup verification failed")
    else:
        print("\n❌ Broker setup failed")

if __name__ == "__main__":
    main() 