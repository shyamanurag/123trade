"""
Bootstrap module for development - SIMPLIFIED
This file is for development only. Production uses main.py
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Minimal lifespan manager for development"""
    logger.info("Bootstrap startup...")
    yield
    logger.info("Bootstrap shutdown...")

def create_app():
    """Create FastAPI app for development"""
    logger.warning("⚠️ Using bootstrap.py - This is for development only!")
    logger.warning("⚠️ Production should use main.py")
    
    # Simple app for development
    app = FastAPI(
        title="Trading System API (Development)",
        description="Development bootstrap - Use main.py for production",
        version="DEV",
        lifespan=lifespan
    )
    
    # Basic health check
    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "mode": "development",
            "warning": "This is development bootstrap - use main.py for production"
        }
    
    return app

# Create app if this module is imported
app = create_app() 