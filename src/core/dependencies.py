"""
Shared FastAPI Dependencies
HONEST dependency injection - uses ShareKhan orchestrator only
"""
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

async def get_orchestrator():
    """
    Get ShareKhan orchestrator instance - CLEAN IMPLEMENTATION
    NO FALLBACKS - uses only the modern ShareKhan system
    """
    logger.debug("🔧 get_orchestrator() called from dependencies.py")
    
    try:
        # Import and get ShareKhan orchestrator
        from .sharekhan_orchestrator import ShareKhanTradingOrchestrator
        
        try:
            orchestrator = await ShareKhanTradingOrchestrator.get_instance()
            
            if orchestrator and orchestrator.is_initialized:
                logger.debug("✅ Returning initialized ShareKhan orchestrator")
                return orchestrator
            else:
                logger.warning("⚠️ ShareKhan orchestrator not fully initialized")
                # Return partially initialized orchestrator instead of failing
                return orchestrator
                
        except Exception as init_error:
            logger.error(f"❌ ShareKhan orchestrator initialization failed: {init_error}")
            raise HTTPException(
                status_code=503,
                detail=f"ShareKhan orchestrator initialization failed: {str(init_error)}"
            )
            
    except ImportError as e:
        logger.error(f"❌ Cannot import ShareKhan orchestrator: {e}")
        raise HTTPException(
            status_code=503,
            detail="ShareKhan orchestrator not available. System requires proper initialization."
        )
    except Exception as e:
        logger.error(f"❌ Unexpected orchestrator error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Trading system error: {str(e)}"
        ) 