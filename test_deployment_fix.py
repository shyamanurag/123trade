#!/usr/bin/env python3
"""
Test script to verify the deployment fixes for 400 errors
"""

import requests
import json
from datetime import datetime

# Your actual DigitalOcean domain
BASE_URL = "https://quantumcrypto-l43mb.ondigitalocean.app"

def test_endpoint(url, endpoint_name):
    """Test a single endpoint"""
    try:
        print(f"Testing {endpoint_name}: {url}")
        response = requests.get(url, timeout=10)
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"  ✅ SUCCESS: {endpoint_name} is working!")
            if endpoint_name in ["System Status", "Health Check"]:
                try:
                    data = response.json()
                    print(f"  Response: {json.dumps(data, indent=2)[:200]}...")
                except:
                    print(f"  Response: {response.text[:100]}...")
        else:
            print(f"  ❌ FAILED: {response.status_code} - {response.text[:100]}")
        
        print("-" * 50)
        return response.status_code == 200
        
    except Exception as e:
        print(f"  ❌ ERROR: {str(e)}")
        print("-" * 50)
        return False

def main():
    """Test all critical endpoints"""
    print("🚀 Testing ShareKhan Trading System Deployment")
    print(f"🌐 Base URL: {BASE_URL}")
    print(f"🕒 Test Time: {datetime.now().isoformat()}")
    print("=" * 60)
    
    endpoints = [
        (f"{BASE_URL}/", "Homepage"),
        (f"{BASE_URL}/health", "Health Check"),
        (f"{BASE_URL}/api/health", "API Health Check"),
        (f"{BASE_URL}/readiness", "Readiness Check"),
        (f"{BASE_URL}/api/system/status", "System Status"),
        (f"{BASE_URL}/docs", "API Documentation"),
        (f"{BASE_URL}/redoc", "API Reference"),
        (f"{BASE_URL}/auth/sharekhan", "ShareKhan Auth"),
        (f"{BASE_URL}/api/autonomous/status", "Autonomous Trading Status"),
        (f"{BASE_URL}/api/performance/metrics", "Performance Metrics"),
    ]
    
    successful = 0
    total = len(endpoints)
    
    for url, name in endpoints:
        if test_endpoint(url, name):
            successful += 1
    
    print("=" * 60)
    print(f"📊 Test Results: {successful}/{total} endpoints successful")
    
    if successful == total:
        print("🎉 ALL TESTS PASSED! Deployment is working correctly!")
    elif successful > total // 2:
        print("⚠️  Most endpoints working - deployment partially successful")
    else:
        print("❌ Deployment still has issues - most endpoints failing")
    
    print("\n🔧 If endpoints are still failing with 400 errors:")
    print("1. Check that the changes to main_full.py have been deployed")
    print("2. Restart the DigitalOcean app service")
    print("3. Check the application logs for any startup errors")
    
    return successful == total

if __name__ == "__main__":
    main() 