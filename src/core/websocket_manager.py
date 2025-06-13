"""
Enhanced WebSocket manager with rate limiting, circuit breaker, and metrics
"""
from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, List, Optional, Set, Any
import json
import logging
import asyncio
from datetime import datetime
import uuid
from .websocket_config import (
    DEFAULT_CONFIG,
    get_ssl_context,
    MAX_CONNECTIONS_PER_USER,
    MAX_MESSAGE_SIZE,
    HEARTBEAT_INTERVAL,
    CONNECTION_TIMEOUT,
    RATE_LIMIT_WINDOW,
    RATE_LIMIT_MAX,
    CIRCUIT_BREAKER_THRESHOLD,
    CIRCUIT_BREAKER_TIMEOUT,
    BATCH_INTERVAL,
    MAX_BATCH_SIZE
)
from .websocket_metrics import WebSocketMetrics
from .websocket_limiter import RateLimiter, CircuitBreaker

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections with enhanced features"""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.user_connections: Dict[str, int] = {}
        self.rate_limiter = RateLimiter(RATE_LIMIT_WINDOW, RATE_LIMIT_MAX)
        self.circuit_breaker = CircuitBreaker(CIRCUIT_BREAKER_THRESHOLD, CIRCUIT_BREAKER_TIMEOUT)
        self.ssl_context = get_ssl_context()
        
        # Initialize components
        self.metrics = WebSocketMetrics()
        self.total_connections = 0
        
        # Message batching
        self.message_batch: Dict[str, List[Dict]] = {}
        self.batch_tasks: Dict[str, asyncio.Task] = {}
        self.websocket_ids: Dict[WebSocket, str] = {}
        
        # Room subscriptions
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.subscription_rooms: Dict[str, Set[str]] = {}
        
    async def validate_connection(self, websocket: WebSocket, user_id: str) -> bool:
        """Validate new connection"""
        try:
            # Check connection count
            if self.user_connections.get(user_id, 0) >= MAX_CONNECTIONS_PER_USER:
                logger.warning(f"User {user_id} exceeded max connections")
                return False
                
            # Check circuit breaker
            if not await self.circuit_breaker.is_allowed(f"connect_{user_id}"):
                logger.warning("Circuit breaker is open")
                return False
                
            # Check rate limit
            if not await self.rate_limiter.is_allowed(f"connect_{user_id}"):
                logger.warning(f"User {user_id} exceeded rate limit")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Connection validation error: {e}")
            return False

    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect with validation and SSL"""
        try:
            if not await self.validate_connection(websocket, user_id):
                raise HTTPException(status_code=429, detail="Connection rejected")
                
            await websocket.accept()
            
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            self.active_connections[user_id].append(websocket)
            self.user_connections[user_id] = self.user_connections.get(user_id, 0) + 1
            
            # Generate unique ID for websocket
            ws_id = str(uuid.uuid4())
            self.websocket_ids[websocket] = ws_id
            
            # Initialize connection metadata
            self.connection_metadata[ws_id] = {
                'user_id': user_id,
                'subscriptions': set(),
                'last_heartbeat': datetime.now(),
                'connected_at': datetime.now()
            }
            
            # Start heartbeat
            asyncio.create_task(self._heartbeat(websocket))
            
            logger.info(f"User {user_id} connected successfully")
        except Exception as e:
            logger.error(f"Connection error: {e}")
            raise

    async def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect with cleanup"""
        try:
            if user_id in self.active_connections:
                self.active_connections[user_id].remove(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                    
            self.user_connections[user_id] = max(0, self.user_connections.get(user_id, 1) - 1)
            if self.user_connections[user_id] == 0:
                del self.user_connections[user_id]
                
            # Cleanup websocket ID and batching
            if websocket in self.websocket_ids:
                ws_id = self.websocket_ids[websocket]
                if ws_id in self.batch_tasks:
                    self.batch_tasks[ws_id].cancel()
                    del self.batch_tasks[ws_id]
                if ws_id in self.message_batch:
                    del self.message_batch[ws_id]
                if ws_id in self.connection_metadata:
                    del self.connection_metadata[ws_id]
                del self.websocket_ids[websocket]
                
            logger.info(f"User {user_id} disconnected")
        except Exception as e:
            logger.error(f"Disconnection error: {e}")

    async def _heartbeat(self, websocket: WebSocket):
        """Send periodic heartbeat"""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                if websocket.client_state.CONNECTED:
                    await websocket.send_json({
                        "type": "heartbeat",
                        "timestamp": datetime.utcnow().isoformat()
                    })
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")

    async def broadcast(self, message: dict, exclude_user: Optional[str] = None):
        """Broadcast with validation"""
        try:
            if len(json.dumps(message)) > MAX_MESSAGE_SIZE:
                logger.warning("Message exceeds size limit")
                return
                
            for user_id, connections in self.active_connections.items():
                if user_id != exclude_user:
                    for connection in connections:
                        try:
                            await self.send_message(connection, message)
                        except Exception as e:
                            logger.error(f"Broadcast error to {user_id}: {e}")
        except Exception as e:
            logger.error(f"Broadcast error: {e}")

    async def send_personal_message(self, message: dict, user_id: str):
        """Send personal message with validation"""
        try:
            if len(json.dumps(message)) > MAX_MESSAGE_SIZE:
                logger.warning("Message exceeds size limit")
                return
                
            if user_id in self.active_connections:
                for connection in self.active_connections[user_id]:
                    try:
                        await self.send_message(connection, message)
                    except Exception as e:
                        logger.error(f"Personal message error to {user_id}: {e}")
        except Exception as e:
            logger.error(f"Personal message error: {e}")

    def get_active_connections(self) -> Dict[str, int]:
        """Get current connection stats"""
        return {
            user_id: len(connections)
            for user_id, connections in self.active_connections.items()
        }
        
    async def send_message(self, websocket: WebSocket, message: Dict):
        """Send a message with batching support"""
        try:
            if websocket not in self.websocket_ids:
                return
                
            ws_id = self.websocket_ids[websocket]
            
            # Add to batch
            if ws_id not in self.message_batch:
                self.message_batch[ws_id] = []
                # Start batch task if not exists
                if ws_id not in self.batch_tasks:
                    self.batch_tasks[ws_id] = asyncio.create_task(
                        self._process_batch(ws_id)
                    )
                    
            self.message_batch[ws_id].append(message)
            
            # Send immediately if batch is full
            if len(self.message_batch[ws_id]) >= MAX_BATCH_SIZE:
                await self._send_batch(ws_id)
        except Exception as e:
            logger.error(f"Error adding message to batch: {e}")
            
    async def _process_batch(self, ws_id: str):
        """Process message batches"""
        try:
            while True:
                await asyncio.sleep(BATCH_INTERVAL / 1000)
                await self._send_batch(ws_id)
        except asyncio.CancelledError:
            # Send any remaining messages
            await self._send_batch(ws_id)
            
    async def _send_batch(self, ws_id: str):
        """Send a batch of messages"""
        if ws_id not in self.message_batch or not self.message_batch[ws_id]:
            return
            
        try:
            # Find websocket by ID
            websocket = None
            for ws, id in self.websocket_ids.items():
                if id == ws_id:
                    websocket = ws
                    break
                    
            if not websocket:
                return
                
            messages = self.message_batch[ws_id]
            self.message_batch[ws_id] = []
            
            # Send batch
            await websocket.send_json({
                'type': 'batch',
                'messages': messages,
                'timestamp': datetime.now().isoformat()
            })
            
            # Update metrics
            await self.metrics.increment('messages_sent', len(messages))
            await self.metrics.increment('message_types', 
                labels={'type': 'batch', 'size': str(len(messages))})
                
        except Exception as e:
            logger.error(f"Error sending batch: {e}")
            await self.metrics.increment('errors')
            
    async def subscribe_to_room(self, websocket: WebSocket, room_name: str) -> bool:
        """Subscribe connection to a room"""
        if websocket not in self.websocket_ids:
            return False
            
        ws_id = self.websocket_ids[websocket]
        if ws_id not in self.connection_metadata:
            return False
            
        # Add to subscription room
        if room_name not in self.subscription_rooms:
            self.subscription_rooms[room_name] = set()
        self.subscription_rooms[room_name].add(ws_id)
        
        # Update connection metadata
        self.connection_metadata[ws_id]['subscriptions'].add(room_name)
        
        # Update metrics
        await self.metrics.increment('room_subscriptions', 
            labels={'room': room_name})
            
        logger.info(f"Connection {ws_id} subscribed to room: {room_name}")
        return True
        
    async def unsubscribe_from_room(self, websocket: WebSocket, room_name: str) -> bool:
        """Unsubscribe connection from a room"""
        if websocket not in self.websocket_ids:
            return False
            
        ws_id = self.websocket_ids[websocket]
        if ws_id not in self.connection_metadata:
            return False
            
        # Remove from subscription room
        if room_name in self.subscription_rooms:
            self.subscription_rooms[room_name].discard(ws_id)
            if not self.subscription_rooms[room_name]:
                del self.subscription_rooms[room_name]
        
        # Update connection metadata
        self.connection_metadata[ws_id]['subscriptions'].discard(room_name)
        
        logger.info(f"Connection {ws_id} unsubscribed from room: {room_name}")
        return True
        
    async def broadcast_to_room(self, room_name: str, message: Dict):
        """Broadcast message to all connections in a room"""
        if room_name not in self.subscription_rooms:
            return
            
        for ws_id in self.subscription_rooms[room_name]:
            # Find websocket by ID
            websocket = None
            for ws, id in self.websocket_ids.items():
                if id == ws_id:
                    websocket = ws
                    break
                    
            if websocket:
                try:
                    await self.send_message(websocket, message)
                except Exception as e:
                    logger.error(f"Error broadcasting to room {room_name}: {e}")
                    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return await self.metrics.get_metrics()
        
    async def check_alerts(self):
        """Check for metric alerts"""
        metrics = await self.metrics.get_metrics()
        
        # Check connection count
        await self.metrics.alert('connections', 1000, 
            "High number of concurrent connections")
            
        # Check error rate
        if 'rates' in metrics and metrics['rates']['errors_per_second'] > 1:
            logger.warning("High error rate detected")
            
        # Check latency
        if 'latency_stats' in metrics and metrics['latency_stats']['p95'] > 1000:
            logger.warning("High latency detected (p95 > 1000ms)") 