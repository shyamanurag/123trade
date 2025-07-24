#!/usr/bin/env python3
"""
🔍 PRODUCTION SYSTEM VERIFICATION SCRIPT
=======================================

This script comprehensively checks:
1. TrueData connectivity and data flow
2. Remaining mock data in the system
3. Health monitoring system status
4. Elite trade recommendations system
5. Autonomous trading system readiness

Run this to verify everything is working before market opens.
"""

import asyncio
import os
import sys
import json
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ProductionSystemVerifier:
    def __init__(self):
        self.api_base = "http://localhost:8000"  # Change to production URL if needed
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "UNKNOWN",
            "checks": {},
            "recommendations": []
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    async def verify_truedata_connectivity(self):
        """1. Verify TrueData is connected and pushing data"""
        self.log("🔍 Checking TrueData connectivity...")
        
        try:
            # Check health endpoint
            response = requests.get(f"{self.api_base}/health", timeout=10)
            health_data = response.json()
            
            truedata_status = "UNKNOWN"
            data_flow = False
            
            # Check TrueData specific health
            if "truedata" in health_data.get("components", {}):
                truedata_health = health_data["components"]["truedata"]
                truedata_status = truedata_health.get("status", "UNKNOWN")
            
            # Check for data flow - try to get market data
            try:
                data_response = requests.get(f"{self.api_base}/api/market-data/symbols", timeout=5)
                if data_response.status_code == 200:
                    symbols_data = data_response.json()
                    data_flow = len(symbols_data.get("symbols", [])) > 0
            except:
                pass
            
            # Check historical data availability 
            historical_data = False
            try:
                hist_response = requests.get(f"{self.api_base}/api/market-data/historical/NIFTY/1day", timeout=5)
                if hist_response.status_code == 200:
                    hist_data = hist_response.json()
                    historical_data = len(hist_data.get("data", [])) > 0
            except:
                pass
            
            self.results["checks"]["truedata"] = {
                "connection_status": truedata_status,
                "data_flow": data_flow,
                "historical_data": historical_data,
                "status": "PASS" if truedata_status == "HEALTHY" else "FAIL"
            }
            
            if truedata_status == "HEALTHY":
                self.log("✅ TrueData connection: HEALTHY")
            else:
                self.log("❌ TrueData connection: Issues detected", "WARNING")
                self.results["recommendations"].append("Check TrueData credentials and network connectivity")
            
            if data_flow:
                self.log("✅ Real-time data flow: Active")
            else:
                self.log("⚠️ Real-time data flow: No data detected", "WARNING")
            
            if historical_data:
                self.log("✅ Historical data: Available")
            else:
                self.log("⚠️ Historical data: Not available", "WARNING")
                
        except Exception as e:
            self.log(f"❌ TrueData check failed: {e}", "ERROR")
            self.results["checks"]["truedata"] = {"status": "FAIL", "error": str(e)}
    
    def check_mock_data_removal(self):
        """2. Check for remaining mock data in the system"""
        self.log("🔍 Checking for remaining mock data...")
        
        mock_patterns = [
            "₹25,750", "₹1.2Cr", "68.2%", "157 trades", "23 users",
            "mock_data", "demo_user", "test_trade"
        ]
        
        mock_files_found = []
        frontend_path = "src/frontend/components"
        
        if os.path.exists(frontend_path):
            for root, dirs, files in os.walk(frontend_path):
                for file in files:
                    if file.endswith(('.jsx', '.js')):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                for pattern in mock_patterns:
                                    if pattern in content:
                                        mock_files_found.append({
                                            "file": file_path,
                                            "pattern": pattern
                                        })
                        except:
                            pass
        
        self.results["checks"]["mock_data"] = {
            "files_with_mock_data": mock_files_found,
            "status": "PASS" if len(mock_files_found) == 0 else "FAIL"
        }
        
        if len(mock_files_found) == 0:
            self.log("✅ Mock data removal: Complete")
        else:
            self.log(f"❌ Found {len(mock_files_found)} files with mock data", "WARNING")
            for mock_file in mock_files_found[:3]:  # Show first 3
                self.log(f"   - {mock_file['file']}: {mock_file['pattern']}")
    
    async def verify_health_monitoring(self):
        """3. Verify health monitoring system is working"""
        self.log("🔍 Checking health monitoring system...")
        
        try:
            # Check main health endpoint
            response = requests.get(f"{self.api_base}/health", timeout=10)
            health_data = response.json()
            
            components_checked = len(health_data.get("components", {}))
            overall_status = health_data.get("status", "UNKNOWN")
            
            # Check specific monitoring endpoints
            monitoring_endpoints = [
                "/api/monitoring/system-stats",
                "/api/monitoring/trading-status", 
                "/api/monitoring/connections"
            ]
            
            active_monitoring = 0
            for endpoint in monitoring_endpoints:
                try:
                    resp = requests.get(f"{self.api_base}{endpoint}", timeout=5)
                    if resp.status_code == 200:
                        active_monitoring += 1
                except:
                    pass
            
            self.results["checks"]["health_monitoring"] = {
                "overall_status": overall_status,
                "components_monitored": components_checked,
                "monitoring_endpoints_active": active_monitoring,
                "status": "PASS" if overall_status == "HEALTHY" and components_checked > 0 else "FAIL"
            }
            
            if overall_status == "HEALTHY":
                self.log(f"✅ Health monitoring: {components_checked} components monitored")
            else:
                self.log("❌ Health monitoring: Issues detected", "WARNING")
                
        except Exception as e:
            self.log(f"❌ Health monitoring check failed: {e}", "ERROR")
            self.results["checks"]["health_monitoring"] = {"status": "FAIL", "error": str(e)}
    
    async def verify_elite_recommendations(self):
        """4. Verify elite recommendations system"""
        self.log("🔍 Checking elite recommendations system...")
        
        try:
            # Check recommendations endpoint
            response = requests.get(f"{self.api_base}/api/recommendations/elite", timeout=10)
            
            if response.status_code == 200:
                recommendations = response.json()
                rec_count = len(recommendations.get("recommendations", []))
                
                # Check scanning capability (should work even on holidays)
                scan_response = requests.post(f"{self.api_base}/api/scan/elite", timeout=15)
                scan_works = scan_response.status_code in [200, 202]  # 202 for async processing
                
                self.results["checks"]["elite_recommendations"] = {
                    "endpoint_accessible": True,
                    "recommendations_count": rec_count,
                    "scanning_capability": scan_works,
                    "status": "PASS" if scan_works else "PARTIAL"
                }
                
                self.log(f"✅ Elite recommendations: {rec_count} active recommendations")
                
                if scan_works:
                    self.log("✅ Scanning system: Ready to generate recommendations")
                else:
                    self.log("⚠️ Scanning system: May need attention", "WARNING")
                    
            else:
                raise Exception(f"API returned {response.status_code}")
                
        except Exception as e:
            self.log(f"❌ Elite recommendations check failed: {e}", "ERROR")
            self.results["checks"]["elite_recommendations"] = {"status": "FAIL", "error": str(e)}
    
    async def verify_autonomous_system_readiness(self):
        """5. Verify autonomous trading system readiness"""
        self.log("🔍 Checking autonomous trading system readiness...")
        
        try:
            # Check autonomous trading status
            response = requests.get(f"{self.api_base}/api/autonomous/status", timeout=10)
            
            if response.status_code == 200:
                status_data = response.json()
                
                system_enabled = status_data.get("enabled", False)
                strategies_loaded = len(status_data.get("strategies", []))
                risk_management = status_data.get("risk_management", {}).get("enabled", False)
                
                # Check if paper trading is disabled (for live trading)
                paper_trading = os.getenv("PAPER_TRADING", "true").lower() == "true"
                
                # Check Zerodha connection
                zerodha_connected = False
                try:
                    zerodha_resp = requests.get(f"{self.api_base}/api/trading/account-info", timeout=5)
                    zerodha_connected = zerodha_resp.status_code == 200
                except:
                    pass
                
                readiness_score = sum([
                    system_enabled,
                    strategies_loaded > 0,
                    risk_management,
                    not paper_trading,  # Live trading enabled
                    zerodha_connected
                ]) / 5 * 100
                
                self.results["checks"]["autonomous_system"] = {
                    "system_enabled": system_enabled,
                    "strategies_loaded": strategies_loaded,
                    "risk_management": risk_management,
                    "live_trading_mode": not paper_trading,
                    "zerodha_connected": zerodha_connected,
                    "readiness_percentage": readiness_score,
                    "status": "PASS" if readiness_score >= 80 else "FAIL"
                }
                
                self.log(f"📊 Autonomous system readiness: {readiness_score:.1f}%")
                
                if system_enabled:
                    self.log("✅ Autonomous trading: Enabled")
                else:
                    self.log("❌ Autonomous trading: Disabled", "WARNING")
                
                if not paper_trading:
                    self.log("✅ Live trading mode: Enabled")
                else:
                    self.log("⚠️ Paper trading mode: Active", "WARNING")
                    self.results["recommendations"].append("Disable paper trading for live market operations")
                
                if zerodha_connected:
                    self.log("✅ Zerodha connection: Active")
                else:
                    self.log("❌ Zerodha connection: Issues", "WARNING")
                    self.results["recommendations"].append("Check Zerodha API credentials and connection")
                    
            else:
                raise Exception(f"API returned {response.status_code}")
                
        except Exception as e:
            self.log(f"❌ Autonomous system check failed: {e}", "ERROR")
            self.results["checks"]["autonomous_system"] = {"status": "FAIL", "error": str(e)}
    
    def generate_final_report(self):
        """Generate final verification report"""
        self.log("📋 Generating final verification report...")
        
        passed_checks = sum(1 for check in self.results["checks"].values() 
                          if check.get("status") == "PASS")
        total_checks = len(self.results["checks"])
        
        if passed_checks == total_checks:
            self.results["overall_status"] = "READY"
            status_emoji = "🎉"
        elif passed_checks >= total_checks * 0.8:
            self.results["overall_status"] = "MOSTLY_READY" 
            status_emoji = "⚠️"
        else:
            self.results["overall_status"] = "NOT_READY"
            status_emoji = "❌"
        
        self.log("=" * 60)
        self.log(f"{status_emoji} PRODUCTION VERIFICATION REPORT")
        self.log("=" * 60)
        self.log(f"Overall Status: {self.results['overall_status']}")
        self.log(f"Checks Passed: {passed_checks}/{total_checks}")
        self.log("")
        
        for check_name, check_data in self.results["checks"].items():
            status = check_data.get("status", "UNKNOWN")
            emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
            self.log(f"{emoji} {check_name.replace('_', ' ').title()}: {status}")
        
        if self.results["recommendations"]:
            self.log("")
            self.log("🔧 RECOMMENDATIONS:")
            for i, rec in enumerate(self.results["recommendations"], 1):
                self.log(f"   {i}. {rec}")
        
        # Save detailed report
        report_file = f"production_verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        self.log(f"📄 Detailed report saved: {report_file}")
        return self.results["overall_status"]

async def main():
    """Run complete production verification"""
    verifier = ProductionSystemVerifier()
    
    print("🚀 PRODUCTION SYSTEM VERIFICATION STARTING...")
    print("=" * 60)
    
    # Run all verification checks
    await verifier.verify_truedata_connectivity()
    verifier.check_mock_data_removal()
    await verifier.verify_health_monitoring()
    await verifier.verify_elite_recommendations()
    await verifier.verify_autonomous_system_readiness()
    
    # Generate final report
    final_status = verifier.generate_final_report()
    
    if final_status == "READY":
        print("\n🎉 SYSTEM IS PRODUCTION READY!")
        print("✅ You can confidently start trading when market opens.")
    elif final_status == "MOSTLY_READY":
        print("\n⚠️ SYSTEM IS MOSTLY READY")
        print("🔧 Address the recommendations above before market opens.")
    else:
        print("\n❌ SYSTEM NEEDS ATTENTION")
        print("🚨 Critical issues must be resolved before trading.")
    
    return final_status

if __name__ == "__main__":
    asyncio.run(main()) 