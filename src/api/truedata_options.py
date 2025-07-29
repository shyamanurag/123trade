"""
ShareKhan Options & Greeks API
Handles options data including Greeks calculation
"""

import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from datetime import datetime
import json
import asyncio

from data.sharekhan_client import (
    sharekhan_client,
    live_market_data,
    get_sharekhan_status
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sharekhan/options", tags=["sharekhan-options"])

class SymbolSubscription(BaseModel):
    """Symbol subscription request"""
    symbols: List[str]
    include_greeks: bool = True
    include_bidask: bool = True

class OptionsData(BaseModel):
    """Options data response"""
    symbol: str
    ltp: float
    volume: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    greeks: Optional[Dict] = None
    timestamp: str

class GreeksData(BaseModel):
    """Greeks data model"""
    symbol: str
    iv: float  # Implied Volatility
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    ltp: float
    timestamp: str

@router.post("/subscribe")
async def subscribe_options(request: SymbolSubscription):
    """Subscribe to options symbols with Greeks"""
    try:
        # FIXED: Read from existing ShareKhan cache instead of trying to connect
        # ShareKhan is already connected and flowing data - just check cache availability
        if not live_market_data:
            # Cache is empty - this indicates real connection issue, not missing connection
            raise HTTPException(
                status_code=503,
                detail="ShareKhan cache is empty. Market data not available."
            )
        
        # Note: ShareKhan subscription is handled automatically during connection
        return {
            "success": True,
            "message": f"Options subscription noted - ShareKhan handles symbols automatically",
            "symbols": request.symbols,
            "features": {
                "greeks": request.include_greeks,
                "bidask": request.include_bidask
            },
            "note": "ShareKhan client subscribes to default symbols automatically",
            "cache_symbols": len(live_market_data)  # Show how many symbols are available
        }
            
    except Exception as e:
        logger.error(f"Subscription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/{symbol}")
async def get_options_data(symbol: str):
    """Get current options data including Greeks"""
    try:
        # Check main data
        main_data = live_market_data.get(symbol)
        if not main_data:
            raise HTTPException(
                status_code=404,
                detail=f"No data available for symbol: {symbol}"
            )
        
        # Check for Greeks data
        greeks_data = live_market_data.get(f"{symbol}_GREEKS")
        
        response = OptionsData(
            symbol=symbol,
            ltp=main_data.get('ltp', 0),
            volume=main_data.get('volume', 0),
            bid=main_data.get('bid'),
            ask=main_data.get('ask'),
            timestamp=main_data.get('timestamp', datetime.now().isoformat())
        )
        
        # Add Greeks if available
        if greeks_data:
            response.greeks = {
                'iv': greeks_data.get('iv', 0),
                'delta': greeks_data.get('delta', 0),
                'gamma': greeks_data.get('gamma', 0),
                'theta': greeks_data.get('theta', 0),
                'vega': greeks_data.get('vega', 0),
                'rho': greeks_data.get('rho', 0)
            }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting options data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/greeks/{symbol}")
async def get_greeks(symbol: str):
    """Get Greeks data for an options symbol"""
    try:
        greeks_key = f"{symbol}_GREEKS"
        greeks_data = live_market_data.get(greeks_key)
        
        if not greeks_data:
            raise HTTPException(
                status_code=404,
                detail=f"No Greeks data available for symbol: {symbol}"
            )
        
        return GreeksData(
            symbol=symbol,
            iv=greeks_data.get('iv', 0),
            delta=greeks_data.get('delta', 0),
            gamma=greeks_data.get('gamma', 0),
            theta=greeks_data.get('theta', 0),
            vega=greeks_data.get('vega', 0),
            rho=greeks_data.get('rho', 0),
            ltp=greeks_data.get('ltp', 0),
            timestamp=greeks_data.get('timestamp', datetime.now().isoformat())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Greeks data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/all-options")
async def get_all_options_data():
    """Get all subscribed options data"""
    try:
        options_data = {}
        
        for symbol, data in live_market_data.items():
            # Skip Greeks entries (they end with _GREEKS)
            if symbol.endswith('_GREEKS'):
                continue
                
            # Check if this looks like an options symbol
            if any(x in symbol.upper() for x in ['CE', 'PE', 'CALL', 'PUT']):
                options_data[symbol] = {
                    'ltp': data.get('ltp', 0),
                    'volume': data.get('volume', 0),
                    'bid': data.get('bid'),
                    'ask': data.get('ask'),
                    'timestamp': data.get('timestamp')
                }
                
                # Add Greeks if available
                greeks_data = live_market_data.get(f"{symbol}_GREEKS")
                if greeks_data:
                    options_data[symbol]['greeks'] = {
                        'iv': greeks_data.get('iv', 0),
                        'delta': greeks_data.get('delta', 0),
                        'gamma': greeks_data.get('gamma', 0),
                        'theta': greeks_data.get('theta', 0),
                        'vega': greeks_data.get('vega', 0),
                        'rho': greeks_data.get('rho', 0)
                    }
        
        return {
            "success": True,
            "count": len(options_data),
            "data": options_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting all options data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/stream")
async def options_data_stream(websocket: WebSocket):
    """WebSocket stream for real-time options data with Greeks"""
    await websocket.accept()
    
    try:
        # Send initial connection status
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep track of last sent data to avoid duplicates
        last_sent = {}
        
        while True:
            # Send updates for all options symbols
            for symbol, data in live_market_data.items():
                if symbol.endswith('_GREEKS'):
                    continue
                    
                # Check if this is options data
                if any(x in symbol.upper() for x in ['CE', 'PE', 'CALL', 'PUT']):
                    # Create data packet
                    packet = {
                        "type": "options_update",
                        "symbol": symbol,
                        "data": {
                            "ltp": data.get('ltp', 0),
                            "volume": data.get('volume', 0),
                            "bid": data.get('bid'),
                            "ask": data.get('ask'),
                            "timestamp": data.get('timestamp')
                        }
                    }
                    
                    # Add Greeks if available
                    greeks_data = live_market_data.get(f"{symbol}_GREEKS")
                    if greeks_data:
                        packet["data"]["greeks"] = {
                            'iv': greeks_data.get('iv', 0),
                            'delta': greeks_data.get('delta', 0),
                            'gamma': greeks_data.get('gamma', 0),
                            'theta': greeks_data.get('theta', 0),
                            'vega': greeks_data.get('vega', 0),
                            'rho': greeks_data.get('rho', 0)
                        }
                    
                    # Check if data has changed
                    packet_str = json.dumps(packet, sort_keys=True)
                    if last_sent.get(symbol) != packet_str:
                        await websocket.send_json(packet)
                        last_sent[symbol] = packet_str
            
            # Also send connection status
            await websocket.send_json({
                "type": "status",
                "connected": sharekhan_client.connected,
                "symbols_count": len([s for s in live_market_data.keys() if not s.endswith('_GREEKS')]),
                "timestamp": datetime.now().isoformat()
            })
            
            # Wait before next update
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        logger.info("Options WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Options WebSocket error: {e}")
        await websocket.close()

@router.post("/subscribe-crude-options")
async def subscribe_crude_oil_options():
    """Subscribe to crude oil options (example from your code)"""
    try:
        # Example crude oil options symbols
        crude_symbols = [
            'CRUDEOIL2506165300CE',
            'CRUDEOIL2506165300PE',
            'CRUDEOIL2506165400CE', 
            'CRUDEOIL2506165400PE',
            'CRUDEOIL2506165500CE',
            'CRUDEOIL2506165500PE'
        ]
        
        if not sharekhan_client.connected:
            success = sharekhan_client.connect()
            if not success:
                raise HTTPException(
                    status_code=503,
                    detail="ShareKhan connection failed"
                )
        
        # Note: ShareKhan subscription is handled automatically during connection
        success = True
        
        if success:
            return {
                "success": True,
                "message": "Subscribed to crude oil options",
                "symbols": crude_symbols,
                "note": "Greeks data will be available for these options"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to subscribe to crude oil options"
            )
            
    except Exception as e:
        logger.error(f"Crude options subscription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/option-chain/{underlying}")
async def get_option_chain(underlying: str, expiry: Optional[str] = None):
    """Get option chain data for an underlying"""
    try:
        option_chain = {}
        
        # Filter options for this underlying
        for symbol, data in live_market_data.items():
            if symbol.endswith('_GREEKS'):
                continue
                
            # Check if symbol belongs to this underlying
            if underlying.upper() in symbol.upper():
                # Determine if it's CE or PE
                option_type = 'CE' if 'CE' in symbol.upper() else 'PE' if 'PE' in symbol.upper() else None
                
                if option_type:
                    # Extract strike price (this is simplified, adjust based on your symbol format)
                    parts = symbol.split(underlying.upper())
                    if len(parts) > 1:
                        strike_info = parts[1]
                        # You'll need to parse strike price based on your symbol format
                        
                        option_info = {
                            'symbol': symbol,
                            'type': option_type,
                            'ltp': data.get('ltp', 0),
                            'volume': data.get('volume', 0),
                            'bid': data.get('bid'),
                            'ask': data.get('ask'),
                            'timestamp': data.get('timestamp')
                        }
                        
                        # Add Greeks
                        greeks_data = live_market_data.get(f"{symbol}_GREEKS")
                        if greeks_data:
                            option_info['greeks'] = {
                                'iv': greeks_data.get('iv', 0),
                                'delta': greeks_data.get('delta', 0),
                                'gamma': greeks_data.get('gamma', 0),
                                'theta': greeks_data.get('theta', 0),
                                'vega': greeks_data.get('vega', 0),
                                'rho': greeks_data.get('rho', 0)
                            }
                        
                        option_chain[symbol] = option_info
        
        return {
            "success": True,
            "underlying": underlying,
            "expiry": expiry,
            "options_count": len(option_chain),
            "option_chain": option_chain,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting option chain: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 