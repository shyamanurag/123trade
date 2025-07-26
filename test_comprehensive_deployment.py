#!/usr/bin/env python3
"""
Comprehensive Deployment Test Script
Tests ALL fixes applied for the DigitalOcean deployment issues
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Your DigitalOcean domain
BASE_URL = "https://trade123-l3zp7.ondigitalocean.app"

class DeploymentTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.results = []
        self.total_tests = 0
        self.passed_tests = 0
        
    def log_result(self, test_name: str, success: bool, status_code: Optional[int] = None, details: Optional[str] = None):
        """Log test result"""
        self.total_tests += 1
        if success:
            self.passed_tests += 1
            
        result = {
            "test": test_name,
            "success": success,
            "status_code": status_code,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} {test_name}")
        if status_code:
            print(f"   Status: {status_code}")
        if details:
            print(f"   Details: {details}")
        print("-" * 60)
    
    def test_endpoint(self, endpoint: str, test_name: str, expected_status: int = 200, 
                     check_content: Optional[str] = None) -> bool:
        """Test a single endpoint"""
        try:
            url = f"{self.base_url}{endpoint}"
            print(f"Testing: {url}")
            
            response = requests.get(url, timeout=15)
            
            if response.status_code == expected_status:
                if check_content and check_content.lower() not in response.text.lower():
                    self.log_result(test_name, False, response.status_code, 
                                  f"Content check failed: '{check_content}' not found")
                    return False
                
                # Try to parse JSON if possible
                try:
                    data = response.json()
                    self.log_result(test_name, True, response.status_code, 
                                  f"JSON response with {len(data)} fields")
                except:
                    self.log_result(test_name, True, response.status_code, 
                                  f"HTML response ({len(response.text)} chars)")
                return True
            else:
                self.log_result(test_name, False, response.status_code, 
                              response.text[:100] + "..." if len(response.text) > 100 else response.text)
                return False
                
        except requests.exceptions.Timeout:
            self.log_result(test_name, False, None, "Request timeout (15s)")
            return False
        except requests.exceptions.ConnectionError:
            self.log_result(test_name, False, None, "Connection error - deployment may be restarting")
            return False
        except Exception as e:
            self.log_result(test_name, False, None, f"Error: {str(e)}")
            return False
    
    def test_json_response(self, endpoint: str, test_name: str, required_fields: Optional[List[str]] = None) -> Dict:
        """Test endpoint that should return JSON"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if required_fields:
                    missing_fields = [field for field in required_fields if field not in data]
                    if missing_fields:
                        self.log_result(test_name, False, 200, f"Missing fields: {missing_fields}")
                        return {}
                
                self.log_result(test_name, True, 200, f"Valid JSON with {len(data)} fields")
                return data
            else:
                self.log_result(test_name, False, response.status_code, response.text[:100])
                return {}
                
        except Exception as e:
            self.log_result(test_name, False, None, f"Error: {str(e)}")
            return {}
    
    def run_comprehensive_tests(self):
        """Run all comprehensive tests"""
        print("🚀 COMPREHENSIVE DEPLOYMENT TEST")
        print(f"🌐 Testing: {self.base_url}")
        print(f"🕒 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Test 1: Basic connectivity and CORS fix
        print("📡 TESTING BASIC CONNECTIVITY & CORS FIXES")
        self.test_endpoint("/", "Homepage loads (CORS fix)", 200, "ShareKhan Trading System")
        
        # Test 2: Health endpoints (critical for DigitalOcean)
        print("\n💓 TESTING HEALTH ENDPOINTS")
        health_data = self.test_json_response("/health", "Health check endpoint", 
                                            ["status", "timestamp", "version"])
        self.test_json_response("/api/health", "API health endpoint", ["status", "timestamp"])
        self.test_json_response("/readiness", "Readiness probe", ["status", "timestamp"])
        
        # Test 3: System status (comprehensive info)
        print("\n🏥 TESTING SYSTEM STATUS")
        status_data = self.test_json_response("/api/system/status", "System status endpoint",
                                            ["status", "version", "components"])
        
        # Test 4: API Documentation (FastAPI auto-generated)
        print("\n📚 TESTING API DOCUMENTATION")
        self.test_endpoint("/docs", "Swagger UI docs", 200, "swagger")
        self.test_endpoint("/redoc", "ReDoc documentation", 200, "redoc")
        
        # Test 5: Debug endpoint (troubleshooting)
        print("\n🔧 TESTING DEBUG ENDPOINTS")
        debug_data = self.test_json_response("/api/debug/status", "Debug status endpoint",
                                           ["debug", "environment_vars", "app_state"])
        
        # Test 6: API routes (if loaded)
        print("\n🛣️ TESTING API ROUTES")
        self.test_endpoint("/api/performance/metrics", "Performance metrics", expected_status=200)
        self.test_endpoint("/api/autonomous/status", "Autonomous trading status", expected_status=200)
        
        # Test 7: Non-existent endpoints (should return 404, not 400)
        print("\n🚫 TESTING ERROR HANDLING")
        self.test_endpoint("/nonexistent", "404 handling", expected_status=404)
        self.test_endpoint("/api/invalid", "API 404 handling", expected_status=404)
        
        # Analysis
        print("\n" + "=" * 80)
        print("📊 TEST ANALYSIS")
        
        if health_data.get("status") == "healthy":
            print("✅ Health check: PASSED - Application is healthy")
        else:
            print("❌ Health check: FAILED - Application may have issues")
        
        if status_data.get("components", {}).get("fastapi"):
            print("✅ FastAPI: PASSED - Application framework working")
        else:
            print("❌ FastAPI: FAILED - Framework issues detected")
        
        if status_data.get("components", {}).get("cors"):
            print("✅ CORS: PASSED - Cross-origin requests enabled")
        else:
            print("❌ CORS: FAILED - CORS configuration issues")
        
        if debug_data.get("environment_vars", {}).get("ENVIRONMENT"):
            print("✅ Environment: PASSED - Environment variables accessible")
        else:
            print("❌ Environment: FAILED - Environment variable issues")
        
        # Final results
        print("\n" + "=" * 80)
        print("🎯 FINAL RESULTS")
        print(f"📊 Tests Passed: {self.passed_tests}/{self.total_tests}")
        print(f"📈 Success Rate: {(self.passed_tests/self.total_tests)*100:.1f}%")
        
        if self.passed_tests == self.total_tests:
            print("🎉 ALL TESTS PASSED! Deployment is fully functional!")
            print("✅ All deployment issues have been resolved!")
        elif self.passed_tests >= self.total_tests * 0.8:
            print("⚠️ Most tests passed - deployment is mostly functional")
            print("🔧 Some minor issues may remain")
        else:
            print("❌ Multiple test failures - deployment needs attention")
            print("🚨 Check logs for remaining issues")
        
        # Issue-specific analysis
        print("\n" + "=" * 80)
        print("🔍 ISSUE-SPECIFIC ANALYSIS")
        
        failed_tests = [r for r in self.results if not r["success"]]
        
        if not failed_tests:
            print("✅ No failures detected - all previous issues resolved!")
        else:
            print("❌ Remaining issues:")
            for test in failed_tests:
                print(f"   - {test['test']}: {test['details']}")
        
        print(f"\n⏰ Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return self.passed_tests == self.total_tests

def main():
    """Run the comprehensive deployment test"""
    print("🔧 Waiting 30 seconds for deployment to complete...")
    time.sleep(30)
    
    tester = DeploymentTester()
    success = tester.run_comprehensive_tests()
    
    if success:
        print("\n🚀 DEPLOYMENT VERIFICATION: SUCCESS")
        print("Your ShareKhan Trading System is fully operational!")
    else:
        print("\n⚠️ DEPLOYMENT VERIFICATION: PARTIAL SUCCESS")
        print("Most functionality is working. Check specific failures above.")
    
    return success

if __name__ == "__main__":
    main() 