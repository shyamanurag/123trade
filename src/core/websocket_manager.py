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
import redis
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

# Singleton instance
_websocket_manager: Optional['WebSocketManager'] = None

def get_websocket_manager() -> Optional['WebSocketManager']:
    """Get the singleton WebSocket manager instance"""
    return _websocket_manager

async def initialize_websocket_manager(redis_client: redis.Redis) -> 'WebSocketManager':
    """Initialize the WebSocket manager singleton"""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager(redis_client)
        await _websocket_manager.start()
    return _websocket_manager

class WebSocketManager:
    """Manages WebSocket connections with enhanced features"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.user_connections: Dict[str, int] = {}
        self.rate_limiter = RateLimiter(RATE_LIMIT_WINDOW, RATE_LIMIT_MAX)
        self.circuit_breaker = CircuitBreaker(CIRCUIT_BREAKER_THRESHOLD, CIRCUIT_BREAKER_TIMEOUT)
        self.ssl_context = get_ssl_context()
        self.is_running = False
        self.background_tasks = []
        
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
    
    async def start(self):
        """Start the WebSocket manager and background tasks"""
        if self.is_running:
            return
            
        self.is_running = True
        
        # Start background tasks
        self.background_tasks = [
            asyncio.create_task(self._market_data_listener()),
            asyncio.create_task(self._position_update_listener()),
            asyncio.create_task(self._heartbeat_monitor()),
            asyncio.create_task(self._redis_subscriber())
        ]
        
        logger.info("WebSocket manager started with background tasks")
    
    async def stop(self):
        """Stop the WebSocket manager and cleanup"""
        if not self.is_running:
            return
            
        self.is_running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Close all connections
        await self.close_all()
        
        logger.info("WebSocket manager stopped")
    
    async def close_all(self):
        """Close all active WebSocket connections"""
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.close()
                except Exception as e:
                    logger.error(f"Error closing connection for user {user_id}: {e}")
        
        self.active_connections.clear()
        self.user_connections.clear()
        self.connection_metadata.clear()
        self.subscription_rooms.clear()
        self.websocket_ids.clear()
        
        logger.info("All WebSocket connections closed")
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Handle new WebSocket connection"""
        # Check connection limits
        if self.user_connections.get(user_id, 0) >= MAX_CONNECTIONS_PER_USER:
            raise HTTPException(status_code=429, detail="Too many connections")
        
        # Check rate limits
        if not self.rate_limiter.check(user_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Check circuit breaker
        if self.circuit_breaker.is_open():
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")
        
        await websocket.accept()
        
        # Generate unique connection ID
        connection_id = str(uuid.uuid4())
        self.websocket_ids[websocket] = connection_id
        
        # Update connection tracking
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        self.user_connections[user_id] = self.user_connections.get(user_id, 0) + 1
        
        # Initialize connection metadata
        self.connection_metadata[connection_id] = {
            'user_id': user_id,
            'connected_at': datetime.now(),
            'last_heartbeat': datetime.now(),
            'message_count': 0
        }
        
        self.total_connections += 1
        await self.metrics.increment_connections()
        
        logger.info(f"New WebSocket connection: {connection_id} for user {user_id}")
    
    async def disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnection"""
        connection_id = self.websocket_ids.get(websocket)
        if not connection_id:
            return
        
        metadata = self.connection_metadata.get(connection_id)
        if metadata:
            user_id = metadata['user_id']
            
            # Remove from active connections
            if user_id in self.active_connections:
                self.active_connections[user_id].remove(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            # Update user connection count
            self.user_connections[user_id] = max(0, self.user_connections.get(user_id, 1) - 1)
            
            # Clean up metadata
            del self.connection_metadata[connection_id]
            del self.websocket_ids[websocket]
            
            # Remove from rooms
            for room in self.subscription_rooms.values():
                if connection_id in room:
                    room.remove(connection_id)
            
            self.total_connections -= 1
            await self.metrics.decrement_connections()
            
            logger.info(f"WebSocket disconnected: {connection_id} for user {user_id}")
    
    async def send_message(self, websocket: WebSocket, message: Dict):
        """Send message to a specific WebSocket connection"""
        try:
            await websocket.send_json(message)
            connection_id = self.websocket_ids.get(websocket)
            if connection_id:
                self.connection_metadata[connection_id]['message_count'] += 1
            await self.metrics.increment_messages()
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            await self.disconnect(websocket)
    
    async def broadcast(self, message: Dict):
        """Broadcast message to all connected clients"""
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await self.send_message(connection, message)
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}: {e}")
    
    async def broadcast_to_user(self, user_id: str, message: Dict):
        """Broadcast message to all connections of a specific user"""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await self.send_message(connection, message)
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}: {e}")
    
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
    
    async def subscribe_to_room(self, websocket: WebSocket, room_name: str):
        """Subscribe a connection to a room"""
        connection_id = self.websocket_ids.get(websocket)
        if not connection_id:
            return
        
        if room_name not in self.subscription_rooms:
            self.subscription_rooms[room_name] = set()
        
        self.subscription_rooms[room_name].add(connection_id)
        logger.info(f"Connection {connection_id} subscribed to room {room_name}")
    
    async def unsubscribe_from_room(self, websocket: WebSocket, room_name: str):
        """Unsubscribe a connection from a room"""
        connection_id = self.websocket_ids.get(websocket)
        if not connection_id or room_name not in self.subscription_rooms:
            return
        
        self.subscription_rooms[room_name].remove(connection_id)
        if not self.subscription_rooms[room_name]:
            del self.subscription_rooms[room_name]
        
        logger.info(f"Connection {connection_id} unsubscribed from room {room_name}")
    
    async def _market_data_listener(self):
        """Listen for market data updates"""
        while self.is_running:
            try:
                # Subscribe to market data channel
                pubsub = self.redis_client.pubsub()
                await pubsub.subscribe('market_data')
                
                async for message in pubsub.listen():
                    if message['type'] == 'message':
                        data = json.loads(message['data'])
                        await self.broadcast_to_room('market_data', data)
                
            except Exception as e:
                logger.error(f"Error in market data listener: {e}")
                await asyncio.sleep(5)
    
    async def _position_update_listener(self):
        """Listen for position updates"""
        while self.is_running:
            try:
                # Subscribe to position updates channel
                pubsub = self.redis_client.pubsub()
                await pubsub.subscribe('position_updates')
                
                async for message in pubsub.listen():
                    if message['type'] == 'message':
                        data = json.loads(message['data'])
                        user_id = data.get('user_id')
                        if user_id:
                            await self.broadcast_to_user(user_id, data)
                
            except Exception as e:
                logger.error(f"Error in position update listener: {e}")
                await asyncio.sleep(5)
    
    async def _heartbeat_monitor(self):
        """Monitor connection health with heartbeat"""
        while self.is_running:
            try:
                current_time = datetime.now()
                dead_connections = []
                
                for connection_id, metadata in self.connection_metadata.items():
                    # Check if connection is stale (no heartbeat for 60 seconds)
                    if (current_time - metadata['last_heartbeat']).seconds > 60:
                        dead_connections.append(connection_id)
                
                # Clean up dead connections
                for connection_id in dead_connections:
                    websocket = None
                    for ws, id in self.websocket_ids.items():
                        if id == connection_id:
                            websocket = ws
                            break
                    if websocket:
                        await self.disconnect(websocket)
                
                # Send heartbeat to all connections
                await self.broadcast({
                    'type': 'heartbeat',
                    'timestamp': current_time.isoformat(),
                    'stats': {
                        'total_connections': self.total_connections,
                        'active_users': len(self.active_connections),
                        'rooms': len(self.subscription_rooms)
                    }
                })
                
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")
                await asyncio.sleep(10)
    
    async def _redis_subscriber(self):
        """Subscribe to Redis channels for system-wide updates"""
        while self.is_running:
            try:
                pubsub = self.redis_client.pubsub()
                await pubsub.subscribe('system_updates')
                
                async for message in pubsub.listen():
                    if message['type'] == 'message':
                        data = json.loads(message['data'])
                        await self.broadcast(data)
                
            except Exception as e:
                logger.error(f"Error in Redis subscriber: {e}")
                await asyncio.sleep(5)
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return await self.metrics.get_metrics()
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get current connection statistics"""
        return {
            'total_connections': self.total_connections,
            'active_users': len(self.active_connections),
            'rooms': len(self.subscription_rooms),
            'user_connections': self.user_connections,
            'subscription_rooms': {room: len(connections) for room, connections in self.subscription_rooms.items()}
        } 