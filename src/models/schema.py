from typing import Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

class TradeStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PENDING = "PENDING"

class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    STOPPED = "STOPPED"
    SUSPENDED = "SUSPENDED"
    INACTIVE = "INACTIVE"

class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    EXTREME = "EXTREME"

# User Models
class UserBase(BaseModel):
    user_id: str
    username: str
    email: str
    status: UserStatus = UserStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class UserCreate(UserBase):
    password: str
    initial_capital: float
    risk_level: RiskLevel = RiskLevel.MODERATE

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    status: Optional[UserStatus] = None
    risk_level: Optional[RiskLevel] = None

class UserResponse(UserBase):
    current_capital: float
    opening_capital: float
    daily_pnl: float
    daily_pnl_percentage: float
    total_pnl: float
    total_pnl_percentage: float
    open_trades: int
    total_trades: int
    win_rate: float
    risk_level: RiskLevel
    hard_stop_status: bool = False

# Order Models
class Order(BaseModel):
    order_id: str
    user_id: str
    symbol: str
    order_type: OrderType
    quantity: int
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    filled_quantity: int = 0
    average_fill_price: Optional[float] = None
    related_orders: List[str] = Field(default_factory=list)

class OrderCreate(BaseModel):
    user_id: str
    symbol: str
    order_type: OrderType
    quantity: int
    price: Optional[float] = None
    stop_price: Optional[float] = None
    execution_strategy: Optional[str] = None  # TWAP, VWAP, IMMEDIATE, etc.
    time_in_force: Optional[str] = "DAY"  # DAY, GTC, IOC, FOK
    iceberg_quantity: Optional[int] = None  # For iceberg orders

    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        return v

    @validator('price')
    def validate_price(cls, v, values):
        if v is not None and v <= 0:
            raise ValueError('Price must be greater than 0')
        if values.get('order_type') in [OrderType.LIMIT, OrderType.STOP_LIMIT] and v is None:
            raise ValueError('Price is required for limit and stop-limit orders')
        return v

    @validator('stop_price')
    def validate_stop_price(cls, v, values):
        if v is not None and v <= 0:
            raise ValueError('Stop price must be greater than 0')
        if values.get('order_type') in [OrderType.STOP, OrderType.STOP_LIMIT] and v is None:
            raise ValueError('Stop price is required for stop and stop-limit orders')
        return v

class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    filled_quantity: Optional[int] = None
    average_fill_price: Optional[float] = None

# Trade Models
class Trade(BaseModel):
    trade_id: str
    user_id: str
    order_id: str
    symbol: str
    quantity: int
    entry_price: float
    current_price: float
    entry_time: datetime
    exit_time: Optional[datetime] = None
    status: TradeStatus = TradeStatus.OPEN
    pnl: float = 0.0
    pnl_percentage: float = 0.0
    strategy_name: Optional[str] = None
    risk_score: Optional[float] = None
    execution_strategy: Optional[str] = None
    execution_quality: Optional[float] = None  # Measure of execution quality (0-1)
    slippage: Optional[float] = None  # Price slippage during execution
    commission: Optional[float] = None
    fees: Optional[float] = None

    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        return v

    @validator('entry_price', 'current_price')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('Price must be greater than 0')
        return v

class TradeCreate(BaseModel):
    user_id: str
    order_id: str
    symbol: str
    quantity: int
    entry_price: float
    strategy_name: Optional[str] = None
    risk_score: Optional[float] = None

class TradeUpdate(BaseModel):
    current_price: Optional[float] = None
    status: Optional[TradeStatus] = None
    exit_time: Optional[datetime] = None
    pnl: Optional[float] = None
    pnl_percentage: Optional[float] = None

# Risk Models
class RiskMetrics(BaseModel):
    user_id: str
    current_capital: float
    opening_capital: float
    daily_pnl: float
    daily_pnl_percentage: float
    max_drawdown: float
    current_drawdown: float
    risk_score: float
    position_limits: Dict[str, float]
    exposure_limits: Dict[str, float]
    hard_stop_status: bool
    hard_stop_threshold: float
    hard_stop_triggered_at: Optional[datetime] = None
    hard_stop_reason: Optional[str] = None
    hard_stop_recovery_threshold: Optional[float] = None
    last_updated: datetime = Field(default_factory=datetime.now)

    @validator('current_capital', 'opening_capital')
    def validate_capital(cls, v):
        if v < 0:
            raise ValueError('Capital cannot be negative')
        return v

    @validator('hard_stop_threshold')
    def validate_hard_stop_threshold(cls, v):
        if v <= 0 or v >= 1:
            raise ValueError('Hard stop threshold must be between 0 and 1')
        return v

