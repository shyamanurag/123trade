#!/usr/bin/env python3
"""
PRODUCTION ENVIRONMENT SETUP AND CRITICAL FIXES
===============================================

This script sets up the production environment variables and fixes critical issues:
1. Database schema fix (broker_user_id column)
2. Redis connection verification
3. Environment variable configuration for production

Run this on the production server or with production credentials.
"""

import os
import sys
import asyncio
import asyncpg
import redis
from datetime import datetime
from typing import Dict, Any

class ProductionEnvironmentSetup:
    def __init__(self):
        self.production_env = {
            # Database configuration
            'DATABASE_URL': os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/trading_db'),
            
            # Redis configuration  
            'REDIS_URL': os.getenv('REDIS_URL', 'redis://localhost:6379'),
            
            # ShareKhan configuration
            'SHAREKHAN_LOGIN_ID': os.getenv('SHAREKHAN_LOGIN_ID', 'username'),
            'SHAREKHAN_PASSWORD': os.getenv('SHAREKHAN_PASSWORD', 'password'),
            
            # ShareKhan configuration
            'SHAREKHAN_API_KEY': 'your_api_key_here',
            'SHAREKHAN_API_SECRET': 'your_api_secret_here',
            'SHAREKHAN_USER_ID': 'your_user_id_here',
            
            # Application configuration
            'ENVIRONMENT': 'production',
            'DEBUG': 'false',
            'LOG_LEVEL': 'INFO'
        }
        
        self.db_connection = None
        self.redis_client = None
        self.fixes_applied = []
        self.issues_found = []

    def setup_environment_variables(self):
        """Set up environment variables for production"""
        print("🔧 Setting up production environment variables...")
        
        for key, value in self.production_env.items():
            if key not in ['SHAREKHAN_API_KEY', 'SHAREKHAN_API_SECRET', 'SHAREKHAN_USER_ID']:
                os.environ[key] = value
                print(f"   ✓ {key} configured")
            else:
                print(f"   ⚠️  {key} needs to be set manually")
        
        print("✅ Environment variables configured")

    async def connect_to_production_database(self) -> bool:
        """Connect to production PostgreSQL database"""
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                self.issues_found.append("DATABASE_URL not configured")
                return False
            
            print("🔗 Connecting to production database...")
            self.db_connection = await asyncpg.connect(database_url)
            print("✅ Production database connected successfully")
            return True
            
        except Exception as e:
            self.issues_found.append(f"Production database connection failed: {str(e)}")
            print(f"❌ Production database connection failed: {str(e)}")
            return False

    async def fix_database_schema(self) -> bool:
        """Fix the critical database schema issue"""
        if not self.db_connection:
            return False
            
        try:
            print("\n🔧 Fixing database schema...")
            
            # Check current schema
            columns = await self.db_connection.fetch("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users'
            """)
            
            existing_columns = [col['column_name'] for col in columns]
            print(f"   Current columns: {existing_columns}")
            
            # Add broker_user_id column if missing
            if 'broker_user_id' not in existing_columns:
                print("   Adding broker_user_id column...")
                await self.db_connection.execute("""
                    ALTER TABLE users 
                    ADD COLUMN broker_user_id VARCHAR(50);
                """)
                
                # Create index
                await self.db_connection.execute("""
                    CREATE INDEX IF NOT EXISTS idx_users_broker_user_id 
                    ON users(broker_user_id);
                """)
                
                # Update existing users
                await self.db_connection.execute("""
                    UPDATE users 
                    SET broker_user_id = 'MASTER_USER_001'
                    WHERE broker_user_id IS NULL;
                """)
                
                self.fixes_applied.append("Added broker_user_id column to users table")
                print("   ✅ broker_user_id column added successfully")
            else:
                print("   ✅ broker_user_id column already exists")
            
            # Test user creation
            test_user_id = f"test_user_{int(datetime.now().timestamp())}"
            await self.db_connection.execute("""
                INSERT INTO users (user_id, broker_user_id, created_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO NOTHING
            """, test_user_id, "TEST_BROKER_001", datetime.now())
            
            # Verify and cleanup
            user_exists = await self.db_connection.fetchval("""
                SELECT EXISTS(SELECT 1 FROM users WHERE user_id = $1)
            """, test_user_id)
            
            if user_exists:
                await self.db_connection.execute("""
                    DELETE FROM users WHERE user_id = $1
                """, test_user_id)
                print("   ✅ User creation test passed")
                return True
            else:
                self.issues_found.append("User creation test failed")
                return False
                
        except Exception as e:
            self.issues_found.append(f"Database schema fix failed: {str(e)}")
            print(f"❌ Database schema fix failed: {str(e)}")
            return False

    def connect_to_production_redis(self) -> bool:
        """Connect to production Redis"""
        try:
            redis_url = os.getenv('REDIS_URL')
            if not redis_url:
                self.issues_found.append("REDIS_URL not configured")
                return False
            
            print("\n🔗 Connecting to production Redis...")
            
            # SSL connection for Digital Ocean managed Redis
            self.redis_client = redis.from_url(
                redis_url,
                ssl_cert_reqs=None,
                socket_connect_timeout=10,
                socket_timeout=10,
                retry_on_timeout=True
            )
            
            # Test connection
            self.redis_client.ping()
            print("✅ Production Redis connected successfully")
            return True
            
        except Exception as e:
            self.issues_found.append(f"Production Redis connection failed: {str(e)}")
            print(f"❌ Production Redis connection failed: {str(e)}")
            return False

    def test_redis_operations(self) -> bool:
        """Test critical Redis operations for trading system"""
        if not self.redis_client:
            return False
            
        try:
            print("🧪 Testing Redis operations...")
            
            # Test ShareKhan token storage
            token_key = "sharekhan:token:MASTER_USER_001"
            test_token = f"test_token_{int(datetime.now().timestamp())}"
            
            self.redis_client.set(token_key, test_token, ex=86400)
            retrieved_token = self.redis_client.get(token_key)
            
            if retrieved_token and retrieved_token.decode() == test_token:
                print("   ✅ ShareKhan token storage working")
            else:
                self.issues_found.append("ShareKhan token storage failed")
                return False
            
            # Test position tracking hash operations
            position_key = "positions:MASTER_USER_001"
            position_data = {
                "NIFTY": '{"quantity": 100, "entry_price": 19500.0, "current_price": 19525.0}',
                "BANKNIFTY": '{"quantity": 50, "entry_price": 45000.0, "current_price": 45100.0}'
            }
            
            self.redis_client.hset(position_key, mapping=position_data)
            retrieved_positions = self.redis_client.hgetall(position_key)
            
            if retrieved_positions and len(retrieved_positions) == 2:
                print("   ✅ Position tracking working")
            else:
                self.issues_found.append("Position tracking failed")
                return False
            
            # Test market data caching
            market_data_key = "market_data:NIFTY"
            market_data = '{"symbol": "NIFTY", "price": 19525.0, "timestamp": "2025-07-18T13:53:00"}'
            
            self.redis_client.set(market_data_key, market_data, ex=300)  # 5 minutes
            retrieved_data = self.redis_client.get(market_data_key)
            
            if retrieved_data and retrieved_data.decode() == market_data:
                print("   ✅ Market data caching working")
            else:
                self.issues_found.append("Market data caching failed")
                return False
            
            # Cleanup test data
            self.redis_client.delete(token_key, position_key, market_data_key)
            
            print("✅ All Redis operations verified")
            return True
            
        except Exception as e:
            self.issues_found.append(f"Redis operations test failed: {str(e)}")
            print(f"❌ Redis operations test failed: {str(e)}")
            return False

    async def create_production_deployment_script(self):
        """Create deployment script for production"""
        deployment_script = """#!/bin/bash
# Production Deployment Script
# Run this on the production server

echo "🚀 Starting production deployment..."

# Set environment variables (replace with actual values in production)
export DATABASE_URL="$DATABASE_URL"
export REDIS_URL="$REDIS_URL"
export SHAREKHAN_LOGIN_ID="$SHAREKHAN_LOGIN_ID"
export SHAREKHAN_PASSWORD="$SHAREKHAN_PASSWORD"
export ENVIRONMENT="production"
export DEBUG="false"
export LOG_LEVEL="INFO"

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Run database schema fix
echo "🔧 Fixing database schema..."
python fix_critical_production_issues.py

# Start the application
echo "🚀 Starting trading system..."
gunicorn main:app --bind 0.0.0.0:8000 --workers 4 --worker-class uvicorn.workers.UvicornWorker --timeout 300

echo "✅ Production deployment complete!"
"""
        
        with open('deploy_production.sh', 'w') as f:
            f.write(deployment_script)
        
        print("📝 Created deploy_production.sh script")

    async def run_production_setup(self):
        """Run complete production setup and fixes"""
        print("🚀 PRODUCTION ENVIRONMENT SETUP")
        print("=" * 50)
        print(f"Started at: {datetime.now()}")
        
        # Step 1: Setup environment
        self.setup_environment_variables()
        
        # Step 2: Fix database
        print("\n📊 DATABASE FIXES")
        print("-" * 30)
        
        if await self.connect_to_production_database():
            await self.fix_database_schema()
        
        # Step 3: Fix Redis
        print("\n🔴 REDIS FIXES")
        print("-" * 30)
        
        if self.connect_to_production_redis():
            self.test_redis_operations()
        
        # Step 4: Create deployment script
        await self.create_production_deployment_script()
        
        # Summary
        print("\n📋 PRODUCTION SETUP SUMMARY")
        print("=" * 50)
        
        if self.fixes_applied:
            print("✅ FIXES APPLIED:")
            for fix in self.fixes_applied:
                print(f"   ✓ {fix}")
        
        if self.issues_found:
            print("\n❌ ISSUES FOUND:")
            for issue in self.issues_found:
                print(f"   ✗ {issue}")
        
        if not self.issues_found:
            print("\n🎉 PRODUCTION ENVIRONMENT READY!")
            print("   ✓ Database schema fixed")
            print("   ✓ Redis connection verified")
            print("   ✓ All critical issues resolved")
            print("   ✓ System ready for production deployment")
        else:
            print(f"\n⚠️  {len(self.issues_found)} ISSUES REMAIN")
            print("   System may not function properly until resolved")
        
        # Cleanup
        if self.db_connection:
            await self.db_connection.close()
        if self.redis_client:
            self.redis_client.close()

async def main():
    """Main function"""
    setup = ProductionEnvironmentSetup()
    await setup.run_production_setup()

if __name__ == "__main__":
    asyncio.run(main())
