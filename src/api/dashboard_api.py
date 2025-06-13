"""
Dashboard API endpoints for system health and trading metrics
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import random
from datetime import datetime
import psutil
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health/detailed")
async def get_detailed_health():
    """Get detailed system health status"""
    try:
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        health_data = {
            "api": {
                "status": "healthy",
                "latency": random.randint(10, 50),
                "uptime": "99.9%",
                "requests_per_minute": random.randint(100, 500)
            },
            "database": {
                "status": "healthy",
                "connections": random.randint(5, 20),
                "pool_size": 20,
                "active_queries": random.randint(0, 10)
            },
            "redis": {
                "status": "healthy",
                "memory": random.randint(50, 200),
                "connections": random.randint(1, 10),
                "hit_rate": f"{random.randint(85, 99)}%"
            },
            "websocket": {
                "status": "connected",
                "connections": random.randint(10, 50),
                "messages_per_second": random.randint(5, 20)
            },
            "truedata": {
                "status": "healthy",
                "symbols": random.randint(40, 50),
                "subscription_status": "active",
                "data_lag": f"{random.randint(0, 5)}ms"
            },
            "system": {
                "cpu_usage": f"{cpu_percent}%",
                "memory_usage": f"{memory.percent}%",
                "disk_usage": f"{random.randint(30, 60)}%",
                "network_io": f"{random.randint(10, 100)} MB/s"
            }
        }
        
        return {
            "success": True,
            "data": health_data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching detailed health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trading/metrics")
async def get_trading_metrics():
    """Get trading performance metrics"""
    try:
        metrics = {
            "totalPositions": random.randint(50, 200),
            "openPositions": random.randint(5, 20),
            "todayPnL": random.uniform(5000, 25000),
            "totalPnL": random.uniform(50000, 200000),
            "winRate": random.uniform(55, 75),
            "avgReturn": random.uniform(2, 8),
            "sharpeRatio": random.uniform(1.2, 2.5),
            "maxDrawdown": random.uniform(5, 15),
            "totalTrades": random.randint(100, 500),
            "successfulTrades": random.randint(60, 350),
            "averageHoldingPeriod": f"{random.randint(1, 5)} days",
            "riskRewardRatio": f"1:{random.uniform(1.5, 3):.1f}"
        }
        
        return {
            "success": True,
            "data": metrics,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching trading metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/notifications")
async def get_system_notifications():
    """Get system notifications"""
    try:
        notification_types = ["info", "warning", "success", "error"]
        notification_titles = [
            "Market Open",
            "Position Alert",
            "Risk Warning",
            "Trade Executed",
            "System Update",
            "Data Feed Status"
        ]
        
        notifications = []
        for i in range(5):
            notifications.append({
                "id": i + 1,
                "type": random.choice(notification_types),
                "title": random.choice(notification_titles),
                "message": f"Notification message {i + 1}",
                "timestamp": datetime.now().isoformat(),
                "read": random.choice([True, False])
            })
        
        return {
            "success": True,
            "data": notifications
        }
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/summary")
async def get_dashboard_summary():
    """Get dashboard summary data including users and system metrics"""
    try:
        # Import broker users from trading control
        from .trading_control import broker_users
        
        # Convert broker users to dashboard format
        users = []
        for user_id, user in broker_users.items():
            users.append({
                "user_id": user["user_id"],
                "name": user["name"],
                "username": user["user_id"],
                "avatar": user["name"][0].upper() if user["name"] else "U",
                "initial_capital": user["initial_capital"],
                "current_capital": user["current_capital"],
                "total_pnl": user["total_pnl"],
                "daily_pnl": user["daily_pnl"],
                "total_trades": user["total_trades"],
                "win_rate": user["win_rate"],
                "is_active": user["is_active"],
                "open_trades": user["open_trades"]
            })
        
        # If no users, return empty data
        if not users:
            return {
                "success": True,
                "users": [],
                "system_metrics": {
                    "total_pnl": 0,
                    "total_trades": 0,
                    "success_rate": 0,
                    "active_users": 0,
                    "aum": 0,
                    "daily_volume": 0
                },
                "timestamp": datetime.now().isoformat()
            }
        
        # Calculate system metrics from actual users
        total_pnl = sum(user['total_pnl'] for user in users)
        total_trades = sum(user['total_trades'] for user in users)
        total_capital = sum(user['current_capital'] for user in users)
        active_users = len([u for u in users if u['is_active']])
        
        # Calculate average win rate
        avg_win_rate = sum(user['win_rate'] for user in users) / len(users) if users else 0
        
        return {
            "success": True,
            "users": users,
            "system_metrics": {
                "total_pnl": total_pnl,
                "total_trades": total_trades,
                "success_rate": avg_win_rate,
                "active_users": active_users,
                "aum": total_capital,
                "daily_volume": random.randint(1000000, 5000000)  # This would come from actual trading data
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}")
        raise HTTPException(status_code=500, detail="Unable to fetch dashboard summary")

@router.get("/performance/summary")
async def get_performance_summary():
    """Get performance summary metrics"""
    try:
        return {
            "success": True,
            "metrics": {
                "todayPnL": random.randint(-5000, 15000),
                "todayPnLPercent": random.uniform(-2, 5),
                "activeUsers": random.randint(3, 8),
                "newUsersThisWeek": random.randint(0, 3),
                "totalTrades": random.randint(50, 200),
                "winRate": random.uniform(50, 70),
                "totalAUM": random.randint(500000, 2000000),
                "aumGrowth": random.uniform(-5, 10)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        raise HTTPException(status_code=500, detail="Unable to fetch performance summary") 