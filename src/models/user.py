from pydantic import BaseModel, EmailStr, Field, validator, condecimal
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=100)
    role: UserRole = UserRole.TRADER
    status: UserStatus = UserStatus.ACTIVE
    is_active: bool = True
    broker_account_id: Optional[str] = None
    trading_enabled: bool = False
    max_position_size: Optional[float] = None
    risk_level: Optional[str] = None
    preferences: Optional[dict] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    confirm_password: str

    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('passwords do not match')
        return v

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    is_active: Optional[bool] = None
    broker_account_id: Optional[str] = None
    trading_enabled: Optional[bool] = None
    max_position_size: Optional[float] = None
    risk_level: Optional[str] = None
    preferences: Optional[dict] = None

class UserInDB(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    password_hash: str
    failed_login_attempts: int = 0
    last_password_change: Optional[datetime] = None
    two_factor_enabled: bool = False
    two_factor_secret: Optional[str] = None

    class Config:
        orm_mode = True

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        orm_mode = True

class RiskTolerance(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class NewUser(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=100)
    initial_capital: condecimal(gt=0) = Field(default=50000)
    risk_tolerance: RiskTolerance = Field(default=RiskTolerance.MEDIUM)
    zerodha_client_id: Optional[str] = None
    broker_account_id: Optional[str] = None
    trading_enabled: bool = Field(default=False)
    max_position_size: Optional[float] = None
    preferences: Optional[dict] = Field(default_factory=dict)

    @validator('password')
    def password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v

    @validator('max_position_size')
    def validate_max_position_size(cls, v, values):
        if v is not None and 'initial_capital' in values:
            if v > values['initial_capital']:
                raise ValueError('max_position_size cannot be greater than initial_capital')
        return v 