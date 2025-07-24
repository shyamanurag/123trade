from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

class SignalAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    EXIT = "EXIT"
    HOLD = "HOLD"

class SignalTimeframe(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"

class N8nSignalIn(BaseModel):
    symbol: str
    action: SignalAction
    quantity: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    strategy: str
    signal_id: str
    timestamp: datetime
    metadata: Dict[str, any] = Field(
        default_factory=dict,
        description="Additional signal metadata"
    )

    @validator('metadata')
    def validate_metadata(cls, v):
        required_fields = ['quality_score', 'timeframe', 'confidence', 'indicators']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required metadata field: {field}")
        
        if not isinstance(v['indicators'], list):
            raise ValueError("indicators must be a list")
        
        if not 0 <= v['quality_score'] <= 10:
            raise ValueError("quality_score must be between 0 and 10")
        
        if not 0 <= v['confidence'] <= 1:
            raise ValueError("confidence must be between 0 and 1")
        
        return v

class N8nSignalOut(BaseModel):
    signal_id: str
    status: str
    execution_time: Optional[datetime] = None
    error: Optional[str] = None
    trade_id: Optional[str] = None
    position_id: Optional[str] = None 