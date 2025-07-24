from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class TradeSource(str, Enum):
    ZERODHA = "zerodha"
    MANUAL = "manual"
    N8N = "n8n"
    AUTONOMOUS = "autonomous"

class TradeBase(BaseModel):
    symbol: str
    quantity: float
    price: float
    side: str
    source: TradeSource
    source_id: Optional[str] = None  # ID from the source system
    source_metadata: Optional[dict] = None  # Additional source-specific data
    strategy_id: Optional[int] = None
    user_id: int
    notes: Optional[str] = None

class TradeCreate(TradeBase):
    pass

class TradeUpdate(BaseModel):
    symbol: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    side: Optional[str] = None
    source: Optional[TradeSource] = None
    source_id: Optional[str] = None
    source_metadata: Optional[dict] = None
    strategy_id: Optional[int] = None
    notes: Optional[str] = None

class TradeInDB(TradeBase):
    id: int
    created_at: datetime
    updated_at: datetime
    status: str
    execution_time: Optional[datetime] = None
    commission: Optional[float] = None
    slippage: Optional[float] = None
    total_cost: Optional[float] = None

    class Config:
        orm_mode = True

class TradeResponse(TradeInDB):
    pass 