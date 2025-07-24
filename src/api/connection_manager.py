"""
Production-Grade WebSocket Connection Manager
Ultra-professional implementation for real-time data streaming
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from collections import defaultdict

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Production-grade WebSocket connection manager with advanced features"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[str, List[WebSocket]] = defaultdict(list)
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        self.connection_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'failed_connections': 0,
            'last_connection_time': None,
            'messages_sent': 0,
            'errors': 0,
            'peak_connections': 0
        }
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.broadcast_task: Optional[asyncio.Task] = None
        self._start_broadcast_worker()
    
    def _start_broadcast_worker(self):
        """Start the background broadcast worker"""
        if self.broadcast_task is None or self.broadcast_task.done():
            self.broadcast_task = asyncio.create_task(self._broadcast_worker())
    
    async def _broadcast_worker(self):
        """Background worker for efficient message broadcasting"""
        while True:
            try:
                message = await self.message_queue.get()
                await self._broadcast_internal(message)
                self.message_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Broadcast worker error: {e}")
                await asyncio.sleep(1)
    
    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None):
        """Accept and register a new WebSocket connection"""
        try:
            await websocket.accept()
            
            # Add to active connections
            self.active_connections.append(websocket)
            
            # Associate with user if provided
            if user_id:
                self.user_connections[user_id].append(websocket)
            
            # Store metadata
            client_info = {
                'host': websocket.client.host if websocket.client else 'unknown',
                'port': websocket.client.port if websocket.client else 0
            }
            
            self.connection_metadata[websocket] = {
                'user_id': user_id,
                'client_info': client_info,
                'connected_at': datetime.now(),
                'last_activity': datetime.now(),
                'messages_sent': 0,
                'messages_received': 0
            }
            
            # Update stats
            self.connection_stats['total_connections'] += 1
            self.connection_stats['active_connections'] = len(self.active_connections)
            self.connection_stats['last_connection_time'] = datetime.now().isoformat()
            
            if self.connection_stats['active_connections'] > self.connection_stats['peak_connections']:
                self.connection_stats['peak_connections'] = self.connection_stats['active_connections']
            
            client_id = f"{client_info['host']}:{client_info['port']}"
            logger.info(f"✅ WebSocket connected: {client_id} (User: {user_id}). Active: {self.connection_stats['active_connections']}")
            
            # Send connection confirmation
            await self.send_personal_message({
                "type": "connection_established",
                "client_id": client_id,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "server_info": {
                    "name": "Quantum Crypto Trading System",
                    "version": "2.0.0",
                    "features": ["real_time_data", "trading_signals", "market_analysis", "portfolio_updates"]
                }
            }, websocket)
            
        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {e}")
            self.connection_stats['failed_connections'] += 1
            raise
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
            # Remove from user connections
            metadata = self.connection_metadata.get(websocket, {})
            user_id = metadata.get('user_id')
            if user_id and user_id in self.user_connections:
                if websocket in self.user_connections[user_id]:
                    self.user_connections[user_id].remove(websocket)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            # Remove metadata
            if websocket in self.connection_metadata:
                del self.connection_metadata[websocket]
            
            # Update stats
            self.connection_stats['active_connections'] = len(self.active_connections)
            logger.info(f"WebSocket disconnected. Active: {self.connection_stats['active_connections']}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to a specific WebSocket connection"""
        try:
            await websocket.send_json(message)
            self.connection_stats['messages_sent'] += 1
            
            # Update metadata
            if websocket in self.connection_metadata:
                self.connection_metadata[websocket]['messages_sent'] += 1
                self.connection_metadata[websocket]['last_activity'] = datetime.now()
                
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            self.connection_stats['errors'] += 1
            self.disconnect(websocket)
    
    async def send_to_user(self, message: dict, user_id: str):
        """Send message to all connections of a specific user"""
        if user_id in self.user_connections:
            connections = self.user_connections[user_id].copy()
            for connection in connections:
                await self.send_personal_message(message, connection)
    
    async def broadcast(self, message: dict):
        """Queue message for broadcasting to all active connections"""
        await self.message_queue.put(message)
    
    async def _broadcast_internal(self, message: dict):
        """Internal broadcast implementation"""
        if not self.active_connections:
            return
        
        # Create a copy to avoid modification during iteration
        connections_copy = self.active_connections.copy()
        
        # Use asyncio.gather for concurrent sending
        tasks = []
        for connection in connections_copy:
            tasks.append(self._send_with_error_handling(message, connection))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_with_error_handling(self, message: dict, connection: WebSocket):
        """Send message with proper error handling"""
        try:
            await connection.send_json(message)
            self.connection_stats['messages_sent'] += 1
            
            # Update metadata
            if connection in self.connection_metadata:
                self.connection_metadata[connection]['messages_sent'] += 1
                self.connection_metadata[connection]['last_activity'] = datetime.now()
                
        except Exception as e:
            logger.error(f"Failed to broadcast to WebSocket: {e}")
            self.connection_stats['errors'] += 1
            self.disconnect(connection)
    
    async def broadcast_to_subscribers(self, message: dict, subscription_type: str):
        """Broadcast to connections subscribed to specific data types"""
        # TODO: Implement subscription-based broadcasting
        await self.broadcast(message)
    
    def get_stats(self) -> dict:
        """Get comprehensive connection statistics"""
        return {
            **self.connection_stats,
            'user_connections': len(self.user_connections),
            'queue_size': self.message_queue.qsize(),
            'connection_details': [
                {
                    'user_id': meta.get('user_id'),
                    'client_info': meta.get('client_info'),
                    'connected_at': meta.get('connected_at').isoformat() if meta.get('connected_at') else None,
                    'messages_sent': meta.get('messages_sent', 0),
                    'messages_received': meta.get('messages_received', 0)
                }
                for meta in self.connection_metadata.values()
            ]
        }
    
    def get_connection_count(self) -> int:
        """Get current active connection count"""
        return len(self.active_connections)
    
    def get_user_connection_count(self, user_id: str) -> int:
        """Get connection count for a specific user"""
        return len(self.user_connections.get(user_id, []))
    
    async def ping_all_connections(self):
        """Send ping to all connections to check health"""
        ping_message = {
            "type": "ping",
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(ping_message)
    
    async def cleanup_stale_connections(self):
        """Clean up stale connections"""
        current_time = datetime.now()
        stale_connections = []
        
        for websocket, metadata in self.connection_metadata.items():
            last_activity = metadata.get('last_activity')
            if last_activity and (current_time - last_activity).total_seconds() > 300:  # 5 minutes
                stale_connections.append(websocket)
        
        for websocket in stale_connections:
            logger.info("Cleaning up stale WebSocket connection")
            self.disconnect(websocket)
    
    async def shutdown(self):
        """Gracefully shutdown the connection manager"""
        logger.info("Shutting down WebSocket connection manager...")
        
        # Cancel broadcast worker
        if self.broadcast_task and not self.broadcast_task.done():
            self.broadcast_task.cancel()
            try:
                await self.broadcast_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        for websocket in self.active_connections.copy():
            try:
                await websocket.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
        
        self.active_connections.clear()
        self.user_connections.clear()
        self.connection_metadata.clear()
        
        logger.info("WebSocket connection manager shutdown complete")

# Global connection manager instance
connection_manager = ConnectionManager()
