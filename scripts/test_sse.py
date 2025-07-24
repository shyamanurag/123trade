#!/usr/bin/env python3
"""
Test SSE endpoint
"""
import requests

url = "https://algoauto-9gx56.ondigitalocean.app/ws/sse"

print(f"Testing SSE endpoint at: {url}")

try:
    # Test SSE endpoint
    response = requests.get(url, headers={'Accept': 'text/event-stream'}, stream=True, timeout=5)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        print("\n✅ SSE endpoint is working!")
        print("First event:")
        # Read first line of SSE stream
        for line in response.iter_lines():
            if line:
                print(line.decode('utf-8'))
                break
    else:
        print(f"\n❌ SSE endpoint returned: {response.status_code}")
        
except Exception as e:
    print(f"\n❌ Error: {e}") 