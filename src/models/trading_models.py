"""
SQLAlchemy models for trading system data storage.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict
from enum import Enum
import uuid

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    Text, JSON, ForeignKey, Index, DECIMAL, BigInteger
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.config.database import Base
from pydantic import BaseModel, Field

class PositionStatus(str, Enum):
    """Position status enum"""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    CLOSED = "closed"
    REJECTED = "rejected"

class PositionModel(BaseModel):
    """Position model for tracking trades"""
    position_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    quantity: int
    entry_price: float
    exit_price: Optional[float] = None
    current_price: Optional[float] = None
    entry_time: datetime = Field(default_factory=datetime.now)
    exit_time: Optional[datetime] = None
    status: PositionStatus = PositionStatus.PENDING
    strategy: str
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    pnl_percent: float = 0.0
    current_risk: float = 0.0
    
    def update_pnl(self, current_price: float):
        """Update PnL based on current price"""
        self.current_price = current_price
        if self.entry_price and self.quantity:
            self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
            self.pnl_percent = ((current_price - self.entry_price) / self.entry_price) * 100
    
    def close(self, exit_price: float):
        """Close position and calculate realized PnL"""
        self.exit_price = exit_price
        self.exit_time = datetime.now()
        self.status = PositionStatus.CLOSED
        if self.entry_price and self.quantity:
            self.realized_pnl = (exit_price - self.entry_price) * self.quantity
            self.unrealized_pnl = 0.0
    
    def to_dict(self) -> Dict:
        """Convert position to dictionary"""
        return {
            'position_id': self.position_id,
            'symbol': self.symbol,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'current_price': self.current_price,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'status': self.status.value,
            'strategy': self.strategy,
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': self.unrealized_pnl,
            'pnl_percent': self.pnl_percent,
            'current_risk': self.current_risk
        }

class User(Base):
    """User accounts and authentication"""
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(200))
    initial_capital = Column(DECIMAL(15,2), default=50000)
    current_balance = Column(DECIMAL(15,2), default=50000)
    risk_tolerance = Column(String(20), default='medium')
    is_active = Column(Boolean, default=True)
    sharekhan_client_id = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships - FIXED: Use proper SQLAlchemy class names
    # Note: These reference the SQLAlchemy models defined later in this file
    trades = relationship("TradingTrade", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    risk_metrics = relationship("RiskMetric", back_populates="user")

class Portfolio(Base):
    """User portfolios and holdings"""
    __tablename__ = "portfolios"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    initial_balance = Column(DECIMAL(15, 2), nullable=False)
    current_balance = Column(DECIMAL(15, 2), nullable=False)
    total_pnl = Column(DECIMAL(15, 2), default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="portfolios")
    positions = relationship("TradingPosition", back_populates="portfolio")
    trades = relationship("TradingTrade", back_populates="portfolio")

class Stock(Base):
    """Stock/Symbol master data"""
    __tablename__ = "stocks"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)
    company_name = Column(String(200))
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap = Column(BigInteger)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    market_data = relationship("MarketData", back_populates="stock")
    positions = relationship("TradingPosition", back_populates="stock")
    trades = relationship("TradingTrade", back_populates="stock")
    recommendations = relationship("Recommendation", back_populates="stock")

class MarketData(Base):
    """Historical and real-time market data"""
    __tablename__ = "market_data"
    __table_args__ = (
        Index('ix_market_data_stock_timestamp', 'stock_id', 'timestamp'),
        {'extend_existing': True}
    )
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    open_price = Column(DECIMAL(10, 4))
    high_price = Column(DECIMAL(10, 4))
    low_price = Column(DECIMAL(10, 4))
    close_price = Column(DECIMAL(10, 4), nullable=False)
    volume = Column(BigInteger)
    adjusted_close = Column(DECIMAL(10, 4))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    stock = relationship("Stock", back_populates="market_data")

class TradingPosition(Base):
    """Trading positions"""
    __tablename__ = "positions"
    __table_args__ = {'extend_existing': True}
    
    position_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False)
    entry_price = Column(DECIMAL(10,2), nullable=False)
    current_price = Column(DECIMAL(10,2))
    entry_time = Column(DateTime(timezone=True), server_default=func.now())
    exit_time = Column(DateTime(timezone=True))
    strategy = Column(String(50))
    status = Column(String(20), default='open')
    unrealized_pnl = Column(DECIMAL(12,2))
    realized_pnl = Column(DECIMAL(12,2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships - FIXED: Remove circular reference
    user = relationship("User")
    trades = relationship("Trade", back_populates="position")

class TradingTrade(Base):  # FIXED: Renamed to avoid conflict with Pydantic Trade
    """Trading transactions"""
    __tablename__ = "trades"
    __table_args__ = {'extend_existing': True}
    
    trade_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    position_id = Column(Integer, ForeignKey("positions.position_id"))
    symbol = Column(String(20), nullable=False)
    trade_type = Column(String(10), nullable=False)  # 'buy' or 'sell'
    quantity = Column(Integer, nullable=False)
    price = Column(DECIMAL(10,2), nullable=False)
    order_id = Column(String(50))
    strategy = Column(String(50))
    commission = Column(DECIMAL(8,2), default=0)
    pnl = Column(DECIMAL(12,2), default=0)
    pnl_percent = Column(DECIMAL(6,2), default=0) 
    status = Column(String(20), default='EXECUTED')
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="trades")
    position = relationship("TradingPosition", back_populates="trades")

class Order(Base):
    """Trading orders"""
    __tablename__ = "orders"
    __table_args__ = {'extend_existing': True}
    
    order_id = Column(String(50), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    broker_order_id = Column(String(100))
    parent_order_id = Column(String(50))
    symbol = Column(String(20), nullable=False)
    order_type = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(DECIMAL(10,2))
    stop_price = Column(DECIMAL(10,2))
    filled_quantity = Column(Integer, default=0)
    average_price = Column(DECIMAL(10,2))
    status = Column(String(20), default='PENDING')
    execution_strategy = Column(String(30))
    time_in_force = Column(String(10), default='DAY')
    strategy_name = Column(String(50))
    signal_id = Column(String(50))
    fees = Column(DECIMAL(8,2), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    placed_at = Column(DateTime(timezone=True))
    filled_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="orders")

class UserMetric(Base):
    """User performance metrics"""
    __tablename__ = "user_metrics"
    __table_args__ = {'extend_existing': True}
    
    metric_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    total_pnl = Column(DECIMAL(12,2), default=0)
    win_rate = Column(DECIMAL(5,2))
    avg_win = Column(DECIMAL(10,2))
    avg_loss = Column(DECIMAL(10,2))
    sharpe_ratio = Column(DECIMAL(5,2))
    max_drawdown = Column(DECIMAL(10,2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="metrics")

class RiskMetric(Base):
    """Risk metrics"""
    __tablename__ = "risk_metrics"
    __table_args__ = {'extend_existing': True}
    
    metric_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    portfolio_value = Column(DECIMAL(15,2))
    var_95 = Column(DECIMAL(10,2))  # Value at Risk 95%
    exposure = Column(DECIMAL(10,2))
    leverage = Column(DECIMAL(5,2))
    risk_level = Column(String(20))  # LOW, MEDIUM, HIGH, CRITICAL
    alerts = Column(JSON)
    
    # Relationships
    user = relationship("User", back_populates="risk_metrics")

class Recommendation(Base):
    """AI-generated trading recommendations"""
    __tablename__ = "recommendations"
    __table_args__ = (
        Index('ix_recommendations_stock_active', 'stock_id', 'is_active'),
        {'extend_existing': True}
    )
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    recommendation_type = Column(String(10), nullable=False)  # BUY, SELL, HOLD
    confidence_score = Column(Float, nullable=False)
    target_price = Column(DECIMAL(10, 4))
    stop_loss = Column(DECIMAL(10, 4))
    analysis = Column(Text)
    algorithm_version = Column(String(20))
    factors = Column(JSON)  # Store analysis factors as JSON
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    stock = relationship("Stock", back_populates="recommendations")

class RiskMetrics(Base):
    """Portfolio risk analysis data"""
    __tablename__ = "portfolio_risk_metrics"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    var_1d = Column(DECIMAL(15, 2))  # Value at Risk 1 day
    var_5d = Column(DECIMAL(15, 2))  # Value at Risk 5 days
    max_drawdown = Column(DECIMAL(5, 4))  # Maximum drawdown percentage
    sharpe_ratio = Column(DECIMAL(8, 4))
    beta = Column(DECIMAL(8, 4))
    volatility = Column(DECIMAL(8, 4))
    risk_score = Column(Integer)  # 1-10 scale
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())

class TradingSession(Base):
    """Trading session tracking"""
    __tablename__ = "trading_sessions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_start = Column(DateTime(timezone=True), server_default=func.now())
    session_end = Column(DateTime(timezone=True))
    trades_count = Column(Integer, default=0)
    total_volume = Column(DECIMAL(15, 2), default=0)
    pnl = Column(DECIMAL(15, 2), default=0)
    status = Column(String(20), default='ACTIVE')  # ACTIVE, CLOSED

class SignalType(str, Enum):
    """Signal type enum"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    EXIT = "exit"

class SignalStrength(str, Enum):
    """Signal strength enum"""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"

class Signal(BaseModel):
    """Trading signal model"""
    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    signal_type: SignalType
    strength: SignalStrength
    price: float
    timestamp: datetime = Field(default_factory=datetime.now)
    strategy: str
    confidence: float = Field(ge=0.0, le=1.0)
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: Dict = Field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert signal to dictionary"""
        return {
            'signal_id': self.signal_id,
            'symbol': self.symbol,
            'signal_type': self.signal_type.value,
            'strength': self.strength.value,
            'price': self.price,
            'timestamp': self.timestamp.isoformat(),
            'strategy': self.strategy,
            'confidence': self.confidence,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'metadata': self.metadata
        }

# Create aliases for backward compatibility - FIXED: Only alias Pydantic models
# Note: TradingPosition SQLAlchemy model is defined above, don't alias it
Position = PositionModel 