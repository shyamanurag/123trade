#!/usr/bin/env python3

import requests

def quick_retest():
    base_url = "https://quantumcrypto-l43mb.ondigitalocean.app"
    
    print("🔍 QUICK RETEST - Current Status")
    print("=" * 40)
    
    # Test root path
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        print(f"Root path (/): {response.status_code}")
        print(f"Content length: {len(response.text)} chars")
        
        if response.status_code == 200:
            if '<div id="root">' in response.text:
                print("✅ REACT FRONTEND DETECTED!")
                return True
            elif len(response.text) > 3000:
                print("📄 Large HTML response (not React)")
                print(f"Preview: {response.text[:80]}...")
            else:
                print("❓ Small response")
        elif response.status_code == 404:
            print("❌ 404 - FastAPI static serving not active")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test static mount points
    print("\n🔍 Testing static file paths:")
    
    static_paths = [
        "/static/index.html",
        "/static/assets/index.CergJYMB.js", 
        "/assets/index.CergJYMB.js"
    ]
    
    for path in static_paths:
        try:
            static_response = requests.get(f"{base_url}{path}", timeout=10)
            print(f"  {path}: {static_response.status_code}")
        except:
            print(f"  {path}: ERROR")
    
    # Test health endpoint to confirm API is working
    try:
        health_response = requests.get(f"{base_url}/health", timeout=10)
        print(f"\nAPI health check: {health_response.status_code}")
    except:
        print(f"\nAPI health check: ERROR")
    
    return False

if __name__ == "__main__":
    success = quick_retest()
    
    if success:
        print("\n🎉 SUCCESS: React frontend is live!")
    else:
        print("\n⏰ Frontend still deploying or needs additional fixes") 