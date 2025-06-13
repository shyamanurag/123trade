"""
SQLAlchemy models for trading system data storage.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    Text, JSON, ForeignKey, Index, DECIMAL, BigInteger
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.config.database import Base

class User(Base):
    """User accounts and authentication"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    portfolios = relationship("Portfolio", back_populates="user")
    trades = relationship("Trade", back_populates="user")

class Portfolio(Base):
    """User portfolios and holdings"""
    __tablename__ = "portfolios"
    
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
    positions = relationship("Position", back_populates="portfolio")
    trades = relationship("Trade", back_populates="portfolio")

class Stock(Base):
    """Stock/Symbol master data"""
    __tablename__ = "stocks"
    
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
    positions = relationship("Position", back_populates="stock")
    trades = relationship("Trade", back_populates="stock")
    recommendations = relationship("Recommendation", back_populates="stock")

class MarketData(Base):
    """Historical and real-time market data"""
    __tablename__ = "market_data"
    
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
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_market_data_stock_timestamp', 'stock_id', 'timestamp'),
    )

class Position(Base):
    """Current portfolio positions"""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    avg_buy_price = Column(DECIMAL(10, 4), nullable=False)
    current_price = Column(DECIMAL(10, 4))
    market_value = Column(DECIMAL(15, 2))
    unrealized_pnl = Column(DECIMAL(15, 2))
    position_type = Column(String(10), default='LONG')  # LONG, SHORT
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="positions")
    stock = relationship("Stock", back_populates="positions")

class Trade(Base):
    """Trading transactions history"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    trade_type = Column(String(10), nullable=False)  # BUY, SELL
    quantity = Column(Integer, nullable=False)
    price = Column(DECIMAL(10, 4), nullable=False)
    total_amount = Column(DECIMAL(15, 2), nullable=False)
    fees = Column(DECIMAL(10, 2), default=0)
    status = Column(String(20), default='PENDING')  # PENDING, EXECUTED, CANCELLED
    execution_time = Column(DateTime(timezone=True))
    strategy = Column(String(50))  # Manual, Algorithm name
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="trades")
    portfolio = relationship("Portfolio", back_populates="trades")
    stock = relationship("Stock", back_populates="trades")
    
    # Indexes
    __table_args__ = (
        Index('ix_trades_user_timestamp', 'user_id', 'created_at'),
        Index('ix_trades_portfolio_timestamp', 'portfolio_id', 'created_at'),
    )

class Recommendation(Base):
    """AI-generated trading recommendations"""
    __tablename__ = "recommendations"
    
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
    
    # Indexes
    __table_args__ = (
        Index('ix_recommendations_stock_active', 'stock_id', 'is_active'),
    )

class RiskMetrics(Base):
    """Portfolio risk analysis data"""
    __tablename__ = "risk_metrics"
    
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
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_start = Column(DateTime(timezone=True), server_default=func.now())
    session_end = Column(DateTime(timezone=True))
    trades_count = Column(Integer, default=0)
    total_volume = Column(DECIMAL(15, 2), default=0)
    pnl = Column(DECIMAL(15, 2), default=0)
    status = Column(String(20), default='ACTIVE')  # ACTIVE, CLOSED 