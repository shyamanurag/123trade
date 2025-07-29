"""
ShareKhan Integration API Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
import logging
from datetime import datetime
import asyncio
from fastapi.responses import JSONResponse
import sys
import os

# Define logger early to avoid undefined errors
logger = logging.getLogger(__name__)

from data.sharekhan_client import (
    sharekhan_client, 
    live_market_data, 
    initialize_sharekhan,
    get_live_data_for_symbol,
    get_sharekhan_status
)

# CRITICAL FIX: Direct bridge to populated ShareKhan cache at module level
sys.path.insert(0, os.path.abspath('.'))

try:
    from data.sharekhan_client import live_market_data as sharekhan_cache_direct
    from data.sharekhan_client import sharekhan_client as sharekhan_client_direct
    DIRECT_BRIDGE_AVAILABLE = True
    logger.info("✅ ShareKhan direct bridge established in integration API")
except ImportError as e:
    logger.error(f"❌ ShareKhan direct bridge failed in integration API: {e}")
    sharekhan_cache_direct = {}
    DIRECT_BRIDGE_AVAILABLE = False

def smart_auto_retry():
    """Smart autonomous retry for ShareKhan - FIXED to check cache instead of connecting"""
    try:
        # FIXED: Check cache availability instead of trying to connect
        from data.sharekhan_client import live_market_data, is_connected
        
        if len(live_market_data) > 0:
            logger.info(f"✅ AUTONOMOUS: ShareKhan cache available: {len(live_market_data)} symbols")
            return True
        else:
            logger.warning("⚠️ AUTONOMOUS: ShareKhan cache is empty")
            return False
            
    except Exception as e:
        logger.error(f"Auto-retry cache check error: {e}")
        return False
        
from src.models.responses import ShareKhanResponse, APIResponse

router = APIRouter(prefix="/sharekhan", tags=["sharekhan"])

@router.post("/connect")
async def connect_sharekhan(credentials: Dict):
    """Connect to ShareKhan live feed - FIXED to check cache instead of connecting"""
    try:
        username = credentials.get("username")
        password = credentials.get("password")
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password required")
        
        # FIXED: Check existing ShareKhan cache instead of trying to connect
        from data.sharekhan_client import live_market_data, is_connected
        
        if len(live_market_data) > 0:
            return {
                "success": True,
                "message": f"ShareKhan cache available: {len(live_market_data)} symbols",
                "cache_size": len(live_market_data),
                "note": "Using existing ShareKhan connection - no new connection needed",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=503, detail="ShareKhan cache is empty - main connection required")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking ShareKhan cache: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/subscribe")
async def subscribe_symbols(symbols: List[str]):
    """Subscribe to symbols for live data"""
    try:
        if not sharekhan_client.connected:
            raise HTTPException(status_code=503, detail="ShareKhan client not connected")
        
        # ShareKhan subscription is handled during connection
        # This endpoint is for compatibility
        return {
            "success": True,
            "message": f"ShareKhan handles symbol subscription automatically",
            "symbols": symbols,
            "timestamp": datetime.now().isoformat()
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subscribing to symbols: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/unsubscribe")
async def unsubscribe_symbols(symbols: List[str]):
    """Unsubscribe from symbols"""
    try:
        if not sharekhan_client.connected:
            raise HTTPException(status_code=503, detail="ShareKhan client not connected")
        
        # For now, just remove from live data (ShareKhan SDK doesn't have unsubscribe)
        for symbol in symbols:
            live_market_data.pop(symbol, None)
        
        return {
            "success": True,
            "message": f"Unsubscribed from {len(symbols)} symbols",
            "symbols": symbols,
            "timestamp": datetime.now().isoformat()
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unsubscribing from symbols: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/status")
async def get_sharekhan_status_endpoint():
    """Get ShareKhan connection status"""
    try:
        if not sharekhan_client:
            return {
                "connected": False,
                "message": "ShareKhan client not initialized",
                "timestamp": datetime.now().isoformat()
            }
        
        status = get_sharekhan_status()
        return {
            "success": True,
            "data": status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting ShareKhan status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/reconnect")
async def reconnect_sharekhan():
    """Attempt to reconnect to ShareKhan - FIXED to check cache instead of connecting"""
    try:
        # FIXED: Check cache availability instead of trying to reconnect
        from data.sharekhan_client import live_market_data, get_sharekhan_status
        
        status = get_sharekhan_status()
        
        if len(live_market_data) > 0:
            return {
                "success": True,
                "message": f"ShareKhan cache available: {len(live_market_data)} symbols",
                "cache_size": len(live_market_data),
                "note": "Using existing ShareKhan connection - no reconnection needed",
                "data": status,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "message": "ShareKhan cache is empty - main app connection required",
                "data": status,
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error checking ShareKhan cache: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/data/{symbol}")
async def get_symbol_data(symbol: str):
    """Get latest market data for a specific symbol"""
    try:
        if not sharekhan_client.connected:
            raise HTTPException(status_code=503, detail="ShareKhan client not connected")
        
        data = get_live_data_for_symbol(symbol)
        
        if data:
            return ShareKhanResponse.create_symbol_data(symbol, data).dict()
        else:
            return APIResponse(
                success=False,
                message=f"No data available for symbol {symbol}",
                data={"symbol": symbol}
            ).dict()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting symbol data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/data")
async def get_all_market_data():
    """Get all market data"""
    try:
        if not sharekhan_client.connected:
            raise HTTPException(status_code=503, detail="ShareKhan client not connected")
        
        return APIResponse(
            success=True,
            message="All market data retrieved successfully",
            data={
                "market_data": live_market_data,
                "total_symbols": len(live_market_data)
            }
        ).dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting all market data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/disconnect")
async def disconnect_sharekhan():
    """Disconnect from ShareKhan"""
    try:
        if not sharekhan_client.connected:
            raise HTTPException(status_code=503, detail="ShareKhan client not connected")
        
        sharekhan_client.disconnect()
        
        return APIResponse(
            success=True,
            message="ShareKhan disconnected successfully",
            data={"disconnected_at": datetime.now().isoformat()}
        ).dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting from ShareKhan: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# WebSocket integration for real-time data
@router.websocket("/ws/{symbol}")
async def sharekhan_websocket(websocket, symbol: str):
    """WebSocket endpoint for real-time ShareKhan"""
    try:
        if not sharekhan_client.connected:
            await websocket.close(code=1011, reason="ShareKhan client not connected")
            return
        
        # Subscribe to symbol if not already subscribed
        if symbol not in live_market_data:
            # CRITICAL FIX: Don't call subscribe_to_symbols() - creates connection conflicts
            # Instead, just log that symbol subscription was requested
            logger.info(f"📝 SYMBOL SUBSCRIPTION REQUESTED: {symbol} - will be available via main ShareKhan client")
        
        # Send initial data
        initial_data = get_live_data_for_symbol(symbol)
        if initial_data:
            await websocket.send_json({
                "type": "initial_data",
                "symbol": symbol,
                "data": initial_data
            })
        
        # Keep connection alive and send updates
        while True:
            # Get latest data
            data = get_live_data_for_symbol(symbol)
            if data:
                await websocket.send_json({
                    "type": "market_data",
                    "symbol": symbol,
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Wait before next update
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"WebSocket error for symbol {symbol}: {e}")
        await websocket.close(code=1011, reason="Internal error")

@router.get("/debug/client-internals")
async def debug_client_internals():
    """Debug ShareKhan client internals"""
    try:
        # Try both client paths
        client = None
        client_type = "unknown"
        
        try:
            from data.sharekhan_client import sharekhan_client, live_market_data, sharekhan_connection_status
            client = sharekhan_client
            client_type = "singleton"
            
            return {
                "success": True,
                "client_type": client_type,
                "client_status": client.get_status() if hasattr(client, 'get_status') else "no_status_method",
                "live_data_count": len(live_market_data),
                "live_data_keys": list(live_market_data.keys()),
                "connection_status": sharekhan_connection_status,
                "sample_data": dict(list(live_market_data.items())[:3]) if live_market_data else {}
            }
            
        except ImportError:
            try:
                from src.data.sharekhan_client import get_sharekhan_client
                client = get_sharekhan_client()
                client_type = "async"
                
                if client:
                    return {
                        "success": True,
                        "client_type": client_type,
                        "is_connected": client.is_connected,
                        "subscribed_symbols": list(client.subscribed_symbols),
                        "market_data_count": len(client.market_data),
                        "market_data_keys": list(client.market_data.keys()),
                        "sample_data": dict(list(client.market_data.items())[:3]) if client.market_data else {}
                    }
                else:
                    return {
                        "success": False,
                        "error": "Client not initialized"
                    }
                    
            except ImportError:
                return {
                    "success": False,
                    "error": "No ShareKhan client found"
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/debug/force-data")
async def force_create_sample_data():
    """ELIMINATED: Force create sample data to test frontend"""
    try:
        # ELIMINATED: Fake sample data generation that could mislead about real market data
        # ❌ sample_data = {
        # ❌     'FORCED_NIFTY': {
        # ❌         'symbol': 'FORCED_NIFTY',
        # ❌         'ltp': 23456.78,
        # ❌         'volume': 987654,
        # ❌         'timestamp': datetime.now().isoformat(),
        # ❌         'data_source': 'FORCED_SAMPLE'
        # ❌     },
        # ❌     'FORCED_BANKNIFTY': {
        # ❌         'symbol': 'FORCED_BANKNIFTY',
        # ❌         'ltp': 45678.90,
        # ❌         'volume': 123456,
        # ❌         'timestamp': datetime.now().isoformat(),
        # ❌         'data_source': 'FORCED_SAMPLE'
        # ❌     }
        # ❌ }
        # ❌ live_market_data.update(sample_data)
        
        # SAFETY: Return error instead of fake sample data
        logger.error("CRITICAL: Force sample data creation ELIMINATED to prevent fake market data")
        
        return {
            "success": False,
            "error": "SAFETY: Force sample data creation disabled - real ShareKhan required",
            "message": "Fake sample data generation eliminated for safety"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/debug/callback-status")
async def debug_callback_status():
    """Debug ShareKhan callback registration and data flow"""
    try:
        from data.sharekhan_client import sharekhan_client, live_market_data
        
        debug_info = {
            "timestamp": datetime.now().isoformat(),
            "client_connected": sharekhan_client.connected if sharekhan_client else False,
            "td_obj_exists": hasattr(sharekhan_client, 'td_obj') and sharekhan_client.td_obj is not None,
            "live_data_count": len(live_market_data),
            "live_data_keys": list(live_market_data.keys()),
        }
        
        # Check if td_obj has the callback methods
        if hasattr(sharekhan_client, 'td_obj') and sharekhan_client.td_obj:
            td_obj = sharekhan_client.td_obj
            debug_info.update({
                "has_trade_callback": hasattr(td_obj, 'trade_callback'),
                "has_bidask_callback": hasattr(td_obj, 'bidask_callback'),
                "has_greek_callback": hasattr(td_obj, 'greek_callback'),
                "td_obj_type": str(type(td_obj)),
                "td_obj_methods": [method for method in dir(td_obj) if 'callback' in method.lower()]
            })
            
            # Try to get internal callback info if available
            try:
                callbacks_attr = getattr(td_obj, '_callbacks', None)
                if callbacks_attr is not None:
                    debug_info["internal_callbacks"] = str(callbacks_attr)
                else:
                    debug_info["internal_callbacks"] = "No _callbacks attribute found"
            except Exception:
                debug_info["internal_callbacks"] = "Cannot access _callbacks"
        
        # Test manual data injection to verify the flow works
        test_symbol = "DEBUG_TEST"
        live_market_data[test_symbol] = {
            'symbol': test_symbol,
            'ltp': 999.99,
            'volume': 12345,
            'timestamp': datetime.now().isoformat(),
            'data_source': 'MANUAL_DEBUG_INJECTION'
        }
        
        debug_info["manual_injection_test"] = "injected DEBUG_TEST symbol"
        debug_info["manual_injection_success"] = test_symbol in live_market_data
        
        return {
            "success": True,
            "debug_info": debug_info
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": str(type(e))
        }

@router.post("/debug/force-callback-test")
async def force_callback_test():
    """Force trigger callback test data"""
    try:
        from data.sharekhan_client import sharekhan_client, live_market_data
        
        if not sharekhan_client.connected:
            return {"success": False, "error": "ShareKhan not connected"}
        
        # ELIMINATED: Manual fake data injection that could mislead about real market data
        # ❌ test_data = {
        # ❌     'MANUAL_TEST_NIFTY': {
        # ❌         'symbol': 'MANUAL_TEST_NIFTY',
        # ❌         'ltp': 23456.78,
        # ❌         'volume': 987654,
        # ❌         'timestamp': datetime.now().isoformat(),
        # ❌         'data_source': 'FORCED_CALLBACK_SIMULATION'
        # ❌     }
        # ❌ }
        # ❌ 
        # ❌ live_market_data.update(test_data)
        
        # SAFETY: Return error instead of fake market data injection
        logger.error("CRITICAL: Manual fake data injection ELIMINATED to prevent fake market data")
        
        return {
            "success": False,
            "error": "SAFETY: Manual fake data injection disabled - real ShareKhan callbacks required",
            "message": "Fake callback simulation eliminated for safety"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/debug/test-live-data-call")
async def test_live_data_call():
    """Test the actual start_live_data call to see if it's working"""
    try:
        from data.sharekhan_client import sharekhan_client, live_market_data
        
        if not sharekhan_client.connected or not sharekhan_client.td_obj:
            return {"success": False, "error": "ShareKhan not connected"}
        
        td_obj = sharekhan_client.td_obj
        
        # Test symbols
        test_symbols = ['NIFTY', 'BANKNIFTY']
        
        # Clear any existing data
        for symbol in test_symbols:
            live_market_data.pop(symbol, None)
        
        # Try calling start_live_data directly and capture the result
        try:
            result = td_obj.start_live_data(test_symbols)
            
            return {
                "success": True,
                "start_live_data_result": str(result),
                "test_symbols": test_symbols,
                "td_obj_type": str(type(td_obj)),
                "message": "start_live_data called - check if callbacks fire in next 30 seconds"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"start_live_data failed: {str(e)}",
                "error_type": str(type(e))
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/debug/callback-registration-test")
async def callback_registration_test():
    """Test if callbacks can be re-registered manually"""
    try:
        from data.sharekhan_client import sharekhan_client, live_market_data
        
        if not sharekhan_client.connected or not sharekhan_client.td_obj:
            return {"success": False, "error": "ShareKhan not connected"}
        
        td_obj = sharekhan_client.td_obj
        
        # Counter for callback calls
        callback_counter = {"count": 0}
        
        # Re-register a simple test callback
        @td_obj.trade_callback
        def test_callback(tick_data):
            callback_counter["count"] += 1
            symbol = tick_data.get('symbol', 'UNKNOWN')
            ltp = tick_data.get('ltp', 0)
            
            # Inject into live data
            live_market_data[f"TEST_CALLBACK_{symbol}"] = {
                'symbol': f"TEST_CALLBACK_{symbol}",
                'ltp': ltp,
                'volume': tick_data.get('volume', 0),
                'timestamp': datetime.now().isoformat(),
                'data_source': 'MANUAL_CALLBACK_REGISTRATION',
                'callback_count': callback_counter["count"]
            }
        
        # Try to start live data for a specific symbol
        test_symbol = 'NIFTY'
        result = td_obj.start_live_data([test_symbol])
        
        return {
            "success": True,
            "message": "Test callback re-registered",
            "start_live_data_result": str(result),
            "test_symbol": test_symbol,
            "note": "Check for TEST_CALLBACK_NIFTY in live data after 30 seconds"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": str(type(e))
        }

@router.post("/force-disconnect")
async def force_disconnect_sharekhan():
    """Force disconnect ShareKhan (deployment cleanup)"""
    try:
        from data.sharekhan_client import force_disconnect_sharekhan
        
        logger.info("🛑 Force disconnect requested via API")
        result = force_disconnect_sharekhan()
        
        if result:
            return {
                "success": True,
                "message": "ShareKhan force disconnected successfully",
                "action": "force_disconnect",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "message": "Force disconnect failed",
                "action": "force_disconnect"
            }
            
    except Exception as e:
        logger.error(f"Force disconnect error: {e}")
        return {
            "success": False,
            "message": f"Force disconnect failed: {str(e)}",
            "error": str(e)
        }

@router.post("/deployment-safe-connect")
async def deployment_safe_connect():
    """Deployment-safe connection with overlap handling"""
    try:
        from data.sharekhan_client import sharekhan_client
        
        logger.info("🔄 Deployment-safe connection requested")
        
        # Force disconnect any existing connections first
        sharekhan_client.force_disconnect()
        
        # Wait a moment for cleanup
        import asyncio
        await asyncio.sleep(2)
        
        # Now attempt new connection
        result = sharekhan_client.connect()
        
        if result:
            status = sharekhan_client.get_status()
            return {
                "success": True,
                "message": "ShareKhan connected with deployment overlap handling",
                "status": status,
                "action": "deployment_safe_connect"
            }
        else:
            return {
                "success": False,
                "message": "Deployment-safe connection failed",
                "action": "deployment_safe_connect",
                "help": "Try setting SKIP_SHAREKHAN_AUTO_INIT=true to break overlap cycle"
            }
            
    except Exception as e:
        logger.error(f"Deployment-safe connect error: {e}")
        return {
            "success": False,
            "message": f"Deployment-safe connect failed: {str(e)}",
            "error": str(e)
        }

@router.get("/deployment-status")
async def get_deployment_status():
    """Get deployment-specific status information"""
    try:
        from data.sharekhan_client import get_sharekhan_status
        import os
        
        status = get_sharekhan_status()
        
        # Add deployment environment info
        deployment_info = {
            "environment": os.getenv("ENVIRONMENT", "development"),
            "app_url": os.getenv("APP_URL", ""),
            "skip_auto_init": os.getenv("SKIP_SHAREKHAN_AUTO_INIT", "false"),
            "is_production": os.getenv("ENVIRONMENT") == "production",
            "is_digitalocean": "ondigitalocean.app" in os.getenv("APP_URL", "")
        }
        
        return {
            "success": True,
            "sharekhan_status": status,
            "deployment_info": deployment_info,
            "overlap_prevention": {
                "active": deployment_info["skip_auto_init"] == "true",
                "recommendation": "Set SKIP_SHAREKHAN_AUTO_INIT=true if experiencing overlap issues"
            }
        }
        
    except Exception as e:
        logger.error(f"Deployment status error: {e}")
        return {
            "success": False,
            "message": f"Deployment status check failed: {str(e)}",
            "error": str(e)
        }

@router.get("/connection-status")
async def get_detailed_connection_status():
    """Get detailed ShareKhan connection status with PERMANENT FIX information"""
    try:
        from data.sharekhan_client import sharekhan_client, sharekhan_connection_status
        
        # Get enhanced status from permanent fix
        if sharekhan_client:
            client_status = sharekhan_client.get_status()
        else:
            client_status = {'connected': False}
        
        detailed_status = {
            'client_connected': client_status.get('connected', False),
            'global_status': sharekhan_connection_status,
            'retry_disabled': sharekhan_connection_status.get('retry_disabled', False),
            'permanent_block': sharekhan_connection_status.get('permanent_block', False),
            'error_type': sharekhan_connection_status.get('error'),
            'can_retry': not sharekhan_connection_status.get('retry_disabled', False),
            'connection_attempts': client_status.get('connection_attempts', 0),
            'max_attempts': client_status.get('max_attempts', 1),
            'global_connection_active': client_status.get('global_connection_active', False),
            'implementation': client_status.get('implementation', 'UNKNOWN'),
            'recommendations': []
        }
        
        # Add recommendations based on status with permanent fix info
        if sharekhan_connection_status.get('error') == 'USER_ALREADY_CONNECTED':
            detailed_status['recommendations'] = [
                "PERMANENT FIX: Account connection conflict detected",
                "Use /force-disconnect endpoint to clear ALL connection state",
                "Persistent state tracking prevents retry loops",
                "Connection blocked until manual reset",
                "Alternative: Wait 10 minutes for auto-expiry"
            ]
        elif detailed_status['permanent_block']:
            detailed_status['recommendations'] = [
                "Connection permanently blocked due to repeated failures",
                "Use /force-disconnect to reset connection state",
                "Check ShareKhan account status and credentials",
                "Verify no other applications are connected"
            ]
        elif not detailed_status['client_connected']:
            detailed_status['recommendations'] = [
                "Try manual connection via /connect endpoint",
                "Check credentials in environment variables",
                "Verify ShareKhan account is active",
                "Use /force-disconnect first if previous attempts failed"
            ]
        else:
            detailed_status['recommendations'] = [
                "Connection is healthy and active",
                "Market data should be flowing normally",
                "All systems operational"
            ]
        
        return APIResponse(
            success=True,
            message="Detailed connection status retrieved (PERMANENT FIX)",
            data=detailed_status
        ).dict()
        
    except Exception as e:
        logger.error(f"Error getting detailed status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 