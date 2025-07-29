"""
Real Position Manager for ShareKhan Trading System
Fetches real positions from ShareKhan API and syncs with database
100% REAL DATA - NO MOCK/SIMULATION
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

logger = logging.getLogger(__name__)

class RealPositionManager:
    """Manages real positions from ShareKhan API"""
    
    def __init__(self):
        self.sharekhan_client = None
        self.db_session = None
    
    async def initialize(self):
        """Initialize position manager"""
        try:
            from src.core.database import get_database_session
            self.db_session = get_database_session()
            
            if not self.db_session:
                raise RuntimeError("Database connection not available")
            
            logger.info("✅ Real Position Manager initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Position manager initialization failed: {e}")
            return False
    
    async def sync_user_positions(
        self, 
        user_id: int,
        sharekhan_client_id: str,
        sharekhan_api_key: str,
        sharekhan_api_secret: str
    ) -> Dict[str, Any]:
        """
        Sync real positions from ShareKhan for a specific user
        Credentials provided at runtime, not stored
        """
        try:
            logger.info(f"🔄 Syncing real positions for user: {user_id}")
            
            # Authenticate with ShareKhan
            from brokers.sharekhan import ShareKhanIntegration
            
            sharekhan = ShareKhanIntegration()
            auth_result = await sharekhan.authenticate(
                client_id=sharekhan_client_id,
                api_key=sharekhan_api_key,
                api_secret=sharekhan_api_secret
            )
            
            if not auth_result.get('success'):
                raise RuntimeError(f"ShareKhan authentication failed: {auth_result.get('error')}")
            
            # Fetch real positions from ShareKhan
            positions_result = await sharekhan.get_positions(sharekhan_client_id)
            
            if not positions_result.get('success'):
                raise RuntimeError(f"Failed to fetch positions: {positions_result.get('error')}")
            
            real_positions = positions_result.get('data', [])
            
            # Clear existing positions for this user
            await self._clear_user_positions(user_id)
            
            # Insert real positions into database
            synced_positions = []
            for position in real_positions:
                if position.get('quantity', 0) != 0:  # Only active positions
                    db_position = await self._insert_real_position(user_id, position)
                    if db_position:
                        synced_positions.append(db_position)
            
            logger.info(f"✅ Synced {len(synced_positions)} real positions for user: {user_id}")
            
            return {
                "success": True,
                "user_id": user_id,
                "positions_synced": len(synced_positions),
                "positions": synced_positions,
                "source": "sharekhan_real",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Position sync failed for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "user_id": user_id,
                "positions_synced": 0
            }
    
    async def get_user_positions(self, user_id: int) -> Dict[str, Any]:
        """Get user positions from database (already synced from ShareKhan)"""
        try:
            positions_query = """
                SELECT position_id, symbol, quantity, entry_price, current_price,
                       entry_time, exit_time, strategy, pnl, unrealized_pnl,
                       side, status, created_at, updated_at
                FROM positions 
                WHERE user_id = %s AND status = 'OPEN'
                ORDER BY entry_time DESC
            """
            
            result = self.db_session.execute(positions_query, (user_id,))
            positions = result.fetchall()
            
            positions_list = []
            total_pnl = 0.0
            
            for pos in positions:
                position_data = {
                    "position_id": pos[0],
                    "symbol": pos[1],
                    "quantity": pos[2],
                    "entry_price": float(pos[3]),
                    "current_price": float(pos[4]) if pos[4] else 0.0,
                    "entry_time": pos[5].isoformat(),
                    "exit_time": pos[6].isoformat() if pos[6] else None,
                    "strategy": pos[7],
                    "realized_pnl": float(pos[8]) if pos[8] else 0.0,
                    "unrealized_pnl": float(pos[9]) if pos[9] else 0.0,
                    "side": pos[10],
                    "status": pos[11],
                    "created_at": pos[12].isoformat(),
                    "updated_at": pos[13].isoformat()
                }
                
                total_pnl += position_data["unrealized_pnl"]
                positions_list.append(position_data)
            
            return {
                "success": True,
                "user_id": user_id,
                "positions": positions_list,
                "total_positions": len(positions_list),
                "total_unrealized_pnl": total_pnl,
                "source": "database_real"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get user positions: {e}")
            return {
                "success": False,
                "error": str(e),
                "positions": []
            }
    
    async def update_position_prices(
        self,
        user_id: int,
        sharekhan_client_id: str,
        sharekhan_api_key: str,
        sharekhan_api_secret: str
    ) -> Dict[str, Any]:
        """Update current prices and P&L for user positions"""
        try:
            logger.info(f"📊 Updating position prices for user: {user_id}")
            
            # Get current positions
            user_positions = await self.get_user_positions(user_id)
            
            if not user_positions.get('success') or not user_positions.get('positions'):
                return {
                    "success": True,
                    "message": "No positions to update",
                    "user_id": user_id
                }
            
            # Authenticate with ShareKhan
            from brokers.sharekhan import ShareKhanIntegration
            
            sharekhan = ShareKhanIntegration()
            auth_result = await sharekhan.authenticate(
                client_id=sharekhan_client_id,
                api_key=sharekhan_api_key,
                api_secret=sharekhan_api_secret
            )
            
            if not auth_result.get('success'):
                raise RuntimeError(f"ShareKhan authentication failed: {auth_result.get('error')}")
            
            # Update each position with real current price
            updated_positions = []
            for position in user_positions['positions']:
                symbol = position['symbol']
                
                # Get real current price from ShareKhan
                quote_result = await sharekhan.get_quote(symbol)
                
                if quote_result.get('success'):
                    current_price = float(quote_result['data'].get('ltp', 0))
                    
                    # Calculate P&L
                    entry_price = position['entry_price']
                    quantity = position['quantity']
                    
                    if position['side'] == 'BUY':
                        unrealized_pnl = (current_price - entry_price) * quantity
                    else:  # SELL
                        unrealized_pnl = (entry_price - current_price) * quantity
                    
                    # Update in database
                    update_query = """
                        UPDATE positions 
                        SET current_price = %s, unrealized_pnl = %s, updated_at = %s
                        WHERE position_id = %s
                    """
                    
                    self.db_session.execute(update_query, (
                        current_price,
                        unrealized_pnl,
                        datetime.now(),
                        position['position_id']
                    ))
                    
                    position['current_price'] = current_price
                    position['unrealized_pnl'] = unrealized_pnl
                    updated_positions.append(position)
            
            self.db_session.commit()
            
            logger.info(f"✅ Updated {len(updated_positions)} position prices for user: {user_id}")
            
            return {
                "success": True,
                "user_id": user_id,
                "positions_updated": len(updated_positions),
                "positions": updated_positions,
                "total_unrealized_pnl": sum(p['unrealized_pnl'] for p in updated_positions),
                "source": "sharekhan_real_time"
            }
            
        except Exception as e:
            logger.error(f"❌ Position price update failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "user_id": user_id
            }
    
    async def close_position(
        self,
        user_id: int,
        position_id: int,
        sharekhan_client_id: str,
        sharekhan_api_key: str,
        sharekhan_api_secret: str
    ) -> Dict[str, Any]:
        """Close a position via ShareKhan API"""
        try:
            logger.info(f"🔒 Closing position {position_id} for user: {user_id}")
            
            # Get position details
            position_query = """
                SELECT symbol, quantity, side, current_price, entry_price
                FROM positions 
                WHERE position_id = %s AND user_id = %s AND status = 'OPEN'
            """
            
            result = self.db_session.execute(position_query, (position_id, user_id))
            position = result.fetchone()
            
            if not position:
                raise HTTPException(status_code=404, detail="Position not found or already closed")
            
            symbol, quantity, side, current_price, entry_price = position
            
            # Authenticate with ShareKhan
            from brokers.sharekhan import ShareKhanIntegration
            
            sharekhan = ShareKhanIntegration()
            auth_result = await sharekhan.authenticate(
                client_id=sharekhan_client_id,
                api_key=sharekhan_api_key,
                api_secret=sharekhan_api_secret
            )
            
            if not auth_result.get('success'):
                raise RuntimeError(f"ShareKhan authentication failed: {auth_result.get('error')}")
            
            # Place closing order via ShareKhan
            closing_side = "SELL" if side == "BUY" else "BUY"
            
            order_result = await sharekhan.place_order(
                symbol=symbol,
                quantity=quantity,
                side=closing_side,
                order_type="MARKET",
                client_id=sharekhan_client_id
            )
            
            if not order_result.get('success'):
                raise RuntimeError(f"Failed to place closing order: {order_result.get('error')}")
            
            # Calculate final P&L
            if side == "BUY":
                realized_pnl = (current_price - entry_price) * quantity
            else:
                realized_pnl = (entry_price - current_price) * quantity
            
            # Update position status in database
            update_query = """
                UPDATE positions 
                SET status = 'CLOSED', exit_time = %s, pnl = %s, updated_at = %s
                WHERE position_id = %s
            """
            
            self.db_session.execute(update_query, (
                datetime.now(),
                realized_pnl,
                datetime.now(),
                position_id
            ))
            self.db_session.commit()
            
            logger.info(f"✅ Position {position_id} closed successfully with P&L: ₹{realized_pnl}")
            
            return {
                "success": True,
                "position_id": position_id,
                "symbol": symbol,
                "quantity": quantity,
                "realized_pnl": realized_pnl,
                "order_id": order_result.get('order_id'),
                "message": f"Position closed successfully with P&L: ₹{realized_pnl}",
                "source": "sharekhan_real"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to close position: {e}")
            return {
                "success": False,
                "error": str(e),
                "position_id": position_id
            }
    
    async def _clear_user_positions(self, user_id: int):
        """Clear existing positions for user (before sync)"""
        try:
            # Only clear OPEN positions, keep CLOSED for history
            clear_query = "DELETE FROM positions WHERE user_id = %s AND status = 'OPEN'"
            self.db_session.execute(clear_query, (user_id,))
            self.db_session.commit()
            
        except Exception as e:
            logger.error(f"❌ Failed to clear user positions: {e}")
    
    async def _insert_real_position(self, user_id: int, position_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Insert real position from ShareKhan into database"""
        try:
            # Calculate P&L
            entry_price = float(position_data.get('avg_price', position_data.get('price', 0)))
            current_price = float(position_data.get('ltp', position_data.get('current_price', entry_price)))
            quantity = int(position_data.get('quantity', 0))
            side = position_data.get('side', 'BUY').upper()
            
            if side == "BUY":
                unrealized_pnl = (current_price - entry_price) * quantity
            else:
                unrealized_pnl = (entry_price - current_price) * quantity
            
            # Insert position
            insert_query = """
                INSERT INTO positions (
                    user_id, symbol, quantity, entry_price, current_price,
                    entry_time, side, status, unrealized_pnl, strategy,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) RETURNING position_id, symbol, quantity, entry_price, current_price, unrealized_pnl
            """
            
            insert_data = (
                user_id,
                position_data.get('symbol', ''),
                quantity,
                entry_price,
                current_price,
                datetime.now(),  # entry_time (since we don't have exact time from ShareKhan)
                side,
                'OPEN',
                unrealized_pnl,
                position_data.get('strategy', 'manual'),
                datetime.now(),
                datetime.now()
            )
            
            result = self.db_session.execute(insert_query, insert_data)
            new_position = result.fetchone()
            self.db_session.commit()
            
            if new_position:
                return {
                    "position_id": new_position[0],
                    "symbol": new_position[1],
                    "quantity": new_position[2],
                    "entry_price": float(new_position[3]),
                    "current_price": float(new_position[4]),
                    "unrealized_pnl": float(new_position[5]),
                    "side": side,
                    "status": "OPEN"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to insert position: {e}")
            return None

# Global position manager instance
position_manager = RealPositionManager()

async def get_position_manager() -> RealPositionManager:
    """Get initialized position manager"""
    if not position_manager.db_session:
        await position_manager.initialize()
    return position_manager 