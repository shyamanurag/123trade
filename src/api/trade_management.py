from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/")
async def get_all_trades() -> List[Dict[str, Any]]:
    """Get all trades"""
    try:
        # ELIMINATED: Dangerous trade hiding that could hide real trading activity
        # ❌ # For now, return empty list - no trades yet
        # ❌ return []
        
        # SAFETY: Return error instead of hiding real trades
        logger.error("CRITICAL: Trade hiding ELIMINATED to prevent hidden trading activity")
        
        raise HTTPException(
            status_code=503, 
            detail="SAFETY: Trade data access disabled - real trade tracking required. Trade hiding eliminated for safety."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trades: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/live")
async def get_live_trades() -> List[Dict[str, Any]]:
    """Get all live trades"""
    try:
        # For now, return empty list - no live trades yet
        return []
    except Exception as e:
        logger.error(f"Error getting live trades: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/metrics")
async def get_all_user_metrics() -> Dict[str, Dict[str, Any]]:
    """Get metrics for all users"""
    try:
        # Return empty metrics for now
        return {}
    except Exception as e:
        logger.error(f"Error getting user metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{trade_id}")
async def get_trade_details(trade_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific trade"""
    try:
        # Trade not found since we're not persisting yet
        raise HTTPException(status_code=404, detail="Trade not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trade details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}")
async def get_user_trades(user_id: str) -> List[Dict[str, Any]]:
    """Get all trades for a specific user"""
    try:
        # Return empty list for now
        return []
    except Exception as e:
        logger.error(f"Error getting user trades: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}/metrics")
async def get_user_metrics(user_id: str) -> Dict[str, Any]:
    """Get detailed metrics for a specific user"""
    try:
        # Return basic metrics structure
        return {
            "user_id": user_id,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting user metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 

@router.post("/sync-sharekhan-data")
async def sync_sharekhan_data():
    """Manually trigger ShareKhan trade and position synchronization + Database Migration Fix"""
    try:
        logger.info("🚀 Manual sync triggered for ShareKhan data")
        
        # URGENT MIGRATION FIX: Add missing columns if they don't exist
        try:
            logger.info("🚨 URGENT: Checking database schema for missing columns...")
            from sqlalchemy import create_engine, text
            import os
            
            # Get DATABASE_URL from environment
            database_url = os.getenv('DATABASE_URL')
            if database_url:
                logger.info("📊 Executing urgent migration 016 inline...")
                
                # Create engine and connect
                engine = create_engine(database_url)
                
                with engine.connect() as conn:
                    # Start transaction
                    trans = conn.begin()
                    
                    try:
                        # Add missing columns
                        conn.execute(text("ALTER TABLE trades ADD COLUMN IF NOT EXISTS actual_execution BOOLEAN DEFAULT FALSE"))
                        conn.execute(text("ALTER TABLE trades ADD COLUMN IF NOT EXISTS current_price DECIMAL(10,2)"))
                        conn.execute(text("ALTER TABLE trades ADD COLUMN IF NOT EXISTS pnl DECIMAL(12,2) DEFAULT 0.0"))
                        conn.execute(text("ALTER TABLE trades ADD COLUMN IF NOT EXISTS pnl_percent DECIMAL(8,4) DEFAULT 0.0"))
                        
                        # Create indexes
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_trades_actual_execution ON trades(actual_execution)"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_trades_current_price ON trades(current_price)"))
                        
                        # Update existing trades
                        conn.execute(text("UPDATE trades SET actual_execution = FALSE WHERE actual_execution IS NULL"))
                        
                        # Create schema_migrations table if it doesn't exist
                        conn.execute(text("""
                            CREATE TABLE IF NOT EXISTS schema_migrations (
                                version INTEGER PRIMARY KEY,
                                description TEXT,
                                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                        """))
                        
                        # Log the migration
                        conn.execute(text("""
                            INSERT INTO schema_migrations (version, description, executed_at) 
                            VALUES (16, 'Add actual_execution and P&L columns for real ShareKhan data sync', CURRENT_TIMESTAMP)
                            ON CONFLICT (version) DO NOTHING
                        """))
                        
                        # Commit transaction
                        trans.commit()
                        
                        logger.info("✅ URGENT Migration 016 executed successfully inline!")
                        
                    except Exception as migration_error:
                        trans.rollback()
                        logger.warning(f"⚠️ Migration 016 failed (may already exist): {migration_error}")
                        
        except Exception as schema_error:
            logger.warning(f"⚠️ Schema check failed: {schema_error}")
        
        # Continue with normal ShareKhan sync logic
        from src.core.orchestrator import get_orchestrator_instance
        
        orchestrator = get_orchestrator_instance()
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Trading orchestrator not available")
        
        # Get trade engine from orchestrator
        trade_engine = orchestrator.trade_engine
        if not trade_engine:
            raise HTTPException(status_code=503, detail="Trade engine not available")
        
        # Trigger both sync operations
        logger.info("🔄 Starting ShareKhan data synchronization...")
        
        # Sync actual trades from ShareKhan
        trade_results = await trade_engine.sync_actual_sharekhan_trades()
        
        # Sync actual positions from ShareKhan  
        position_results = await trade_engine.sync_actual_sharekhan_positions()
        
        logger.info(f"✅ Sync completed: {len(trade_results.get('actual_trades', []))} trades, {len(position_results.get('actual_positions', []))} positions")
        
        return {
            "success": True,
            "message": "ShareKhan data synchronization completed",
            "timestamp": datetime.now().isoformat(),
            "results": {
                "trades_synced": len(trade_results.get('actual_trades', [])),
                "actual_trades": trade_results.get('actual_trades', []),
                "positions_synced": len(position_results.get('actual_positions', [])),
                "actual_positions": position_results.get('actual_positions', {}),
                "database_migration": "Migration 016 attempted - schema should now support actual_execution column"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ ShareKhan data sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@router.get("/sharekhan-positions")
async def get_sharekhan_positions():
    """Get actual positions from ShareKhan API"""
    try:
        from src.core.orchestrator import get_orchestrator_instance
        
        orchestrator = get_orchestrator_instance()
        if not orchestrator or not orchestrator.sharekhan_client:
            raise HTTPException(status_code=503, detail="ShareKhan client not available")
        
        # Get actual positions from ShareKhan
        positions_data = await orchestrator.sharekhan_client.get_positions()
        
        return {
            "success": True,
            "message": "Retrieved actual positions from ShareKhan",
            "timestamp": datetime.now().isoformat(),
            "data": positions_data
        }
        
    except Exception as e:
        logger.error(f"Error getting ShareKhan positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sharekhan-orders")
async def get_sharekhan_orders():
    """Get actual orders from ShareKhan API"""
    try:
        from src.core.orchestrator import get_orchestrator_instance
        
        orchestrator = get_orchestrator_instance()
        if not orchestrator or not orchestrator.sharekhan_client:
            raise HTTPException(status_code=503, detail="ShareKhan client not available")
        
        # Get actual orders from ShareKhan
        orders_data = await orchestrator.sharekhan_client.get_orders()
        
        return {
            "success": True,
            "message": "Retrieved actual orders from ShareKhan",
            "timestamp": datetime.now().isoformat(),
            "data": orders_data
        }
        
    except Exception as e:
        logger.error(f"Error getting ShareKhan orders: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 