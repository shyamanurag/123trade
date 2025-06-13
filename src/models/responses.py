"""Shared Pydantic response envelopes used by the public API.

Keeping them in one place guarantees a consistent OpenAPI schema across all
routers and eases front-end consumption.
"""
from __future__ import annotations

from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel):
    success: bool = Field(..., description="Whether the request succeeded")
    message: Optional[str] = Field(None, description="Human-readable description")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DataResponse(Generic[T], BaseResponse):
    data: T = Field(..., description="Payload for successful request")

    class Config:
        arbitrary_types_allowed = True
