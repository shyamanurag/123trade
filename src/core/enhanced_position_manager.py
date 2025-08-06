"""
Enhanced Position Manager
Comprehensive position tracking with real-time updates and P&L calculations
100% REAL DATA from ShareKhan - NO SIMULATION
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP

from brokers.sharekhan import ShareKhanIntegration, ShareKhanMarketData
from src.core.database import db_manager

logger = logging.getLogger(__name__)

@dataclass
class Position:
    """Enhanced position structure with comprehensive tracking"""
    position_id: Optional[int]
    user_id: int
    symbol: str
    exchange: str
    quantity: int
    entry_price: Decimal
    current_price: Decimal
    average_price: Decimal  # For multiple entries
    side: str  # LONG/SHORT
    status: str  # OPEN/CLOSED/PARTIAL
    entry_time: datetime
    last_update: datetime
    
    # P&L Calculations
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    day_pnl: Decimal
    total_pnl: Decimal
    
    # Risk Management
    stop_loss: Optional[Decimal]
    take_profit: Optional[Decimal]
    max_drawdown: Decimal
    max_profit: Decimal
    
    # Metadata
    strategy: Optional[str]
    notes: Optional[str]
    broker_position_id: Optional[str]
    created_at: datetime
    updated_at: datetime

@dataclass
class PositionUpdate:
    """Position update from ShareKhan"""
    symbol: str
    current_price: Decimal
    timestamp: datetime
    volume: int
    change_percent: float

class EnhancedPositionManager:
    """
    Enhanced position manager with real-time tracking and comprehensive P&L
    Consolidates all position management functionality
    """
    
    def __init__(self, sharekhan_client: Optional[ShareKhanIntegration] = None):
        self.sharekhan_client = sharekhan_client
        self.db_session = None
        
        # In-memory position tracking
        self.active_positions: Dict[str, Position] = {}  # symbol -> Position
        self.user_positions: Dict[int, List[Position]] = {}  # user_id -> List[Position]
        
        # Price tracking
        self.last_prices: Dict[str, Decimal] = {}
        self.price_history: Dict[str, List[Tuple[datetime, Decimal]]] = {}
        
        # Configuration
        self.update_interval_seconds = 5  # Real-time updates every 5 seconds
        self.price_precision = Decimal('0.01')  # 2 decimal places
        
        # Background tasks
        self.price_update_task: Optional[asyncio.Task] = None
        self.pnl_calculation_task: Optional[asyncio.Task] = None
        
        logger.info("✅ Enhanced Position Manager initialized")
    
    async def initialize(self) -> bool:
        """Initialize enhanced position manager"""
        try:
            # Get database session
            from src.core.database import db_manager
            self.db_session = db_manager.get_shared_session()
            
            if not self.db_session:
                raise RuntimeError("Database connection not available")
            
            # Load existing positions from database
            await self._load_positions_from_db()
            
            # Start background tasks
            self.price_update_task = asyncio.create_task(self._real_time_price_updates())
            self.pnl_calculation_task = asyncio.create_task(self._continuous_pnl_calculation())
            
            logger.info("✅ Enhanced Position Manager fully initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize enhanced position manager: {e}")
            return False
    
    async def sync_positions_from_sharekhan(
        self, 
        user_id: int,
        sharekhan_client_id: str,
        sharekhan_api_key: str,
        sharekhan_api_secret: str
    ) -> Dict[str, Any]:
        """
        Sync all positions from ShareKhan for a user
        Returns comprehensive position data with real-time P&L
        """
        try:
            logger.info(f"🔄 Syncing positions from ShareKhan for user: {user_id}")
            
            # Initialize ShareKhan client if not provided
            if not self.sharekhan_client:
                from brokers.sharekhan import ShareKhanIntegration
                client = ShareKhanIntegration(
                    api_key=sharekhan_api_key,
                    secret_key=sharekhan_api_secret,
                    customer_id=sharekhan_client_id
                )
                
                # Authenticate (this would need proper token handling)
                auth_result = await client.authenticate()
                if not auth_result:
                    raise RuntimeError("ShareKhan authentication failed")
                
                self.sharekhan_client = client
            
            # Fetch positions from ShareKhan
            positions_result = await self.sharekhan_client.get_positions()
            
            if not positions_result.get('success'):
                raise RuntimeError(f"Failed to fetch positions: {positions_result.get('error')}")
            
            sharekhan_positions = positions_result.get('positions', [])
            
            # Fetch current market prices for all symbols
            symbols = [pos.get('symbol') for pos in sharekhan_positions if pos.get('quantity', 0) != 0]
            
            current_prices = {}
            if symbols:
                quotes_result = await self.sharekhan_client.get_market_quote(symbols)
                current_prices = {
                    symbol: Decimal(str(data.ltp)) for symbol, data in quotes_result.items()
                }
            
            # Process and store positions
            synced_positions = []
            
            for pos_data in sharekhan_positions:
                quantity = pos_data.get('quantity', 0)
                if quantity == 0:
                    continue  # Skip closed positions
                
                symbol = pos_data.get('symbol', '')
                current_price = current_prices.get(symbol, Decimal('0'))
                
                # Create enhanced position object
                position = await self._create_enhanced_position(
                    user_id=user_id,
                    position_data=pos_data,
                    current_price=current_price
                )
                
                if position:
                    # Store in database
                    await self._upsert_position_to_db(position)
                    
                    # Update in-memory tracking
                    self.active_positions[f"{user_id}_{symbol}"] = position
                    if user_id not in self.user_positions:
                        self.user_positions[user_id] = []
                    
                    # Remove existing position for this symbol
                    self.user_positions[user_id] = [
                        p for p in self.user_positions[user_id] if p.symbol != symbol
                    ]
                    self.user_positions[user_id].append(position)
                    
                    synced_positions.append(asdict(position))
            
            logger.info(f"✅ Synced {len(synced_positions)} positions for user {user_id}")
            
            return {
                "success": True,
                "user_id": user_id,
                "positions_count": len(synced_positions),
                "positions": synced_positions,
                "total_unrealized_pnl": sum(pos["unrealized_pnl"] for pos in synced_positions),
                "total_day_pnl": sum(pos["day_pnl"] for pos in synced_positions),
                "sync_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to sync positions from ShareKhan: {e}")
            return {
                "success": False,
                "error": str(e),
                "user_id": user_id
            }
    
    async def get_user_positions(
        self, 
        user_id: int, 
        include_closed: bool = False
    ) -> List[Dict[str, Any]]:
        """Get all positions for a user with real-time P&L"""
        try:
            positions = self.user_positions.get(user_id, [])
            
            if not include_closed:
                positions = [pos for pos in positions if pos.status != 'CLOSED']
            
            # Update real-time prices and P&L
            updated_positions = []
            for position in positions:
                updated_position = await self._update_position_realtime(position)
                updated_positions.append(asdict(updated_position))
            
            return updated_positions
            
        except Exception as e:
            logger.error(f"❌ Failed to get user positions: {e}")
            return []
    
    async def update_position_prices(self, symbols: List[str]) -> Dict[str, Any]:
        """Update current prices for specific symbols"""
        try:
            if not self.sharekhan_client:
                raise RuntimeError("ShareKhan client not available")
            
            # Fetch current quotes
            quotes_result = await self.sharekhan_client.get_market_quote(symbols)
            
            updated_positions = []
            price_updates = {}
            
            for symbol, market_data in quotes_result.items():
                current_price = Decimal(str(market_data.ltp))
                price_updates[symbol] = float(current_price)
                
                # Update price history
                if symbol not in self.price_history:
                    self.price_history[symbol] = []
                
                self.price_history[symbol].append((datetime.now(), current_price))
                
                # Keep only last 100 price points
                if len(self.price_history[symbol]) > 100:
                    self.price_history[symbol] = self.price_history[symbol][-100:]
                
                # Update all positions for this symbol
                for position_key, position in self.active_positions.items():
                    if position.symbol == symbol:
                        old_pnl = position.unrealized_pnl
                        
                        # Update position price and P&L
                        position.current_price = current_price
                        position.last_update = datetime.now()
                        
                        # Recalculate P&L
                        await self._calculate_position_pnl(position)
                        
                        # Update in database
                        await self._update_position_in_db(position)
                        
                        updated_positions.append({
                            "symbol": symbol,
                            "user_id": position.user_id,
                            "old_pnl": float(old_pnl),
                            "new_pnl": float(position.unrealized_pnl),
                            "price_change": float(current_price - position.entry_price),
                            "current_price": float(current_price)
                        })
            
            logger.info(f"✅ Updated prices for {len(symbols)} symbols")
            
            return {
                "success": True,
                "updated_symbols": len(symbols),
                "price_updates": price_updates,
                "position_updates": updated_positions,
                "update_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to update position prices: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def close_position(
        self,
        user_id: int,
        symbol: str,
        quantity: Optional[int] = None,  # None = close all
        close_price: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """Close position (partial or full) with P&L calculation"""
        try:
            position_key = f"{user_id}_{symbol}"
            position = self.active_positions.get(position_key)
            
            if not position:
                raise ValueError(f"Position not found: {symbol} for user {user_id}")
            
            if position.status == 'CLOSED':
                raise ValueError(f"Position already closed: {symbol}")
            
            # Get current market price if not provided
            if close_price is None:
                if not self.sharekhan_client:
                    raise RuntimeError("ShareKhan client required for market price")
                
                quotes = await self.sharekhan_client.get_market_quote([symbol])
                if symbol in quotes:
                    close_price = Decimal(str(quotes[symbol].ltp))
                else:
                    raise ValueError(f"Could not get current price for {symbol}")
            
            # Determine quantity to close
            close_quantity = quantity if quantity is not None else position.quantity
            
            if close_quantity > position.quantity:
                raise ValueError(f"Cannot close {close_quantity} shares, only {position.quantity} available")
            
            # Calculate realized P&L
            if position.side == 'LONG':
                realized_pnl = (close_price - position.average_price) * close_quantity
            else:  # SHORT
                realized_pnl = (position.average_price - close_price) * close_quantity
            
            # Update position
            position.quantity -= close_quantity
            position.realized_pnl += realized_pnl
            position.last_update = datetime.now()
            
            if position.quantity == 0:
                position.status = 'CLOSED'
                # Remove from active positions
                self.active_positions.pop(position_key, None)
            else:
                position.status = 'PARTIAL'
                # Recalculate unrealized P&L for remaining quantity
                await self._calculate_position_pnl(position)
            
            # Update in database
            await self._update_position_in_db(position)
            
            logger.info(f"✅ Closed {close_quantity} shares of {symbol} for user {user_id}, P&L: {realized_pnl}")
            
            return {
                "success": True,
                "symbol": symbol,
                "user_id": user_id,
                "closed_quantity": close_quantity,
                "close_price": float(close_price),
                "realized_pnl": float(realized_pnl),
                "remaining_quantity": position.quantity,
                "position_status": position.status,
                "total_realized_pnl": float(position.realized_pnl)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to close position: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_position_analytics(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive position analytics for user"""
        try:
            positions = self.user_positions.get(user_id, [])
            
            if not positions:
                return {
                    "user_id": user_id,
                    "total_positions": 0,
                    "analytics": {}
                }
            
            # Calculate analytics
            total_unrealized_pnl = sum(pos.unrealized_pnl for pos in positions)
            total_realized_pnl = sum(pos.realized_pnl for pos in positions)
            total_day_pnl = sum(pos.day_pnl for pos in positions)
            
            profitable_positions = [pos for pos in positions if pos.unrealized_pnl > 0]
            losing_positions = [pos for pos in positions if pos.unrealized_pnl < 0]
            
            largest_gain = max((pos.unrealized_pnl for pos in positions), default=Decimal('0'))
            largest_loss = min((pos.unrealized_pnl for pos in positions), default=Decimal('0'))
            
            # Portfolio value calculation
            portfolio_value = sum(pos.current_price * pos.quantity for pos in positions)
            
            return {
                "user_id": user_id,
                "total_positions": len(positions),
                "open_positions": len([pos for pos in positions if pos.status == 'OPEN']),
                "analytics": {
                    "total_unrealized_pnl": float(total_unrealized_pnl),
                    "total_realized_pnl": float(total_realized_pnl),
                    "total_day_pnl": float(total_day_pnl),
                    "portfolio_value": float(portfolio_value),
                    "profitable_positions": len(profitable_positions),
                    "losing_positions": len(losing_positions),
                    "win_rate": len(profitable_positions) / len(positions) * 100 if positions else 0,
                    "largest_gain": float(largest_gain),
                    "largest_loss": float(largest_loss),
                    "average_position_size": float(portfolio_value / len(positions)) if positions else 0,
                    "total_pnl": float(total_unrealized_pnl + total_realized_pnl)
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get position analytics: {e}")
            return {
                "user_id": user_id,
                "error": str(e)
            }
    
    async def _create_enhanced_position(
        self,
        user_id: int,
        position_data: Dict[str, Any],
        current_price: Decimal
    ) -> Optional[Position]:
        """Create enhanced position from ShareKhan data"""
        try:
            symbol = position_data.get('symbol', '')
            quantity = int(position_data.get('quantity', 0))
            entry_price = Decimal(str(position_data.get('average_price', 0)))
            
            # Determine side based on quantity
            side = 'LONG' if quantity > 0 else 'SHORT'
            quantity = abs(quantity)  # Work with absolute quantity
            
            # Create position object
            position = Position(
                position_id=None,  # Will be set when saved to DB
                user_id=user_id,
                symbol=symbol,
                exchange=position_data.get('exchange', 'NSE'),
                quantity=quantity,
                entry_price=entry_price,
                current_price=current_price,
                average_price=entry_price,
                side=side,
                status='OPEN',
                entry_time=datetime.now(),  # ShareKhan doesn't provide exact entry time
                last_update=datetime.now(),
                unrealized_pnl=Decimal('0'),
                realized_pnl=Decimal(str(position_data.get('realized_pnl', 0))),
                day_pnl=Decimal('0'),
                total_pnl=Decimal('0'),
                stop_loss=None,
                take_profit=None,
                max_drawdown=Decimal('0'),
                max_profit=Decimal('0'),
                strategy=position_data.get('strategy', 'manual'),
                notes=None,
                broker_position_id=position_data.get('position_id'),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Calculate initial P&L
            await self._calculate_position_pnl(position)
            
            return position
            
        except Exception as e:
            logger.error(f"❌ Failed to create enhanced position: {e}")
            return None
    
    async def _calculate_position_pnl(self, position: Position):
        """Calculate comprehensive P&L for position"""
        try:
            if position.side == 'LONG':
                unrealized_pnl = (position.current_price - position.average_price) * position.quantity
            else:  # SHORT
                unrealized_pnl = (position.average_price - position.current_price) * position.quantity
            
            position.unrealized_pnl = unrealized_pnl.quantize(self.price_precision, rounding=ROUND_HALF_UP)
            position.total_pnl = position.unrealized_pnl + position.realized_pnl
            
            # Update max profit/drawdown
            if unrealized_pnl > position.max_profit:
                position.max_profit = unrealized_pnl
            
            if unrealized_pnl < position.max_drawdown:
                position.max_drawdown = unrealized_pnl
            
            # Calculate day P&L (simplified - would need opening price)
            position.day_pnl = position.unrealized_pnl  # Approximation
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate P&L: {e}")
    
    async def _update_position_realtime(self, position: Position) -> Position:
        """Update position with real-time data"""
        try:
            # Get latest price if available
            if position.symbol in self.last_prices:
                position.current_price = self.last_prices[position.symbol]
                position.last_update = datetime.now()
                await self._calculate_position_pnl(position)
            
            return position
            
        except Exception as e:
            logger.error(f"❌ Failed to update position real-time: {e}")
            return position
    
    async def _load_positions_from_db(self):
        """Load existing positions from database"""
        try:
            query = """
                SELECT * FROM positions 
                WHERE status IN ('OPEN', 'PARTIAL')
                ORDER BY created_at DESC
            """
            
            result = self.db_session.execute(query)
            rows = result.fetchall()
            
            for row in rows:
                # Convert DB row to Position object
                position = Position(
                    position_id=row[0],  # Assuming first column is position_id
                    user_id=row[1],
                    symbol=row[2],
                    exchange=row[3] if len(row) > 3 else 'NSE',
                    quantity=row[4],
                    entry_price=Decimal(str(row[5])),
                    current_price=Decimal(str(row[6])),
                    average_price=Decimal(str(row[5])),  # Same as entry for now
                    side=row[7] if len(row) > 7 else 'LONG',
                    status=row[8] if len(row) > 8 else 'OPEN',
                    entry_time=row[9] if len(row) > 9 else datetime.now(),
                    last_update=datetime.now(),
                    unrealized_pnl=Decimal(str(row[10])) if len(row) > 10 else Decimal('0'),
                    realized_pnl=Decimal('0'),
                    day_pnl=Decimal('0'),
                    total_pnl=Decimal('0'),
                    stop_loss=None,
                    take_profit=None,
                    max_drawdown=Decimal('0'),
                    max_profit=Decimal('0'),
                    strategy=row[11] if len(row) > 11 else 'manual',
                    notes=None,
                    broker_position_id=None,
                    created_at=row[12] if len(row) > 12 else datetime.now(),
                    updated_at=datetime.now()
                )
                
                # Store in memory
                position_key = f"{position.user_id}_{position.symbol}"
                self.active_positions[position_key] = position
                
                if position.user_id not in self.user_positions:
                    self.user_positions[position.user_id] = []
                self.user_positions[position.user_id].append(position)
            
            logger.info(f"✅ Loaded {len(rows)} positions from database")
            
        except Exception as e:
            logger.error(f"❌ Failed to load positions from DB: {e}")
    
    async def _upsert_position_to_db(self, position: Position) -> bool:
        """Insert or update position in database"""
        try:
            upsert_query = """
                INSERT INTO positions (
                    user_id, symbol, exchange, quantity, entry_price, current_price,
                    side, status, entry_time, unrealized_pnl, strategy, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, symbol) DO UPDATE SET
                    quantity = EXCLUDED.quantity,
                    current_price = EXCLUDED.current_price,
                    unrealized_pnl = EXCLUDED.unrealized_pnl,
                    status = EXCLUDED.status,
                    updated_at = EXCLUDED.updated_at
                RETURNING position_id
            """
            
            data = (
                position.user_id,
                position.symbol,
                position.exchange,
                position.quantity,
                float(position.entry_price),
                float(position.current_price),
                position.side,
                position.status,
                position.entry_time,
                float(position.unrealized_pnl),
                position.strategy,
                position.created_at,
                position.updated_at
            )
            
            result = self.db_session.execute(upsert_query, data)
            position_id = result.fetchone()
            
            if position_id and position.position_id is None:
                position.position_id = position_id[0]
            
            self.db_session.commit()
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to upsert position to DB: {e}")
            return False
    
    async def _update_position_in_db(self, position: Position) -> bool:
        """Update existing position in database"""
        try:
            if not position.position_id:
                return await self._upsert_position_to_db(position)
            
            update_query = """
                UPDATE positions SET
                    quantity = %s,
                    current_price = %s,
                    unrealized_pnl = %s,
                    status = %s,
                    updated_at = %s
                WHERE position_id = %s
            """
            
            data = (
                position.quantity,
                float(position.current_price),
                float(position.unrealized_pnl),
                position.status,
                datetime.now(),
                position.position_id
            )
            
            self.db_session.execute(update_query, data)
            self.db_session.commit()
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update position in DB: {e}")
            return False
    
    async def _real_time_price_updates(self):
        """Background task for real-time price updates"""
        while True:
            try:
                await asyncio.sleep(self.update_interval_seconds)
                
                if not self.active_positions or not self.sharekhan_client:
                    continue
                
                # Get unique symbols from active positions
                symbols = list(set(pos.symbol for pos in self.active_positions.values()))
                
                if symbols:
                    # Update prices
                    await self.update_position_prices(symbols)
                
            except Exception as e:
                logger.error(f"❌ Error in real-time price updates: {e}")
                await asyncio.sleep(30)  # Wait 30 seconds before retrying
    
    async def _continuous_pnl_calculation(self):
        """Background task for continuous P&L calculation"""
        while True:
            try:
                await asyncio.sleep(1)  # Update P&L every second
                
                for position in self.active_positions.values():
                    if position.status == 'OPEN':
                        await self._calculate_position_pnl(position)
                
            except Exception as e:
                logger.error(f"❌ Error in P&L calculation: {e}")
                await asyncio.sleep(5)  # Wait 5 seconds before retrying
    
    async def shutdown(self):
        """Shutdown position manager"""
        try:
            if self.price_update_task:
                self.price_update_task.cancel()
            
            if self.pnl_calculation_task:
                self.pnl_calculation_task.cancel()
            
            logger.info("✅ Enhanced Position Manager shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")

# Global instance
enhanced_position_manager = EnhancedPositionManager()