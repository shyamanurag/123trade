#!/usr/bin/env python3
"""
PRODUCTION DEPLOYMENT WITH CRITICAL FIXES
=========================================

This script must be run on the production server to fix:
1. Database schema issue (broker_user_id column)
2. Redis connection verification
3. Complete system health check

Without these fixes, the system cannot function properly.
"""

import os
import sys
import asyncio
import subprocess
from datetime import datetime

class ProductionDeployment:
    def __init__(self):
        self.deployment_steps = []
        self.critical_issues = []
        
    def check_environment(self):
        """Check if we're in production environment"""
        print("🔍 Checking production environment...")
        
        required_env_vars = [
            'DATABASE_URL',
            'REDIS_URL', 
            'SHAREKHAN_LOGIN_ID',
            'SHAREKHAN_PASSWORD'
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing environment variables: {missing_vars}")
            print("\n🔧 TO FIX: Set these environment variables on production server:")
            print("export DATABASE_URL='<your_database_url>'")
            print("export REDIS_URL='<your_redis_url>'")
            print("export SHAREKHAN_LOGIN_ID='<your_sharekhan_login>'")
            print("export SHAREKHAN_PASSWORD='<your_sharekhan_password>'")
            return False
        
        print("✅ All environment variables present")
        return True
    
    def fix_database_schema(self):
        """Fix database schema using SQL script"""
        print("\n📊 FIXING DATABASE SCHEMA...")
        print("-" * 40)
        
        try:
            # Check if psql is available
            result = subprocess.run(['which', 'psql'], capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ psql not found. Install PostgreSQL client:")
                print("   sudo apt-get install postgresql-client")
                return False
            
            # Run the SQL fix script
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                print("❌ DATABASE_URL not set")
                return False
            
            print("🔧 Running database schema fix...")
            result = subprocess.run([
                'psql', database_url, '-f', 'fix_database_schema.sql'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Database schema fixed successfully")
                print(result.stdout)
                self.deployment_steps.append("Database schema fixed")
                return True
            else:
                print(f"❌ Database schema fix failed: {result.stderr}")
                self.critical_issues.append("Database schema fix failed")
                return False
                
        except Exception as e:
            print(f"❌ Database schema fix error: {str(e)}")
            self.critical_issues.append(f"Database schema fix error: {str(e)}")
            return False
    
    def test_redis_connection(self):
        """Test Redis connection"""
        print("\n🔴 TESTING REDIS CONNECTION...")
        print("-" * 40)
        
        try:
            import redis
            
            redis_url = os.getenv('REDIS_URL')
            if not redis_url:
                print("❌ REDIS_URL not set")
                return False
            
            print(f"🔗 Connecting to Redis: {redis_url[:50]}...")
            
            # SSL connection for Digital Ocean managed Redis
            client = redis.from_url(
                redis_url,
                ssl_cert_reqs=None,
                socket_connect_timeout=10,
                socket_timeout=10
            )
            
            # Test connection
            client.ping()
            print("✅ Redis connection successful")
            
            # Test operations
            test_key = "production:health:check"
            test_value = f"test_{datetime.now().timestamp()}"
            
            client.set(test_key, test_value, ex=60)
            retrieved = client.get(test_key)
            
            if retrieved and retrieved.decode() == test_value:
                print("✅ Redis operations working")
                client.delete(test_key)
                self.deployment_steps.append("Redis connection verified")
                return True
            else:
                print("❌ Redis operations failed")
                self.critical_issues.append("Redis operations failed")
                return False
                
        except Exception as e:
            print(f"❌ Redis connection failed: {str(e)}")
            self.critical_issues.append(f"Redis connection failed: {str(e)}")
            return False
    
    def restart_application(self):
        """Restart the application services"""
        print("\n🚀 RESTARTING APPLICATION...")
        print("-" * 40)
        
        try:
            # Kill existing processes
            print("🔄 Stopping existing processes...")
            subprocess.run(['pkill', '-f', 'gunicorn'], capture_output=True)
            subprocess.run(['pkill', '-f', 'uvicorn'], capture_output=True)
            
            # Wait a moment
            import time
            time.sleep(3)
            
            # Start new process
            print("🚀 Starting new application instance...")
            
            # Start in background
            process = subprocess.Popen([
                'gunicorn', 'main:app',
                '--bind', '0.0.0.0:8000',
                '--workers', '4',
                '--worker-class', 'uvicorn.workers.UvicornWorker',
                '--timeout', '300',
                '--daemon'
            ])
            
            # Wait a moment for startup
            time.sleep(5)
            
            # Check if process is running
            result = subprocess.run(['pgrep', '-f', 'gunicorn'], capture_output=True)
            if result.returncode == 0:
                print("✅ Application restarted successfully")
                self.deployment_steps.append("Application restarted")
                return True
            else:
                print("❌ Application restart failed")
                self.critical_issues.append("Application restart failed")
                return False
                
        except Exception as e:
            print(f"❌ Application restart error: {str(e)}")
            self.critical_issues.append(f"Application restart error: {str(e)}")
            return False
    
    def verify_system_health(self):
        """Verify system health after fixes"""
        print("\n🏥 SYSTEM HEALTH CHECK...")
        print("-" * 40)
        
        try:
            import requests
            import time
            
            # Wait for application to fully start
            time.sleep(10)
            
            # Test health endpoint
            response = requests.get('http://localhost:8000/health', timeout=30)
            
            if response.status_code == 200:
                print("✅ Application health check passed")
                self.deployment_steps.append("System health verified")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                self.critical_issues.append("Health check failed")
                return False
                
        except Exception as e:
            print(f"❌ Health check error: {str(e)}")
            self.critical_issues.append(f"Health check error: {str(e)}")
            return False
    
    def run_deployment(self):
        """Run complete production deployment"""
        print("🚀 PRODUCTION DEPLOYMENT WITH CRITICAL FIXES")
        print("=" * 60)
        print(f"Started at: {datetime.now()}")
        
        success = True
        
        # Step 1: Check environment
        if not self.check_environment():
            success = False
        
        # Step 2: Fix database schema
        if success and not self.fix_database_schema():
            success = False
        
        # Step 3: Test Redis
        if success and not self.test_redis_connection():
            success = False
        
        # Step 4: Restart application
        if success and not self.restart_application():
            success = False
        
        # Step 5: Verify system health
        if success and not self.verify_system_health():
            success = False
        
        # Summary
        print("\n📋 DEPLOYMENT SUMMARY")
        print("=" * 60)
        
        if self.deployment_steps:
            print("✅ COMPLETED STEPS:")
            for step in self.deployment_steps:
                print(f"   ✓ {step}")
        
        if self.critical_issues:
            print("\n❌ CRITICAL ISSUES:")
            for issue in self.critical_issues:
                print(f"   ✗ {issue}")
        
        if success and not self.critical_issues:
            print("\n🎉 DEPLOYMENT SUCCESSFUL!")
            print("   ✓ Database schema fixed")
            print("   ✓ Redis connection verified")
            print("   ✓ Application restarted")
            print("   ✓ System health verified")
            print("   🚀 TRADING SYSTEM IS NOW PRODUCTION READY!")
        else:
            print(f"\n💥 DEPLOYMENT FAILED!")
            print("   ❌ Critical issues must be resolved before system can work")
            print("   ❌ P&L updates will remain at ₹0.00 until fixed")
            print("   ❌ Analytics will not work without database fix")
            print("   ❌ Redis issues will cause system instability")
            
        return success

def main():
    """Main deployment function"""
    deployment = ProductionDeployment()
    success = deployment.run_deployment()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
