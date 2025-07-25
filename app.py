"""
ShareKhan Trading System - Cloud Deployment Entry Point
This file serves as the entry point for cloud deployments (Heroku, DigitalOcean, etc.)
"""

import os
import sys
import logging
from pathlib import Path

# Setup logging early
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add src to Python path for cloud deployment
src_path = str(Path(__file__).parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Add project root to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables with error handling
try:
    from dotenv import load_dotenv
    load_dotenv('config/local_deployment.env')
    load_dotenv('config/sharekhan_credentials.env')
    logger.info("Environment files loaded")
except ImportError:
    logger.info("dotenv not available - using system environment variables")
except FileNotFoundError:
    logger.info("Environment files not found - using system environment variables")
except Exception as e:
    logger.warning(f"Error loading environment files: {e}")

# Set essential environment variables for cloud deployment
os.environ.setdefault('DATABASE_URL', os.getenv('DATABASE_URL', 'sqlite:///./trading_system_local.db'))
os.environ.setdefault('REDIS_URL', os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
os.environ.setdefault('ENVIRONMENT', 'production')
os.environ.setdefault('DEBUG', 'false')

# Import the main application with error handling
try:
    from main_full import app
    logger.info("Successfully imported main application")
except ImportError as e:
    logger.error(f"Failed to import main application: {e}")
    
    # Create a minimal fallback app
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    
    app = FastAPI(title="ShareKhan Trading System - Recovery Mode")
    
    @app.get("/")
    async def recovery_mode():
        return JSONResponse({
            "status": "recovery_mode",
            "message": "Application is starting up",
            "error": str(e)
        })
    
    @app.get("/health")
    async def health():
        return {"status": "recovery", "message": "System in recovery mode"}

# This is what cloud platforms will import
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting application on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port) 