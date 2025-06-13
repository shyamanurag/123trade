"""
Real-Time WebSocket Manager
Handles live market data, position updates, and trading notifications
"""

import asyncio
import json
import logging
import redis.asyncio as redis
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import dataclass, asdict
import uuid

logger = logging.getLogger(__name__)

@dataclass
class MarketDataUpdate:
    """Market data update structure"""
    symbol: str
    price: float
    volume: int
    timestamp: str
    change: float
    change_percent: float
    bid: float
    ask: float
    high: float
    low: float
    open_price: float

@dataclass
class PositionUpdate:
    """Position update structure"""
    user_id: str
    symbol: str
    quantity: int
    entry_price: float
    current_price: float
    unrealized_pnl: float
    strategy: str
    timestamp: str

@dataclass
class TradeAlert:
    """Trade alert structure"""
    user_id: str
    alert_type: str  # 'entry', 'exit', 'stop_loss', 'target_hit'
    symbol: str
    price: float
    quantity: int
    strategy: str
    message: str
    timestamp: str
    priority: str  # 'low', 'medium', 'high', 'critical'

@dataclass
class SystemAlert:
    """System alert structure"""
    alert_type: str
    message: str
    timestamp: str
    severity: str  # 'info', 'warning', 'error', 'critical'
    component: str

class ConnectionManager:
    """Manages WebSocket connections with user authentication and room management"""
    
    def __init__(self):
        # User connections: {user_id: {connection_id: websocket}}
        self.user_connections: Dict[str, Dict[str, WebSocket]] = {}
        # Connection metadata: {connection_id: {user_id, subscriptions, last_heartbeat}}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        # Subscription rooms: {room_name: {connection_id}}
        self.subscription_rooms: Dict[str, Set[str]] = {}
        self.total_connections = 0
        
    async def connect(self, websocket: WebSocket, user_id: str, connection_id: Optional[str] = None) -> str:
        """Connect a new WebSocket with user authentication"""
        if connection_id is None:
            connection_id = str(uuid.uuid4())
            
        await websocket.accept()
        
        # Add user connection
        if user_id not in self.user_connections:
            self.user_connections[user_id] = {}
        self.user_connections[user_id][connection_id] = websocket
        
        # Store connection metadata
        self.connection_metadata[connection_id] = {
            'user_id': user_id,
            'subscriptions': set(),
            'last_heartbeat': datetime.now(),
            'connected_at': datetime.now()
        }
        
        self.total_connections += 1
        logger.info(f"WebSocket connected: user={user_id}, connection={connection_id}, total={self.total_connections}")
        
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Disconnect a WebSocket connection"""
        if connection_id not in self.connection_metadata:
            return
            
        metadata = self.connection_metadata[connection_id]
        user_id = metadata['user_id']
        
        # Remove from user connections
        if user_id in self.user_connections and connection_id in self.user_connections[user_id]:
            del self.user_connections[user_id][connection_id]
            if not self.user_connections[user_id]:  # No more connections for user
                del self.user_connections[user_id]
        
        # Remove from subscription rooms
        for subscription in metadata['subscriptions']:
            if subscription in self.subscription_rooms:
                self.subscription_rooms[subscription].discard(connection_id)
                if not self.subscription_rooms[subscription]:
                    del self.subscription_rooms[subscription]
        
        # Remove metadata
        del self.connection_metadata[connection_id]
        self.total_connections -= 1
        
        logger.info(f"WebSocket disconnected: user={user_id}, connection={connection_id}, total={self.total_connections}")
    
    async def subscribe_to_room(self, connection_id: str, room_name: str):
        """Subscribe connection to a specific room"""
        if connection_id not in self.connection_metadata:
            return False
            
        # Add to subscription room
        if room_name not in self.subscription_rooms:
            self.subscription_rooms[room_name] = set()
        self.subscription_rooms[room_name].add(connection_id)
        
        # Update connection metadata
        self.connection_metadata[connection_id]['subscriptions'].add(room_name)
        
        logger.info(f"Connection {connection_id} subscribed to room: {room_name}")
        return True
    
    async def unsubscribe_from_room(self, connection_id: str, room_name: str):
        """Unsubscribe connection from a specific room"""
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]['subscriptions'].discard(room_name)
        
        if room_name in self.subscription_rooms:
            self.subscription_rooms[room_name].discard(connection_id)
            if not self.subscription_rooms[room_name]:
                del self.subscription_rooms[room_name]
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send message to all connections of a specific user"""
        if user_id not in self.user_connections:
            return 0
            
        sent_count = 0
        dead_connections = []
        
        for connection_id, websocket in self.user_connections[user_id].items():
            try:
                await websocket.send_json(message)
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send to user {user_id}, connection {connection_id}: {e}")
                dead_connections.append(connection_id)
        
        # Clean up dead connections
        for connection_id in dead_connections:
            await self.disconnect(connection_id)
        
        return sent_count
    
    async def send_to_room(self, room_name: str, message: dict):
        """Send message to all connections in a room"""
        if room_name not in self.subscription_rooms:
            return 0
            
        sent_count = 0
        dead_connections = []
        
        for connection_id in self.subscription_rooms[room_name].copy():
            if connection_id not in self.connection_metadata:
                continue
                
            user_id = self.connection_metadata[connection_id]['user_id']
            if user_id in self.user_connections and connection_id in self.user_connections[user_id]:
                websocket = self.user_connections[user_id][connection_id]
                try:
                    await websocket.send_json(message)
                    sent_count += 1
                except Exception as e:
                    logger.warning(f"Failed to send to room {room_name}, connection {connection_id}: {e}")
                    dead_connections.append(connection_id)
        
        # Clean up dead connections
        for connection_id in dead_connections:
            await self.disconnect(connection_id)
        
        return sent_count
    
    async def broadcast(self, message: dict, exclude_user: Optional[str] = None):
        """Broadcast message to all connected users"""
        sent_count = 0
        
        for user_id in self.user_connections:
            if exclude_user and user_id == exclude_user:
                continue
            sent_count += await self.send_to_user(user_id, message)
        
        return sent_count
    
    def get_connection_stats(self) -> dict:
        """Get connection statistics"""
        return {
            'total_connections': self.total_connections,
            'total_users': len(self.user_connections),
            'total_rooms': len(self.subscription_rooms),
            'room_stats': {room: len(connections) for room, connections in self.subscription_rooms.items()}
        }

