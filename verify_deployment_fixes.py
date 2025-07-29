#!/usr/bin/env python3
"""
Deployment Verification Script
=============================
Tests all fixed endpoints to ensure they're working
"""

import requests
import asyncio
import json
from datetime import datetime

BASE_URL = "https://trade123-edtd2.ondigitalocean.app"

def test_endpoint(endpoint, method="GET", expected_status=200):
    """Test a single endpoint"""
    try:
        url = f"{BASE_URL}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json={}, timeout=10)
        
        success = response.status_code == expected_status
        
        print(f"{'✅' if success else '❌'} {method} {endpoint} - Status: {response.status_code}")
        
        if not success:
            print(f"   Response: {response.text[:200]}")
        
        return success
    except Exception as e:
        print(f"❌ {method} {endpoint} - Error: {str(e)}")
        return False

def main():
    """Run all verification tests"""
    print(f"🔍 DEPLOYMENT VERIFICATION - {datetime.now()}")
    print("=" * 50)
    
    endpoints_to_test = [
        # Fixed endpoints
        ("/api/system/database-health", "GET"),
        ("/api/system/logs?limit=10", "GET"),
        ("/api/risk/settings", "GET"),
        ("/api/strategies", "GET"),
        ("/api/system/control", "GET"),
        ("/api/system/api-health", "GET"),
        
        # Existing endpoints that should work
        ("/api/system/status", "GET"),
        ("/api/indices", "GET"),
        ("/health", "GET"),
        
        # Authentication endpoints
        ("/api/sharekhan/auth/generate-url", "GET"),
        ("/api/auth/tokens", "GET"),
    ]
    
    passed = 0
    total = len(endpoints_to_test)
    
    for endpoint, method in endpoints_to_test:
        if test_endpoint(endpoint, method):
            passed += 1
    
    print("=" * 50)
    print(f"RESULTS: {passed}/{total} endpoints working")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Deployment is healthy!")
    else:
        print(f"⚠️ {total - passed} endpoints need attention")
    
    return passed == total

if __name__ == "__main__":
    main() 