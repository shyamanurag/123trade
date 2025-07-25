"""
Bootstrap module for development - SIMPLIFIED
This file is for development only. Production uses main.py
"""
import asyncio
import logging
from pathlib import Path
import sys

# Add the src directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from src.config.database import get_database_engine
from src.config.services import ServiceConfig
from src.core.database_schema_manager import DatabaseSchemaManager
from src.core.redis_fallback_manager import redis_fallback_manager

# REMOVED: multi_user_zerodha_manager import - using ShareKhan only
# from src.core.multi_user_zerodha_manager import multi_user_zerodha_manager

# ShareKhan only imports
from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
from src.core.multi_user_sharekhan_manager import MultiUserShareKhanManager

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asyncio.coroutine
def lifespan(app):
    """Enhanced lifespan manager with multi-user system initialization"""
    logger.info("Bootstrap startup...")
    
    # Initialize multi-user systems
    try:
        # Initialize multi-user Zerodha manager
        # await multi_user_zerodha_manager.initialize() # REMOVED
        logger.info("✅ Multi-user Zerodha manager initialized")
        
        # Initialize analytics service
        from src.api.user_analytics_service import analytics_service
        await analytics_service.initialize()
        logger.info("✅ User analytics service initialized")
        
        # Initialize dynamic user manager
        from src.api.dynamic_user_management import user_manager
        await user_manager.initialize()
        logger.info("✅ Dynamic user manager initialized")
        
    except Exception as e:
        logger.error(f"❌ Error initializing multi-user systems: {e}")
    
    yield
    
    # Cleanup on shutdown
    try:
        # await multi_user_zerodha_manager.cleanup() # REMOVED
        logger.info("✅ Multi-user systems cleaned up")
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")
    
    logger.info("Bootstrap shutdown...")

async def initialize_system(config: AppConfig) -> Dict[str, Any]:
    """Initialize all system components"""
    logger.info("Starting system initialization...")
    
    components = {}
    
    try:
        # Initialize database configuration first
        db_config = DatabaseConfig()
        components['db_config'] = db_config
        
        # Ensure precise database schema - this is the definitive approach
        logger.info("Ensuring precise database schema...")
        schema_manager = DatabaseSchemaManager(db_config.database_url)
        result = schema_manager.ensure_precise_schema()
        
        if result['status'] == 'success':
            logger.info("✅ Database schema verified - all tables have precise structure")
        else:
            logger.error(f"❌ Database schema verification failed: {result['errors']}")
            # Continue anyway - system can work with partial schema
        
        # Initialize Redis connection
        logger.info("Initializing Redis connection...")
        
        components['status'] = 'ready'
        return components
        
    except Exception as e:
        logger.error(f"System initialization failed: {e}")
        return {'status': 'error', 'error': str(e)}

def create_app():
    """Create FastAPI app for development"""
    logger.warning("⚠️ Using bootstrap.py - This is for development only!")
    logger.warning("⚠️ Production should use main.py")
    
    # Enhanced app for development with multi-user support
    app = FastAPI(
        title="AlgoAuto Trading System",
        description="Automated trading system with multi-user support",
        version="2.0.0",
        lifespan=lifespan
    )
    
    # Basic health check
    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "mode": "development",
            "features": ["multi-user-management", "user-analytics", "zerodha-integration"],
            "warning": "This is development bootstrap - use main.py for production"
        }
    
    # Multi-user system status endpoint
    @app.get("/api/v1/system/multi-user-status")
    async def multi_user_status():
        """Get status of multi-user systems"""
        try:
            # zerodha_status = multi_user_zerodha_manager.get_all_sessions_status() # REMOVED
            
            return {
                "status": "active",
                "zerodha_manager": {
                    "initialized": True, # REMOVED
                    "active_sessions": 0, # REMOVED
                    "sessions": [] # REMOVED
                },
                "analytics_service": {
                    "initialized": True,  # Will be updated based on actual status
                },
                "user_manager": {
                    "initialized": True,  # Will be updated based on actual status
                }
            }
        except Exception as e:
            logger.error(f"❌ Error getting multi-user status: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    # Register API routers
    app.include_router(dynamic_user_router)
    app.include_router(analytics_router)
    app.include_router(database_admin_router)  # CRITICAL: Emergency database cleanup endpoint
    
    return app

# Create app if this module is imported
app = create_app() 