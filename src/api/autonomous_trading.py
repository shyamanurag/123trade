"""Autonomous Trading API endpoints
Production-grade wiring to the TradingOrchestrator.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from core.providers import get_orchestrator
from core.orchestrator import TradingOrchestrator
from src.models.responses import BaseResponse, DataResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status", response_model=DataResponse)
async def get_status(
    orchestrator: TradingOrchestrator = Depends(get_orchestrator),
):
    """Return current orchestrator status snapshot."""
    try:
        status = await orchestrator.get_trading_status()
        return DataResponse(success=True, message="Status", data=status)
    except Exception as e:
        logger.error(f"Status endpoint failure: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch status")


@router.post("/start", response_model=BaseResponse)
async def start_trading(
    orchestrator: TradingOrchestrator = Depends(get_orchestrator),
):
    """Enable trading on orchestrator (idempotent)."""
    try:
        await orchestrator.enable_trading()
        return BaseResponse(success=True, message="Autonomous trading started")
    except Exception as e:
        logger.error(f"Start trading failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to start trading")


@router.post("/stop", response_model=BaseResponse)
async def stop_trading(
    orchestrator: TradingOrchestrator = Depends(get_orchestrator),
):
    """Disable trading and flatten orchestrator tasks."""
    try:
        await orchestrator.disable_trading()
        return BaseResponse(success=True, message="Autonomous trading stopped")
    except Exception as e:
        logger.error(f"Stop trading failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop trading")


@router.get("/positions", response_model=DataResponse)
async def get_positions(
    orchestrator: TradingOrchestrator = Depends(get_orchestrator),
):
    """Return all open positions managed by the engine."""
    try:
        positions = await orchestrator.get_all_positions()
        return DataResponse(success=True, message="Positions", data=positions)
    except Exception as e:
        logger.error(f"Get positions failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch positions")


@router.get("/performance", response_model=DataResponse)
async def get_performance(
    orchestrator: TradingOrchestrator = Depends(get_orchestrator),
):
    """Return aggregated trading metrics for current day."""
    try:
        metrics = await orchestrator.get_trading_metrics()
        return DataResponse(success=True, message="Performance", data=metrics)
    except Exception as e:
        logger.error(f"Performance endpoint failure: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch performance")


@router.get("/strategies", response_model=DataResponse)
async def get_strategies(
    orchestrator: TradingOrchestrator = Depends(get_orchestrator),
):
    """List active strategies."""
    try:
        strategies = await orchestrator.get_active_strategies()
        return DataResponse(success=True, message="Strategies", data=strategies)
    except Exception as e:
        logger.error(f"Strategies endpoint failure: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch strategies")


@router.get("/risk", response_model=DataResponse)
async def get_risk_metrics(
    orchestrator: TradingOrchestrator = Depends(get_orchestrator),
):
    """Return current risk metrics from risk manager."""
    try:
        risk = await orchestrator.get_risk_metrics()
        return DataResponse(success=True, message="Risk metrics", data=risk)
    except Exception as e:
        logger.error(f"Risk endpoint failure: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch risk metrics")
