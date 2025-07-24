#!/usr/bin/env python3
"""
Test WebSocket connection with detailed headers
"""
import requests

url = "https://algoauto-9gx56.ondigitalocean.app/ws"

# Test with WebSocket upgrade headers
headers = {
    "Connection": "Upgrade",
    "Upgrade": "websocket",
    "Sec-WebSocket-Version": "13",
    "Sec-WebSocket-Key": "x3JJHMbDL1EzLkh9GBhXDw==",
    "Origin": "https://algoauto-9gx56.ondigitalocean.app",
    "Host": "algoauto-9gx56.ondigitalocean.app"
}

print(f"Testing WebSocket upgrade at: {url}")
print(f"Headers: {headers}")

try:
    response = requests.get(url, headers=headers, allow_redirects=False)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body: {response.text[:500]}")
    
    if response.status_code == 403:
        print("\n❌ Getting 403 Forbidden - likely a proxy/CDN issue")
        print("The Digital Ocean proxy might be blocking WebSocket upgrades")
    elif response.status_code == 101:
        print("\n✅ Server supports WebSocket upgrade!")
    else:
        print(f"\n⚠️ Unexpected status code: {response.status_code}")
        
except Exception as e:
    print(f"\n❌ Error: {e}") 