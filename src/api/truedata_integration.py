"""
TrueData Integration API Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
import logging
from datetime import datetime
import asyncio

from data.truedata_client import (
    truedata_client, 
    live_market_data, 
    truedata_connection_status,
    initialize_truedata,
    subscribe_to_symbols,
    get_live_data_for_symbol
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/truedata", tags=["truedata"])

@router.post("/connect")
async def connect_truedata(credentials: Dict):
    """Connect to TrueData live feed"""
    try:
        username = credentials.get("username")
        password = credentials.get("password")
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password required")
        
        # Set credentials in environment for singleton client
        import os
        os.environ['TRUEDATA_USERNAME'] = username
        os.environ['TRUEDATA_PASSWORD'] = password
        
        # Initialize TrueData singleton client
        success = initialize_truedata()
        
        if success:
            return {
                "success": True,
                "message": "TrueData connected successfully",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to connect to TrueData")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting to TrueData: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/subscribe")
async def subscribe_symbols(symbols: List[str]):
    """Subscribe to symbols for live data"""
    try:
        if not truedata_client.connected:
            raise HTTPException(status_code=503, detail="TrueData client not connected")
        
        success = subscribe_to_symbols(symbols)
        
        if success:
            return {
                "success": True,
                "message": f"Subscribed to {len(symbols)} symbols",
                "symbols": symbols,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to subscribe to symbols")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subscribing to symbols: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/unsubscribe")
async def unsubscribe_symbols(symbols: List[str]):
    """Unsubscribe from symbols"""
    try:
        if not truedata_client.connected:
            raise HTTPException(status_code=503, detail="TrueData client not connected")
        
        # For now, just remove from live data (TrueData SDK doesn't have unsubscribe)
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
async def get_truedata_status():
    """Get TrueData connection status"""
    try:
        if not truedata_client:
            return {
                "connected": False,
                "message": "TrueData client not initialized",
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "connected": truedata_client.connected,
            "subscribed_symbols": list(live_market_data.keys()),
            "total_symbols": len(live_market_data),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting TrueData status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/data/{symbol}")
async def get_symbol_data(symbol: str):
    """Get latest market data for a specific symbol"""
    try:
        if not truedata_client.connected:
            raise HTTPException(status_code=503, detail="TrueData client not connected")
        
        data = get_live_data_for_symbol(symbol)
        
        if data:
            return {
                "success": True,
                "symbol": symbol,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "symbol": symbol,
                "message": "No data available for symbol",
                "timestamp": datetime.now().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting symbol data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/data")
async def get_all_market_data():
    """Get all market data"""
    try:
        if not truedata_client.connected:
            raise HTTPException(status_code=503, detail="TrueData client not connected")
        
        return {
            "success": True,
            "data": live_market_data,
            "total_symbols": len(live_market_data),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting all market data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/disconnect")
async def disconnect_truedata():
    """Disconnect from TrueData"""
    try:
        if not truedata_client.connected:
            raise HTTPException(status_code=503, detail="TrueData client not connected")
        
        truedata_client.disconnect()
        
        return {
            "success": True,
            "message": "TrueData disconnected successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting from TrueData: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# WebSocket integration for real-time data
@router.websocket("/ws/{symbol}")
async def truedata_websocket(websocket, symbol: str):
    """WebSocket endpoint for real-time TrueData"""
    try:
        if not truedata_client.connected:
            await websocket.close(code=1011, reason="TrueData client not connected")
            return
        
        # Subscribe to symbol if not already subscribed
        if symbol not in live_market_data:
            subscribe_to_symbols([symbol])
        
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
    """Debug TrueData client internals"""
    try:
        # Try both client paths
        client = None
        client_type = "unknown"
        
        try:
            from data.truedata_client import truedata_client, live_market_data, truedata_connection_status
            client = truedata_client
            client_type = "singleton"
            
            return {
                "success": True,
                "client_type": client_type,
                "client_status": client.get_status() if hasattr(client, 'get_status') else "no_status_method",
                "live_data_count": len(live_market_data),
                "live_data_keys": list(live_market_data.keys()),
                "connection_status": truedata_connection_status,
                "sample_data": dict(list(live_market_data.items())[:3]) if live_market_data else {}
            }
            
        except ImportError:
            try:
                from src.data.truedata_client import get_truedata_client
                client = get_truedata_client()
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
                    "error": "No TrueData client found"
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/debug/force-data")
async def force_create_sample_data():
    """Force create sample data to test frontend"""
    try:
        # Import the working client
        try:
            from data.truedata_client import live_market_data
            
            # Force inject sample data for testing
            live_market_data.update({
                "NIFTY": {
                    "symbol": "NIFTY",
                    "ltp": 23250.75,
                    "volume": 1250000,
                    "change": 125.50,
                    "change_percent": 0.54,
                    "timestamp": datetime.now().isoformat(),
                    "data_source": "FORCED_SAMPLE"
                },
                "BANKNIFTY": {
                    "symbol": "BANKNIFTY", 
                    "ltp": 51150.25,
                    "volume": 850000,
                    "change": -85.75,
                    "change_percent": -0.17,
                    "timestamp": datetime.now().isoformat(),
                    "data_source": "FORCED_SAMPLE"
                }
            })
            
            return {
                "success": True,
                "message": "Sample data injected",
                "data_count": len(live_market_data)
            }
            
        except ImportError:
            return {
                "success": False,
                "error": "Cannot access live_market_data"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/debug/callback-status")
async def debug_callback_status():
    """Debug TrueData callback registration and data flow"""
    try:
        from data.truedata_client import truedata_client, live_market_data
        
        debug_info = {
            "timestamp": datetime.now().isoformat(),
            "client_connected": truedata_client.connected if truedata_client else False,
            "td_obj_exists": hasattr(truedata_client, 'td_obj') and truedata_client.td_obj is not None,
            "live_data_count": len(live_market_data),
            "live_data_keys": list(live_market_data.keys()),
        }
        
        # Check if td_obj has the callback methods
        if hasattr(truedata_client, 'td_obj') and truedata_client.td_obj:
            td_obj = truedata_client.td_obj
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
        from data.truedata_client import truedata_client, live_market_data
        
        if not truedata_client.connected:
            return {"success": False, "error": "TrueData not connected"}
        
        # Manually inject test data to simulate callback
        test_data = {
            'MANUAL_TEST_NIFTY': {
                'symbol': 'MANUAL_TEST_NIFTY',
                'ltp': 23456.78,
                'volume': 987654,
                'timestamp': datetime.now().isoformat(),
                'data_source': 'FORCED_CALLBACK_SIMULATION'
            }
        }
        
        live_market_data.update(test_data)
        
        return {
            "success": True,
            "message": "Test data injected manually",
            "test_data": test_data,
            "total_symbols": len(live_market_data)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        } 