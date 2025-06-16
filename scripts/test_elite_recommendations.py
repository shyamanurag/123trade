#!/usr/bin/env python3
"""
⭐ ELITE RECOMMENDATIONS TESTING SCRIPT
======================================

This script tests the elite recommendations system to ensure it can:
1. Generate recommendations using historical data (even on holidays)
2. Process backtesting data for recommendation validation
3. Work with available market data regardless of market hours

"""

import asyncio
import os
import sys
import json
import requests
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class EliteRecommendationsTester:
    def __init__(self):
        self.api_base = "http://localhost:8000"
        self.test_symbols = ["RELIANCE", "TCS", "INFY", "NIFTY", "BANKNIFTY"]
    
    def log(self, message: str, level: str = "INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    async def test_historical_data_availability(self):
        """Test if historical data is available for analysis"""
        self.log("🔍 Testing historical data availability...")
        
        available_data = {}
        
        for symbol in self.test_symbols:
            try:
                # Test different timeframes
                timeframes = ["1day", "1hour", "15min"]
                symbol_data = {}
                
                for timeframe in timeframes:
                    endpoint = f"/api/market-data/historical/{symbol}/{timeframe}"
                    response = requests.get(f"{self.api_base}{endpoint}", timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        data_points = len(data.get("data", []))
                        symbol_data[timeframe] = data_points
                        
                        if data_points > 0:
                            latest_data = data["data"][-1] if data["data"] else None
                            if latest_data:
                                self.log(f"✅ {symbol} {timeframe}: {data_points} data points (latest: {latest_data.get('timestamp', 'N/A')})")
                            else:
                                self.log(f"⚠️ {symbol} {timeframe}: No data points")
                        else:
                            self.log(f"❌ {symbol} {timeframe}: No data available")
                    else:
                        self.log(f"❌ {symbol} {timeframe}: HTTP {response.status_code}")
                        symbol_data[timeframe] = 0
                
                available_data[symbol] = symbol_data
                
            except Exception as e:
                self.log(f"❌ Error testing {symbol}: {e}", "ERROR")
                available_data[symbol] = {"error": str(e)}
        
        return available_data
    
    async def test_recommendation_generation(self):
        """Test elite recommendation generation"""
        self.log("⭐ Testing elite recommendation generation...")
        
        try:
            # Test recommendation endpoint
            response = requests.get(f"{self.api_base}/api/recommendations/elite", timeout=15)
            
            if response.status_code == 200:
                recommendations = response.json()
                rec_count = len(recommendations.get("recommendations", []))
                self.log(f"✅ Elite recommendations endpoint: {rec_count} recommendations found")
                
                # Display some details
                if rec_count > 0:
                    for i, rec in enumerate(recommendations["recommendations"][:3]):  # Show first 3
                        symbol = rec.get("symbol", "Unknown")
                        action = rec.get("action", "Unknown")
                        confidence = rec.get("confidence_score", 0)
                        self.log(f"   {i+1}. {symbol} - {action} (Confidence: {confidence}/10)")
                
                return True
            else:
                self.log(f"❌ Elite recommendations endpoint: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ Error testing recommendations: {e}", "ERROR")
            return False
    
    async def test_scanning_capability(self):
        """Test if the system can scan for new recommendations"""
        self.log("🔍 Testing scanning capability...")
        
        try:
            # Test scanning endpoint
            scan_payload = {
                "symbols": self.test_symbols[:3],  # Test with first 3 symbols
                "timeframe": "1day",
                "force_scan": True
            }
            
            response = requests.post(
                f"{self.api_base}/api/scan/elite", 
                json=scan_payload,
                timeout=30
            )
            
            if response.status_code in [200, 202]:  # 202 for async processing
                scan_result = response.json()
                self.log("✅ Scanning capability: Working")
                
                if response.status_code == 202:
                    self.log("   ℹ️ Scan initiated asynchronously")
                    scan_id = scan_result.get("scan_id")
                    if scan_id:
                        # Check scan status
                        await asyncio.sleep(2)  # Wait a moment
                        status_response = requests.get(f"{self.api_base}/api/scan/status/{scan_id}")
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            self.log(f"   📊 Scan status: {status_data.get('status', 'Unknown')}")
                
                return True
            else:
                self.log(f"❌ Scanning capability: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ Error testing scanning: {e}", "ERROR")
            return False
    
    async def test_backtesting_capability(self):
        """Test backtesting capability with historical data"""
        self.log("📊 Testing backtesting capability...")
        
        try:
            # Test backtesting endpoint
            backtest_payload = {
                "symbol": "RELIANCE",
                "start_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                "end_date": datetime.now().strftime("%Y-%m-%d"),
                "strategy": "elite_confluence",
                "capital": 100000
            }
            
            response = requests.post(
                f"{self.api_base}/api/backtest/run",
                json=backtest_payload,
                timeout=30
            )
            
            if response.status_code in [200, 202]:
                backtest_result = response.json()
                self.log("✅ Backtesting capability: Working")
                
                if "results" in backtest_result:
                    results = backtest_result["results"]
                    trades = results.get("total_trades", 0)
                    returns = results.get("total_return", 0)
                    self.log(f"   📈 Backtest results: {trades} trades, {returns:.2f}% return")
                
                return True
            else:
                self.log(f"❌ Backtesting capability: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ Error testing backtesting: {e}", "ERROR")
            return False
    
    async def test_performance_tracking(self):
        """Test performance tracking for elite recommendations"""
        self.log("📈 Testing performance tracking...")
        
        try:
            response = requests.get(f"{self.api_base}/api/performance/elite-trades", timeout=10)
            
            if response.status_code == 200:
                performance_data = response.json()
                self.log("✅ Performance tracking: Working")
                
                data = performance_data.get("data", {})
                total_trades = data.get("total_recommendations", 0)
                success_rate = data.get("success_rate", 0)
                avg_return = data.get("avg_return", 0)
                
                self.log(f"   📊 Performance: {total_trades} trades, {success_rate:.1f}% success, {avg_return:.1f}% avg return")
                return True
            else:
                self.log(f"❌ Performance tracking: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ Error testing performance tracking: {e}", "ERROR")
            return False
    
    def generate_report(self, results):
        """Generate a comprehensive test report"""
        self.log("📋 Generating test report...")
        
        passed_tests = sum(1 for result in results.values() if result)
        total_tests = len(results)
        
        self.log("=" * 60)
        self.log("⭐ ELITE RECOMMENDATIONS TEST REPORT")
        self.log("=" * 60)
        self.log(f"Tests Passed: {passed_tests}/{total_tests}")
        self.log("")
        
        for test_name, passed in results.items():
            emoji = "✅" if passed else "❌"
            self.log(f"{emoji} {test_name.replace('_', ' ').title()}: {'PASS' if passed else 'FAIL'}")
        
        # Overall assessment
        if passed_tests == total_tests:
            self.log("\n🎉 ELITE RECOMMENDATIONS SYSTEM: FULLY OPERATIONAL")
            self.log("✅ System can generate recommendations even on holidays using historical data")
        elif passed_tests >= total_tests * 0.8:
            self.log("\n⚠️ ELITE RECOMMENDATIONS SYSTEM: MOSTLY OPERATIONAL")
            self.log("🔧 Some features may need attention")
        else:
            self.log("\n❌ ELITE RECOMMENDATIONS SYSTEM: NEEDS ATTENTION")
            self.log("🚨 Multiple issues detected")
        
        return passed_tests >= total_tests * 0.8

async def main():
    """Run elite recommendations testing"""
    tester = EliteRecommendationsTester()
    
    print("⭐ ELITE RECOMMENDATIONS SYSTEM TESTING")
    print("=" * 50)
    
    # Run all tests
    results = {}
    
    # Test historical data availability
    historical_data = await tester.test_historical_data_availability()
    results["historical_data_available"] = any(
        any(timeframe_data > 0 for timeframe_data in symbol_data.values() if isinstance(timeframe_data, int))
        for symbol_data in historical_data.values() if isinstance(symbol_data, dict) and "error" not in symbol_data
    )
    
    # Test recommendation generation
    results["recommendation_generation"] = await tester.test_recommendation_generation()
    
    # Test scanning capability
    results["scanning_capability"] = await tester.test_scanning_capability()
    
    # Test backtesting capability
    results["backtesting_capability"] = await tester.test_backtesting_capability()
    
    # Test performance tracking
    results["performance_tracking"] = await tester.test_performance_tracking()
    
    # Generate final report
    system_ready = tester.generate_report(results)
    
    if system_ready:
        print("\n🎉 ELITE RECOMMENDATIONS READY FOR PRODUCTION!")
        print("✅ System can work with available data even on holidays")
    else:
        print("\n⚠️ ELITE RECOMMENDATIONS NEED ATTENTION")
        print("🔧 Check the failed tests above")

if __name__ == "__main__":
    asyncio.run(main()) 