class WebSocketManager:
    """Main WebSocket manager for real-time trading data"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.connection_manager = ConnectionManager()
        self.is_running = False
        self.background_tasks = []
        
        # No more demo data - will get real data from database/external sources
        
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
        
        logger.info("WebSocket manager stopped")
    
    async def _market_data_listener(self):
        """Listen for real market data updates from external sources"""
        while self.is_running:
            try:
                # In production, this would listen to:
                # - TrueData WebSocket feeds
                # - Zerodha KiteConnect WebSocket
                # - Database changes via Redis pub/sub
                
                # For now, just maintain connection and process Redis events
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in market data listener: {e}")
                await asyncio.sleep(5)
    
    async def _position_update_listener(self):
        """Listen for position updates from database changes"""
        while self.is_running:
            try:
                # In production, this would:
                # - Listen to database change notifications
                # - Get position updates from Redis pub/sub
                # - Query database for current positions periodically
                
                # For now, just maintain the service
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in position update listener: {e}")
                await asyncio.sleep(5)
    
    async def _heartbeat_monitor(self):
        """Monitor connection health with heartbeat"""
        while self.is_running:
            try:
                current_time = datetime.now()
                dead_connections = []
                
                for connection_id, metadata in self.connection_manager.connection_metadata.items():
                    # Check if connection is stale (no heartbeat for 60 seconds)
                    if (current_time - metadata['last_heartbeat']).seconds > 60:
                        dead_connections.append(connection_id)
                
                # Clean up dead connections
                for connection_id in dead_connections:
                    await self.connection_manager.disconnect(connection_id)
                
                # Send heartbeat to all connections
                await self.connection_manager.broadcast({
                    'type': 'heartbeat',
                    'timestamp': current_time.isoformat(),
                    'stats': self.connection_manager.get_connection_stats()
                })
                
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")
                await asyncio.sleep(10)
    
    async def _redis_subscriber(self):
        """Subscribe to Redis channels for real-time updates"""
        while self.is_running:
            try:
                # Create pubsub instance
                pubsub = self.redis_client.pubsub()
                
                # Subscribe to channels
                await pubsub.subscribe(
                    'market_data',
                    'trade_updates',
                    'system_alerts',
                    'user_notifications'
                )
                
                logger.info("Redis subscriber started")
                
                # Listen for messages
                async for message in pubsub.listen():
                    if message['type'] == 'message':
                        channel = message['channel']
                        data = message['data']
                        
                        # Parse and broadcast message
                        try:
                            if isinstance(data, bytes):
                                data = data.decode('utf-8')
                            
                            parsed_data = json.loads(data)
                            
                            # Broadcast to appropriate room
                            room = f"{channel}_all"
                            await self.connection_manager.send_to_room(room, {
                                'type': channel,
                                'data': parsed_data,
                                'timestamp': datetime.now().isoformat()
                            })
                            
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON in Redis message: {data}")
                        except Exception as e:
                            logger.error(f"Error processing Redis message: {e}")
                            
            except asyncio.CancelledError:
                logger.info("Redis subscriber cancelled")
                break
            except Exception as e:
                logger.error(f"Error in Redis subscriber: {e}")
                # Wait before reconnecting
                await asyncio.sleep(5)
                logger.info("Attempting to reconnect to Redis...")
                continue
                
        logger.info("Redis subscriber stopped")
    
    async def _handle_trading_event(self, data: dict):
        """Handle trading events from Redis"""
        event_type = data.get('type')
        user_id = data.get('user_id')
        
        if not user_id:
            logger.warning(f"Trading event without user_id: {data}")
            return
        
        if event_type == 'trade_executed':
            await self.connection_manager.send_to_user(user_id, {
                'type': 'trade_alert',
                'data': data
            })
        elif event_type == 'position_opened':
            await self.connection_manager.send_to_user(user_id, {
                'type': 'position_alert',
                'data': data
            })
    
    async def _handle_system_alert(self, data: dict):
        """Handle system alerts from Redis"""
        await self.connection_manager.broadcast({
            'type': 'system_alert',
            'data': data
        })
    
    async def _handle_market_event(self, data: dict):
        """Handle market events from Redis"""
        symbol = data.get('symbol')
        if symbol:
            await self.connection_manager.send_to_room(f"market_data_{symbol}", {
                'type': 'market_event',
                'data': data
            })
    
    async def _handle_position_update(self, data: dict):
        """Handle position updates from Redis"""
        user_id = data.get('user_id')
        if user_id:
            await self.connection_manager.send_to_user(user_id, {
                'type': 'position_update',
                'data': data
            })
    
    async def handle_client_message(self, connection_id: str, message: dict):
        """Handle incoming messages from WebSocket clients"""
        try:
            msg_type = message.get('type')
            
            if msg_type == 'subscribe':
                room = message.get('room')
                if room:
                    await self.connection_manager.subscribe_to_room(connection_id, room)
                    return {'type': 'subscription_success', 'room': room}
            
            elif msg_type == 'unsubscribe':
                room = message.get('room')
                if room:
                    await self.connection_manager.unsubscribe_from_room(connection_id, room)
                    return {'type': 'unsubscription_success', 'room': room}
            
            elif msg_type == 'heartbeat':
                # Update last heartbeat
                if connection_id in self.connection_manager.connection_metadata:
                    self.connection_manager.connection_metadata[connection_id]['last_heartbeat'] = datetime.now()
                return {'type': 'heartbeat_ack', 'timestamp': datetime.now().isoformat()}
            
            elif msg_type == 'get_stats':
                return {
                    'type': 'stats',
                    'data': self.connection_manager.get_connection_stats()
                }
            
            else:
                return {'type': 'error', 'message': f'Unknown message type: {msg_type}'}
                
        except Exception as e:
            logger.error(f"Error handling client message: {e}")
            return {'type': 'error', 'message': 'Internal server error'}
    
    async def send_trade_alert(self, user_id: str, alert: TradeAlert):
        """Send trade alert to specific user"""
        await self.connection_manager.send_to_user(user_id, {
            'type': 'trade_alert',
            'data': asdict(alert)
        })
    
    async def send_system_alert(self, alert: SystemAlert):
        """Send system alert to all users"""
        await self.connection_manager.broadcast({
            'type': 'system_alert',
            'data': asdict(alert)
        })
    
    async def publish_market_data(self, market_data: MarketDataUpdate):
        """Publish market data update"""
        await self.connection_manager.send_to_room(f"market_data_{market_data.symbol}", {
            'type': 'market_data',
            'data': asdict(market_data)
        })
    
    async def publish_position_update(self, position_update: PositionUpdate):
        """Publish position update to user"""
        await self.connection_manager.send_to_user(position_update.user_id, {
            'type': 'position_update',
            'data': asdict(position_update)
        })

# Global WebSocket manager instance
websocket_manager: Optional[WebSocketManager] = None

def get_websocket_manager() -> Optional[WebSocketManager]:
    """Get the global WebSocket manager instance"""
    return websocket_manager

def init_websocket_manager(redis_client: redis.Redis) -> WebSocketManager:
    """Initialize the global WebSocket manager"""
    global websocket_manager
    websocket_manager = WebSocketManager(redis_client)
    return websocket_manager 