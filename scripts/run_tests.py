#!/usr/bin/env python3
"""
Comprehensive Test Runner for Crypto Trading System
Executes sanity tests, API tests, and generates reports
"""

import os
import sys
import subprocess
import argparse
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestRunner:
    """Comprehensive test runner for the trading system"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_results = {}
        self.start_time = time.time()
    
    def setup_test_environment(self):
        """Setup test environment and dependencies"""
        logger.info("Setting up test environment...")
        
        # Set test environment variables
        os.environ["TESTING"] = "true"
        os.environ["ENVIRONMENT"] = "testing"
        os.environ["DATABASE_URL"] = "sqlite:///test.db"
        os.environ["REDIS_URL"] = "redis://localhost:6379/15"
        os.environ["LOG_LEVEL"] = "DEBUG"
        
        # Create necessary directories
        test_dirs = ["logs", "data", "backups", "reports"]
        for dir_name in test_dirs:
            (self.project_root / dir_name).mkdir(exist_ok=True)
        
        logger.info("Test environment setup complete")
    
    def run_sanity_tests(self) -> Dict:
        """Run basic sanity tests"""
        logger.info("Running sanity tests...")
        
        cmd = [
            sys.executable, "-m", "pytest", 
            "tests/test_sanity.py",
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=reports/sanity_report.json"
        ]
        
        result = self._run_command(cmd, "Sanity Tests")
        self.test_results["sanity"] = result
        return result
    
    def run_api_tests(self) -> Dict:
        """Run API tests"""
        logger.info("Running API tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/",
            "-m", "api",
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=reports/api_report.json"
        ]
        
        result = self._run_command(cmd, "API Tests")
        self.test_results["api"] = result
        return result
    
    def run_unit_tests(self) -> Dict:
        """Run unit tests"""
        logger.info("Running unit tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/",
            "-m", "unit",
            "-v",
            "--tb=short",
            "--cov=src",
            "--cov-report=html:reports/coverage_html",
            "--cov-report=json:reports/coverage.json",
            "--json-report",
            "--json-report-file=reports/unit_report.json"
        ]
        
        result = self._run_command(cmd, "Unit Tests")
        self.test_results["unit"] = result
        return result
    
    def run_integration_tests(self) -> Dict:
        """Run integration tests"""
        logger.info("Running integration tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/",
            "-m", "integration",
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=reports/integration_report.json"
        ]
        
        result = self._run_command(cmd, "Integration Tests")
        self.test_results["integration"] = result
        return result
    
    def run_performance_tests(self) -> Dict:
        """Run performance tests"""
        logger.info("Running performance tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/",
            "-m", "slow",
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=reports/performance_report.json"
        ]
        
        result = self._run_command(cmd, "Performance Tests")
        self.test_results["performance"] = result
        return result
    
    def test_docker_build(self) -> Dict:
        """Test Docker build process"""
        logger.info("Testing Docker build...")
        
        # Test Dockerfile syntax
        cmd = ["docker", "build", "--help"]
        docker_available = self._run_command(cmd, "Docker Availability", capture_output=True)
        
        if docker_available["success"]:
            # Test actual build
            cmd = [
                "docker", "build", 
                "-t", "trading-system-test",
                "--target", "production",
                "."
            ]
            result = self._run_command(cmd, "Docker Build")
        else:
            result = {
                "success": False,
                "message": "Docker not available",
                "duration": 0
            }
        
        self.test_results["docker_build"] = result
        return result
    
    def test_docker_compose(self) -> Dict:
        """Test docker-compose configuration"""
        logger.info("Testing Docker Compose...")
        
        # Test docker-compose syntax
        cmd = ["docker-compose", "config"]
        result = self._run_command(cmd, "Docker Compose Config", capture_output=True)
        
        if result["success"]:
            # Test enhanced compose file if it exists
            if (self.project_root / "docker-compose.enhanced.yml").exists():
                cmd = ["docker-compose", "-f", "docker-compose.enhanced.yml", "config"]
                enhanced_result = self._run_command(cmd, "Enhanced Docker Compose Config", capture_output=True)
                result["enhanced"] = enhanced_result["success"]
        
        self.test_results["docker_compose"] = result
        return result
    
    def run_health_checks(self) -> Dict:
        """Run application health checks"""
        logger.info("Running health checks...")
        
        # Start application in background for testing
        import threading
        import time
        
        def start_app():
            try:
                subprocess.run([
                    sys.executable, "app.py"
                ], timeout=30, capture_output=True)
            except subprocess.TimeoutExpired:
                pass  # Expected for health check
        
        # Start app in thread
        app_thread = threading.Thread(target=start_app)
        app_thread.daemon = True
        app_thread.start()
        
        # Wait for startup
        time.sleep(5)
        
        # Test health endpoints
        health_results = []
        
        try:
            import httpx
            
            endpoints = [
                "http://localhost:8000/api/health/",
                "http://localhost:8000/api/health/liveness",
                "http://localhost:8000/api/health/readiness"
            ]
            
            for endpoint in endpoints:
                try:
                    response = httpx.get(endpoint, timeout=5)
                    health_results.append({
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "success": response.status_code == 200
                    })
                except Exception as e:
                    health_results.append({
                        "endpoint": endpoint,
                        "error": str(e),
                        "success": False
                    })
        
        except ImportError:
            health_results.append({
                "error": "httpx not available for health checks",
                "success": False
            })
        
        result = {
            "success": any(r.get("success", False) for r in health_results),
            "results": health_results,
            "duration": 0
        }
        
        self.test_results["health_checks"] = result
        return result
    
    def _run_command(self, cmd: List[str], description: str, capture_output: bool = False) -> Dict:
        """Run a command and return result details"""
        start = time.time()
        
        try:
            if capture_output:
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=300,
                    cwd=self.project_root
                )
            else:
                result = subprocess.run(
                    cmd, 
                    timeout=300,
                    cwd=self.project_root
                )
            
            duration = time.time() - start
            success = result.returncode == 0
            
            return {
                "success": success,
                "returncode": result.returncode,
                "duration": duration,
                "command": " ".join(cmd),
                "description": description
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timed out",
                "duration": time.time() - start,
                "command": " ".join(cmd),
                "description": description
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "Command not found",
                "duration": time.time() - start,
                "command": " ".join(cmd),
                "description": description
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start,
                "command": " ".join(cmd),
                "description": description
            }
    
    def generate_report(self) -> Dict:
        """Generate comprehensive test report"""
        total_duration = time.time() - self.start_time
        
        # Calculate summary statistics
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results.values() if result.get("success", False))
        
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": total_duration,
            "summary": {
                "total_test_suites": total_tests,
                "successful_test_suites": successful_tests,
                "failed_test_suites": total_tests - successful_tests,
                "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0
            },
            "details": self.test_results,
            "recommendations": self._generate_recommendations()
        }
        
        # Save report
        report_file = self.project_root / "reports" / "test_summary.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Test report saved to {report_file}")
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        if not self.test_results.get("sanity", {}).get("success", False):
            recommendations.append("Fix basic sanity test failures before proceeding")
        
        if not self.test_results.get("docker_build", {}).get("success", False):
            recommendations.append("Fix Docker build issues for proper containerization")
        
        if not self.test_results.get("health_checks", {}).get("success", False):
            recommendations.append("Implement or fix health check endpoints")
        
        if self.test_results.get("unit", {}).get("success", False):
            recommendations.append("Excellent unit test coverage!")
        
        if not self.test_results.get("api", {}).get("success", False):
            recommendations.append("Fix API test failures for reliable endpoints")
        
        return recommendations
    
    def print_summary(self):
        """Print test summary to console"""
        print("\n" + "="*60)
        print("CRYPTO TRADING SYSTEM - TEST SUMMARY")
        print("="*60)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
            duration = result.get("duration", 0)
            print(f"{test_name.upper():<20} {status} ({duration:.1f}s)")
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results.values() if result.get("success", False))
        
        print("-"*60)
        print(f"TOTAL: {successful_tests}/{total_tests} test suites passed")
        print(f"SUCCESS RATE: {(successful_tests/total_tests*100):.1f}%" if total_tests > 0 else "NO TESTS RUN")
        print(f"TOTAL DURATION: {time.time() - self.start_time:.1f}s")
        print("="*60)

def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description="Crypto Trading System Test Runner")
    parser.add_argument("--sanity", action="store_true", help="Run sanity tests only")
    parser.add_argument("--api", action="store_true", help="Run API tests only")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only")
    parser.add_argument("--docker", action="store_true", help="Run Docker tests only")
    parser.add_argument("--health", action="store_true", help="Run health checks only")
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only (sanity + API)")
    
    args = parser.parse_args()
    
    # Determine which tests to run
    run_all = args.all or not any([
        args.sanity, args.api, args.unit, args.integration, 
        args.performance, args.docker, args.health, args.quick
    ])
    
    runner = TestRunner(project_root)
    runner.setup_test_environment()
    
    try:
        if args.quick:
            runner.run_sanity_tests()
            runner.run_api_tests()
        elif run_all:
            runner.run_sanity_tests()
            runner.run_api_tests()
            runner.run_unit_tests()
            runner.run_integration_tests()
            runner.test_docker_build()
            runner.test_docker_compose()
            runner.run_health_checks()
            # Skip performance tests in "all" mode unless explicitly requested
        else:
            if args.sanity:
                runner.run_sanity_tests()
            if args.api:
                runner.run_api_tests()
            if args.unit:
                runner.run_unit_tests()
            if args.integration:
                runner.run_integration_tests()
            if args.performance:
                runner.run_performance_tests()
            if args.docker:
                runner.test_docker_build()
                runner.test_docker_compose()
            if args.health:
                runner.run_health_checks()
        
        # Generate and display results
        runner.generate_report()
        runner.print_summary()
        
        # Exit with appropriate code
        success_rate = len([r for r in runner.test_results.values() if r.get("success", False)]) / len(runner.test_results)
        sys.exit(0 if success_rate >= 0.8 else 1)
        
    except KeyboardInterrupt:
        logger.info("Test run interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test run failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()