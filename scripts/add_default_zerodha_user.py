#!/usr/bin/env python3
"""
Add default Zerodha user for paper trading
"""
import requests
import json

# API endpoint
base_url = "https://algoauto-9gx56.ondigitalocean.app"
endpoint = f"{base_url}/api/v1/control/users/broker"

# Default user data
user_data = {
    "user_id": "ZERODHA_DEFAULT",
    "name": "Default Zerodha User",
    "broker": "zerodha",
    "api_key": "sylcoq492qz6f7ej",
    "api_secret": "jm3h4iejwnxr4ngmma2qxccpkhevo8sy",
    "client_id": "QSW899",
    "initial_capital": 100000.0,
    "risk_tolerance": "medium",
    "paper_trading": True
}

# Send request
try:
    response = requests.post(endpoint, json=user_data)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Successfully added default Zerodha user")
        print(json.dumps(response.json(), indent=2))
    else:
        print("❌ Failed to add user")
        print(response.text)
        
except Exception as e:
    print(f"Error: {e}") 