"""
Orchestrator Debug API
Diagnostic endpoint to test orchestrator initialization
"""
from fastapi import APIRouter
from typing import Dict, Any
import logging
import traceback

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/orchestrator/debug", tags=["debug"])
async def debug_orchestrator_initialization():
    """Debug orchestrator initialization step by step"""
    debug_results = {
        "step_1_import": {"status": "pending", "error": None},
        "step_2_create_instance": {"status": "pending", "error": None},
        "step_3_initialize": {"status": "pending", "error": None},
        "overall_status": "testing"
    }
    
    try:
        # Step 1: Test import
        logger.info("Debug Step 1: Testing import...")
        try:
            from src.core.orchestrator import TradingOrchestrator
            debug_results["step_1_import"]["status"] = "success"
            logger.info("✅ Import successful")
        except Exception as e:
            debug_results["step_1_import"]["status"] = "failed"
            debug_results["step_1_import"]["error"] = str(e)
            debug_results["step_1_import"]["traceback"] = traceback.format_exc()
            logger.error(f"❌ Import failed: {e}")
            return debug_results
        
        # Step 2: Test instance creation
        logger.info("Debug Step 2: Testing instance creation...")
        try:
            orchestrator = TradingOrchestrator()
            debug_results["step_2_create_instance"]["status"] = "success"
            logger.info("✅ Instance creation successful")
        except Exception as e:
            debug_results["step_2_create_instance"]["status"] = "failed"
            debug_results["step_2_create_instance"]["error"] = str(e)
            debug_results["step_2_create_instance"]["traceback"] = traceback.format_exc()
            logger.error(f"❌ Instance creation failed: {e}")
            return debug_results
        
        # Step 3: Test initialization
        logger.info("Debug Step 3: Testing initialization...")
        try:
            init_result = await orchestrator.initialize()
            debug_results["step_3_initialize"]["status"] = "success" if init_result else "failed"
            debug_results["step_3_initialize"]["result"] = init_result
            debug_results["step_3_initialize"]["error"] = None if init_result else "Initialize returned False"
            logger.info(f"✅ Initialize result: {init_result}")
        except Exception as e:
            debug_results["step_3_initialize"]["status"] = "failed"
            debug_results["step_3_initialize"]["error"] = str(e)
            debug_results["step_3_initialize"]["traceback"] = traceback.format_exc()
            logger.error(f"❌ Initialize failed: {e}")
            return debug_results
        
        debug_results["overall_status"] = "success"
        
    except Exception as e:
        debug_results["overall_status"] = "failed"
        debug_results["general_error"] = str(e)
        logger.error(f"❌ General error: {e}")
    
    return debug_results

@router.get("/orchestrator/dependencies", tags=["debug"])
async def check_dependencies():
    """Check if required dependencies are available"""
    dependencies = {
        "pydantic_settings": {"available": False, "error": None},
        "brokers.zerodha": {"available": False, "error": None},
        "strategies.momentum_surfer": {"available": False, "error": None},
        "src.core.config": {"available": False, "error": None}
    }
    
    # Test pydantic_settings
    try:
        from pydantic_settings import BaseSettings, SettingsConfigDict
        dependencies["pydantic_settings"]["available"] = True
    except Exception as e:
        dependencies["pydantic_settings"]["error"] = str(e)
    
    # Test brokers.zerodha
    try:
        from brokers.zerodha import ZerodhaIntegration
        dependencies["brokers.zerodha"]["available"] = True
    except Exception as e:
        dependencies["brokers.zerodha"]["error"] = str(e)
    
    # Test strategies.momentum_surfer
    try:
        from strategies.momentum_surfer import EnhancedMomentumSurfer
        dependencies["strategies.momentum_surfer"]["available"] = True
    except Exception as e:
        dependencies["strategies.momentum_surfer"]["error"] = str(e)
    
    # Test src.core.config
    try:
        from src.core.config import settings
        dependencies["src.core.config"]["available"] = True
    except Exception as e:
        dependencies["src.core.config"]["error"] = str(e)
    
    return dependencies 