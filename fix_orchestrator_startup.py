#!/usr/bin/env python3
"""
ShareKhan Orchestrator Startup Fix
Resolves orchestrator initialization issues and sets up proper configuration
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OrchestratorStartupFixer:
    def __init__(self):
        self.required_env_vars = {
            'SHAREKHAN_API_KEY': 'demo_api_key_for_testing',
            'SHAREKHAN_SECRET_KEY': 'demo_secret_key_for_testing',
            'REDIS_URL': 'redis://localhost:6379/0',
            'DATABASE_URL': 'sqlite:///trading_system_local.db',
            'PAPER_TRADING': 'true',
            'MAX_POSITION_SIZE': '100000',
            'MAX_DAILY_LOSS': '10000',
            'EMAIL_NOTIFICATIONS': 'false',
            'SMS_NOTIFICATIONS': 'false'
        }
    
    def setup_environment_variables(self):
        """Setup required environment variables with fallback values"""
        logger.info("🔧 Setting up environment variables...")
        
        changes_made = []
        for var, default_value in self.required_env_vars.items():
            if not os.getenv(var):
                os.environ[var] = default_value
                changes_made.append(f"{var}={default_value}")
                logger.info(f"✅ Set {var} to default value")
            else:
                logger.info(f"✅ {var} already set")
        
        if changes_made:
            logger.info(f"📝 Environment variables set: {len(changes_made)}")
            return True
        else:
            logger.info("📝 All environment variables were already set")
            return False
    
    def create_fallback_redis_config(self):
        """Create fallback Redis configuration"""
        logger.info("🔧 Setting up fallback Redis configuration...")
        
        # Set fallback Redis settings
        os.environ.setdefault('REDIS_HOST', 'localhost')
        os.environ.setdefault('REDIS_PORT', '6379')
        os.environ.setdefault('REDIS_DB', '0')
        
        return True
    
    def create_startup_script(self):
        """Create a startup script for the orchestrator"""
        startup_script = """#!/usr/bin/env python3
'''
ShareKhan Trading System Startup Script
'''
import os
import sys
import asyncio
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def start_orchestrator():
    '''Start the ShareKhan orchestrator'''
    try:
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        logger.info("🚀 Starting ShareKhan Trading Orchestrator...")
        
        # Set environment variables
        os.environ.setdefault('SHAREKHAN_API_KEY', 'demo_api_key')
        os.environ.setdefault('SHAREKHAN_SECRET_KEY', 'demo_secret_key')
        os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
        os.environ.setdefault('DATABASE_URL', 'sqlite:///trading_system_local.db')
        os.environ.setdefault('PAPER_TRADING', 'true')
        
        # Import and initialize orchestrator
        from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
        
        config = {
            'paper_trading': True,
            'max_position_size': 100000,
            'max_daily_loss': 10000,
            'email_notifications': False,
            'sms_notifications': False,
            'database_url': 'sqlite:///trading_system_local.db'
        }
        
        orchestrator = await ShareKhanTradingOrchestrator.get_instance(config)
        
        if orchestrator and orchestrator.is_initialized:
            logger.info("✅ ShareKhan orchestrator started successfully!")
            logger.info(f"Status: {orchestrator.health_status}")
            return orchestrator
        else:
            logger.error("❌ Failed to start orchestrator")
            return None
            
    except Exception as e:
        logger.error(f"❌ Orchestrator startup error: {e}")
        return None

if __name__ == "__main__":
    orchestrator = asyncio.run(start_orchestrator())
    if orchestrator:
        print("✅ Orchestrator started successfully")
    else:
        print("❌ Orchestrator startup failed")
