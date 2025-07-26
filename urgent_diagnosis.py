#!/usr/bin/env python3

import requests
import json

def diagnose_deployment():
    print("🚨 URGENT DIAGNOSIS: Why React Frontend Not Deploying")
    print("=" * 60)
    
    url = "https://trade123-l3zp7.ondigitalocean.app/"
    
    try:
        # Test root path
        response = requests.get(url)
        headers = dict(response.headers)
        
        print(f"🌐 URL: {url}")
        print(f"📊 Status: {response.status_code}")
        print(f"📏 Content Length: {len(response.text)}")
        
        print(f"\n🔍 CRITICAL HEADERS:")
        print(f"  Content-Type: {headers.get('content-type')}")
        print(f"  X-DO-App-Origin: {headers.get('x-do-app-origin')}")
        print(f"  Server: {headers.get('server', 'Not set')}")
        print(f"  Cache-Control: {headers.get('cache-control', 'Not set')}")
        
        # Check if it's API service or static site
        app_origin = headers.get('x-do-app-origin')
        if app_origin:
            if app_origin == "9a8e24f3-8b4c-437d-9426-315271fca030":
                print(f"\n❌ PROBLEM: Serving from API service!")
                print(f"   Expected: Static site service")
                print(f"   Actual: API service (main_full.py)")
            else:
                print(f"\n✅ Different service detected: {app_origin}")
        
        # Analyze content
        content = response.text
        if '<div id="root">' in content:
            print(f"\n✅ React root div found!")
        elif 'ShareKhan Trading System' in content and 'api' in content.lower():
            print(f"\n❌ BACKEND HTML detected!")
            print(f"   This is the FastAPI generated page, not React!")
        
        # Test specific static file
        print(f"\n🔍 Testing static file access...")
        static_test = requests.get(f"{url}assets/index.CergJYMB.js")
        print(f"  /assets/index.CergJYMB.js: {static_test.status_code}")
        
        if static_test.status_code == 404:
            print(f"❌ Static files not accessible - frontend not deployed!")
        elif static_test.status_code == 200:
            print(f"✅ Static files accessible!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print(f"\n💡 DIAGNOSIS:")
    print(f"1. If X-DO-App-Origin shows API service ID: Ingress routing problem")
    print(f"2. If static files 404: Frontend build/deployment failed")
    print(f"3. If backend HTML: API still intercepting root path")

if __name__ == "__main__":
    diagnose_deployment() 