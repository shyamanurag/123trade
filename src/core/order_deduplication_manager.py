"""
Order Deduplication Manager
Prevents duplicate orders and maintains order integrity
100% REAL TRADING - CRITICAL FOR MONEY SAFETY
"""

import asyncio
import logging
import hashlib
import time
from typing import Dict, Set, Optional, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import redis.asyncio as redis

logger = logging.getLogger(__name__)

@dataclass
class OrderFingerprint:
    """Unique order identification"""
    symbol: str
    quantity: int
    price: float
    side: str  # BUY/SELL
    order_type: str  # MARKET/LIMIT
    user_id: int
    timestamp_window: int  # 5-minute window grouping
    
    def generate_hash(self) -> str:
        """Generate unique hash for order deduplication"""
        # Create fingerprint string
        fingerprint_str = f"{self.symbol}|{self.quantity}|{self.price}|{self.side}|{self.order_type}|{self.user_id}|{self.timestamp_window}"
        
        # Generate SHA256 hash
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()

@dataclass
class OrderSubmission:
    """Order submission tracking"""
    order_id: str
    fingerprint_hash: str
    user_id: int
    symbol: str
    quantity: int
    price: float
    side: str
    order_type: str
    submitted_at: datetime
    status: str  # PENDING, SUBMITTED, REJECTED, DUPLICATE
    broker_order_id: Optional[str] = None
    rejection_reason: Optional[str] = None

