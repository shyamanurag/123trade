"""
SQLAlchemy models for crypto trading system data storage.
Enhanced for crypto symbol parsing and market data.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, List
from enum import Enum
import uuid

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    Text, JSON, ForeignKey, Index, DECIMAL, BigInteger, ARRAY
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

class CryptoSymbol(BaseModel):
    """Crypto symbol parsing and validation model"""
    symbol: str
    base_asset: str
    quote_asset: str
    exchange: str = "BINANCE"
    min_qty: Decimal = Decimal("0.00000001")
    max_qty: Decimal = Decimal("1000000")
    step_size: Decimal = Decimal("0.00000001")
    min_price: Decimal = Decimal("0.00000001")
    max_price: Decimal = Decimal("1000000")
    tick_size: Decimal = Decimal("0.00000001")
    min_notional: Decimal = Decimal("10")
    
    @classmethod
    def parse_symbol(cls, symbol_input: str) -> 'CryptoSymbol':
        """Parse crypto symbol from string (e.g., BTCUSDT -> BTC/USDT)"""
        symbol = symbol_input.upper()
        
        # Common quote assets
        quote_assets = ['USDT', 'BTC', 'ETH', 'BNB', 'BUSD', 'USDC']
        
        base_asset = None
        quote_asset = None
        
        for quote in quote_assets:
            if symbol.endswith(quote):
                quote_asset = quote
                base_asset = symbol[:-len(quote)]
                break
        
        if not base_asset or not quote_asset:
            # Default to USDT pair
            base_asset = symbol
            quote_asset = 'USDT'
            symbol = f"{base_asset}USDT"
        
        return cls(
            symbol=symbol,
            base_asset=base_asset,
            quote_asset=quote_asset
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'base_asset': self.base_asset,
            'quote_asset': self.quote_asset,
            'exchange': self.exchange,
            'min_qty': float(self.min_qty),
            'max_qty': float(self.max_qty),
            'step_size': float(self.step_size),
            'min_price': float(self.min_price),
            'max_price': float(self.max_price),
            'tick_size': float(self.tick_size),
            'min_notional': float(self.min_notional)
        }

class CryptoMarketData(BaseModel):
    """Enhanced crypto market data model"""
    symbol: str
    timestamp: datetime
    
    # Price data
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    
    # Volume data
    volume: Decimal
    quote_volume: Decimal
    
    # Trading metrics
    trade_count: int = 0
    taker_buy_volume: Decimal = Decimal("0")
    taker_buy_quote_volume: Decimal = Decimal("0")
    
    # Advanced metrics
    vwap: Optional[Decimal] = None
    price_change: Decimal = Decimal("0")
    price_change_percent: Decimal = Decimal("0")
    weighted_avg_price: Optional[Decimal] = None
    
    # Market depth
    bid_prices: List[Decimal] = Field(default_factory=list)
    bid_quantities: List[Decimal] = Field(default_factory=list)
    ask_prices: List[Decimal] = Field(default_factory=list)
    ask_quantities: List[Decimal] = Field(default_factory=list)
    
    # Additional data
    market_cap: Optional[Decimal] = None
    circulating_supply: Optional[Decimal] = None
    total_supply: Optional[Decimal] = None
    
    @property
    def spread(self) -> Decimal:
        """Calculate bid-ask spread"""
        if self.bid_prices and self.ask_prices:
            return self.ask_prices[0] - self.bid_prices[0]
        return Decimal("0")
    
    @property
    def spread_percent(self) -> Decimal:
        """Calculate spread percentage"""
        if self.close_price > 0 and self.spread > 0:
            return (self.spread / self.close_price) * 100
        return Decimal("0")
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'open_price': float(self.open_price),
            'high_price': float(self.high_price),
            'low_price': float(self.low_price),
            'close_price': float(self.close_price),
            'volume': float(self.volume),
            'quote_volume': float(self.quote_volume),
            'trade_count': self.trade_count,
            'taker_buy_volume': float(self.taker_buy_volume),
            'taker_buy_quote_volume': float(self.taker_buy_quote_volume),
            'vwap': float(self.vwap) if self.vwap else None,
            'price_change': float(self.price_change),
            'price_change_percent': float(self.price_change_percent),
            'weighted_avg_price': float(self.weighted_avg_price) if self.weighted_avg_price else None,
            'bid_prices': [float(p) for p in self.bid_prices],
            'bid_quantities': [float(q) for q in self.bid_quantities],
            'ask_prices': [float(p) for p in self.ask_prices],
            'ask_quantities': [float(q) for q in self.ask_quantities],
            'market_cap': float(self.market_cap) if self.market_cap else None,
            'circulating_supply': float(self.circulating_supply) if self.circulating_supply else None,
            'total_supply': float(self.total_supply) if self.total_supply else None,
            'spread': float(self.spread),
            'spread_percent': float(self.spread_percent)
        }

class PositionModel(BaseModel):
    """Enhanced position model for crypto trading"""
    position_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    base_asset: str = ""
    quote_asset: str = ""
    quantity: Decimal
    entry_price: Decimal
    exit_price: Optional[Decimal] = None
    current_price: Optional[Decimal] = None
    entry_time: datetime = Field(default_factory=datetime.now)
    exit_time: Optional[datetime] = None
    status: PositionStatus = PositionStatus.PENDING
    strategy: str
    realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    pnl_percent: Decimal = Decimal("0")
    current_risk: Decimal = Decimal("0")
    
    # Crypto-specific fields
    fees_paid: Decimal = Decimal("0")
    slippage: Decimal = Decimal("0")
    trade_count: int = 0
    
    def __post_init__(self):
        """Parse symbol after initialization"""
        if self.symbol and not self.base_asset:
            parsed = CryptoSymbol.parse_symbol(self.symbol)
            self.base_asset = parsed.base_asset
            self.quote_asset = parsed.quote_asset
    
    def update_pnl(self, current_price: Decimal):
        """Update PnL based on current price"""
        self.current_price = current_price
        if self.entry_price and self.quantity:
            self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
            self.pnl_percent = ((current_price - self.entry_price) / self.entry_price) * 100
    
    def close(self, exit_price: Decimal):
        """Close position and calculate realized PnL"""
        self.exit_price = exit_price
        self.exit_time = datetime.now()
        self.status = PositionStatus.CLOSED
        if self.entry_price and self.quantity:
            self.realized_pnl = (exit_price - self.entry_price) * self.quantity - self.fees_paid
            self.unrealized_pnl = Decimal("0")
    
    def to_dict(self) -> Dict:
        """Convert position to dictionary"""
        return {
            'position_id': self.position_id,
            'symbol': self.symbol,
            'base_asset': self.base_asset,
            'quote_asset': self.quote_asset,
            'quantity': float(self.quantity),
            'entry_price': float(self.entry_price),
            'exit_price': float(self.exit_price) if self.exit_price else None,
            'current_price': float(self.current_price) if self.current_price else None,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'status': self.status.value,
            'strategy': self.strategy,
            'realized_pnl': float(self.realized_pnl),
            'unrealized_pnl': float(self.unrealized_pnl),
            'pnl_percent': float(self.pnl_percent),
            'current_risk': float(self.current_risk),
            'fees_paid': float(self.fees_paid),
            'slippage': float(self.slippage),
            'trade_count': self.trade_count
        }

class User(Base):
    """User accounts and authentication - Enhanced for crypto"""
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(200))
    initial_capital = Column(DECIMAL(20,8), default=10000)  # Updated for crypto precision
    current_balance = Column(DECIMAL(20,8), default=10000)
    risk_tolerance = Column(String(20), default='medium')
    is_active = Column(Boolean, default=True)
    
    # Crypto-specific fields
    api_key_binance = Column(String(255))
    api_secret_binance = Column(String(255))
    testnet_mode = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    positions = relationship("Position", back_populates="user")
    trades = relationship("Trade", back_populates="user")
    orders = relationship("Order", back_populates="user")
    metrics = relationship("UserMetric", back_populates="user")
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
    positions = relationship("Position", back_populates="portfolio")
    trades = relationship("Trade", back_populates="portfolio")

class Stock(Base):
    """Updated symbols table for crypto assets"""
    __tablename__ = "symbols"  # Renamed from stocks
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    exchange = Column(String(20), default='BINANCE')
    symbol_type = Column(String(20), default='SPOT')
    
    # Crypto-specific fields
    base_asset = Column(String(10))
    quote_asset = Column(String(10))
    min_qty = Column(DECIMAL(20,8), default=0.00000001)
    max_qty = Column(DECIMAL(20,8), default=1000000)
    step_size = Column(DECIMAL(20,8), default=0.00000001)
    min_price = Column(DECIMAL(20,8), default=0.00000001)
    max_price = Column(DECIMAL(20,8), default=1000000)
    tick_size_price = Column(DECIMAL(20,8), default=0.00000001)
    min_notional = Column(DECIMAL(20,8), default=10)
    trading_status = Column(String(20), default='TRADING')
    permissions = Column(JSON, default=list)
    filters = Column(JSON, default=dict)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    market_data = relationship("CryptoMarketDataTable", backref="symbol_info")
    positions = relationship("Position", back_populates="stock")
    trades = relationship("Trade", back_populates="stock")

class CryptoMarketDataTable(Base):
    """Enhanced crypto market data table"""
    __tablename__ = "crypto_market_data"
    __table_args__ = (
        Index('ix_crypto_market_data_symbol_timestamp', 'symbol', 'timestamp'),
        {'extend_existing': True}
    )
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Price data
    open_price = Column(DECIMAL(20,8), nullable=False)
    high_price = Column(DECIMAL(20,8), nullable=False)
    low_price = Column(DECIMAL(20,8), nullable=False)
    close_price = Column(DECIMAL(20,8), nullable=False)
    
    # Volume data
    volume = Column(DECIMAL(20,8), nullable=False)
    quote_volume = Column(DECIMAL(20,8), nullable=False)
    
    # Trading data
    trade_count = Column(Integer, default=0)
    taker_buy_volume = Column(DECIMAL(20,8), default=0)
    taker_buy_quote_volume = Column(DECIMAL(20,8), default=0)
    
    # Advanced metrics
    vwap = Column(DECIMAL(20,8))
    price_change = Column(DECIMAL(20,8), default=0)
    price_change_percent = Column(DECIMAL(10,4), default=0)
    weighted_avg_price = Column(DECIMAL(20,8))
    
    # Market depth (arrays)
    bid_prices = Column(ARRAY(DECIMAL(20,8)), default=list)
    bid_quantities = Column(ARRAY(DECIMAL(20,8)), default=list)
    ask_prices = Column(ARRAY(DECIMAL(20,8)), default=list)
    ask_quantities = Column(ARRAY(DECIMAL(20,8)), default=list)
    
    # Additional data
    market_cap = Column(DECIMAL(30,2))
    circulating_supply = Column(DECIMAL(30,8))
    total_supply = Column(DECIMAL(30,8))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CryptoTickData(Base):
    """Real-time crypto tick data"""
    __tablename__ = "crypto_tick_data"
    __table_args__ = (
        Index('ix_crypto_tick_data_symbol_timestamp', 'symbol', 'timestamp'),
        {'extend_existing': True}
    )
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Tick data
    price = Column(DECIMAL(20,8), nullable=False)
    quantity = Column(DECIMAL(20,8), nullable=False)
    
    # Order book
    best_bid = Column(DECIMAL(20,8))
    best_ask = Column(DECIMAL(20,8))
    bid_quantity = Column(DECIMAL(20,8))
    ask_quantity = Column(DECIMAL(20,8))
    
    # Trade info
    trade_id = Column(String(50))
    is_buyer_maker = Column(Boolean)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Position(Base):
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
    
    # Relationships
    user = relationship("User", back_populates="positions")
    trades = relationship("Trade", back_populates="position")

class Trade(Base):
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
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="trades")
    position = relationship("Position", back_populates="trades")

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
    var_5d = Column(DECIMAL(15,2))  # Value at Risk 5 days
    exposure = Column(DECIMAL(10,2))
    leverage = Column(DECIMAL(5,2))
    risk_level = Column(String(20))  # LOW, MEDIUM, HIGH, CRITICAL
    max_drawdown = Column(DECIMAL(5,4))  # Maximum drawdown percentage
    sharpe_ratio = Column(DECIMAL(8,4))
    beta = Column(DECIMAL(8,4))
    volatility = Column(DECIMAL(8,4))
    risk_score = Column(Integer)  # 1-10 scale
    alerts = Column(JSON)
    
    # Relationships
    user = relationship("User", back_populates="risk_metrics")

class Recommendation(Base):
    """AI-generated trading recommendations"""
    __tablename__ = "recommendations"
    __table_args__ = (
        Index('ix_recommendations_stock_created', 'stock_id', 'created_at'),
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
    """Trading signal types"""
    BUY = "buy"
    SELL = "sell" 
    HOLD = "hold"

class Signal(BaseModel):
    """Trading signal model"""
    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    signal_type: SignalType
    confidence: float = Field(ge=0.0, le=1.0)
    price: Optional[Decimal] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    strategy_name: str
    metadata: Dict = Field(default_factory=dict)

class SignalStrength(str, Enum):
    """Signal strength enum"""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"

class CryptoSignal(BaseModel):
    """Enhanced crypto trading signal model"""
    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    base_asset: str = ""
    quote_asset: str = ""
    signal_type: SignalType
    strength: SignalStrength
    price: Decimal
    timestamp: datetime = Field(default_factory=datetime.now)
    strategy: str
    confidence: float = Field(ge=0.0, le=1.0)
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    
    # Crypto-specific fields
    volume_profile: Dict = Field(default_factory=dict)
    order_book_pressure: Optional[float] = None
    whale_activity: Optional[bool] = None
    social_sentiment: Optional[float] = None
    
    metadata: Dict = Field(default_factory=dict)

    def __post_init__(self):
        """Parse symbol after initialization"""
        if self.symbol and not self.base_asset:
            parsed = CryptoSymbol.parse_symbol(self.symbol)
            self.base_asset = parsed.base_asset
            self.quote_asset = parsed.quote_asset

    def to_dict(self) -> Dict:
        """Convert signal to dictionary"""
        return {
            'signal_id': self.signal_id,
            'symbol': self.symbol,
            'base_asset': self.base_asset,
            'quote_asset': self.quote_asset,
            'signal_type': self.signal_type.value,
            'strength': self.strength.value,
            'price': float(self.price),
            'timestamp': self.timestamp.isoformat(),
            'strategy': self.strategy,
            'confidence': self.confidence,
            'stop_loss': float(self.stop_loss) if self.stop_loss else None,
            'take_profit': float(self.take_profit) if self.take_profit else None,
            'volume_profile': self.volume_profile,
            'order_book_pressure': self.order_book_pressure,
            'whale_activity': self.whale_activity,
            'social_sentiment': self.social_sentiment,
            'metadata': self.metadata
        } 