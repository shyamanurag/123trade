#!/usr/bin/env python3
"""
Comprehensive Deployment Test Script
Tests all critical endpoints and identifies remaining issues
"""

import requests
import json
import time
from datetime import datetime
import sys

BASE_URL = "https://trade123-l3zp7.ondigitalocean.app"

def test_endpoint(endpoint, method="GET", data=None, expected_success=True):
    """Test a single endpoint and return results"""
    try:
        url = f"{BASE_URL}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        
        # Try to parse JSON
        try:
            json_data = response.json()
        except:
            json_data = {"raw_response": response.text[:500]}
        
        result = {
            "endpoint": endpoint,
            "method": method,
            "status_code": response.status_code,
            "success": response.status_code < 400,
            "data": json_data,
            "expected": expected_success
        }
        
        # Print immediate result
        status = "✅" if result["success"] == expected_success else "❌"
        print(f"{status} {method} {endpoint} - {response.status_code}")
        
        if not result["success"] and result["data"]:
            error_msg = result["data"].get("detail", result["data"].get("message", "Unknown error"))
            print(f"   Error: {error_msg}")
        
        return result
        
    except Exception as e:
        result = {
            "endpoint": endpoint,
            "method": method,
            "status_code": None,
            "success": False,
            "data": {"error": str(e)},
            "expected": expected_success
        }
        print(f"❌ {method} {endpoint} - Connection Error: {str(e)}")
        return result

def main():
    """Run comprehensive deployment tests"""
    print("🚀 DEPLOYMENT TEST SUITE")
    print("=" * 50)
    
    test_results = []
    
    # Basic Health Checks
    print("\n🔍 BASIC HEALTH CHECKS")
    print("-" * 30)
    test_results.append(test_endpoint("/health"))
    test_results.append(test_endpoint("/api/v1/system/status"))
    
    # Market Data Tests
    print("\n📊 MARKET DATA TESTS")
    print("-" * 30)
    test_results.append(test_endpoint("/api/market/indices"))
    test_results.append(test_endpoint("/api/v1/market-data/NIFTY"))
    
    # Autonomous Trading Tests  
    print("\n🤖 AUTONOMOUS TRADING TESTS")
    print("-" * 30)
    test_results.append(test_endpoint("/api/v1/autonomous/status"))
    test_results.append(test_endpoint("/api/v1/autonomous/strategies"))
    
    # Trading Control Tests
    print("\n🎮 TRADING CONTROL TESTS")
    print("-" * 30)
    test_results.append(test_endpoint("/api/v1/control/trading/status?user_id=PAPER_TRADER_001"))
    test_results.append(test_endpoint("/api/v1/control/users/broker"))
    
    # ShareKhan Authentication Tests
    print("\n🔐 SHAREKHAN AUTHENTICATION TESTS")
    print("-" * 30)
    test_results.append(test_endpoint("/auth/sharekhan/status?user_id=QSW899"))
    test_results.append(test_endpoint("/auth/sharekhan/auth-url?user_id=QSW899"))
    
    # User Management Tests
    print("\n👥 USER MANAGEMENT TESTS")
    print("-" * 30)
    test_results.append(test_endpoint("/api/v1/users/performance?user_id=PAPER_TRADER_001"))
    test_results.append(test_endpoint("/api/v1/users/current"))
    
    # Trading Data Tests
    print("\n💼 TRADING DATA TESTS")
    print("-" * 30)
    test_results.append(test_endpoint("/api/v1/trades?user_id=PAPER_TRADER_001"))
    test_results.append(test_endpoint("/api/v1/positions?user_id=PAPER_TRADER_001"))
    test_results.append(test_endpoint("/api/v1/orders?user_id=PAPER_TRADER_001"))
    
    # System Configuration Tests
    print("\n⚙️ SYSTEM CONFIGURATION TESTS")
    print("-" * 30)
    test_results.append(test_endpoint("/api/v1/system/config"))
    test_results.append(test_endpoint("/config"))
    
    # Generate Summary Report
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY REPORT")
    print("=" * 50)
    
    total_tests = len(test_results)
    passed_tests = len([t for t in test_results if t["success"] == t["expected"]])
    failed_tests = total_tests - passed_tests
    
    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    # Critical Issues Found
    print("\n🚨 CRITICAL ISSUES IDENTIFIED:")
    print("-" * 40)
    
    critical_issues = []
    
    for result in test_results:
        if not result["success"] and result["expected"]:
            endpoint = result["endpoint"]
            error = result["data"].get("detail", result["data"].get("message", result["data"].get("error", "Unknown")))
            
            if "paper_trading" in str(error):
                critical_issues.append(f"❌ TRADING CONTROL ERROR: Missing paper_trading attribute")
            elif "Not authenticated" in str(error):
                critical_issues.append(f"❌ SHAREKHAN AUTH ERROR: User QSW899 not authenticated")
            elif result["status_code"] == 500:
                critical_issues.append(f"❌ SERVER ERROR: {endpoint} - {error}")
            elif result["status_code"] == 404:
                critical_issues.append(f"❌ NOT FOUND: {endpoint}")
            elif "Connection" in str(error):
                critical_issues.append(f"❌ CONNECTION ERROR: {endpoint}")
    
    if critical_issues:
        for issue in set(critical_issues):  # Remove duplicates
            print(issue)
    else:
        print("✅ No critical issues found!")
    
    # Recommendations
    print("\n💡 IMMEDIATE ACTION REQUIRED:")
    print("-" * 40)
    
    recommendations = []
    
    for result in test_results:
        if not result["success"]:
            endpoint = result["endpoint"]
            if "trading/status" in endpoint:
                recommendations.append("1. Fix trading_state global variable missing paper_trading key")
            elif "sharekhan/status" in endpoint and "Not authenticated" in str(result["data"]):
                recommendations.append("2. Authenticate ShareKhan user QSW899 via /auth/sharekhan/auth-url")
            elif "/trades" in endpoint:
                recommendations.append("3. Fix trades API endpoint returning empty responses")
            elif result["status_code"] == 500:
                recommendations.append("4. Debug server errors in endpoints")
    
    if recommendations:
        for rec in set(recommendations):  # Remove duplicates
            print(rec)
    else:
        print("✅ System appears to be functioning correctly!")
    
    # Save detailed results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"deployment_test_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": (passed_tests/total_tests)*100
            },
            "test_results": test_results,
            "critical_issues": list(set(critical_issues)),
            "recommendations": list(set(recommendations))
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {filename}")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 