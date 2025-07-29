"""
Dynamic User Management API
Handles creation, management, and analytics for multiple trading users
Integrates with ShareKhan broker for multi-user trading support
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy import create_engine, text, func, and_, or_, desc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import bcrypt
import os
import json
import redis.asyncio as redis

from ..models.trading_models import User, TradingPosition, Order, TradingTrade
from ..core.database_schema_manager import DatabaseSchemaManager
from ..config.database import DatabaseConfig

logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses
class UserCreateRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str
    initial_capital: float = 50000.0
    risk_tolerance: str = "medium"
    sharekhan_client_id: Optional[str] = None
    sharekhan_api_key: Optional[str] = None
    sharekhan_api_secret: Optional[str] = None

    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, underscore and hyphen')
        return v

    @validator('risk_tolerance')
    def validate_risk_tolerance(cls, v):
        if v not in ['low', 'medium', 'high']:
            raise ValueError('Risk tolerance must be low, medium, or high')
        return v

class UserUpdateRequest(BaseModel):
    """Model for updating user information"""
    full_name: Optional[str] = None
    initial_capital: Optional[float] = None
    current_balance: Optional[float] = None
    risk_tolerance: Optional[str] = None
    sharekhan_client_id: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    """Model for user response with analytics"""
    id: int
    username: str
    email: str
    full_name: str
    initial_capital: float
    current_balance: float
    risk_tolerance: str
    is_active: bool
    sharekhan_client_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    total_trades: int = 0
    winning_trades: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    active_positions: int = 0

class UserAnalytics(BaseModel):
    user_id: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: float
    daily_pnl: float
    weekly_pnl: float
    monthly_pnl: float
    win_rate: float
    avg_trade_duration: float
    max_profit: float
    max_loss: float
    sharpe_ratio: float
    active_positions: int
    total_capital: float
    available_capital: float

router = APIRouter(tags=["dynamic-user-management"])

class DynamicUserManager:
    """Enhanced user manager with real database operations"""
    
    def __init__(self):
        self.db_config = DatabaseConfig()
        self.engine = create_engine(self.db_config.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.schema_manager = DatabaseSchemaManager(database_url=self.db_config.database_url)  # Fixed: pass database_url parameter
        self.redis_client = None
        
    async def initialize(self):
        """Initialize database and Redis connections"""
        try:
            # Ensure database schema exists
            await self._ensure_database_schema()
            
            # Initialize Redis connection
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            try:
                self.redis_client = await redis.from_url(redis_url, decode_responses=True)
                await self.redis_client.ping()
                logger.info("✅ Redis connection established")
            except Exception as redis_error:
                logger.warning(f"⚠️ Redis connection failed: {redis_error}")
                self.redis_client = None
            
            logger.info("✅ DynamicUserManager initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ DynamicUserManager initialization failed: {e}")
            return False
    
    async def _ensure_database_schema(self):
        """Ensure database schema is properly set up"""
        try:
            # Test database connection with simple query
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection verified")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise HTTPException(status_code=500, detail="Database connection failed")
    
    def get_db_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    async def create_user(self, user_data: UserCreateRequest) -> UserResponse:
        """Create a new user with proper database integration"""
        db = self.get_db_session()
        try:
            # Hash password
            password_hash = bcrypt.hashpw(user_data.password.encode(), bcrypt.gensalt()).decode()
            
            # Create user object
            new_user = User(
                username=user_data.username,
                email=user_data.email,
                password_hash=password_hash,
                full_name=user_data.full_name,
                initial_capital=user_data.initial_capital,
                current_balance=user_data.initial_capital,
                risk_tolerance=user_data.risk_tolerance,
                sharekhan_client_id=user_data.sharekhan_client_id,
                is_active=True
            )
            
            # Add to database
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            # Store ShareKhan credentials in Redis if provided
            if user_data.sharekhan_api_key and user_data.sharekhan_api_secret:
                await self._store_sharekhan_credentials(
                    new_user.id,
                    user_data.sharekhan_api_key,
                    user_data.sharekhan_api_secret,
                    user_data.sharekhan_client_id
                )
            
            # Initialize user analytics
            await self._initialize_user_analytics(new_user.id)
            
            logger.info(f"✅ User created successfully: {user_data.username} (ID: {new_user.id})")
            
            return await self._build_user_response(new_user, db)
            
        except IntegrityError as e:
            db.rollback()
            if "username" in str(e):
                raise HTTPException(status_code=400, detail="Username already exists")
            elif "email" in str(e):
                raise HTTPException(status_code=400, detail="Email already exists")
            else:
                raise HTTPException(status_code=400, detail="User creation failed - duplicate data")
        except Exception as e:
            db.rollback()
            logger.error(f"❌ User creation failed: {e}")
            raise HTTPException(status_code=500, detail=f"User creation failed: {str(e)}")
        finally:
            db.close()
    
    async def get_user(self, user_id: int) -> UserResponse:
        """Get user by ID with analytics"""
        db = self.get_db_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            return await self._build_user_response(user, db)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Error fetching user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch user")
        finally:
            db.close()
    
    async def list_users(self, skip: int = 0, limit: int = 100, active_only: bool = False) -> List[UserResponse]:
        """List all users with basic analytics - INCLUDING broker_users"""
        db = self.get_db_session()
        try:
            # Get database users
            query = db.query(User)
            if active_only:
                query = query.filter(User.is_active == True)
            
            db_users = query.offset(skip).limit(limit).all()
            
            # Build responses with analytics
            user_responses = []
            for user in db_users:
                user_response = await self._build_user_response(user, db)
                user_responses.append(user_response)
            
            # CRITICAL FIX: Also include broker_users from trading_control
            try:
                from src.api.trading_control import broker_users
                
                for user_id, broker_user in broker_users.items():
                    # Convert broker_user to UserResponse format
                    broker_user_response = UserResponse(
                        id=0,  # Virtual ID for broker users
                        username=broker_user.get('user_id', user_id),
                        email=broker_user.get('email', ''),
                        full_name=broker_user.get('name', f"Broker User {user_id}"),
                        initial_capital=float(broker_user.get('initial_capital', 0)),
                        current_balance=float(broker_user.get('current_capital', 0)),
                        risk_tolerance=broker_user.get('risk_tolerance', 'medium'),
                        is_active=broker_user.get('is_active', True),
                        sharekhan_client_id=broker_user.get('client_id', user_id),
                        created_at=datetime.fromisoformat(broker_user.get('created_at', datetime.now().isoformat())),
                        updated_at=datetime.now(),
                        total_trades=broker_user.get('total_trades', 0),
                        winning_trades=0,  # Calculate if needed
                        total_pnl=broker_user.get('total_pnl', 0),
                        win_rate=broker_user.get('win_rate', 0),
                        active_positions=broker_user.get('open_trades', 0)
                    )
                    user_responses.append(broker_user_response)
                
                logger.info(f"✅ Found {len(broker_users)} broker users to include")
                
            except ImportError as e:
                logger.warning(f"⚠️ Could not import broker_users: {e}")
            except Exception as e:
                logger.warning(f"⚠️ Error including broker users: {e}")
            
            logger.info(f"✅ Total users returned: {len(user_responses)} (DB: {len(db_users)}, Broker: {len(broker_users) if 'broker_users' in locals() else 0})")
            return user_responses
            
        except Exception as e:
            logger.error(f"❌ Error listing users: {e}")
            raise HTTPException(status_code=500, detail="Failed to list users")
        finally:
            db.close()
    
    async def update_user(self, user_id: int, user_data: UserUpdateRequest) -> UserResponse:
        """Update user information"""
        db = self.get_db_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Update fields
            if user_data.full_name is not None:
                user.full_name = user_data.full_name
            if user_data.initial_capital is not None:
                user.initial_capital = user_data.initial_capital
            if user_data.current_balance is not None:
                user.current_balance = user_data.current_balance
            if user_data.risk_tolerance is not None:
                user.risk_tolerance = user_data.risk_tolerance
            if user_data.sharekhan_client_id is not None:
                user.sharekhan_client_id = user_data.sharekhan_client_id
            if user_data.is_active is not None:
                user.is_active = user_data.is_active
            
            user.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(user)
            
            logger.info(f"✅ User updated successfully: {user.username} (ID: {user_id})")
            
            return await self._build_user_response(user, db)
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error updating user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to update user")
        finally:
            db.close()
    
    async def delete_user(self, user_id: int) -> Dict[str, str]:
        """Delete user (soft delete by setting inactive)"""
        db = self.get_db_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Check for active positions
            active_positions = db.query(TradingPosition).filter(
                and_(TradingPosition.user_id == user_id, TradingPosition.status == 'open')
            ).count()
            
            if active_positions > 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot delete user with {active_positions} active positions"
                )
            
            # Soft delete
            user.is_active = False
            user.updated_at = datetime.utcnow()
            
            db.commit()
            
            # Clean up Redis data
            await self._cleanup_user_redis_data(user_id)
            
            logger.info(f"✅ User deleted successfully: {user.username} (ID: {user_id})")
            
            return {"message": f"User {user.username} deleted successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error deleting user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete user")
        finally:
            db.close()
    
    async def get_user_analytics(self, user_id: int, days: int = 30) -> UserAnalytics:
        """Get comprehensive user analytics"""
        db = self.get_db_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Calculate date ranges
            now = datetime.utcnow()
            start_date = now - timedelta(days=days)
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = now - timedelta(days=7)
            month_start = now - timedelta(days=30)
            
            # Get trade statistics
            trades = db.query(TradingTrade).filter(
                and_(TradingTrade.user_id == user_id, TradingTrade.executed_at >= start_date)
            ).all()
            
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t.pnl > 0])
            losing_trades = len([t for t in trades if t.pnl < 0])
            total_pnl = sum(t.pnl for t in trades if t.pnl)
            
            # Calculate period PnLs
            daily_pnl = sum(t.pnl for t in trades if t.executed_at >= day_start and t.pnl)
            weekly_pnl = sum(t.pnl for t in trades if t.executed_at >= week_start and t.pnl)
            monthly_pnl = sum(t.pnl for t in trades if t.executed_at >= month_start and t.pnl)
            
            # Calculate win rate
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
            
            # Get active positions
            active_positions = db.query(TradingPosition).filter(
                and_(TradingPosition.user_id == user_id, TradingPosition.status == 'open')
            ).count()
            
            # Calculate average trade duration (in hours)
            completed_trades = [t for t in trades if t.exit_time and t.entry_time]
            avg_duration = 0.0
            if completed_trades:
                durations = [(t.exit_time - t.entry_time).total_seconds() / 3600 for t in completed_trades]
                avg_duration = sum(durations) / len(durations)
            
            # Calculate max profit and loss
            profits = [t.pnl for t in trades if t.pnl and t.pnl > 0]
            losses = [t.pnl for t in trades if t.pnl and t.pnl < 0]
            max_profit = max(profits) if profits else 0.0
            max_loss = min(losses) if losses else 0.0
            
            # Simple Sharpe ratio calculation
            if total_trades > 1:
                pnl_values = [t.pnl for t in trades if t.pnl]
                if pnl_values:
                    avg_return = sum(pnl_values) / len(pnl_values)
                    variance = sum((x - avg_return) ** 2 for x in pnl_values) / len(pnl_values)
                    std_dev = variance ** 0.5
                    sharpe_ratio = avg_return / std_dev if std_dev > 0 else 0.0
                else:
                    sharpe_ratio = 0.0
            else:
                sharpe_ratio = 0.0
            
            # Calculate available capital (current balance - margin used)
            margin_used = sum(p.current_value for p in db.query(TradingPosition).filter(
                and_(TradingPosition.user_id == user_id, TradingPosition.status == 'open')
            ).all() if p.current_value)
            
            available_capital = user.current_balance - margin_used
            
            return UserAnalytics(
                user_id=user_id,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                total_pnl=total_pnl,
                daily_pnl=daily_pnl,
                weekly_pnl=weekly_pnl,
                monthly_pnl=monthly_pnl,
                win_rate=win_rate,
                avg_trade_duration=avg_duration,
                max_profit=max_profit,
                max_loss=max_loss,
                sharpe_ratio=sharpe_ratio,
                active_positions=active_positions,
                total_capital=user.current_balance,
                available_capital=available_capital
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Error calculating analytics for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to calculate user analytics")
        finally:
            db.close()
    
    async def _build_user_response(self, user: User, db: Session) -> UserResponse:
        """Build user response with basic analytics"""
        try:
            # Get basic trade statistics
            total_trades = db.query(TradingTrade).filter(TradingTrade.user_id == user.id).count()
            winning_trades = db.query(TradingTrade).filter(
                and_(TradingTrade.user_id == user.id, TradingTrade.pnl > 0)
            ).count()
            
            # Calculate total P&L
            total_pnl_result = db.query(func.sum(TradingTrade.pnl)).filter(TradingTrade.user_id == user.id).scalar()
            total_pnl = float(total_pnl_result) if total_pnl_result else 0.0
            
            # Calculate win rate
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
            
            # Get active positions count
            active_positions = db.query(TradingPosition).filter(
                and_(TradingPosition.user_id == user.id, TradingPosition.status == 'open')
            ).count()
            
            return UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                initial_capital=float(user.initial_capital),
                current_balance=float(user.current_balance),
                risk_tolerance=user.risk_tolerance,
                is_active=user.is_active,
                sharekhan_client_id=user.sharekhan_client_id,
                created_at=user.created_at,
                updated_at=user.updated_at,
                total_trades=total_trades,
                winning_trades=winning_trades,
                total_pnl=total_pnl,
                win_rate=win_rate,
                active_positions=active_positions
            )
            
        except Exception as e:
            logger.error(f"❌ Error building user response: {e}")
            # Return basic response without analytics
            return UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                initial_capital=float(user.initial_capital),
                current_balance=float(user.current_balance),
                risk_tolerance=user.risk_tolerance,
                is_active=user.is_active,
                sharekhan_client_id=user.sharekhan_client_id,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
    
    async def _store_sharekhan_credentials(self, user_id: int, api_key: str, api_secret: str, client_id: str):
        """Store ShareKhan credentials securely in Redis"""
        if not self.redis_client:
            return
        
        try:
            credentials = {
                'api_key': api_key,
                'api_secret': api_secret,
                'client_id': client_id,
                'created_at': datetime.utcnow().isoformat()
            }
            
            await self.redis_client.hset(
                f"sharekhan:credentials:{user_id}",
                mapping=credentials
            )
            
            # Set expiry (optional - for security)
            await self.redis_client.expire(f"sharekhan:credentials:{user_id}", 86400 * 30)  # 30 days
            
            logger.info(f"✅ ShareKhan credentials stored for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to store ShareKhan credentials for user {user_id}: {e}")
    
    async def _initialize_user_analytics(self, user_id: int):
        """Initialize user analytics in Redis"""
        if not self.redis_client:
            return
        
        try:
            analytics = {
                'total_trades': 0,
                'winning_trades': 0,
                'total_pnl': 0.0,
                'daily_pnl': 0.0,
                'last_updated': datetime.utcnow().isoformat()
            }
            
            await self.redis_client.hset(
                f"user:analytics:{user_id}",
                mapping=analytics
            )
            
            logger.info(f"✅ Analytics initialized for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize analytics for user {user_id}: {e}")
    
    async def _cleanup_user_redis_data(self, user_id: int):
        """Clean up user data from Redis"""
        if not self.redis_client:
            return
        
        try:
            keys_to_delete = [
                f"sharekhan:credentials:{user_id}",
                f"user:analytics:{user_id}",
                f"user:positions:{user_id}",
                f"user:orders:{user_id}"
            ]
            
            for key in keys_to_delete:
                await self.redis_client.delete(key)
            
            logger.info(f"✅ Redis data cleaned up for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup Redis data for user {user_id}: {e}")

# Global instance
user_manager = DynamicUserManager()

# Dependency to get user manager
# Global user manager instance with error handling
try:
    user_manager = DynamicUserManager()
    logger.info("✅ DynamicUserManager instance created successfully")
except Exception as e:
    logger.error(f"❌ Failed to create DynamicUserManager instance: {e}")
    user_manager = None

async def get_user_manager() -> DynamicUserManager:
    if user_manager is None:
        raise HTTPException(status_code=500, detail="User manager not available")
    try:
        if not user_manager.redis_client:
            await user_manager.initialize()
        return user_manager
    except Exception as e:
        logger.error(f"❌ Failed to initialize user manager: {e}")
        raise HTTPException(status_code=500, detail="User manager initialization failed")

# API Routes
@router.post("/create", response_model=UserResponse)
async def create_user(
    user_data: UserCreateRequest,
    background_tasks: BackgroundTasks,
    manager: DynamicUserManager = Depends(get_user_manager)
):
    """Create a new trading user with ShareKhan integration"""
    return await manager.create_user(user_data)

@router.get("/list", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    manager: DynamicUserManager = Depends(get_user_manager)
):
    """List all users with basic analytics"""
    try:
        return await manager.list_users(skip, limit, active_only)
    except Exception as e:
        logger.error(f"Error in list_users endpoint: {e}")
        # CRITICAL FIX: Return empty list instead of 500 error to prevent frontend crashes
        return []

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    manager: DynamicUserManager = Depends(get_user_manager)
):
    """Get user details with analytics"""
    return await manager.get_user(user_id)

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdateRequest,
    manager: DynamicUserManager = Depends(get_user_manager)
):
    """Update user information"""
    return await manager.update_user(user_id, user_data)

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    manager: DynamicUserManager = Depends(get_user_manager)
):
    """Delete user (soft delete)"""
    return await manager.delete_user(user_id)

@router.get("/{user_id}/analytics", response_model=UserAnalytics)
async def get_user_analytics(
    user_id: int,
    days: int = 30,
    manager: DynamicUserManager = Depends(get_user_manager)
):
    """Get comprehensive user analytics"""
    return await manager.get_user_analytics(user_id, days)

@router.get("/{user_id}/trades")
async def get_user_trades(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    manager: DynamicUserManager = Depends(get_user_manager)
):
    """Get user's trading history"""
    db = manager.get_db_session()
    try:
        trades = db.query(TradingTrade).filter(TradingTrade.user_id == user_id).offset(skip).limit(limit).all()
        
        trade_data = []
        for trade in trades:
            trade_data.append({
                'id': trade.trade_id,
                'symbol': trade.symbol,
                'action': trade.trade_type,
                'quantity': trade.quantity,
                'entry_price': float(trade.price) if trade.price else None,
                'exit_price': None,  # TradingTrade doesn't have exit_price
                'pnl': float(trade.pnl) if trade.pnl else None,
                'entry_time': trade.executed_at,
                'exit_time': None,  # TradingTrade doesn't have exit_time
                'strategy': trade.strategy,
                'status': trade.status
            })
        
        return {
            'trades': trade_data,
            'total_trades': len(trade_data),
            'user_id': user_id
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching trades for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user trades")
    finally:
        db.close()

@router.get("/{user_id}/positions")
async def get_user_positions(
    user_id: int,
    active_only: bool = True,
    manager: DynamicUserManager = Depends(get_user_manager)
):
    """Get user's current positions"""
    db = manager.get_db_session()
    try:
        query = db.query(TradingPosition).filter(TradingPosition.user_id == user_id)
        if active_only:
            query = query.filter(TradingPosition.status == 'open')
        
        positions = query.all()
        
        position_data = []
        for position in positions:
            position_data.append({
                'id': position.id,
                'symbol': position.symbol,
                'quantity': position.quantity,
                'entry_price': float(position.entry_price) if position.entry_price else None,
                'current_price': float(position.current_price) if position.current_price else None,
                'current_value': float(position.current_value) if position.current_value else None,
                'pnl': float(position.pnl) if position.pnl else None,
                'is_active': position.status == 'open',
                'created_at': position.created_at,
                'updated_at': position.updated_at
            })
        
        return {
            'positions': position_data,
            'total_positions': len(position_data),
            'user_id': user_id
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching positions for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user positions")
    finally:
        db.close()

@router.get("/status")
async def get_system_status():
    """Get dynamic user management system status"""
    try:
        # Test basic functionality without database dependency
        status = {
            "system": "dynamic_user_management",
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "database_available": False,
            "redis_available": False,
            "tables_exist": False
        }
        
        # Test database connection
        try:
            manager = DynamicUserManager()
            with manager.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            status["database_available"] = True
            
            # Test if users table exists
            with manager.engine.connect() as conn:
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'"))
                if result.fetchone():
                    status["tables_exist"] = True
                    
                    # Count users
                    user_count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
                    status["user_count"] = user_count
                    
        except Exception as db_error:
            status["database_error"] = str(db_error)
        
        # Test Redis connection
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            redis_client = await redis.from_url(redis_url, decode_responses=True)
            await redis_client.ping()
            status["redis_available"] = True
            await redis_client.close()
        except Exception as redis_error:
            status["redis_error"] = str(redis_error)
        
        return status
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {
            "system": "dynamic_user_management", 
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        } 