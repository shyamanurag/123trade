"""
Shared FastAPI Dependencies
Centralized dependency injection to prevent singleton issues
"""
import logging
from .orchestrator import get_orchestrator as get_orchestrator_instance

logger = logging.getLogger(__name__)

async def get_orchestrator():
    """
    Get the singleton orchestrator instance
    CRITICAL: This is the ONLY function that should create/return orchestrator instances
    """
    logger.debug("🔧 get_orchestrator() called from dependencies.py")
    
    orchestrator = await get_orchestrator_instance()
    logger.debug(f"   Returning orchestrator instance")
    
    return orchestrator 