class OrderDeduplicationManager:
    """
    Manages order deduplication to prevent accidental duplicate submissions
    Critical for real money trading safety
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        
        # In-memory tracking (fallback if Redis unavailable)
        self.submitted_orders: Dict[str, OrderSubmission] = {}
        self.order_fingerprints: Set[str] = set()
        self.user_order_limits: Dict[int, int] = {}  # user_id -> order_count
        
        # Configuration
        self.deduplication_window_minutes = 5  # 5-minute deduplication window
        self.max_orders_per_user_per_minute = 10  # Rate limiting
        self.cleanup_interval_seconds = 300  # 5 minutes
        
        # Background cleanup task
        self.cleanup_task: Optional[asyncio.Task] = None
        
        logger.info("✅ Order Deduplication Manager initialized")
    
    async def initialize(self) -> bool:
        """Initialize the deduplication manager"""
        try:
            # Start background cleanup task
            self.cleanup_task = asyncio.create_task(self._cleanup_expired_orders())
            
            logger.info("✅ Order deduplication manager fully initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize order deduplication manager: {e}")
            return False
    
    async def validate_order_submission(
        self,
        user_id: int,
        symbol: str,
        quantity: int,
        price: float,
        side: str,
        order_type: str = "MARKET"
    ) -> Dict[str, Any]:
        """
        Validate order submission for duplicates and limits
        Returns validation result with submission approval
        """
        try:
            # Generate order fingerprint
            current_time = datetime.now()
            timestamp_window = int(current_time.timestamp() // (self.deduplication_window_minutes * 60))
            
            fingerprint = OrderFingerprint(
                symbol=symbol,
                quantity=quantity,
                price=price,
                side=side,
                order_type=order_type,
                user_id=user_id,
                timestamp_window=timestamp_window
            )
            
            fingerprint_hash = fingerprint.generate_hash()
            
            # Check for duplicate order
            is_duplicate = await self._check_duplicate_order(fingerprint_hash)
            
            if is_duplicate:
                logger.warning(f"🚫 DUPLICATE ORDER DETECTED: User {user_id}, Symbol {symbol}, Hash {fingerprint_hash[:12]}...")
                return {
                    "success": False,
                    "allowed": False,
                    "reason": "DUPLICATE_ORDER",
                    "message": f"Identical order already submitted within {self.deduplication_window_minutes} minutes",
                    "fingerprint_hash": fingerprint_hash,
                    "duplicate_detected": True
                }
            
            # Check rate limiting
            rate_limit_check = await self._check_rate_limits(user_id)
            
            if not rate_limit_check["allowed"]:
                logger.warning(f"🚫 RATE LIMIT EXCEEDED: User {user_id}")
                return {
                    "success": False,
                    "allowed": False,
                    "reason": "RATE_LIMIT_EXCEEDED",
                    "message": rate_limit_check["message"],
                    "fingerprint_hash": fingerprint_hash,
                    "rate_limited": True
                }
            
            # Order validation passed
            logger.info(f"✅ Order validation PASSED: User {user_id}, Symbol {symbol}")
            return {
                "success": True,
                "allowed": True,
                "reason": "VALIDATION_PASSED",
                "message": "Order validation successful",
                "fingerprint_hash": fingerprint_hash,
                "order_fingerprint": fingerprint
            }
            
        except Exception as e:
            logger.error(f"❌ Order validation error: {e}")
            return {
                "success": False,
                "allowed": False,
                "reason": "VALIDATION_ERROR",
                "message": f"Order validation failed: {str(e)}",
                "error": str(e)
            }
    
    async def register_order_submission(
        self,
        order_id: str,
        fingerprint_hash: str,
        user_id: int,
        symbol: str,
        quantity: int,
        price: float,
        side: str,
        order_type: str,
        broker_order_id: Optional[str] = None
    ) -> bool:
        """
        Register successful order submission to prevent future duplicates
        """
        try:
            submission = OrderSubmission(
                order_id=order_id,
                fingerprint_hash=fingerprint_hash,
                user_id=user_id,
                symbol=symbol,
                quantity=quantity,
                price=price,
                side=side,
                order_type=order_type,
                submitted_at=datetime.now(),
                status="SUBMITTED",
                broker_order_id=broker_order_id
            )
            
            # Store in memory
            self.submitted_orders[order_id] = submission
            self.order_fingerprints.add(fingerprint_hash)
            
            # Store in Redis if available
            if self.redis_client:
                await self._store_order_in_redis(submission)
            
            # Update user rate limiting counter
            current_minute = int(time.time() // 60)
            user_minute_key = f"{user_id}_{current_minute}"
            self.user_order_limits[user_minute_key] = self.user_order_limits.get(user_minute_key, 0) + 1
            
            logger.info(f"✅ Order submission registered: {order_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to register order submission: {e}")
            return False
    
    async def mark_order_failed(
        self,
        order_id: str,
        fingerprint_hash: str,
        rejection_reason: str
    ) -> bool:
        """
        Mark order as failed/rejected to allow retry
        """
        try:
            # Remove from fingerprint tracking to allow retry
            if fingerprint_hash in self.order_fingerprints:
                self.order_fingerprints.remove(fingerprint_hash)
            
            # Update order status
            if order_id in self.submitted_orders:
                self.submitted_orders[order_id].status = "REJECTED"
                self.submitted_orders[order_id].rejection_reason = rejection_reason
            
            # Remove from Redis if available
            if self.redis_client:
                await self._remove_order_from_redis(fingerprint_hash)
            
            logger.info(f"✅ Order marked as failed: {order_id}, reason: {rejection_reason}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to mark order as failed: {e}")
            return False
    
    async def get_order_history(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get order submission history"""
        try:
            history = []
            
            for order_id, submission in self.submitted_orders.items():
                if user_id is None or submission.user_id == user_id:
                    history.append({
                        "order_id": order_id,
                        "user_id": submission.user_id,
                        "symbol": submission.symbol,
                        "quantity": submission.quantity,
                        "price": submission.price,
                        "side": submission.side,
                        "order_type": submission.order_type,
                        "submitted_at": submission.submitted_at.isoformat(),
                        "status": submission.status,
                        "broker_order_id": submission.broker_order_id,
                        "rejection_reason": submission.rejection_reason,
                        "fingerprint_hash": submission.fingerprint_hash[:12] + "..."
                    })
            
            # Sort by submission time (newest first)
            history.sort(key=lambda x: x["submitted_at"], reverse=True)
            
            return history
            
        except Exception as e:
            logger.error(f"❌ Failed to get order history: {e}")
            return []
    
    async def _check_duplicate_order(self, fingerprint_hash: str) -> bool:
        """Check if order fingerprint already exists"""
        try:
            # Check in-memory first
            if fingerprint_hash in self.order_fingerprints:
                return True
            
            # Check Redis if available
            if self.redis_client:
                exists = await self.redis_client.exists(f"order_fingerprint:{fingerprint_hash}")
                return bool(exists)
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error checking duplicate order: {e}")
            return False  # Allow order if check fails (safety fallback)
    
    async def _check_rate_limits(self, user_id: int) -> Dict[str, Any]:
        """Check if user has exceeded rate limits"""
        try:
            current_minute = int(time.time() // 60)
            user_minute_key = f"{user_id}_{current_minute}"
            
            current_count = self.user_order_limits.get(user_minute_key, 0)
            
            if current_count >= self.max_orders_per_user_per_minute:
                return {
                    "allowed": False,
                    "message": f"Rate limit exceeded: {current_count}/{self.max_orders_per_user_per_minute} orders per minute",
                    "current_count": current_count,
                    "limit": self.max_orders_per_user_per_minute
                }
            
            return {
                "allowed": True,
                "message": "Rate limit check passed",
                "current_count": current_count,
                "limit": self.max_orders_per_user_per_minute
            }
            
        except Exception as e:
            logger.error(f"❌ Error checking rate limits: {e}")
            return {"allowed": True, "message": "Rate limit check failed - allowing order"}
    
    async def _store_order_in_redis(self, submission: OrderSubmission):
        """Store order submission in Redis"""
        try:
            if not self.redis_client:
                return
            
            # Store fingerprint with expiration
            await self.redis_client.setex(
                f"order_fingerprint:{submission.fingerprint_hash}",
                self.deduplication_window_minutes * 60,  # TTL in seconds
                submission.order_id
            )
            
            # Store full order data
            order_data = {
                "order_id": submission.order_id,
                "user_id": submission.user_id,
                "symbol": submission.symbol,
                "quantity": submission.quantity,
                "price": submission.price,
                "side": submission.side,
                "order_type": submission.order_type,
                "submitted_at": submission.submitted_at.isoformat(),
                "status": submission.status,
                "broker_order_id": submission.broker_order_id or ""
            }
            
            await self.redis_client.setex(
                f"order_data:{submission.order_id}",
                3600,  # 1 hour TTL
                str(order_data)
            )
            
        except Exception as e:
            logger.error(f"❌ Error storing order in Redis: {e}")
    
    async def _remove_order_from_redis(self, fingerprint_hash: str):
        """Remove order fingerprint from Redis"""
        try:
            if not self.redis_client:
                return
            
            await self.redis_client.delete(f"order_fingerprint:{fingerprint_hash}")
            
        except Exception as e:
            logger.error(f"❌ Error removing order from Redis: {e}")
    
    async def _cleanup_expired_orders(self):
        """Background task to cleanup expired orders"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval_seconds)
                
                current_time = datetime.now()
                expired_orders = []
                
                # Find expired orders
                for order_id, submission in self.submitted_orders.items():
                    if current_time - submission.submitted_at > timedelta(minutes=self.deduplication_window_minutes):
                        expired_orders.append(order_id)
                
                # Remove expired orders
                for order_id in expired_orders:
                    submission = self.submitted_orders.pop(order_id, None)
                    if submission and submission.fingerprint_hash in self.order_fingerprints:
                        self.order_fingerprints.remove(submission.fingerprint_hash)
                
                # Cleanup rate limiting counters
                current_minute = int(time.time() // 60)
                expired_rate_keys = [
                    key for key in self.user_order_limits.keys()
                    if int(key.split('_')[1]) < current_minute - 2  # Keep last 2 minutes
                ]
                
                for key in expired_rate_keys:
                    self.user_order_limits.pop(key, None)
                
                if expired_orders:
                    logger.info(f"🧹 Cleaned up {len(expired_orders)} expired orders")
                
            except Exception as e:
                logger.error(f"❌ Error in cleanup task: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def shutdown(self):
        """Shutdown the deduplication manager"""
        try:
            if self.cleanup_task:
                self.cleanup_task.cancel()
                
            logger.info("✅ Order deduplication manager shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")

# Global instance
order_deduplication_manager = OrderDeduplicationManager()