class RiskLimits(BaseModel):
    max_position_size: float
    max_daily_loss: float
    max_drawdown: float
    risk_per_trade: float
    max_positions: int
    max_correlation: float
    max_concentration: float
    vix_threshold_high: float
    vix_threshold_extreme: float

# Performance Models
class PerformanceMetrics(BaseModel):
    user_id: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    average_win: float
    average_loss: float
    profit_factor: float
    total_pnl: float
    total_pnl_percentage: float
    sharpe_ratio: Optional[float] = None
    max_drawdown: float
    average_trade_duration: float
    last_updated: datetime = Field(default_factory=datetime.now)

# System Metrics
class SystemMetrics(BaseModel):
    total_users: int
    active_users: int
    total_trades: int
    open_trades: int
    total_volume: float
    system_pnl: float
    system_risk_score: float
    node_health: Dict[str, bool]
    load_metrics: Dict[str, float]
    execution_metrics: Dict[str, float]  # Execution quality metrics
    market_impact: Dict[str, float]  # Market impact metrics
    last_updated: datetime = Field(default_factory=datetime.now)

# WebSocket Message Models
class TradeUpdateMessage(BaseModel):
    type: str = "TRADE_UPDATE"
    trade: Trade
    timestamp: datetime = Field(default_factory=datetime.now)

class UserMetricsUpdateMessage(BaseModel):
    type: str = "USER_METRICS_UPDATE"
    user_id: str
    metrics: RiskMetrics
    timestamp: datetime = Field(default_factory=datetime.now)

class SystemMetricsUpdateMessage(BaseModel):
    type: str = "SYSTEM_METRICS_UPDATE"
    metrics: SystemMetrics
    timestamp: datetime = Field(default_factory=datetime.now)

# Redis Key Patterns
class RedisKeys:
    USER = "user:{user_id}"
    USER_METRICS = "user:{user_id}:metrics"
    USER_RISK = "user:{user_id}:risk"
    USER_PERFORMANCE = "user:{user_id}:performance"
    TRADE = "trade:{trade_id}"
    ORDER = "order:{order_id}"
    SYSTEM_METRICS = "system:metrics"
    NODE_HEALTH = "node:{node_id}:health"
    LOAD_METRICS = "node:{node_id}:load"

# Database Indexes
class Indexes:
    USER_EMAIL = "user_email_idx"
    USER_STATUS = "user_status_idx"
    TRADE_USER = "trade_user_idx"
    TRADE_SYMBOL = "trade_symbol_idx"
    TRADE_STATUS = "trade_status_idx"
    ORDER_USER = "order_user_idx"
    ORDER_STATUS = "order_status_idx"

# Position Models
class Position(BaseModel):
    user_id: str
    symbol: str
    quantity: int
    average_entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    last_updated: datetime = Field(default_factory=datetime.now)

    @validator('quantity')
    def validate_quantity(cls, v):
        if v == 0:
            raise ValueError('Position quantity cannot be zero')
        return v

# Market Data Models
class MarketData(BaseModel):
    symbol: str
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    vwap: Optional[float] = None
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None

    @validator('open_price', 'high_price', 'low_price', 'close_price', 'bid_price', 'ask_price')
    def validate_price(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Price must be greater than 0')
        return v

# Strategy Models
class StrategyConfig(BaseModel):
    strategy_id: str
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Union[float, int, str, bool]]
    risk_level: RiskLevel
    max_position_size: float
    stop_loss_percentage: float
    take_profit_percentage: float
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @validator('stop_loss_percentage', 'take_profit_percentage')
    def validate_percentage(cls, v):
        if v <= 0 or v >= 1:
            raise ValueError('Percentage must be between 0 and 1')
        return v

class SignalMetadata(BaseModel):
    source: str
    confidence: float
    timestamp: datetime = Field(default_factory=datetime.now)
    additional_data: Optional[Dict[str, Any]] = None

class TradingSignal(BaseModel):
    signal_id: str
    symbol: str
    signal_type: str  # BUY, SELL, HOLD
    strength: float
    metadata: SignalMetadata
    created_at: datetime = Field(default_factory=datetime.now)

    @validator('strength')
    def validate_strength(cls, v):
        if v < -1 or v > 1:
            raise ValueError('Signal strength must be between -1 and 1')
        return v 