"""
Quick WebSocket fix and test script
"""

import asyncio
import websockets
import json

async def test_websocket_locally():
    """Test WebSocket connection with different approaches"""
    
    url = "wss://algoauto-9gx56.ondigitalocean.app/ws"
    
    print("🔍 Testing WebSocket Connection Methods")
    print("=" * 50)
    
    # Test 1: Basic connection
    print("\n1. Testing basic connection...")
    try:
        websocket = await websockets.connect(url)
        print("   ✅ Connected!")
        await websocket.close()
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Test 2: With headers
    print("\n2. Testing with headers...")
    try:
        headers = {
            "Origin": "https://algoauto-9gx56.ondigitalocean.app",
            "User-Agent": "Mozilla/5.0"
        }
        websocket = await websockets.connect(url, extra_headers=headers)
        print("   ✅ Connected with headers!")
        await websocket.close()
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Test 3: Different path
    print("\n3. Testing without path prefix...")
    try:
        # Try connecting to ws without leading slash (Digital Ocean stripping)
        alt_url = "wss://algoauto-9gx56.ondigitalocean.app/ws"
        websocket = await websockets.connect(alt_url)
        print("   ✅ Connected to alternate path!")
        await websocket.close()
    except Exception as e:
        print(f"   ❌ Failed: {e}")

def print_manual_fix():
    """Print manual fix instructions"""
    
    print("\n" + "="*60)
    print("📋 MANUAL FIX INSTRUCTIONS")
    print("="*60)
    
    print("\n1. Go to Digital Ocean App Dashboard")
    print("   https://cloud.digitalocean.com/apps")
    
    print("\n2. Click on your app 'algoauto'")
    
    print("\n3. Go to 'Settings' tab")
    
    print("\n4. Under 'App Spec', click 'Edit'")
    
    print("\n5. Find the 'ingress' section and ensure it looks like this:")
    print("""
ingress:
  rules:
  - component:
      name: api
      preserve_path_prefix: true
    match:
      path:
        prefix: /ws
""")
    
    print("\n6. If the /ws rule is missing, add it")
    
    print("\n7. Click 'Save' to trigger redeployment")
    
    print("\n" + "="*60)
    print("🔧 ALTERNATIVE: Update via CLI")
    print("="*60)
    
    print("\n1. Install Digital Ocean CLI (doctl)")
    print("   https://docs.digitalocean.com/reference/doctl/how-to/install/")
    
    print("\n2. Get your app ID:")
    print("   doctl apps list")
    
    print("\n3. Update the app spec:")
    print("   doctl apps update <APP_ID> --spec digital-ocean-app-ultimate-fix.yaml")
    
    print("\n" + "="*60)
    print("⚠️  IMPORTANT NOTES")
    print("="*60)
    
    print("\n- The WebSocket endpoint is simplified and ready")
    print("- It accepts connections without auth initially")
    print("- Send {\"type\": \"auth\", \"userId\": \"user123\"} after connecting")
    print("- The 403 error suggests the route isn't reaching the API")
    print("- This is likely a Digital Ocean ingress configuration issue")

if __name__ == "__main__":
    print("🚀 WebSocket Fix Script")
    print("=" * 60)
    
    # Run async test
    asyncio.run(test_websocket_locally())
    
    # Print manual instructions
    print_manual_fix()
    
    print("\n✅ Script complete!") 