import logging
import asyncio
from typing import Dict, Any, List, Optional
import random
from datetime import datetime

from .models import Order, OrderStatus
from .exceptions import OrderError

logger = logging.getLogger(__name__)

class LoadBalancer:
    """Handles load balancing for distributed operations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.broker_nodes = {}  # broker_id -> node_info
        self.user_nodes = {}    # user_id -> node_info
        self.training_nodes = {} # node_id -> node_info
        self.redis_nodes = {}   # node_id -> node_info
        
        # Initialize node health tracking
        self.node_health = {}
        self.health_check_interval = config.get('load_balancer', {}).get('health_check_interval', 30)
        
        # Start health monitoring
        asyncio.create_task(self._monitor_node_health())
    
    async def get_broker_node(self, order: Order) -> str:
        """Get optimal broker node for order execution"""
        try:
            # Filter healthy nodes
            healthy_nodes = {
                node_id: info for node_id, info in self.broker_nodes.items()
                if self._is_node_healthy(node_id)
            }
            
            if not healthy_nodes:
                raise OrderError("No healthy broker nodes available")
            
            # Get node with lowest load
            selected_node = min(
                healthy_nodes.items(),
                key=lambda x: x[1].get('current_load', 0)
            )[0]
            
            # Update node load
            self.broker_nodes[selected_node]['current_load'] += 1
            
            return selected_node
            
        except Exception as e:
            logger.error(f"Error selecting broker node: {str(e)}")
            raise OrderError(f"Failed to select broker node: {str(e)}")
    
    async def get_user_node(self, user_id: str) -> str:
        """Get optimal node for user operations"""
        try:
            # Check if user already has a node
            if user_id in self.user_nodes:
                node_id = self.user_nodes[user_id]
                if self._is_node_healthy(node_id):
                    return node_id
            
            # Get node with lowest user count
            healthy_nodes = {
                node_id: info for node_id, info in self.user_nodes.items()
                if self._is_node_healthy(node_id)
            }
            
            if not healthy_nodes:
                raise OrderError("No healthy user nodes available")
            
            selected_node = min(
                healthy_nodes.items(),
                key=lambda x: len(x[1].get('users', []))
            )[0]
            
            # Update user mapping
            self.user_nodes[selected_node]['users'].append(user_id)
            self.user_nodes[user_id] = selected_node
            
            return selected_node
            
        except Exception as e:
            logger.error(f"Error selecting user node: {str(e)}")
            raise OrderError(f"Failed to select user node: {str(e)}")
    
    async def get_training_node(self) -> str:
        """Get optimal node for model training"""
        try:
            # Filter healthy nodes
            healthy_nodes = {
                node_id: info for node_id, info in self.training_nodes.items()
                if self._is_node_healthy(node_id)
            }
            
            if not healthy_nodes:
                raise OrderError("No healthy training nodes available")
            
            # Get node with lowest training load
            selected_node = min(
                healthy_nodes.items(),
                key=lambda x: x[1].get('training_load', 0)
            )[0]
            
            # Update training load
            self.training_nodes[selected_node]['training_load'] += 1
            
            return selected_node
            
        except Exception as e:
            logger.error(f"Error selecting training node: {str(e)}")
            raise OrderError(f"Failed to select training node: {str(e)}")
    
    async def get_redis_node(self) -> str:
        """Get optimal Redis node for operations"""
        try:
            # Filter healthy nodes
            healthy_nodes = {
                node_id: info for node_id, info in self.redis_nodes.items()
                if self._is_node_healthy(node_id)
            }
            
            if not healthy_nodes:
                raise OrderError("No healthy Redis nodes available")
            
            # Get node with lowest latency
            selected_node = min(
                healthy_nodes.items(),
                key=lambda x: x[1].get('latency', float('inf'))
            )[0]
            
            return selected_node
            
        except Exception as e:
            logger.error(f"Error selecting Redis node: {str(e)}")
            raise OrderError(f"Failed to select Redis node: {str(e)}")
    
    def _is_node_healthy(self, node_id: str) -> bool:
        """Check if node is healthy"""
        try:
            health_info = self.node_health.get(node_id, {})
            last_check = health_info.get('last_check', datetime.min)
            
            # Check if health check is recent
            if (datetime.now() - last_check).total_seconds() > self.health_check_interval:
                return False
            
            return health_info.get('is_healthy', False)
            
        except Exception as e:
            logger.error(f"Error checking node health: {str(e)}")
            return False
    
    async def _monitor_node_health(self):
        """Monitor health of all nodes"""
        while True:
            try:
                # Check broker nodes
                for node_id in self.broker_nodes:
                    await self._check_node_health(node_id, 'broker')
                
                # Check user nodes
                for node_id in self.user_nodes:
                    await self._check_node_health(node_id, 'user')
                
                # Check training nodes
                for node_id in self.training_nodes:
                    await self._check_node_health(node_id, 'training')
                
                # Check Redis nodes
                for node_id in self.redis_nodes:
                    await self._check_node_health(node_id, 'redis')
                
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring node health: {str(e)}")
                await asyncio.sleep(5)
    
    async def _check_node_health(self, node_id: str, node_type: str):
        """Check health of specific node"""
        try:
            # Get node info
            node_info = getattr(self, f"{node_type}_nodes").get(node_id, {})
            
            # Perform health check based on node type
            is_healthy = await self._perform_health_check(node_id, node_type)
            
            # Update health info
            self.node_health[node_id] = {
                'last_check': datetime.now(),
                'is_healthy': is_healthy,
                'node_type': node_type
            }
            
            if not is_healthy:
                logger.warning(f"Node {node_id} ({node_type}) is unhealthy")
                
        except Exception as e:
            logger.error(f"Error checking health of node {node_id}: {str(e)}")
            self.node_health[node_id] = {
                'last_check': datetime.now(),
                'is_healthy': False,
                'node_type': node_type
            }
    
    async def _perform_health_check(self, node_id: str, node_type: str) -> bool:
        """Perform health check for specific node type"""
        try:
            if node_type == 'broker':
                # Check broker connectivity and order processing
                return await self._check_broker_health(node_id)
            elif node_type == 'user':
                # Check user service availability
                return await self._check_user_service_health(node_id)
            elif node_type == 'training':
                # Check training service availability
                return await self._check_training_service_health(node_id)
            elif node_type == 'redis':
                # Check Redis connectivity
                return await self._check_redis_health(node_id)
            
            return False
            
        except Exception as e:
            logger.error(f"Error performing health check for node {node_id}: {str(e)}")
            return False
    
    async def _check_broker_health(self, node_id: str) -> bool:
        """Check broker node health"""
        # Implementation would check broker connectivity and order processing
        return True
    
    async def _check_user_service_health(self, node_id: str) -> bool:
        """Check user service health"""
        # Implementation would check user service availability
        return True
    
    async def _check_training_service_health(self, node_id: str) -> bool:
        """Check training service health"""
        # Implementation would check training service availability
        return True
    
    async def _check_redis_health(self, node_id: str) -> bool:
        """Check Redis node health"""
        # Implementation would check Redis connectivity
        return True 