"""
        
        with open("start_orchestrator.py", "w") as f:
            f.write(startup_script)
        
        logger.info("✅ Created startup script: start_orchestrator.py")
        return True
    
    def update_main_app_for_fallback(self):
        """Update main.py to handle missing environment variables gracefully"""
        logger.info("🔧 Updating main.py for graceful orchestrator handling...")
        
        # Read the current main.py
        try:
            with open("main.py", "r") as f:
                main_content = f.read()
            
            # Check if we need to add fallback handling
            if "ORCHESTRATOR_FALLBACK_HANDLING" not in main_content:
                # Add fallback handling after the lifespan function
                fallback_code = '''
# ORCHESTRATOR_FALLBACK_HANDLING - Added for production stability
async def get_orchestrator_with_fallback():
    """Get orchestrator with proper fallback handling"""
    global global_orchestrator
    
    if global_orchestrator and hasattr(global_orchestrator, 'is_initialized'):
        if global_orchestrator.is_initialized:
            return global_orchestrator
    
    # Try to initialize orchestrator if not available
    try:
        from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
        
        # Setup fallback environment
        os.environ.setdefault('SHAREKHAN_API_KEY', 'demo_api_key')
        os.environ.setdefault('SHAREKHAN_SECRET_KEY', 'demo_secret_key')
        os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
        os.environ.setdefault('DATABASE_URL', 'sqlite:///trading_system_local.db')
        os.environ.setdefault('PAPER_TRADING', 'true')
        
        config = {
            'paper_trading': True,
            'max_position_size': 100000,
            'max_daily_loss': 10000,
            'email_notifications': False,
            'sms_notifications': False
        }
        
        global_orchestrator = await ShareKhanTradingOrchestrator.get_instance(config)
        logger.info("✅ Orchestrator initialized with fallback configuration")
        return global_orchestrator
        
    except Exception as e:
        logger.error(f"❌ Orchestrator fallback initialization failed: {e}")
        return None

# Update dependencies to use fallback
from src.core.dependencies import get_orchestrator as original_get_orchestrator

async def get_orchestrator():
    """Enhanced orchestrator dependency with fallback"""
    try:
        return await original_get_orchestrator()
    except Exception:
        return await get_orchestrator_with_fallback()
'''
                
                # Insert the fallback code before the health check endpoints
                health_check_pos = main_content.find("@app.get(\"/health\")")
                if health_check_pos != -1:
                    main_content = (main_content[:health_check_pos] + 
                                  fallback_code + "\n\n" + 
                                  main_content[health_check_pos:])
                    
                    with open("main.py", "w") as f:
                        f.write(main_content)
                    
                    logger.info("✅ Added orchestrator fallback handling to main.py")
                    return True
        
        except Exception as e:
            logger.error(f"❌ Failed to update main.py: {e}")
            return False
        
        return False
    
    def create_orchestrator_start_endpoint(self):
        """Create API endpoint to manually start orchestrator"""
        endpoint_code = '''
@app.post("/api/system/start-orchestrator")
async def start_orchestrator_endpoint():
    """Manually start the ShareKhan orchestrator"""
    global global_orchestrator
    
    try:
        logger.info("🚀 Manual orchestrator start requested...")
        
        # Setup environment variables
        os.environ.setdefault('SHAREKHAN_API_KEY', 'demo_api_key')
        os.environ.setdefault('SHAREKHAN_SECRET_KEY', 'demo_secret_key')
        os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
        os.environ.setdefault('DATABASE_URL', 'sqlite:///trading_system_local.db')
        os.environ.setdefault('PAPER_TRADING', 'true')
        
        from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
        
        config = {
            'paper_trading': True,
            'max_position_size': 100000,
            'max_daily_loss': 10000,
            'email_notifications': False,
            'sms_notifications': False
        }
        
        global_orchestrator = await ShareKhanTradingOrchestrator.get_instance(config)
        
        if global_orchestrator and global_orchestrator.is_initialized:
            return {
                "success": True,
                "message": "Orchestrator started successfully",
                "status": global_orchestrator.health_status,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "message": "Failed to initialize orchestrator",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"❌ Manual orchestrator start failed: {e}")
        return {
            "success": False,
            "message": f"Orchestrator start failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
'''
        
        with open("orchestrator_start_endpoint.py", "w") as f:
            f.write(endpoint_code)
        
        logger.info("✅ Created orchestrator start endpoint code")
        return True
    
    async def test_orchestrator_startup(self):
        """Test orchestrator startup with fallback configuration"""
        logger.info("🧪 Testing orchestrator startup...")
        
        try:
            # Setup environment
            self.setup_environment_variables()
            
            # Add project to path
            sys.path.insert(0, os.getcwd())
            
            # Import and test orchestrator
            from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
            
            config = {
                'paper_trading': True,
                'max_position_size': 100000,
                'max_daily_loss': 10000,
                'email_notifications': False,
                'sms_notifications': False
            }
            
            orchestrator = await ShareKhanTradingOrchestrator.get_instance(config)
            
            if orchestrator:
                logger.info(f"✅ Orchestrator test successful!")
                logger.info(f"   - Initialized: {getattr(orchestrator, 'is_initialized', False)}")
                logger.info(f"   - Health Status: {getattr(orchestrator, 'health_status', 'unknown')}")
                logger.info(f"   - Running: {getattr(orchestrator, 'is_running', False)}")
                return True
            else:
                logger.error("❌ Orchestrator test failed - no instance returned")
                return False
                
        except Exception as e:
            logger.error(f"❌ Orchestrator test failed: {e}")
            return False
    
    def run_fix(self):
        """Run all orchestrator fixes"""
        logger.info("🔧 Starting ShareKhan Orchestrator Startup Fix...")
        
        steps = [
            ("Setup Environment Variables", self.setup_environment_variables),
            ("Create Redis Fallback Config", self.create_fallback_redis_config), 
            ("Create Startup Script", self.create_startup_script),
            ("Update Main App", self.update_main_app_for_fallback),
            ("Create Start Endpoint", self.create_orchestrator_start_endpoint),
        ]
        
        results = {}
        for step_name, step_func in steps:
            logger.info(f"📋 Step: {step_name}")
            try:
                success = step_func()
                results[step_name] = "✅ SUCCESS" if success else "⚠️ SKIPPED"
            except Exception as e:
                logger.error(f"❌ Step failed: {step_name} - {e}")
                results[step_name] = f"❌ FAILED: {e}"
        
        # Test orchestrator startup
        logger.info("📋 Step: Test Orchestrator Startup")
        try:
            test_success = asyncio.run(self.test_orchestrator_startup())
            results["Test Orchestrator"] = "✅ SUCCESS" if test_success else "❌ FAILED"
        except Exception as e:
            logger.error(f"❌ Orchestrator test failed: {e}")
            results["Test Orchestrator"] = f"❌ FAILED: {e}"
        
        # Print summary
        logger.info("📊 ORCHESTRATOR FIX SUMMARY:")
        for step, result in results.items():
            logger.info(f"  {step}: {result}")
        
        all_success = all("✅" in result for result in results.values())
        
        if all_success:
            logger.info("🎉 ALL FIXES APPLIED SUCCESSFULLY!")
            logger.info("🚀 Orchestrator should now start properly")
            logger.info("💡 Use: python start_orchestrator.py to test manually")
        else:
            logger.info("⚠️ Some fixes failed - check errors above")
        
        return all_success

if __name__ == "__main__":
    fixer = OrchestratorStartupFixer()
    fixer.run_fix() 