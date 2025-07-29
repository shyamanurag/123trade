"""
System Control API - Orchestrator Management
Provides endpoints to start, stop, and monitor the ShareKhan orchestrator
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/system", tags=["system-control"])

# Global orchestrator reference
global_orchestrator = None

@router.post("/start-orchestrator")
async def start_orchestrator():
    """Start the ShareKhan orchestrator manually"""
    global global_orchestrator
    
    try:
        logger.info("🚀 Manual orchestrator start requested...")
        
        # Setup environment variables with fallback values
        os.environ.setdefault('SHAREKHAN_API_KEY', 'demo_api_key_for_testing')
        os.environ.setdefault('SHAREKHAN_SECRET_KEY', 'demo_secret_key_for_testing')
        os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
        os.environ.setdefault('DATABASE_URL', 'sqlite:///trading_system_local.db')
        os.environ.setdefault('PAPER_TRADING', 'true')
        os.environ.setdefault('MAX_POSITION_SIZE', '100000')
        os.environ.setdefault('MAX_DAILY_LOSS', '10000')
        os.environ.setdefault('EMAIL_NOTIFICATIONS', 'false')
        os.environ.setdefault('SMS_NOTIFICATIONS', 'false')
        
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
        
        # Get or create orchestrator instance
        global_orchestrator = await ShareKhanTradingOrchestrator.get_instance(config)
        
        if global_orchestrator and global_orchestrator.is_initialized:
            # Start the orchestrator
            if hasattr(global_orchestrator, 'start') and callable(global_orchestrator.start):
                await global_orchestrator.start()
            
            return {
                "success": True,
                "message": "ShareKhan orchestrator started successfully",
                "status": global_orchestrator.health_status,
                "initialized": global_orchestrator.is_initialized,
                "running": getattr(global_orchestrator, 'is_running', False),
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "message": "Failed to initialize ShareKhan orchestrator",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"❌ Manual orchestrator start failed: {e}")
        return {
            "success": False,
            "message": f"Orchestrator start failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@router.get("/orchestrator-status")
async def get_orchestrator_status():
    """Get current orchestrator status"""
    global global_orchestrator
    
    try:
        # Try to get existing orchestrator
        if not global_orchestrator:
            try:
                from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
                global_orchestrator = await ShareKhanTradingOrchestrator.get_instance()
            except Exception:
                pass
        
        if global_orchestrator:
            status = {
                "orchestrator_status": "running" if getattr(global_orchestrator, 'is_running', False) else "stopped",
                "health_status": getattr(global_orchestrator, 'health_status', 'unknown'),
                "initialized": getattr(global_orchestrator, 'is_initialized', False),
                "error_count": getattr(global_orchestrator, 'error_count', 0),
                "last_health_check": getattr(global_orchestrator, 'last_health_check', datetime.now()).isoformat(),
                "active_users": 0,  # Placeholder
                "total_trades": 0,  # Placeholder
                "timestamp": datetime.now().isoformat()
            }
        else:
            status = {
                "orchestrator_status": "unknown",
                "health_status": "not_initialized",
                "initialized": False,
                "error_count": 0,
                "active_users": 0,
                "total_trades": 0,
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "success": True,
            "data": status,
            "message": "Orchestrator status retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting orchestrator status: {e}")
        return {
            "success": False,
            "message": f"Failed to get orchestrator status: {str(e)}",
            "data": {
                "orchestrator_status": "error",
                "health_status": "error",
                "initialized": False,
                "timestamp": datetime.now().isoformat()
            }
        }

@router.post("/stop-orchestrator") 
async def stop_orchestrator():
    """Stop the ShareKhan orchestrator"""
    global global_orchestrator
    
    try:
        if global_orchestrator and hasattr(global_orchestrator, 'stop'):
            await global_orchestrator.stop()
            
            return {
                "success": True,
                "message": "Orchestrator stopped successfully",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "message": "No orchestrator instance available to stop",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"❌ Error stopping orchestrator: {e}")
        return {
            "success": False,
            "message": f"Failed to stop orchestrator: {str(e)}",
            "timestamp": datetime.now().isoformat()
        } 