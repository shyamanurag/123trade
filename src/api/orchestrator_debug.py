"""
Orchestrator Debug and Monitoring API
Provides debugging and monitoring endpoints for the trading orchestrator
Helps diagnose integration and performance issues
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
import asyncio
import json
import traceback
from pathlib import Path

# Import models
try:
    from src.models.responses import BaseResponse
except ImportError:
    from ..models.responses import BaseResponse

# Fixed orchestrator import
try:
    from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
except ImportError:
    from ..core.sharekhan_orchestrator import ShareKhanTradingOrchestrator

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
        logger.info("Debug Step 1: Testing ShareKhan orchestrator import...")
        try:
            from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
            debug_results["step_1_import"]["status"] = "success"
            logger.info("✅ ShareKhan orchestrator import successful")
        except Exception as e:
            debug_results["step_1_import"]["status"] = "failed"
            debug_results["step_1_import"]["error"] = str(e)
            debug_results["step_1_import"]["traceback"] = traceback.format_exc()
            logger.error(f"❌ ShareKhan orchestrator import failed: {e}")
            return debug_results
        
        # Step 2: Test instance creation
        logger.info("Debug Step 2: Testing ShareKhan orchestrator instance creation...")
        try:
            orchestrator = await ShareKhanTradingOrchestrator.get_instance()
            debug_results["step_2_create_instance"]["status"] = "success"
            logger.info("✅ ShareKhan orchestrator instance creation successful")
        except Exception as e:
            debug_results["step_2_create_instance"]["status"] = "failed"
            debug_results["step_2_create_instance"]["error"] = str(e)
            debug_results["step_2_create_instance"]["traceback"] = traceback.format_exc()
            logger.error(f"❌ ShareKhan orchestrator instance creation failed: {e}")
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
                    "brokers.sharekhan": {"available": False, "error": None},
        "strategies.momentum_surfer": {"available": False, "error": None},
        "src.core.config": {"available": False, "error": None}
    }
    
    # Test pydantic_settings
    try:
        from pydantic_settings import BaseSettings, SettingsConfigDict
        dependencies["pydantic_settings"]["available"] = True
    except Exception as e:
        dependencies["pydantic_settings"]["error"] = str(e)
    
    # Test core modules
    try:
        from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
        dependencies["src.core.sharekhan_orchestrator"]["available"] = True
    except Exception as e:
        dependencies["src.core.sharekhan_orchestrator"]["error"] = str(e)

    # Test ShareKhan integration
    try:
        from brokers.sharekhan import ShareKhanIntegration
        dependencies["brokers.sharekhan"]["available"] = True
    except Exception as e:
        dependencies["brokers.sharekhan"]["error"] = str(e)

    # REMOVED: ShareKhan testing - no longer supported
    # brokers.sharekhan testing has been removed as system now uses ShareKhan only
    
    return dependencies 