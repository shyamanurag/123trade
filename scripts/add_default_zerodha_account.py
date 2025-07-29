"""
Script to add default ShareKhan account to the trading system
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

# Default ShareKhan account configuration
DEFAULT_SHAREKHAN_ACCOUNT = {
    "user_id": "SHAREKHAN_DEFAULT",
    "name": "Default ShareKhan Account",
    "broker": "sharekhan",
    "api_key": os.getenv('SHAREKHAN_API_KEY', 'sylcoq492qz6f7ej'),
    "api_secret": os.getenv('SHAREKHAN_API_SECRET', 'jm3h4iejwnxr4ngmma2qxccpkhevo8sy'),
    "client_id": os.getenv('SHAREKHAN_CLIENT_ID', 'QSW899'),
    "initial_capital": 100000.0,
    "risk_tolerance": "medium",
    "paper_trading": True
}

def add_default_account():
    """Add default ShareKhan account to the system"""
    try:
        # First check if account already exists
        check_response = requests.get(f"{API_BASE_URL}/api/v1/control/users/broker")
        if check_response.status_code == 200:
            users_data = check_response.json()
            existing_users = users_data.get('users', [])
            
            # Check if default account already exists
            for user in existing_users:
                if user.get('user_id') == DEFAULT_SHAREKHAN_ACCOUNT['user_id']:
                    print(f"✅ Default ShareKhan account already exists: {user['user_id']}")
                    return True
        
        # Add the account
        print("Adding default ShareKhan account...")
        response = requests.post(
            API_ENDPOINT,
            json=DEFAULT_SHAREKHAN_ACCOUNT,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ Successfully added default ShareKhan account!")
                print(f"   User ID: {DEFAULT_SHAREKHAN_ACCOUNT['user_id']}")
                print(f"   Client ID: {DEFAULT_SHAREKHAN_ACCOUNT['client_id']}")
                print(f"   Initial Capital: ₹{DEFAULT_SHAREKHAN_ACCOUNT['initial_capital']:,.2f}")
                print(f"   Paper Trading: {DEFAULT_SHAREKHAN_ACCOUNT['paper_trading']}")
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

def check_sharekhan_daily_auth():
    """Check if ShareKhan daily authentication is configured"""
    print("\n📋 Checking ShareKhan Daily Authentication Setup...")
    
    # Check environment variables
    required_vars = ['SHAREKHAN_API_KEY', 'SHAREKHAN_API_SECRET', 'SHAREKHAN_CLIENT_ID', 'SHAREKHAN_USER_ID']
    all_configured = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: {'*' * 10}{value[-4:] if len(value) > 4 else value}")
        else:
            print(f"   ❌ {var}: Not configured")
            all_configured = False
    
    if all_configured:
        print("\n✅ All ShareKhan credentials are configured!")
        print("\n📌 Daily Authentication Process:")
        print("   1. Go to: http://localhost:8000/sharekhan (or your production URL/sharekhan)")
        print("   2. Click 'Login to ShareKhan' button")
        print("   3. Enter your ShareKhan credentials")
        print("   4. You'll be redirected back automatically")
        print("   5. Token expires daily at 6:00 AM and needs re-authentication")
    else:
        print("\n❌ Some ShareKhan credentials are missing. Please configure them in your environment.")
    
    return all_configured

if __name__ == "__main__":
    print("🚀 Trading System - Add Default ShareKhan Account")
    print("=" * 50)
    
    # Add default account
    success = add_default_account()
    
    # Check daily auth setup
    auth_configured = check_sharekhan_daily_auth()
    
    if success and auth_configured:
        print("\n✅ Setup complete! You can now:")
        print("   1. Start trading from the dashboard")
        print("   2. Authenticate with ShareKhan daily at /sharekhan endpoint")
    else:
        print("\n⚠️  Setup incomplete. Please check the errors above.") 