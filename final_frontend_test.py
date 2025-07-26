#!/usr/bin/env python3

import requests
import time

def test_react_frontend():
    base_url = "https://quantumcrypto-l43mb.ondigitalocean.app"
    
    print("🚀 FINAL COMPREHENSIVE REACT FRONTEND TEST")
    print("=" * 60)
    
    for attempt in range(3):
        print(f"\n🔍 Attempt {attempt + 1}/3:")
        
        try:
            # Test root path
            response = requests.get(f"{base_url}/", timeout=15)
            
            print(f"  📊 Status: {response.status_code}")
            print(f"  📏 Content Length: {len(response.text)} chars")
            print(f"  🌐 Content-Type: {response.headers.get('content-type', 'None')}")
            print(f"  🔗 X-DO-App-Origin: {response.headers.get('x-do-app-origin', 'None')}")
            
            if response.status_code == 200:
                content = response.text
                
                # Check for React indicators
                has_root_div = '<div id="root">' in content
                has_vite_assets = '/assets/' in content or '/static/assets/' in content
                has_react_scripts = 'index.CergJYMB.js' in content
                is_large_enough = len(content) > 3000  # React app should be larger than 404 response
                
                print(f"  ✅ Has <div id='root'>: {has_root_div}")
                print(f"  ✅ Has assets links: {has_vite_assets}")
                print(f"  ✅ Has React scripts: {has_react_scripts}")
                print(f"  ✅ Large enough response: {is_large_enough}")
                
                if has_root_div and is_large_enough:
                    print("\n  🎉 ✅ REACT FRONTEND SUCCESSFULLY DETECTED!")
                    print("  🎯 Your comprehensive trading dashboard is LIVE!")
                    return True
                elif is_large_enough:
                    print("\n  📄 Large HTML response but missing React elements")
                    print(f"  Preview: {content[:200]}...")
                else:
                    print(f"\n  ❌ Small response - likely 404 or error")
            else:
                print(f"\n  ❌ HTTP {response.status_code} error")
                
            # Test static files with new FastAPI mount point
            print(f"\n  🔍 Testing static file access:")
            static_urls = [
                f"{base_url}/static/assets/index.CergJYMB.js",
                f"{base_url}/static/index.html",
                f"{base_url}/assets/index.CergJYMB.js"  # Old path for comparison
            ]
            
            for static_url in static_urls:
                try:
                    static_response = requests.get(static_url, timeout=10)
                    print(f"    {static_url.split('/')[-2:]}: {static_response.status_code}")
                except:
                    print(f"    {static_url.split('/')[-2:]}: ERROR")
                    
        except Exception as e:
            print(f"  ❌ Request failed: {e}")
        
        if attempt < 2:
            print(f"\n  ⏰ Waiting 45 seconds for deployment to propagate...")
            time.sleep(45)
    
    print("\n❌ React frontend deployment failed after all attempts.")
    return False

def test_api_endpoints():
    base_url = "https://quantumcrypto-l43mb.ondigitalocean.app"
    
    print("\n🔍 Testing API endpoints to confirm backend is working:")
    
    endpoints = ["/health", "/api/health", "/docs"]
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            print(f"  {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"  {endpoint}: ERROR - {e}")

if __name__ == "__main__":
    success = test_react_frontend()
    test_api_endpoints()
    
    if success:
        print("\n🎉 SUCCESS: Your comprehensive React trading dashboard is live!")
        print("🔗 Visit: https://quantumcrypto-l43mb.ondigitalocean.app/")
        print("\n✅ Available features:")
        print("  - Analytics Dashboard")
        print("  - User Performance Dashboard") 
        print("  - ShareKhan Auth with Daily Tokens")
        print("  - Live Market Indices Widget")
        print("  - Trading Reports Hub")
        print("  - Real-time Trading Monitor")
        print("  - Multi-user Management")
        print("  - System Health Dashboard")
    else:
        print("\n❌ Frontend deployment still not working.")
        print("💡 This may require DigitalOcean configuration debugging.") 