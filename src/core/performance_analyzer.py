"""
User-specific Performance Analytics
Analyzes trading performance for individual users
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import pandas as pd
import numpy as np
from dataclasses import dataclass
import redis.asyncio as redis

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics for a user"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    average_holding_time: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    recovery_factor: float
    expectancy: float

class PerformanceAnalyzer:
    """Analyzes user-specific trading performance"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.redis = redis.from_url(config['redis_url'])
        
    async def analyze_user_performance(self, user_id: str, start_date: Optional[datetime] = None,
                                     end_date: Optional[datetime] = None) -> Optional[PerformanceMetrics]:
        """Analyze user's trading performance"""
        try:
            # Get user's trades
            trades = await self._get_user_trades(user_id, start_date, end_date)
            if not trades:
                return None
                
            # Convert to DataFrame
            df = pd.DataFrame(trades)
            
            # Calculate basic metrics
            total_trades = len(df)
            winning_trades = len(df[df['pnl'] > 0])
            losing_trades = len(df[df['pnl'] < 0])
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            # Calculate P&L metrics
            total_profit = df[df['pnl'] > 0]['pnl'].sum()
            total_loss = abs(df[df['pnl'] < 0]['pnl'].sum())
            profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
            
            average_win = df[df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
            average_loss = df[df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
            largest_win = df['pnl'].max()
            largest_loss = df['pnl'].min()
            
            # Calculate time-based metrics
            df['entry_time'] = pd.to_datetime(df['entry_time'])
            df['exit_time'] = pd.to_datetime(df['exit_time'])
            df['holding_time'] = (df['exit_time'] - df['entry_time']).dt.total_seconds() / 3600  # hours
            average_holding_time = df['holding_time'].mean()
            
            # Calculate risk-adjusted metrics
            daily_returns = df.groupby(df['exit_time'].dt.date)['pnl'].sum()
            sharpe_ratio = self._calculate_sharpe_ratio(daily_returns)
            sortino_ratio = self._calculate_sortino_ratio(daily_returns)
            
            # Calculate drawdown metrics
            cumulative_returns = daily_returns.cumsum()
            max_drawdown = self._calculate_max_drawdown(cumulative_returns)
            recovery_factor = abs(total_profit / max_drawdown) if max_drawdown < 0 else float('inf')
            
            # Calculate expectancy
            expectancy = (win_rate * average_win) - ((1 - win_rate) * abs(average_loss))
            
            return PerformanceMetrics(
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                profit_factor=profit_factor,
                average_win=average_win,
                average_loss=average_loss,
                largest_win=largest_win,
                largest_loss=largest_loss,
                average_holding_time=average_holding_time,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                max_drawdown=max_drawdown,
                recovery_factor=recovery_factor,
                expectancy=expectancy
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze performance for user {user_id}: {e}")
            return None
            
    async def get_user_statistics(self, user_id: str) -> Dict:
        """Get user's trading statistics"""
        try:
            # Get user's trades
            trades = await self._get_user_trades(user_id)
            if not trades:
                return {}
                
            # Convert to DataFrame
            df = pd.DataFrame(trades)
            
            # Calculate daily statistics
            daily_stats = df.groupby(df['exit_time'].dt.date).agg({
                'pnl': ['sum', 'count', 'mean'],
                'quantity': 'sum'
            }).reset_index()
            
            # Calculate monthly statistics
            monthly_stats = df.groupby(df['exit_time'].dt.to_period('M')).agg({
                'pnl': ['sum', 'count', 'mean'],
                'quantity': 'sum'
            }).reset_index()
            
            # Calculate symbol statistics
            symbol_stats = df.groupby('symbol').agg({
                'pnl': ['sum', 'count', 'mean'],
                'quantity': 'sum'
            }).reset_index()
            
            return {
                'daily_stats': daily_stats.to_dict('records'),
                'monthly_stats': monthly_stats.to_dict('records'),
                'symbol_stats': symbol_stats.to_dict('records')
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics for user {user_id}: {e}")
            return {}
            
    async def get_user_equity_curve(self, user_id: str) -> List[Dict]:
        """Get user's equity curve"""
        try:
            # Get user's trades
            trades = await self._get_user_trades(user_id)
            if not trades:
                return []
                
            # Convert to DataFrame
            df = pd.DataFrame(trades)
            
            # Calculate cumulative P&L
            df['exit_time'] = pd.to_datetime(df['exit_time'])
            df = df.sort_values('exit_time')
            df['cumulative_pnl'] = df['pnl'].cumsum()
            
            # Create equity curve
            equity_curve = df[['exit_time', 'cumulative_pnl']].to_dict('records')
            
            return equity_curve
            
        except Exception as e:
            logger.error(f"Failed to get equity curve for user {user_id}: {e}")
            return []
            
    async def _get_user_trades(self, user_id: str, start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None) -> List[Dict]:
        """Get user's trades from Redis"""
        try:
            # Get all trades
            trades = []
            async for key in self.redis.scan_iter(f"user:{user_id}:trades:*"):
                trade_data = await self.redis.hgetall(key)
                if trade_data:
                    trade = json.loads(trade_data)
                    trade['exit_time'] = datetime.fromisoformat(trade['exit_time'])
                    
                    # Filter by date range
                    if start_date and trade['exit_time'] < start_date:
                        continue
                    if end_date and trade['exit_time'] > end_date:
                        continue
                        
                    trades.append(trade)
                    
            return trades
            
        except Exception as e:
            logger.error(f"Failed to get trades for user {user_id}: {e}")
            return []
            
    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        try:
            if len(returns) < 2:
                return 0.0
                
            excess_returns = returns - risk_free_rate/252  # Daily risk-free rate
            return np.sqrt(252) * excess_returns.mean() / excess_returns.std()
            
        except Exception as e:
            logger.error(f"Failed to calculate Sharpe ratio: {e}")
            return 0.0
            
    def _calculate_sortino_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate Sortino ratio"""
        try:
            if len(returns) < 2:
                return 0.0
                
            excess_returns = returns - risk_free_rate/252  # Daily risk-free rate
            downside_returns = excess_returns[excess_returns < 0]
            
            if len(downside_returns) == 0:
                return float('inf')
                
            return np.sqrt(252) * excess_returns.mean() / downside_returns.std()
            
        except Exception as e:
            logger.error(f"Failed to calculate Sortino ratio: {e}")
            return 0.0
            
    def _calculate_max_drawdown(self, cumulative_returns: pd.Series) -> float:
        """Calculate maximum drawdown"""
        try:
            if len(cumulative_returns) < 2:
                return 0.0
                
            rolling_max = cumulative_returns.expanding().max()
            drawdowns = cumulative_returns - rolling_max
            return drawdowns.min()
            
        except Exception as e:
            logger.error(f"Failed to calculate maximum drawdown: {e}")
            return 0.0 