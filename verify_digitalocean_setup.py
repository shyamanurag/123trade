
#!/usr/bin/env python3
"""
DigitalOcean Environment Verification Script
Verify that all required environment variables and connections are working
"""

import os
import asyncio
import asyncpg
import redis.asyncio as redis
from datetime import datetime

async def verify_environment():
    """Verify DigitalOcean environment setup"""
    print("🔍 DIGITALOCEAN ENVIRONMENT VERIFICATION")
    print("=" * 60)
    
    # Check environment variables
    required_vars = [
        'DATABASE_URL', 'REDIS_URL', 'JWT_SECRET', 
        'ZERODHA_API_KEY', 'TRUEDATA_USERNAME'
    ]
    
    print("\n📋 Environment Variables:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            masked_value = value[:20] + "..." if len(value) > 20 else value
            print(f"   ✅ {var}: {masked_value}")
        else:
            print(f"   ❌ {var}: Not set")
    
    # Test Redis connection
    print("\n🔴 Testing Redis Connection:")
    try:
        redis_url = os.getenv('REDIS_URL')
        if redis_url:
            client = redis.from_url(
                redis_url,
                decode_responses=True,
                ssl_cert_reqs=None,
                ssl_check_hostname=False,
                socket_timeout=10
            )
            await client.ping()
            await client.set("test_key", "test_value", ex=10)
            test_value = await client.get("test_key")
            await client.close()
            
            if test_value == "test_value":
                print(f"   ✅ Redis connection successful")
                print(f"   ✅ Redis read/write operations working")
            else:
                print(f"   ❌ Redis read/write failed")
        else:
            print(f"   ❌ REDIS_URL not found")
    except Exception as e:
        print(f"   ❌ Redis connection failed: {e}")
    
    # Test Database connection
    print("\n🐘 Testing PostgreSQL Connection:")
    try:
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            conn = await asyncpg.connect(database_url)
            result = await conn.fetchval("SELECT version()")
            await conn.close()
            
            print(f"   ✅ Database connection successful")
            print(f"   ✅ PostgreSQL version: {result[:50]}...")
        else:
            print(f"   ❌ DATABASE_URL not found")
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
    
    # Test API endpoints
    print("\n🌐 Testing Application Endpoints:")
    try:
        import aiohttp
        app_url = os.getenv('APP_URL', 'https://algoauto-ua2iq.ondigitalocean.app')
        
        async with aiohttp.ClientSession() as session:
            # Test health endpoint
            async with session.get(f"{app_url}/health/ready", timeout=10) as response:
                if response.status == 200:
                    print(f"   ✅ Health endpoint responding")
                else:
                    print(f"   ❌ Health endpoint returned {response.status}")
            
            # Test API endpoint
            async with session.get(f"{app_url}/api/users", timeout=10) as response:
                if response.status in [200, 401]:  # 401 is expected without auth
                    print(f"   ✅ API endpoints accessible")
                else:
                    print(f"   ❌ API endpoint returned {response.status}")
                    
    except Exception as e:
        print(f"   ❌ API endpoint test failed: {e}")
    
    print(f"\n✅ Verification completed at {datetime.now()}")
    print("🚀 If all tests pass, your DigitalOcean deployment is ready!")

if __name__ == "__main__":
    asyncio.run(verify_environment())
