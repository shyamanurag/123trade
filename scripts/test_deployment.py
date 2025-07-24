#!/usr/bin/env python3
"""
Test script to verify Digital Ocean deployment
"""
import requests
import json
import sys

BASE_URL = "https://algoauto-9gx56.ondigitalocean.app"

def test_endpoint(name, url, method="GET", data=None, headers=None):
    """Test a single endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"Method: {method}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers)
        else:
            response = requests.request(method, url, json=data, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        # Check content type
        content_type = response.headers.get('content-type', '')
        print(f"Content-Type: {content_type}")
        
        # Try to parse response
        if 'application/json' in content_type:
            try:
                json_data = response.json()
                print(f"JSON Response: {json.dumps(json_data, indent=2)}")
            except:
                print(f"Failed to parse JSON. Raw: {response.text[:200]}")
        else:
            print(f"Response Text: {response.text[:500]}")
            
        return response.status_code < 400
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("Testing AlgoAuto Trading System Deployment")
    print(f"Base URL: {BASE_URL}")
    
    tests_passed = 0
    tests_failed = 0
    
    # Test cases
    tests = [
        # Basic endpoints
        ("Root", f"{BASE_URL}/", "GET"),
        ("Health", f"{BASE_URL}/health", "GET"),
        ("Ready", f"{BASE_URL}/ready", "GET"),
        ("Health Ready", f"{BASE_URL}/health/ready", "GET"),
        
        # API routes
        ("API Routes", f"{BASE_URL}/api/routes", "GET"),
        
        # Auth endpoints
        ("Auth Login", f"{BASE_URL}/auth/login", "POST", {
            "username": "admin",
            "password": "admin123"
        }),
        ("API Auth Login (redirect)", f"{BASE_URL}/api/auth/login", "POST", {
            "username": "admin",
            "password": "admin123"
        }),
        
        # Market data
        ("Market Data", f"{BASE_URL}/api/market/data", "GET"),
        
        # Documentation
        ("OpenAPI JSON", f"{BASE_URL}/openapi.json", "GET"),
        ("Docs", f"{BASE_URL}/docs", "GET"),
    ]
    
    # Run tests
    for test in tests:
        name = test[0]
        url = test[1]
        method = test[2] if len(test) > 2 else "GET"
        data = test[3] if len(test) > 3 else None
        headers = test[4] if len(test) > 4 else None
        
        if test_endpoint(name, url, method, data, headers):
            tests_passed += 1
        else:
            tests_failed += 1
    
    # Test authenticated endpoints
    print("\n" + "="*60)
    print("Testing authenticated endpoints...")
    
    # First login
    login_response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    
    if login_response.status_code == 200:
        token = login_response.json().get("access_token")
        auth_headers = {"Authorization": f"Bearer {token}"}
        
        auth_tests = [
            ("Auth Me", f"{BASE_URL}/auth/me", "GET"),
            ("API Auth Me (redirect)", f"{BASE_URL}/api/auth/me", "GET"),
            ("Dashboard Data", f"{BASE_URL}/api/v1/dashboard/data", "GET"),
        ]
        
        for test in auth_tests:
            name = test[0]
            url = test[1]
            method = test[2] if len(test) > 2 else "GET"
            
            if test_endpoint(name, url, method, headers=auth_headers):
                tests_passed += 1
            else:
                tests_failed += 1
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print(f"Tests Passed: {tests_passed}")
    print(f"Tests Failed: {tests_failed}")
    print(f"Success Rate: {tests_passed/(tests_passed+tests_failed)*100:.1f}%")
    
    return tests_failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 