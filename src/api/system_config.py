"""
System Configuration API
Provides system-wide configuration settings for the frontend
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system")

@router.get("/config")
async def get_system_config():
    """Get system configuration settings"""
    try:
        # Get system configuration from environment variables
        config = {
            "initial_capital": float(os.getenv("INITIAL_CAPITAL", "1000000")),  # Default 10L
            "capital": float(os.getenv("TRADING_CAPITAL", "1000000")),
            "max_daily_loss": float(os.getenv("MAX_DAILY_LOSS", "50000")),  # Default 50K
            "max_position_size": float(os.getenv("MAX_POSITION_SIZE", "100000")),  # Default 1L
            "risk_per_trade": float(os.getenv("RISK_PER_TRADE", "0.02")),  # Default 2%
            "max_open_positions": int(os.getenv("MAX_OPEN_POSITIONS", "10")),
            "trading_enabled": os.getenv("TRADING_ENABLED", "true").lower() == "true",
            "paper_trading": os.getenv("PAPER_TRADING", "false").lower() == "true",
            "environment": os.getenv("ENVIRONMENT", "production"),
            "deployment_id": os.getenv("DEPLOYMENT_ID", "unknown"),
            "version": "4.0.1",
            "features": {
                "autonomous_trading": True,
                "risk_management": True,
                "position_monitoring": True,
                "real_time_data": True,
                "elite_recommendations": True
            },
            "limits": {
                "max_strategies": 5,
                "max_symbols": 250,
                "max_concurrent_orders": 50
            },
            "market_hours": {
                "start": "09:15",
                "end": "15:30",
                "timezone": "Asia/Kolkata"
            }
        }
        
        logger.info(f"System config requested - Capital: ₹{config['initial_capital']:,.0f}")
        
        return {
            "success": True,
            "data": config,
            "message": "System configuration retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting system config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get system config: {str(e)}")

@router.get("/status")
async def get_system_status():
    """Get basic system status information with orchestrator status"""
    try:
        # Default status
        status = {
            "status": "operational",
            "version": "4.0.1",
            "environment": os.getenv("ENVIRONMENT", "production"),
            "uptime": "running",
            "orchestrator_status": "stopped",
            "components": {
                "api": True,
                "database": True,
                "redis": True,
                "trading": True,
                "market_data": True
            },
            "deployment": {
                "id": os.getenv("DEPLOYMENT_ID", "unknown"),
                "timestamp": os.getenv("DEPLOYMENT_TIMESTAMP", "unknown")
            }
        }
        
        # Try to get orchestrator status
        try:
            from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
            orchestrator = await ShareKhanTradingOrchestrator.get_instance()
            if orchestrator and hasattr(orchestrator, 'is_running'):
                status["orchestrator_status"] = "running" if orchestrator.is_running else "stopped"
            else:
                status["orchestrator_status"] = "stopped"
        except Exception as orch_error:
            logger.warning(f"Could not get orchestrator status: {orch_error}")
            status["orchestrator_status"] = "unknown"
        
        return {
            "success": True,
            "data": status,
            "message": "System status retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}")

@router.get("/metrics")
async def get_system_metrics():
    """Get system performance metrics"""
    try:
        import psutil
        
        metrics = {
            "cpu_usage": psutil.cpu_percent(interval=1),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "active_connections": len(psutil.net_connections()),
            "uptime": "running",
            "last_restart": "unknown"
        }
        
        return {
            "success": True,
            "data": metrics,
            "message": "System metrics retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting system metrics: {str(e)}")
        # Return basic metrics if psutil fails
        return {
            "success": True,
            "data": {
                "cpu_usage": 0,
                "memory_usage": 0,
                "disk_usage": 0,
                "active_connections": 0,
                "uptime": "unknown",
                "last_restart": "unknown"
            },
            "message": "Basic system metrics retrieved (monitoring unavailable)"
        } 