"""
Comprehensive test script for production API endpoints
Tests all critical endpoints and WebSocket connectivity
"""

import requests
import json
import asyncio
import websockets
import time
from datetime import datetime
from urllib.parse import urlparse

# Production URL
BASE_URL = "https://algoauto-9gx56.ondigitalocean.app"

# Test results storage
test_results = {
    "passed": 0,
    "failed": 0,
    "errors": []
}

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def test_endpoint(name, url, method="GET", data=None, headers=None, expected_status=200):
    """Test a single endpoint"""
    print(f"\n🔍 Testing {name}: {url}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        else:
            response = requests.request(method, url, json=data, headers=headers, timeout=10)
        
        print(f"   Status Code: {response.status_code}")
        
        # Check if response is JSON
        try:
            json_data = response.json()
            print(f"   Response Type: JSON")
            print(f"   Response Keys: {list(json_data.keys())[:5]}...")  # Show first 5 keys
            
            # Check for success field
            if 'success' in json_data:
                print(f"   Success: {json_data['success']}")
            if 'error' in json_data:
                print(f"   Error: {json_data['error']}")
            if 'detail' in json_data:
                print(f"   Detail: {json_data['detail']}")
                
        except json.JSONDecodeError:
            # Check if it's HTML
            if response.text.startswith('<!DOCTYPE') or response.text.startswith('<html'):
                print(f"   ❌ Response Type: HTML (Expected JSON)")
                print(f"   First 100 chars: {response.text[:100]}...")
                test_results["errors"].append(f"{name}: Returns HTML instead of JSON")
            else:
                print(f"   Response Type: Plain Text")
                print(f"   Content: {response.text[:200]}...")
        
        if response.status_code == expected_status:
            print(f"   ✅ PASSED")
            test_results["passed"] += 1
            return True
        else:
            print(f"   ❌ FAILED (Expected {expected_status})")
            test_results["failed"] += 1
            test_results["errors"].append(f"{name}: Got {response.status_code}, expected {expected_status}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"   ❌ TIMEOUT")
        test_results["failed"] += 1
        test_results["errors"].append(f"{name}: Request timed out")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ CONNECTION ERROR: {str(e)}")
        test_results["failed"] += 1
        test_results["errors"].append(f"{name}: Connection error")
        return False
    except Exception as e:
        print(f"   ❌ ERROR: {type(e).__name__}: {str(e)}")
        test_results["failed"] += 1
        test_results["errors"].append(f"{name}: {type(e).__name__}")
        return False

async def test_websocket(url):
    """Test WebSocket connectivity"""
    print(f"\n🔍 Testing WebSocket: {url}")
    
    try:
        websocket = await websockets.connect(url)
        try:
            print("   ✅ Connected successfully")
            
            # Send auth message
            auth_msg = json.dumps({"type": "auth", "userId": "test_user"})
            await websocket.send(auth_msg)
            print("   📤 Sent auth message")
            
            # Try to receive a message with timeout
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=3)
                print(f"   📥 Received: {response[:100]}...")
                test_results["passed"] += 1
                return True
            except asyncio.TimeoutError:
                print("   ⏱️  No response received (timeout)")
                test_results["passed"] += 1  # Connection works, just no data
                return True
        finally:
            await websocket.close()
                
    except Exception as e:
        print(f"   ❌ Connection failed: {type(e).__name__}: {str(e)}")
        test_results["failed"] += 1
        test_results["errors"].append(f"WebSocket: {type(e).__name__}")
        return False

def run_api_tests():
    """Run all API endpoint tests"""
    
    print_header("TESTING PRODUCTION API ENDPOINTS")
    print(f"Base URL: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Health endpoints
    print_header("Health Check Endpoints")
    test_endpoint("Health", f"{BASE_URL}/health")
    test_endpoint("Health Ready", f"{BASE_URL}/health/ready")
    test_endpoint("Health Ready JSON", f"{BASE_URL}/health/ready/json")
    test_endpoint("Ready (stripped)", f"{BASE_URL}/ready")
    
    # API Routes
    print_header("API Information")
    test_endpoint("API Routes", f"{BASE_URL}/api/routes")
    
    # Auth endpoints
    print_header("Authentication Endpoints")
    test_endpoint("Login (GET)", f"{BASE_URL}/auth/login", expected_status=405)  # Should fail with GET
    test_endpoint("Current User (No Auth)", f"{BASE_URL}/auth/me", expected_status=401)
    
    # User management
    print_header("User Management Endpoints")
    test_endpoint("Users List", f"{BASE_URL}/api/v1/users/")
    test_endpoint("Broker Users", f"{BASE_URL}/api/v1/control/users/broker")
    test_endpoint("Current User", f"{BASE_URL}/api/v1/users/current")
    
    # Trading endpoints
    print_header("Trading Endpoints")
    test_endpoint("Trading Status", f"{BASE_URL}/api/v1/control/trading/status")
    test_endpoint("Positions", f"{BASE_URL}/api/v1/positions")
    test_endpoint("Orders", f"{BASE_URL}/api/v1/orders")
    test_endpoint("Trades", f"{BASE_URL}/api/v1/trades")
    
    # Market data
    print_header("Market Data Endpoints")
    test_endpoint("Market Indices", f"{BASE_URL}/api/market/indices")
    test_endpoint("Market Status", f"{BASE_URL}/api/market/market-status")
    
    # Dashboard
    print_header("Dashboard Endpoints")
    test_endpoint("Dashboard Summary", f"{BASE_URL}/api/v1/dashboard/dashboard/summary")
    test_endpoint("Daily PnL", f"{BASE_URL}/api/v1/monitoring/daily-pnl")
    
    # Monitoring
    print_header("Monitoring Endpoints")
    test_endpoint("System Metrics", f"{BASE_URL}/api/v1/monitoring/metrics")
    test_endpoint("Components Status", f"{BASE_URL}/api/v1/monitoring/components")
    
    # WebSocket test
    print_header("WebSocket Test")
    asyncio.run(test_websocket(f"wss://algoauto-9gx56.ondigitalocean.app/ws"))
    
    # Summary
    print_header("TEST SUMMARY")
    print(f"✅ Passed: {test_results['passed']}")
    print(f"❌ Failed: {test_results['failed']}")
    print(f"📊 Success Rate: {test_results['passed']/(test_results['passed']+test_results['failed'])*100:.1f}%")
    
    if test_results['errors']:
        print("\n🚨 Errors Found:")
        for error in test_results['errors']:
            print(f"   - {error}")
    
    # Recommendations
    print_header("RECOMMENDATIONS")
    
    html_errors = [e for e in test_results['errors'] if 'HTML instead of JSON' in e]
    if html_errors:
        print("\n⚠️  Multiple endpoints returning HTML instead of JSON")
        print("   This indicates routing issues in Digital Ocean")
        print("   Affected endpoints:")
        for error in html_errors:
            print(f"   - {error.split(':')[0]}")
    
    ws_errors = [e for e in test_results['errors'] if 'WebSocket' in e]
    if ws_errors:
        print("\n⚠️  WebSocket connection issues detected")
        print("   Check if /ws endpoint is properly configured in ingress rules")
    
    return test_results

if __name__ == "__main__":
    run_api_tests() 