"""
Simple User Management API for ShareKhan Trading System
Creates basic user records without storing credentials
100% REAL DATA from ShareKhan API
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["simple-user-management"])

class SimpleUserCreate(BaseModel):
    """Simple user creation model - NO CREDENTIALS STORED"""
    username: str
    full_name: str
    email: str
    initial_capital: float = 100000.00
    risk_tolerance: str = "medium"  # low, medium, high
    max_position_size: float = 50000.00
    max_daily_trades: int = 50
    # Note: No ShareKhan credentials stored here

class UserResponse(BaseModel):
    """User response model"""
    success: bool
    user_id: int
    username: str
    full_name: str
    email: str
    initial_capital: float
    current_balance: float
    is_active: bool
    trading_enabled: bool
    created_at: str
    message: str

@router.post("/create", response_model=UserResponse)
async def create_simple_user(user_data: SimpleUserCreate):
    """
    Create a simple user record in database (no credentials stored)
    User credentials will be provided separately when needed
    """
    try:
        logger.info(f"🚀 Creating simple user: {user_data.username}")
        
        # Create user in database
        from src.core.database import get_database_session
        
        session = get_database_session()
        if not session:
            raise HTTPException(status_code=503, detail="Database connection not available")
        
        # Insert user without credentials
        user_insert_query = """
            INSERT INTO users (
                username, email, full_name, 
                initial_capital, current_balance, risk_tolerance,
                is_active, trading_enabled, 
                max_daily_trades, max_position_size, 
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id, username, email, full_name, initial_capital, 
                       current_balance, is_active, trading_enabled, created_at
        """
        
        user_data_tuple = (
            user_data.username,
            user_data.email,
            user_data.full_name,
            user_data.initial_capital,
            user_data.initial_capital,  # current_balance = initial_capital initially
            user_data.risk_tolerance,
            True,  # is_active
            True,  # trading_enabled
            user_data.max_daily_trades,
            user_data.max_position_size,
            datetime.now(),
            datetime.now()
        )
        
        result = session.execute(user_insert_query, user_data_tuple)
        new_user = result.fetchone()
        session.commit()
        
        if not new_user:
            raise RuntimeError("Failed to create user in database")
        
        user_id = new_user[0]
        logger.info(f"✅ Simple user created: {user_data.username} (ID: {user_id})")
        
        return UserResponse(
            success=True,
            user_id=user_id,
            username=new_user[1],
            full_name=new_user[3],
            email=new_user[2],
            initial_capital=float(new_user[4]),
            current_balance=float(new_user[5]),
            is_active=new_user[6],
            trading_enabled=new_user[7],
            created_at=new_user[8].isoformat(),
            message=f"User {user_data.username} created successfully. Provide ShareKhan credentials when starting trading."
        )
        
    except Exception as e:
        logger.error(f"❌ User creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"User creation failed: {str(e)}")

@router.get("/list")
async def list_all_users():
    """Get list of all users"""
    try:
        from src.core.database import get_database_session
        
        session = get_database_session()
        if not session:
            raise HTTPException(status_code=503, detail="Database connection not available")
        
        users_query = """
            SELECT id, username, email, full_name, current_balance, 
                   is_active, trading_enabled, created_at, updated_at
            FROM users 
            ORDER BY created_at DESC
        """
        
        result = session.execute(users_query)
        users = result.fetchall()
        
        users_list = []
        for user in users:
            users_list.append({
                "user_id": user[0],
                "username": user[1],
                "email": user[2],
                "full_name": user[3],
                "current_balance": float(user[4]),
                "is_active": user[5],
                "trading_enabled": user[6],
                "created_at": user[7].isoformat(),
                "last_updated": user[8].isoformat()
            })
        
        return {
            "success": True,
            "data": users_list,
            "total_users": len(users_list),
            "source": "database"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to list users: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}")
async def get_user_details(user_id: int):
    """Get specific user details"""
    try:
        from src.core.database import get_database_session
        
        session = get_database_session()
        user_query = """
            SELECT id, username, email, full_name, initial_capital, 
                   current_balance, risk_tolerance, is_active, trading_enabled,
                   max_daily_trades, max_position_size, created_at, updated_at
            FROM users WHERE id = %s
        """
        
        result = session.execute(user_query, (user_id,))
        user = result.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "success": True,
            "data": {
                "user_id": user[0],
                "username": user[1],
                "email": user[2],
                "full_name": user[3],
                "initial_capital": float(user[4]),
                "current_balance": float(user[5]),
                "risk_tolerance": user[6],
                "is_active": user[7],
                "trading_enabled": user[8],
                "max_daily_trades": user[9],
                "max_position_size": float(user[10]),
                "created_at": user[11].isoformat(),
                "last_updated": user[12].isoformat()
            },
            "source": "database"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get user details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}/trading-data")
async def get_user_trading_data(
    user_id: int,
    sharekhan_client_id: str,
    sharekhan_api_key: str,
    sharekhan_api_secret: str
):
    """
    Get real trading data from ShareKhan for a user
    Credentials provided at runtime, not stored
    """
    try:
        logger.info(f"📊 Fetching real trading data for user: {user_id}")
        
        # Verify user exists
        from src.core.database import get_database_session
        session = get_database_session()
        
        user_check = session.execute("SELECT username, full_name FROM users WHERE id = %s", (user_id,))
        user = user_check.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Import real ShareKhan client
        from brokers.sharekhan import ShareKhanIntegration
        
        # Initialize ShareKhan with provided credentials
        sharekhan = ShareKhanIntegration()
        auth_result = await sharekhan.authenticate(
            client_id=sharekhan_client_id,
            api_key=sharekhan_api_key,
            api_secret=sharekhan_api_secret
        )
        
        if not auth_result.get('success'):
            raise HTTPException(
                status_code=401, 
                detail=f"ShareKhan authentication failed: {auth_result.get('error')}"
            )
        
        # Fetch real trading data
        trading_data = await fetch_comprehensive_trading_data(sharekhan, sharekhan_client_id)
        
        # Update user's current balance with real data
        if trading_data.get('account_balance'):
            update_query = """
                UPDATE users 
                SET current_balance = %s, updated_at = %s 
                WHERE id = %s
            """
            session.execute(update_query, (
                trading_data['account_balance']['available_balance'], 
                datetime.now(), 
                user_id
            ))
            session.commit()
        
        return {
            "success": True,
            "user_id": user_id,
            "username": user[0],
            "full_name": user[1],
            "data": trading_data,
            "source": "sharekhan_live",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get trading data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def fetch_comprehensive_trading_data(sharekhan, client_id: str) -> Dict[str, Any]:
    """Fetch comprehensive trading data from ShareKhan"""
    try:
        logger.info(f"📊 Fetching comprehensive data for client: {client_id}")
        
        # Fetch all real data in parallel
        import asyncio
        
        tasks = {
            'account_balance': sharekhan.get_account_balance(client_id),
            'positions': sharekhan.get_positions(client_id),
            'trades': sharekhan.get_trades(client_id),
            'pnl': sharekhan.get_pnl_summary(client_id),
            'orders': sharekhan.get_orders(client_id),
            'funds': sharekhan.get_funds(client_id),
            'holdings': sharekhan.get_holdings(client_id)
        }
        
        # Execute all requests concurrently
        results = {}
        for key, task in tasks.items():
            try:
                results[key] = await task
            except Exception as e:
                logger.error(f"❌ Failed to fetch {key}: {e}")
                results[key] = {"error": str(e), "data": []}
        
        # Calculate summary metrics
        summary = calculate_trading_summary(results)
        
        return {
            "account_balance": results.get('account_balance', {}),
            "positions": results.get('positions', {}),
            "trades": results.get('trades', {}),
            "pnl": results.get('pnl', {}),
            "orders": results.get('orders', {}),
            "funds": results.get('funds', {}),
            "holdings": results.get('holdings', {}),
            "summary": summary,
            "data_source": "sharekhan_real_time"
        }
        
    except Exception as e:
        logger.error(f"❌ Comprehensive data fetch failed: {e}")
        return {"error": str(e)}

def calculate_trading_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate trading summary from real data"""
    try:
        summary = {
            "total_pnl": 0.0,
            "day_pnl": 0.0,
            "total_trades": 0,
            "open_positions": 0,
            "pending_orders": 0,
            "available_balance": 0.0,
            "used_margin": 0.0,
            "portfolio_value": 0.0
        }
        
        # Calculate from real data
        if data.get('pnl') and 'data' in data['pnl']:
            pnl_data = data['pnl']['data']
            summary['total_pnl'] = float(pnl_data.get('total_pnl', 0))
            summary['day_pnl'] = float(pnl_data.get('day_pnl', 0))
        
        if data.get('trades') and 'data' in data['trades']:
            summary['total_trades'] = len(data['trades']['data'])
        
        if data.get('positions') and 'data' in data['positions']:
            summary['open_positions'] = len([p for p in data['positions']['data'] if p.get('quantity', 0) != 0])
        
        if data.get('orders') and 'data' in data['orders']:
            summary['pending_orders'] = len([o for o in data['orders']['data'] if o.get('status') in ['PENDING', 'OPEN']])
        
        if data.get('account_balance') and 'data' in data['account_balance']:
            balance_data = data['account_balance']['data']
            summary['available_balance'] = float(balance_data.get('available_balance', 0))
            summary['used_margin'] = float(balance_data.get('used_margin', 0))
            summary['portfolio_value'] = float(balance_data.get('total_portfolio_value', 0))
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Summary calculation failed: {e}")
        return {"error": str(e)}

@router.post("/{user_id}/sync-positions")
async def sync_user_positions(
    user_id: int,
    sharekhan_client_id: str,
    sharekhan_api_key: str,
    sharekhan_api_secret: str
):
    """Sync real positions from ShareKhan for a user"""
    try:
        from src.core.real_position_manager import get_position_manager
        
        position_manager = await get_position_manager()
        
        sync_result = await position_manager.sync_user_positions(
            user_id=user_id,
            sharekhan_client_id=sharekhan_client_id,
            sharekhan_api_key=sharekhan_api_key,
            sharekhan_api_secret=sharekhan_api_secret
        )
        
        return sync_result
        
    except Exception as e:
        logger.error(f"❌ Position sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}/positions")
async def get_user_positions(user_id: int):
    """Get user positions from database"""
    try:
        from src.core.real_position_manager import get_position_manager
        
        position_manager = await get_position_manager()
        positions_result = await position_manager.get_user_positions(user_id)
        
        return positions_result
        
    except Exception as e:
        logger.error(f"❌ Failed to get positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{user_id}/update-position-prices")
async def update_position_prices(
    user_id: int,
    sharekhan_client_id: str,
    sharekhan_api_key: str,
    sharekhan_api_secret: str
):
    """Update current prices and P&L for user positions"""
    try:
        from src.core.real_position_manager import get_position_manager
        
        position_manager = await get_position_manager()
        
        update_result = await position_manager.update_position_prices(
            user_id=user_id,
            sharekhan_client_id=sharekhan_client_id,
            sharekhan_api_key=sharekhan_api_key,
            sharekhan_api_secret=sharekhan_api_secret
        )
        
        return update_result
        
    except Exception as e:
        logger.error(f"❌ Position price update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{user_id}")
async def delete_user(user_id: int):
    """Delete a user (for testing/cleanup)"""
    try:
        from src.core.database import get_database_session
        
        session = get_database_session()
        
        # Check if user exists
        user_check = session.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        user = user_check.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete user (CASCADE will handle related records)
        delete_query = "DELETE FROM users WHERE id = %s"
        session.execute(delete_query, (user_id,))
        session.commit()
        
        logger.info(f"✅ User deleted: {user[0]} (ID: {user_id})")
        
        return {
            "success": True,
            "message": f"User {user[0]} (ID: {user_id}) deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete user: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 