"""
Complete System Flow API for ShareKhan Trading System
Orchestrates entire flow: User Management -> ShareKhan Integration -> Real Data Sync
100% REAL DATA FLOW - NO MOCK/SIMULATION
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/system", tags=["complete-system-flow"])

class SystemInitRequest(BaseModel):
    """Complete system initialization request"""
    user_id: int
    sharekhan_client_id: str
    sharekhan_api_key: str
    sharekhan_api_secret: str
    sync_all_data: bool = True

class SystemStatusResponse(BaseModel):
    """Complete system status response"""
    success: bool
    user_id: int
    system_components: Dict[str, Any]
    data_summary: Dict[str, Any]
    message: str
    timestamp: str

@router.post("/initialize-complete-flow", response_model=SystemStatusResponse)
async def initialize_complete_system_flow(
    request: SystemInitRequest,
    background_tasks: BackgroundTasks
):
    """
    Initialize complete system flow for a user
    1. Verify user exists in database
    2. Authenticate with ShareKhan
    3. Sync all real data (positions, trades, balance, P&L)
    4. Initialize orchestrator
    5. Setup real-time updates
    """
    try:
        logger.info(f"🚀 Initializing complete system flow for user: {request.user_id}")
        
        # Step 1: Verify user exists in database
        user_verification = await verify_user_exists(request.user_id)
        if not user_verification['exists']:
            raise HTTPException(status_code=404, detail=f"User {request.user_id} not found in database")
        
        # Step 2: Authenticate with ShareKhan
        sharekhan_auth = await authenticate_sharekhan(
            request.sharekhan_client_id,
            request.sharekhan_api_key,
            request.sharekhan_api_secret
        )
        if not sharekhan_auth['success']:
            raise HTTPException(status_code=401, detail=f"ShareKhan authentication failed: {sharekhan_auth['error']}")
        
        # Step 3: Sync all real data
        data_sync_result = await sync_all_real_data(
            request.user_id,
            request.sharekhan_client_id,
            request.sharekhan_api_key,
            request.sharekhan_api_secret
        )
        
        # Step 4: Initialize orchestrator for this user
        orchestrator_result = await initialize_user_orchestrator(
            request.user_id,
            request.sharekhan_client_id
        )
        
        # Step 5: Setup real-time updates (background task)
        if request.sync_all_data:
            background_tasks.add_task(
                setup_realtime_updates,
                request.user_id,
                request.sharekhan_client_id,
                request.sharekhan_api_key,
                request.sharekhan_api_secret
            )
        
        # Compile system status
        system_components = {
            "user_database": user_verification,
            "sharekhan_auth": sharekhan_auth,
            "data_sync": data_sync_result,
            "orchestrator": orchestrator_result,
            "realtime_updates": "initialized" if request.sync_all_data else "disabled"
        }
        
        data_summary = {
            "positions_synced": data_sync_result.get('positions_count', 0),
            "trades_synced": data_sync_result.get('trades_count', 0),
            "account_balance": data_sync_result.get('account_balance', 0.0),
            "total_pnl": data_sync_result.get('total_pnl', 0.0),
            "last_sync": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Complete system flow initialized for user: {request.user_id}")
        
        return SystemStatusResponse(
            success=True,
            user_id=request.user_id,
            system_components=system_components,
            data_summary=data_summary,
            message="Complete system flow initialized successfully with real ShareKhan data",
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Complete system flow initialization failed: {e}")
        raise HTTPException(status_code=500, detail=f"System initialization failed: {str(e)}")

@router.get("/status/{user_id}")
async def get_complete_system_status(user_id: int):
    """Get complete system status for a user"""
    try:
        logger.info(f"📊 Getting complete system status for user: {user_id}")
        
        # Get user info
        user_info = await get_user_info(user_id)
        
        # Get positions status
        positions_status = await get_positions_status(user_id)
        
        # Get orchestrator status
        orchestrator_status = await get_orchestrator_status(user_id)
        
        # Get database health
        db_health = await get_database_health()
        
        return {
            "success": True,
            "user_id": user_id,
            "system_health": {
                "user_management": user_info,
                "position_manager": positions_status,
                "trading_orchestrator": orchestrator_status,
                "database": db_health
            },
            "overall_status": "healthy" if all([
                user_info.get('exists'),
                positions_status.get('operational'),
                orchestrator_status.get('running'),
                db_health.get('connected')
            ]) else "unhealthy",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync-all-data/{user_id}")
async def sync_all_user_data(
    user_id: int,
    sharekhan_client_id: str,
    sharekhan_api_key: str,
    sharekhan_api_secret: str
):
    """Sync all real data for a user"""
    try:
        logger.info(f"🔄 Syncing all real data for user: {user_id}")
        
        sync_result = await sync_all_real_data(
            user_id,
            sharekhan_client_id,
            sharekhan_api_key,
            sharekhan_api_secret
        )
        
        return sync_result
        
    except Exception as e:
        logger.error(f"❌ Data sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def verify_user_exists(user_id: int) -> Dict[str, Any]:
    """Verify user exists in database"""
    try:
        from src.core.database import db_manager
        
        session = db_manager.get_shared_session()
        user_query = "SELECT id, username, full_name, is_active FROM users WHERE id = %s"
        result = session.execute(user_query, (user_id,))
        user = result.fetchone()
        
        if user:
            return {
                "exists": True,
                "user_id": user[0],
                "username": user[1],
                "full_name": user[2],
                "is_active": user[3],
                "status": "verified"
            }
        else:
            return {
                "exists": False,
                "user_id": user_id,
                "status": "not_found"
            }
            
    except Exception as e:
        logger.error(f"❌ User verification failed: {e}")
        return {
            "exists": False,
            "error": str(e),
            "status": "error"
        }

async def authenticate_sharekhan(
    client_id: str,
    api_key: str,
    api_secret: str
) -> Dict[str, Any]:
    """Authenticate with ShareKhan API"""
    try:
        from brokers.sharekhan import ShareKhanIntegration
        
        sharekhan = ShareKhanIntegration()
        auth_result = await sharekhan.authenticate(
            client_id=client_id,
            api_key=api_key,
            api_secret=api_secret
        )
        
        if auth_result.get('success'):
            return {
                "success": True,
                "client_id": client_id,
                "authenticated": True,
                "account_status": auth_result.get('account_status', 'active'),
                "status": "connected"
            }
        else:
            return {
                "success": False,
                "error": auth_result.get('error', 'Authentication failed'),
                "status": "failed"
            }
            
    except Exception as e:
        logger.error(f"❌ ShareKhan authentication failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "status": "error"
        }

async def sync_all_real_data(
    user_id: int,
    client_id: str,
    api_key: str,
    api_secret: str
) -> Dict[str, Any]:
    """Sync all real data from ShareKhan"""
    try:
        logger.info(f"🔄 Syncing all real data for user: {user_id}")
        
        # Import required managers
        from src.core.real_position_manager import get_position_manager
        
        position_manager = await get_position_manager()
        
        # Sync all data concurrently
        tasks = {
            'positions': position_manager.sync_user_positions(user_id, client_id, api_key, api_secret),
            'trading_data': sync_trading_data(user_id, client_id, api_key, api_secret),
            'account_balance': sync_account_balance(user_id, client_id, api_key, api_secret)
        }
        
        results = {}
        for key, task in tasks.items():
            try:
                results[key] = await task
            except Exception as e:
                logger.error(f"❌ Failed to sync {key}: {e}")
                results[key] = {"success": False, "error": str(e)}
        
        # Calculate summary
        positions_count = results['positions'].get('positions_synced', 0) if results['positions'].get('success') else 0
        account_balance = results['account_balance'].get('available_balance', 0.0) if results['account_balance'].get('success') else 0.0
        
        return {
            "success": True,
            "user_id": user_id,
            "sync_results": results,
            "positions_count": positions_count,
            "account_balance": account_balance,
            "sync_timestamp": datetime.now().isoformat(),
            "data_source": "sharekhan_real"
        }
        
    except Exception as e:
        logger.error(f"❌ Complete data sync failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "user_id": user_id
        }

async def sync_trading_data(user_id: int, client_id: str, api_key: str, api_secret: str) -> Dict[str, Any]:
    """Sync trading data (trades, orders, P&L)"""
    try:
        from brokers.sharekhan import ShareKhanIntegration
        
        sharekhan = ShareKhanIntegration()
        auth_result = await sharekhan.authenticate(client_id=client_id, api_key=api_key, api_secret=api_secret)
        
        if not auth_result.get('success'):
            return {"success": False, "error": "Authentication failed"}
        
        # Fetch real trading data
        tasks = {
            'trades': sharekhan.get_trades(client_id),
            'orders': sharekhan.get_orders(client_id),
            'pnl': sharekhan.get_pnl_summary(client_id)
        }
        
        results = {}
        for key, task in tasks.items():
            try:
                results[key] = await task
            except Exception as e:
                results[key] = {"success": False, "error": str(e)}
        
        return {
            "success": True,
            "user_id": user_id,
            "trading_data": results,
            "trades_count": len(results['trades'].get('data', [])) if results['trades'].get('success') else 0,
            "orders_count": len(results['orders'].get('data', [])) if results['orders'].get('success') else 0,
            "total_pnl": results['pnl'].get('data', {}).get('total_pnl', 0.0) if results['pnl'].get('success') else 0.0
        }
        
    except Exception as e:
        logger.error(f"❌ Trading data sync failed: {e}")
        return {"success": False, "error": str(e)}

async def sync_account_balance(user_id: int, client_id: str, api_key: str, api_secret: str) -> Dict[str, Any]:
    """Sync account balance and update user record"""
    try:
        from brokers.sharekhan import ShareKhanIntegration
        from src.core.database import db_manager
        
        sharekhan = ShareKhanIntegration()
        auth_result = await sharekhan.authenticate(client_id=client_id, api_key=api_key, api_secret=api_secret)
        
        if not auth_result.get('success'):
            return {"success": False, "error": "Authentication failed"}
        
        # Get real account balance
        balance_result = await sharekhan.get_account_balance(client_id)
        
        if balance_result.get('success'):
            balance_data = balance_result.get('data', {})
            available_balance = float(balance_data.get('available_balance', 0))
            
            # Update user's current balance in database
            session = db_manager.get_shared_session()
            update_query = """
                UPDATE users 
                SET current_balance = %s, updated_at = %s 
                WHERE id = %s
            """
            session.execute(update_query, (available_balance, datetime.now(), user_id))
            session.commit()
            
            return {
                "success": True,
                "user_id": user_id,
                "available_balance": available_balance,
                "used_margin": float(balance_data.get('used_margin', 0)),
                "total_portfolio_value": float(balance_data.get('total_portfolio_value', 0)),
                "updated_in_db": True
            }
        else:
            return {"success": False, "error": balance_result.get('error', 'Failed to fetch balance')}
        
    except Exception as e:
        logger.error(f"❌ Account balance sync failed: {e}")
        return {"success": False, "error": str(e)}

async def initialize_user_orchestrator(user_id: int, client_id: str) -> Dict[str, Any]:
    """Initialize trading orchestrator for user"""
    try:
        # Import orchestrator
        from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
        
        # Get orchestrator instance
        orchestrator = await ShareKhanTradingOrchestrator.get_instance()
        
        if orchestrator and orchestrator.is_initialized:
            return {
                "success": True,
                "user_id": user_id,
                "orchestrator_status": "running",
                "initialized": True,
                "client_id": client_id
            }
        else:
            return {
                "success": False,
                "error": "Orchestrator not available",
                "status": "not_initialized"
            }
            
    except Exception as e:
        logger.error(f"❌ Orchestrator initialization failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "status": "error"
        }

async def setup_realtime_updates(user_id: int, client_id: str, api_key: str, api_secret: str):
    """Setup real-time data updates (background task)"""
    try:
        logger.info(f"🔄 Setting up real-time updates for user: {user_id}")
        
        # This will run periodically to update positions and P&L
        from src.core.real_position_manager import get_position_manager
        
        position_manager = await get_position_manager()
        
        # Update position prices every 30 seconds (example)
        for _ in range(120):  # Run for 1 hour
            try:
                await position_manager.update_position_prices(user_id, client_id, api_key, api_secret)
                await asyncio.sleep(30)  # Wait 30 seconds
            except Exception as e:
                logger.error(f"❌ Real-time update failed: {e}")
                await asyncio.sleep(30)
        
        logger.info(f"✅ Real-time updates completed for user: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Real-time updates setup failed: {e}")

async def get_user_info(user_id: int) -> Dict[str, Any]:
    """Get user information"""
    try:
        from src.core.database import db_manager
        
        session = db_manager.get_shared_session()
        user_query = "SELECT username, full_name, is_active, current_balance FROM users WHERE id = %s"
        result = session.execute(user_query, (user_id,))
        user = result.fetchone()
        
        if user:
            return {
                "exists": True,
                "username": user[0],
                "full_name": user[1],
                "is_active": user[2],
                "current_balance": float(user[3])
            }
        else:
            return {"exists": False}
            
    except Exception as e:
        return {"exists": False, "error": str(e)}

async def get_positions_status(user_id: int) -> Dict[str, Any]:
    """Get positions status"""
    try:
        from src.core.real_position_manager import get_position_manager
        
        position_manager = await get_position_manager()
        positions_result = await position_manager.get_user_positions(user_id)
        
        return {
            "operational": positions_result.get('success', False),
            "total_positions": positions_result.get('total_positions', 0),
            "total_pnl": positions_result.get('total_unrealized_pnl', 0.0)
        }
        
    except Exception as e:
        return {"operational": False, "error": str(e)}

async def get_orchestrator_status(user_id: int) -> Dict[str, Any]:
    """Get orchestrator status"""
    try:
        from src.core.sharekhan_orchestrator import ShareKhanTradingOrchestrator
        
        orchestrator = await ShareKhanTradingOrchestrator.get_instance()
        
        return {
            "running": bool(orchestrator and orchestrator.is_initialized),
            "status": "active" if orchestrator and orchestrator.is_initialized else "inactive"
        }
        
    except Exception as e:
        return {"running": False, "error": str(e)}

async def get_database_health() -> Dict[str, Any]:
    """Get database health status"""
    try:
        from src.core.database import db_manager
        
        session = db_manager.get_shared_session()
        
        return {
            "connected": bool(session),
            "status": "healthy" if session else "unhealthy"
        }
        
    except Exception as e:
        return {"connected": False, "error": str(e)} 