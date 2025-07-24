"""
Script to add default Zerodha account to the trading system
"""

import requests
import os
import json
from datetime import datetime

# API Configuration
API_BASE_URL = os.getenv('API_URL', 'http://localhost:8000')
if API_BASE_URL.startswith('https://'):
    # Production URL
    API_ENDPOINT = f"{API_BASE_URL}/api/v1/control/users/broker"
else:
    # Local development
    API_ENDPOINT = f"{API_BASE_URL}/api/v1/control/users/broker"

# Default Zerodha account configuration
DEFAULT_ZERODHA_ACCOUNT = {
    "user_id": "ZERODHA_DEFAULT",
    "name": "Default Zerodha Account",
    "broker": "zerodha",
    "api_key": os.getenv('ZERODHA_API_KEY', 'sylcoq492qz6f7ej'),
    "api_secret": os.getenv('ZERODHA_API_SECRET', 'jm3h4iejwnxr4ngmma2qxccpkhevo8sy'),
    "client_id": os.getenv('ZERODHA_CLIENT_ID', 'QSW899'),
    "initial_capital": 100000.0,
    "risk_tolerance": "medium",
    "paper_trading": True
}

def add_default_account():
    """Add default Zerodha account to the system"""
    try:
        # First check if account already exists
        check_response = requests.get(f"{API_BASE_URL}/api/v1/control/users/broker")
        if check_response.status_code == 200:
            users_data = check_response.json()
            existing_users = users_data.get('users', [])
            
            # Check if default account already exists
            for user in existing_users:
                if user.get('user_id') == DEFAULT_ZERODHA_ACCOUNT['user_id']:
                    print(f"✅ Default Zerodha account already exists: {user['user_id']}")
                    return True
        
        # Add the account
        print("Adding default Zerodha account...")
        response = requests.post(
            API_ENDPOINT,
            json=DEFAULT_ZERODHA_ACCOUNT,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ Successfully added default Zerodha account!")
                print(f"   User ID: {DEFAULT_ZERODHA_ACCOUNT['user_id']}")
                print(f"   Client ID: {DEFAULT_ZERODHA_ACCOUNT['client_id']}")
                print(f"   Initial Capital: ₹{DEFAULT_ZERODHA_ACCOUNT['initial_capital']:,.2f}")
                print(f"   Paper Trading: {DEFAULT_ZERODHA_ACCOUNT['paper_trading']}")
                return True
            else:
                print(f"❌ Failed to add account: {data.get('message', 'Unknown error')}")
                return False
        else:
            print(f"❌ API Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Details: {error_data.get('detail', 'No details available')}")
            except:
                print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API. Make sure the trading system is running.")
        print(f"   Tried to connect to: {API_ENDPOINT}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

def check_zerodha_daily_auth():
    """Check if Zerodha daily authentication is configured"""
    print("\n📋 Checking Zerodha Daily Authentication Setup...")
    
    # Check environment variables
    required_vars = ['ZERODHA_API_KEY', 'ZERODHA_API_SECRET', 'ZERODHA_CLIENT_ID', 'ZERODHA_USER_ID']
    all_configured = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: {'*' * 10}{value[-4:] if len(value) > 4 else value}")
        else:
            print(f"   ❌ {var}: Not configured")
            all_configured = False
    
    if all_configured:
        print("\n✅ All Zerodha credentials are configured!")
        print("\n📌 Daily Authentication Process:")
        print("   1. Go to: http://localhost:8000/zerodha (or your production URL/zerodha)")
        print("   2. Click 'Login to Zerodha' button")
        print("   3. Enter your Zerodha credentials")
        print("   4. You'll be redirected back automatically")
        print("   5. Token expires daily at 6:00 AM and needs re-authentication")
    else:
        print("\n❌ Some Zerodha credentials are missing. Please configure them in your environment.")
    
    return all_configured

if __name__ == "__main__":
    print("🚀 Trading System - Add Default Zerodha Account")
    print("=" * 50)
    
    # Add default account
    success = add_default_account()
    
    # Check daily auth setup
    auth_configured = check_zerodha_daily_auth()
    
    if success and auth_configured:
        print("\n✅ Setup complete! You can now:")
        print("   1. Start trading from the dashboard")
        print("   2. Authenticate with Zerodha daily at /zerodha endpoint")
    else:
        print("\n⚠️  Setup incomplete. Please check the errors above.") 