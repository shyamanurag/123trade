from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional
import logging

# Import from root directory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from websocket_manager import get_websocket_manager

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time trade updates"""
    connection_id = None
    try:
        # Get WebSocket manager instance
        ws_manager = get_websocket_manager()
        if not ws_manager:
            await websocket.close(code=1011, reason="WebSocket service unavailable")
            return
        
        # For now, use a default user_id. In production, this would come from authentication
        user_id = "default_user"
        
        # Connect client with user_id
        connection_id = await ws_manager.connection_manager.connect(websocket, user_id)
        
        try:
            # Keep connection alive and handle messages
            while True:
                # Wait for any message from client
                data = await websocket.receive_json()
                
                # Handle client messages
                response = await ws_manager.handle_client_message(connection_id, data)
                if response:
                    await websocket.send_json(response)
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {connection_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            # Cleanup on disconnect
            if connection_id:
                await ws_manager.connection_manager.disconnect(connection_id)
            
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {e}")
        if websocket.client_state.CONNECTED:
            await websocket.close() 