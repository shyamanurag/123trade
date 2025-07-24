"""
WebSocket API endpoints for real-time data streaming
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from typing import Set, AsyncGenerator, Dict, Any
import json
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()

# Store active connections with user context
active_connections: Dict[str, Set[WebSocket]] = {}
sse_clients: Set[asyncio.Queue] = set()
connection_stats = {
    'total_connections': 0,
    'active_connections': 0,
    'failed_connections': 0,
    'last_connection_time': None
}

@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time updates - IMPROVED"""
    client_id = f"{websocket.client.host}:{websocket.client.port}"
    logger.info(f"WebSocket connection attempt from {client_id}")
    
    try:
        # Accept connection with proper error handling
        await websocket.accept()
        
        # Add to active connections
        if 'all' not in active_connections:
            active_connections['all'] = set()
        active_connections['all'].add(websocket)
        
        # Update connection stats
        connection_stats['total_connections'] += 1
        connection_stats['active_connections'] = len(active_connections['all'])
        connection_stats['last_connection_time'] = datetime.now().isoformat()
        
        logger.info(f"✅ WebSocket connected: {client_id}. Active: {connection_stats['active_connections']}")
        
        # Send connection confirmation with server info
        await websocket.send_json({
            "type": "connection_established",
            "status": "connected",
            "client_id": client_id,
            "server_time": datetime.now().isoformat(),
            "message": "Real-time connection established",
            "features": ["trades", "positions", "orders", "market_data", "signals"]
        })
        
        # Main connection loop with improved error handling
        ping_interval = 30.0  # Send ping every 30 seconds
        last_ping = datetime.now()
        
        while True:
            try:
                # Check if ping is needed
                if (datetime.now() - last_ping).total_seconds() > ping_interval:
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": datetime.now().isoformat()
                    })
                    last_ping = datetime.now()
                
                # Wait for message with timeout
                message = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                
                # Handle different message types
                if message == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                elif message == "heartbeat":
                    await websocket.send_json({
                        "type": "heartbeat_response",
                        "server_time": datetime.now().isoformat(),
                        "status": "healthy"
                    })
                elif message.startswith("subscribe:"):
                    # Handle subscription requests
                    topic = message.split(":", 1)[1]
                    await websocket.send_json({
                        "type": "subscription_confirmed",
                        "topic": topic,
                        "timestamp": datetime.now().isoformat()
                    })
                    logger.info(f"Client {client_id} subscribed to {topic}")
                else:
                    # Handle JSON messages
                    try:
                        json_data = json.loads(message)
                        await handle_websocket_message(websocket, json_data, client_id)
                    except json.JSONDecodeError:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Invalid JSON format",
                            "timestamp": datetime.now().isoformat()
                        })
                        
            except asyncio.TimeoutError:
                # Timeout is normal - just continue the loop
                continue
            except WebSocketDisconnect:
                logger.info(f"Client {client_id} disconnected normally")
                break
            except Exception as e:
                logger.error(f"WebSocket error for {client_id}: {e}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Server error: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    })
                except:
                    break
                
    except Exception as e:
        logger.error(f"WebSocket connection error for {client_id}: {e}")
        connection_stats['failed_connections'] += 1
    finally:
        # Clean up connection
        if 'all' in active_connections:
            active_connections['all'].discard(websocket)
        connection_stats['active_connections'] = len(active_connections.get('all', set()))
        logger.info(f"WebSocket {client_id} disconnected. Active: {connection_stats['active_connections']}")

async def handle_websocket_message(websocket: WebSocket, data: Dict[str, Any], client_id: str):
    """Handle incoming WebSocket messages"""
    try:
        message_type = data.get("type", "unknown")
        
        if message_type == "subscribe":
            # Handle subscription
            topics = data.get("topics", [])
            await websocket.send_json({
                "type": "subscription_success",
                "topics": topics,
                "timestamp": datetime.now().isoformat()
            })
        elif message_type == "get_status":
            # Return current status
            await websocket.send_json({
                "type": "status_response",
                "data": {
                    "connection_stats": connection_stats,
                    "server_time": datetime.now().isoformat(),
                    "client_id": client_id
                }
            })
        else:
            # Echo back unknown messages
            await websocket.send_json({
                "type": "echo",
                "original_message": data,
                "timestamp": datetime.now().isoformat()
            })
    except Exception as e:
        logger.error(f"Error handling WebSocket message: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Error processing message: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })

# Server-Sent Events as fallback
@router.get("/sse")
async def sse_endpoint(request: Request):
    """Server-Sent Events endpoint as fallback for WebSocket"""
    logger.info(f"SSE connection from {request.client}")
    
    async def event_generator() -> AsyncGenerator[str, None]:
        queue = asyncio.Queue()
        sse_clients.add(queue)
        
        try:
            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connection', 'status': 'connected', 'message': 'SSE connection established', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            
            while True:
                try:
                    # Wait for messages with timeout
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(message)}\n\n"
                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                except asyncio.CancelledError:
                    break
        finally:
            sse_clients.discard(queue)
            logger.info(f"SSE client disconnected. Total SSE clients: {len(sse_clients)}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        }
    )

async def broadcast_message(message: dict):
    """Broadcast message to all connected clients (WebSocket and SSE)"""
    # Add timestamp if not present
    if 'timestamp' not in message:
        message['timestamp'] = datetime.utcnow().isoformat()
    
    # Broadcast to WebSocket clients
    if active_connections:
        disconnected = set()
        
        for connection in active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket client: {e}")
                disconnected.add(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            active_connections.discard(conn)
    
    # Broadcast to SSE clients
    for queue in sse_clients:
        try:
            await queue.put(message)
        except Exception as e:
            logger.error(f"Error broadcasting to SSE client: {e}")

# Add a test page for both WebSocket and SSE
@router.get("/test")
async def get_websocket_test():
    """Test page for WebSocket and SSE connections"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket/SSE Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            button { margin: 5px; padding: 10px; }
            #messages { 
                border: 1px solid #ccc; 
                height: 300px; 
                overflow-y: auto; 
                padding: 10px; 
                margin-top: 20px;
                background: #f5f5f5;
            }
            .error { color: red; }
            .success { color: green; }
            .info { color: blue; }
        </style>
    </head>
    <body>
        <h1>Real-time Connection Test</h1>
        
        <h2>WebSocket Test</h2>
        <button onclick="connectWS()">Connect WebSocket</button>
        <button onclick="sendPing()">Send Ping</button>
        <button onclick="disconnectWS()">Disconnect WebSocket</button>
        
        <h2>SSE Test (Fallback)</h2>
        <button onclick="connectSSE()">Connect SSE</button>
        <button onclick="disconnectSSE()">Disconnect SSE</button>
        
        <div id="messages"></div>
        
        <script>
            let ws = null;
            let eventSource = null;
            const messages = document.getElementById('messages');
            
            function log(msg, type = 'info') {
                const timestamp = new Date().toLocaleTimeString();
                messages.innerHTML += '<p class="' + type + '">[' + timestamp + '] ' + msg + '</p>';
                messages.scrollTop = messages.scrollHeight;
            }
            
            function connectWS() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    log('WebSocket already connected', 'error');
                    return;
                }
                
                const wsUrl = window.location.protocol === 'https:' 
                    ? 'wss://' + window.location.host + '/ws'
                    : 'ws://' + window.location.host + '/ws';
                
                log('Connecting to WebSocket: ' + wsUrl);
                ws = new WebSocket(wsUrl);
                
                ws.onopen = () => log('WebSocket connected', 'success');
                ws.onmessage = (e) => log('WebSocket received: ' + e.data);
                ws.onerror = (e) => log('WebSocket error occurred', 'error');
                ws.onclose = (e) => log('WebSocket disconnected (code: ' + e.code + ')', 'error');
            }
            
            function sendPing() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send('ping');
                    log('Sent ping via WebSocket');
                } else {
                    log('WebSocket not connected', 'error');
                }
            }
            
            function disconnectWS() {
                if (ws) {
                    ws.close();
                    ws = null;
                }
            }
            
            function connectSSE() {
                if (eventSource) {
                    log('SSE already connected', 'error');
                    return;
                }
                
                const sseUrl = '/ws/sse';
                log('Connecting to SSE: ' + sseUrl);
                
                eventSource = new EventSource(sseUrl);
                
                eventSource.onopen = () => log('SSE connected', 'success');
                
                eventSource.onmessage = (e) => {
                    log('SSE received: ' + e.data);
                };
                
                eventSource.onerror = (e) => {
                    if (eventSource.readyState === EventSource.CLOSED) {
                        log('SSE disconnected', 'error');
                    } else {
                        log('SSE error occurred', 'error');
                    }
                };
            }
            
            function disconnectSSE() {
                if (eventSource) {
                    eventSource.close();
                    eventSource = null;
                    log('SSE disconnected');
                }
            }
            
            // Auto-connect SSE if WebSocket fails
            function autoFallback() {
                connectWS();
                setTimeout(() => {
                    if (!ws || ws.readyState !== WebSocket.OPEN) {
                        log('WebSocket failed, falling back to SSE', 'info');
                        connectSSE();
                    }
                }, 3000);
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html) 