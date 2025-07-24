"""
API endpoints for Intelligent Symbol Management
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List
import logging
from datetime import datetime

from src.core.intelligent_symbol_manager import (
    intelligent_symbol_manager,
    start_intelligent_symbol_management,
    stop_intelligent_symbol_management,
    get_intelligent_symbol_status,
    get_active_symbols
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/intelligent-symbols")
async def get_intelligent_symbols_status():
    """Get IntelligentSymbolManager status and symbol expansion info"""
    try:
        # Get current status
        status = intelligent_symbol_manager.get_status()
        
        # Get active symbols list
        active_symbols = list(intelligent_symbol_manager.active_symbols)
        
        # Categorize symbols
        symbol_categories = {
            'core_indices': [],
            'priority_stocks': [],
            'options': [],
            'other': []
        }
        
        for symbol in active_symbols:
            if symbol in intelligent_symbol_manager.config.core_indices:
                symbol_categories['core_indices'].append(symbol)
            elif symbol in intelligent_symbol_manager.config.priority_stocks:
                symbol_categories['priority_stocks'].append(symbol)
            elif 'CE' in symbol or 'PE' in symbol:
                symbol_categories['options'].append(symbol)
            else:
                symbol_categories['other'].append(symbol)
        
        return {
            "success": True,
            "data": {
                "status": status,
                "symbol_breakdown": symbol_categories,
                "expansion_progress": {
                    "current": len(active_symbols),
                    "target": intelligent_symbol_manager.config.max_symbols,
                    "remaining_capacity": intelligent_symbol_manager.config.max_symbols - len(active_symbols),
                    "percentage": round((len(active_symbols) / intelligent_symbol_manager.config.max_symbols) * 100, 1)
                },
                "active_symbols": active_symbols[:20],  # First 20 for display
                "total_symbols": len(active_symbols)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting intelligent symbols status: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/intelligent-symbols/start")
async def start_intelligent_symbol_management():
    """Start the IntelligentSymbolManager to expand symbols"""
    try:
        if intelligent_symbol_manager.is_running:
            return {
                "success": True,
                "message": "IntelligentSymbolManager is already running",
                "timestamp": datetime.now().isoformat()
            }
        
        # Start the symbol manager
        await intelligent_symbol_manager.start()
        
        return {
            "success": True,
            "message": "IntelligentSymbolManager started successfully",
            "status": intelligent_symbol_manager.get_status(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error starting intelligent symbol management: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/intelligent-symbols/stop")
async def stop_intelligent_symbol_management():
    """Stop the IntelligentSymbolManager"""
    try:
        if not intelligent_symbol_manager.is_running:
            return {
                "success": True,
                "message": "IntelligentSymbolManager is already stopped",
                "timestamp": datetime.now().isoformat()
            }
        
        # Stop the symbol manager
        await intelligent_symbol_manager.stop()
        
        return {
            "success": True,
            "message": "IntelligentSymbolManager stopped successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error stopping intelligent symbol management: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/intelligent-symbols/expand-now")
async def trigger_symbol_expansion():
    """Manually trigger symbol expansion to reach 250 symbols"""
    try:
        if not intelligent_symbol_manager.is_running:
            return {
                "success": False,
                "error": "IntelligentSymbolManager must be running to expand symbols",
                "timestamp": datetime.now().isoformat()
            }
        
        # Get current count
        current_count = len(intelligent_symbol_manager.active_symbols)
        target_count = intelligent_symbol_manager.config.max_symbols
        
        if current_count >= target_count:
            return {
                "success": True,
                "message": f"Already at target symbol count: {current_count}/{target_count}",
                "timestamp": datetime.now().isoformat()
            }
        
        # Trigger expansion by calling setup methods
        await intelligent_symbol_manager.initial_symbol_setup()
        await intelligent_symbol_manager.add_new_contracts()
        await intelligent_symbol_manager.optimize_symbol_allocation()
        
        # Get new count
        new_count = len(intelligent_symbol_manager.active_symbols)
        symbols_added = new_count - current_count
        
        return {
            "success": True,
            "message": f"Symbol expansion triggered: {symbols_added} symbols added",
            "expansion_result": {
                "previous_count": current_count,
                "new_count": new_count,
                "symbols_added": symbols_added,
                "target_count": target_count,
                "remaining": target_count - new_count
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering symbol expansion: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/intelligent-symbols/active")
async def get_active_symbols_list():
    """Get list of currently active symbols"""
    try:
        symbols = get_active_symbols()
        return {
            "success": True,
            "symbols": symbols,
            "count": len(symbols),
            "message": f"Retrieved {len(symbols)} active symbols"
        }
    except Exception as e:
        logger.error(f"Failed to get active symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/intelligent-symbols/analytics")
async def get_symbol_analytics():
    """Get analytics about symbol usage"""
    try:
        status = get_intelligent_symbol_status()
        symbols = get_active_symbols()
        
        # Analyze symbol distribution
        symbol_types = {
            'indices': 0,
            'stocks': 0,
            'options': 0,
            'others': 0
        }
        
        for symbol in symbols:
            if symbol in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']:
                symbol_types['indices'] += 1
            elif 'CE' in symbol or 'PE' in symbol:
                symbol_types['options'] += 1
            elif symbol.isalpha():
                symbol_types['stocks'] += 1
            else:
                symbol_types['others'] += 1
        
        return {
            "success": True,
            "analytics": {
                "total_symbols": len(symbols),
                "symbol_distribution": symbol_types,
                "utilization_percentage": round((len(symbols) / 250) * 100, 2),
                "manager_status": status
            },
            "message": "Symbol analytics retrieved"
        }
    except Exception as e:
        logger.error(f"Failed to get symbol analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/intelligent-symbols/manual-add")
async def manually_add_symbols(symbols: List[str]):
    """Manually add symbols to the active list"""
    try:
        # Check current symbol count
        current_count = len(get_active_symbols())
        if current_count + len(symbols) > 250:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot add {len(symbols)} symbols. Would exceed 250 limit. Current: {current_count}"
            )
        
        await intelligent_symbol_manager.subscribe_symbols(symbols)
        
        return {
            "success": True,
            "message": f"Added {len(symbols)} symbols manually",
            "symbols_added": symbols,
            "new_total": len(get_active_symbols())
        }
    except Exception as e:
        logger.error(f"Failed to manually add symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/intelligent-symbols/manual-remove")
async def manually_remove_symbols(symbols: List[str]):
    """Manually remove symbols from the active list"""
    try:
        await intelligent_symbol_manager.unsubscribe_symbols(symbols)
        
        return {
            "success": True,
            "message": f"Removed {len(symbols)} symbols manually",
            "symbols_removed": symbols,
            "new_total": len(get_active_symbols())
        }
    except Exception as e:
        logger.error(f"Failed to manually remove symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/intelligent-symbols/recommendations")
async def get_symbol_recommendations():
    """Get recommended symbols to add based on market conditions"""
    try:
        # Generate recommendations based on current market conditions
        recommendations = {
            "high_priority": [
                "NIFTY", "BANKNIFTY", "FINNIFTY"  # Core indices
            ],
            "medium_priority": [
                "RELIANCE", "TCS", "INFY", "HDFC", "ICICIBANK"  # Top F&O stocks
            ],
            "low_priority": [
                "SBIN", "ITC", "LT", "WIPRO", "BHARTIARTL"  # Secondary F&O stocks
            ]
        }
        
        return {
            "success": True,
            "recommendations": recommendations,
            "message": "Symbol recommendations generated based on market conditions"
        }
    except Exception as e:
        logger.error(f"Failed to get symbol recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 