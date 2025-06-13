import logging
import asyncio
from datetime import datetime, time
from typing import Dict, Any, List
import json

from .models import Order, OrderStatus, Trade
from .exceptions import OrderError

logger = logging.getLogger(__name__)

class CapitalManager:
    """Manages dynamic capital updates for users"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.user_capital = {}  # user_id -> current_capital
        self.daily_pnl = {}     # user_id -> daily_pnl
        self.trade_history = {} # user_id -> list of trades
        self.opening_capital = {} # user_id -> opening_day_capital
        self.hard_stop_threshold = 0.02  # 2% hard stop loss
        self.redis_client = None  # Will be initialized with Redis connection
        
    async def initialize_user(self, user_id: str, initial_capital: float):
        """Initialize user's capital tracking"""
        try:
            self.user_capital[user_id] = initial_capital
            self.opening_capital[user_id] = initial_capital  # Set initial opening capital
            self.daily_pnl[user_id] = 0.0
            self.trade_history[user_id] = []
            
            # Store in Redis for persistence
            await self._store_user_capital(user_id, initial_capital)
            await self._store_opening_capital(user_id, initial_capital)
            await self._store_daily_pnl(user_id, 0.0)
            
            logger.info(f"Initialized capital tracking for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error initializing user capital: {str(e)}")
            raise OrderError(f"Failed to initialize user capital: {str(e)}")
    
    async def update_capital_after_trade(self, user_id: str, trade: Trade):
        """Update user's capital after a trade"""
        try:
            # Calculate trade P&L
            pnl = self._calculate_trade_pnl(trade)
            
            # Update capital
            current_capital = self.user_capital.get(user_id, 0.0)
            new_capital = current_capital + pnl
            self.user_capital[user_id] = new_capital
            
            # Check for hard stop loss
            opening_capital = self.opening_capital.get(user_id, current_capital)
            max_loss = opening_capital * self.hard_stop_threshold
            current_loss = opening_capital - new_capital
            
            if current_loss >= max_loss:
                logger.warning(f"Hard stop loss triggered for user {user_id}")
                await self._trigger_hard_stop(user_id)
                return new_capital
            
            # Update daily P&L
            self.daily_pnl[user_id] = self.daily_pnl.get(user_id, 0.0) + pnl
            
            # Store trade in history
            self.trade_history[user_id].append(trade)
            
            # Update Redis
            await self._store_user_capital(user_id, new_capital)
            await self._store_daily_pnl(user_id, self.daily_pnl[user_id])
            await self._store_trade(user_id, trade)
            
            logger.info(f"Updated capital for user {user_id} after trade: {pnl}")
            
            return new_capital
            
        except Exception as e:
            logger.error(f"Error updating capital after trade: {str(e)}")
            raise OrderError(f"Failed to update capital: {str(e)}")
    
    async def end_of_day_update(self):
        """Perform end of day capital updates"""
        try:
            current_time = datetime.now().time()
            market_close = time(16, 0)  # 4:00 PM
            
            if current_time >= market_close:
                for user_id in self.user_capital:
                    # Store end of day capital
                    await self._store_eod_capital(user_id, self.user_capital[user_id])
                    
                    # Set new opening capital for next day
                    self.opening_capital[user_id] = self.user_capital[user_id]
                    await self._store_opening_capital(user_id, self.user_capital[user_id])
                    
                    # Reset daily P&L
                    self.daily_pnl[user_id] = 0.0
                    await self._store_daily_pnl(user_id, 0.0)
                    
                    # Generate daily report
                    await self._generate_daily_report(user_id)
                    
                logger.info("Completed end of day capital updates")
                
        except Exception as e:
            logger.error(f"Error in end of day update: {str(e)}")
            raise OrderError(f"Failed to perform end of day update: {str(e)}")
    
    async def get_user_capital(self, user_id: str) -> float:
        """Get current capital for user"""
        try:
            # Try to get from Redis first
            capital = await self._get_user_capital(user_id)
            if capital is not None:
                self.user_capital[user_id] = capital
                return capital
            
            # Fallback to in-memory value
            return self.user_capital.get(user_id, 0.0)
            
        except Exception as e:
            logger.error(f"Error getting user capital: {str(e)}")
            raise OrderError(f"Failed to get user capital: {str(e)}")
    
    async def get_daily_pnl(self, user_id: str) -> float:
        """Get daily P&L for user"""
        try:
            # Try to get from Redis first
            pnl = await self._get_daily_pnl(user_id)
            if pnl is not None:
                self.daily_pnl[user_id] = pnl
                return pnl
            
            # Fallback to in-memory value
            return self.daily_pnl.get(user_id, 0.0)
            
        except Exception as e:
            logger.error(f"Error getting daily P&L: {str(e)}")
            raise OrderError(f"Failed to get daily P&L: {str(e)}")
    
    def _calculate_trade_pnl(self, trade: Trade) -> float:
        """Calculate P&L for a trade"""
        try:
            if trade.order_type == "MARKET":
                return (trade.execution_price - trade.entry_price) * trade.quantity
            elif trade.order_type == "LIMIT":
                return (trade.limit_price - trade.entry_price) * trade.quantity
            elif trade.order_type == "STOP":
                return (trade.stop_price - trade.entry_price) * trade.quantity
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Error calculating trade P&L: {str(e)}")
            return 0.0
    
    async def _store_user_capital(self, user_id: str, capital: float):
        """Store user capital in Redis"""
        if self.redis_client:
            await self.redis_client.set(f"user:{user_id}:capital", str(capital))
    
    async def _store_daily_pnl(self, user_id: str, pnl: float):
        """Store daily P&L in Redis"""
        if self.redis_client:
            await self.redis_client.set(f"user:{user_id}:daily_pnl", str(pnl))
    
    async def _store_trade(self, user_id: str, trade: Trade):
        """Store trade in Redis"""
        if self.redis_client:
            trade_key = f"user:{user_id}:trades:{trade.trade_id}"
            await self.redis_client.set(trade_key, json.dumps(trade.to_dict()))
    
    async def _store_eod_capital(self, user_id: str, capital: float):
        """Store end of day capital in Redis"""
        if self.redis_client:
            date = datetime.now().strftime("%Y-%m-%d")
            await self.redis_client.set(f"user:{user_id}:eod_capital:{date}", str(capital))
    
    async def _get_user_capital(self, user_id: str) -> float:
        """Get user capital from Redis"""
        if self.redis_client:
            capital = await self.redis_client.get(f"user:{user_id}:capital")
            return float(capital) if capital else None
        return None
    
    async def _get_daily_pnl(self, user_id: str) -> float:
        """Get daily P&L from Redis"""
        if self.redis_client:
            pnl = await self.redis_client.get(f"user:{user_id}:daily_pnl")
            return float(pnl) if pnl else None
        return None
    
    async def _generate_daily_report(self, user_id: str):
        """Generate daily trading report"""
        try:
            report = {
                "user_id": user_id,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "starting_capital": await self._get_eod_capital(user_id, -1),  # Previous day's EOD
                "ending_capital": self.user_capital[user_id],
                "daily_pnl": self.daily_pnl[user_id],
                "trades": self.trade_history[user_id],
                "metrics": await self._calculate_daily_metrics(user_id)
            }
            
            # Store report
            if self.redis_client:
                date = datetime.now().strftime("%Y-%m-%d")
                await self.redis_client.set(
                    f"user:{user_id}:daily_report:{date}",
                    json.dumps(report)
                )
            
            logger.info(f"Generated daily report for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error generating daily report: {str(e)}")
    
    async def _get_eod_capital(self, user_id: str, days_ago: int) -> float:
        """Get end of day capital from previous day"""
        if self.redis_client:
            date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            capital = await self.redis_client.get(f"user:{user_id}:eod_capital:{date}")
            return float(capital) if capital else None
        return None
    
    async def _calculate_daily_metrics(self, user_id: str) -> Dict[str, Any]:
        """Calculate daily trading metrics"""
        try:
            trades = self.trade_history[user_id]
            if not trades:
                return {}
            
            winning_trades = [t for t in trades if self._calculate_trade_pnl(t) > 0]
            losing_trades = [t for t in trades if self._calculate_trade_pnl(t) < 0]
            
            return {
                "total_trades": len(trades),
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "win_rate": len(winning_trades) / len(trades) if trades else 0,
                "average_win": sum(self._calculate_trade_pnl(t) for t in winning_trades) / len(winning_trades) if winning_trades else 0,
                "average_loss": sum(self._calculate_trade_pnl(t) for t in losing_trades) / len(losing_trades) if losing_trades else 0,
                "profit_factor": abs(sum(self._calculate_trade_pnl(t) for t in winning_trades) / 
                                   sum(self._calculate_trade_pnl(t) for t in losing_trades)) if losing_trades else float('inf')
            }
            
        except Exception as e:
            logger.error(f"Error calculating daily metrics: {str(e)}")
            return {}
    
    async def _trigger_hard_stop(self, user_id: str):
        """Trigger hard stop loss for user"""
        try:
            # Close all open positions
            open_positions = await self._get_open_positions(user_id)
            for position in open_positions:
                await self._close_position(user_id, position)
            
            # Update user status
            await self._update_user_status(user_id, "STOPPED")
            
            # Store hard stop event
            await self._store_hard_stop_event(user_id)
            
            # Send notification
            await self._send_hard_stop_notification(user_id)
            
            logger.info(f"Hard stop loss executed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error triggering hard stop: {str(e)}")
    
    async def _store_opening_capital(self, user_id: str, capital: float):
        """Store opening day capital in Redis"""
        if self.redis_client:
            date = datetime.now().strftime("%Y-%m-%d")
            await self.redis_client.set(f"user:{user_id}:opening_capital:{date}", str(capital))
    
    async def _get_opening_capital(self, user_id: str) -> float:
        """Get opening day capital from Redis"""
        if self.redis_client:
            date = datetime.now().strftime("%Y-%m-%d")
            capital = await self.redis_client.get(f"user:{user_id}:opening_capital:{date}")
            return float(capital) if capital else None
        return None
    
    async def _store_hard_stop_event(self, user_id: str):
        """Store hard stop event in Redis"""
        if self.redis_client:
            event = {
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "opening_capital": self.opening_capital.get(user_id, 0.0),
                "current_capital": self.user_capital.get(user_id, 0.0),
                "loss_percentage": (self.opening_capital.get(user_id, 0.0) - self.user_capital.get(user_id, 0.0)) / 
                                 self.opening_capital.get(user_id, 0.0) * 100
            }
            await self.redis_client.set(
                f"user:{user_id}:hard_stop:{datetime.now().strftime('%Y-%m-%d')}",
                json.dumps(event)
            )
    
    async def _send_hard_stop_notification(self, user_id: str):
        """Send notification about hard stop"""
        try:
            notification = {
                "user_id": user_id,
                "type": "HARD_STOP",
                "message": f"Trading stopped due to 2% capital loss. Opening capital: ${self.opening_capital.get(user_id, 0.0):,.2f}, Current capital: ${self.user_capital.get(user_id, 0.0):,.2f}",
                "timestamp": datetime.now().isoformat()
            }
            # Send notification (implementation depends on notification system)
            logger.info(f"Hard stop notification: {json.dumps(notification)}")
        except Exception as e:
            logger.error(f"Error sending hard stop notification: {str(e)}") 