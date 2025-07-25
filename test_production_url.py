#!/usr/bin/env python3
"""
Production URL Test for ShareKhan Trading System
Tests the key endpoints of the deployed application
"""

import requests
import json
from datetime import datetime

PRODUCTION_URL = "https://quantumcrypto-l43mb.ondigitalocean.app"

def test_endpoint(endpoint, method="GET"):
    """Test a specific endpoint"""
    url = f"{PRODUCTION_URL}{endpoint}"
    try:
        print(f"🔄 Testing: {endpoint}")
        
        if method == "GET":
            response = requests.get(url, timeout=10, verify=True)
        else:
            response = requests.post(url, timeout=10, verify=True)
            
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ SUCCESS")
            try:
                data = response.json()
                if 'message' in data:
                    print(f"   Message: {data['message']}")
            except:
                print(f"   Response length: {len(response.text)} chars")
        else:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Connection Error: {e}")
    
    print()

def main():
    """Test all key endpoints"""
    print("🚀 ShareKhan Trading System - Production URL Test")
    print(f"🌐 Testing: {PRODUCTION_URL}")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Core System Endpoints
    print("📊 CORE SYSTEM ENDPOINTS:")
    test_endpoint("/health")
    test_endpoint("/api/system/status") 
    test_endpoint("/")
    
    # API Documentation
    print("📚 API DOCUMENTATION:")
    test_endpoint("/docs")
    test_endpoint("/redoc")
    
    # ShareKhan Integration
    print("🔐 SHAREKHAN INTEGRATION:")
    test_endpoint("/auth/sharekhan")
    test_endpoint("/api/sharekhan/status")
    
    # Trading System
    print("📈 TRADING SYSTEM:")
    test_endpoint("/api/autonomous/status")
    test_endpoint("/api/performance/metrics")
    
    print("=" * 60)
    print("✅ Production URL test completed!")
    print(f"🌐 Your ShareKhan Trading System: {PRODUCTION_URL}")

if __name__ == "__main__":
    main() 