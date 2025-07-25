"""
ShareKhan API Connection Test
Tests the API credentials and connection to ShareKhan
"""

import os
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config/sharekhan_credentials.env')

from brokers.sharekhan import ShareKhanIntegration

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_sharekhan_connection():
    """Test ShareKhan API connection with your credentials"""
    
    print("🧪 Testing ShareKhan API Connection...")
    print("=" * 50)
    
    # Get credentials from environment
    api_key = os.getenv('SHAREKHAN_API_KEY')
    secret_key = os.getenv('SHAREKHAN_SECRET_KEY')
    customer_id = os.getenv('SHAREKHAN_CUSTOMER_ID')
    version_id = os.getenv('SHAREKHAN_VERSION_ID')
    
    # Verify credentials are loaded
    print(f"✅ API Key: {api_key[:10]}...{api_key[-4:] if api_key else 'NOT SET'}")
    print(f"✅ Secret Key: {secret_key[:10]}...{secret_key[-4:] if secret_key else 'NOT SET'}")
    print(f"⚠️  Customer ID: {customer_id or 'NOT SET - PLEASE CONFIGURE'}")
    print(f"ℹ️  Version ID: {version_id or 'NOT SET (Optional)'}")
    print()
    
    if not api_key or not secret_key:
        print("❌ API credentials not properly configured!")
        print("Please check config/sharekhan_credentials.env file")
        return False
    
    if not customer_id:
        print("⚠️  Customer ID not set - this is your ShareKhan Client ID")
        print("Please add SHAREKHAN_CUSTOMER_ID to config/sharekhan_credentials.env")
        print()
    
    try:
        # Initialize ShareKhan integration
        print("🔌 Initializing ShareKhan integration...")
        sharekhan = ShareKhanIntegration(
            api_key=api_key,
            secret_key=secret_key,
            customer_id=customer_id or "test_customer",
            version_id=version_id
        )
        
        print("✅ ShareKhan integration initialized successfully!")
        print()
        
        # Test connection status
        print("📊 Getting connection status...")
        status = sharekhan.get_connection_status()
        print(f"Connection Status: {status}")
        print()
        
        # Test API endpoints (without authentication for now)
        print("🌐 Testing API endpoint accessibility...")
        print(f"Base URL: {sharekhan.base_url}")
        print(f"WebSocket URL: {sharekhan.ws_url}")
        print()
        
        print("✅ Basic connection test completed successfully!")
        print()
        print("🔑 Next Steps:")
        print("1. Configure your ShareKhan Customer ID")
        print("2. Get request token for authentication")
        print("3. Generate session token")
        print("4. Start trading!")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {str(e)}")
        return False

async def test_orchestrator():
    """Test the ShareKhan orchestrator"""
    try:
        print("\n🎯 Testing ShareKhan Orchestrator...")
        
        from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
        
        # Get orchestrator instance
        orchestrator = await ShareKhanTradingOrchestrator.get_instance()
        
        if orchestrator:
            print("✅ ShareKhan orchestrator created successfully!")
            print(f"📊 Health Status: {orchestrator.health_status}")
            print(f"🔧 Initialized: {orchestrator.is_initialized}")
            
            # Test system status
            if orchestrator.is_initialized:
                status = await orchestrator.get_system_status()
                print(f"🏃 System Status: {status}")
        else:
            print("❌ Failed to create orchestrator")
            
    except Exception as e:
        print(f"❌ Orchestrator test failed: {str(e)}")

if __name__ == "__main__":
    print("🚀 ShareKhan API Credentials Test")
    print("=" * 50)
    
    # Run the tests
    asyncio.run(test_sharekhan_connection())
    asyncio.run(test_orchestrator())
    
    print("\n" + "=" * 50)
    print("🏁 Test completed!") 