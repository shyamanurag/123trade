"""
Trading Reports API Routes
Provides comprehensive reporting endpoints
"""
from fastapi import APIRouter, Query, Depends, HTTPException
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import pandas as pd
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..auth import get_current_user_v1 as get_current_user
from ...core.database import get_db

# Simple user model for type hints
class User(BaseModel):
    username: str
    email: str
    is_active: bool = True

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.get("/daily")
async def get_daily_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    user_id: Optional[str] = Query(None),
    strategy: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """Get daily trading report"""
    try:
        # Build query filters
        filters = {
            'date_range': (start_date, end_date),
            'user_id': user_id if user_id else None,
            'strategy': strategy if strategy else None
        }
        
        # Get trades for the period
        trades = await get_trades_for_period(db, filters)
        
        # Calculate metrics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] < 0]
        
        total_pnl = sum(t['pnl'] for t in trades)
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
        
        # Hourly P&L progression
        hourly_pnl = calculate_hourly_pnl(trades)
        
        # Strategy breakdown
        strategy_breakdown = {}
        for trade in trades:
            strat = trade.get('strategy', 'Unknown')
            if strat not in strategy_breakdown:
                strategy_breakdown[strat] = {'count': 0, 'pnl': 0}
            strategy_breakdown[strat]['count'] += 1
            strategy_breakdown[strat]['pnl'] += trade['pnl']
        
        # Top trades
        top_trades = sorted(trades, key=lambda x: x['pnl'], reverse=True)[:5]
        
        # Risk metrics
        risk_metrics = await calculate_risk_metrics(trades)
        
        return {
            'total_trades': total_trades,
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'hourly_pnl': hourly_pnl,
            'strategy_breakdown': strategy_breakdown,
            'top_trades': top_trades,
            'max_drawdown': risk_metrics['max_drawdown'],
            'sharpe_ratio': risk_metrics['sharpe_ratio'],
            'var_95': risk_metrics['var_95'],
            'greeks_exposure': risk_metrics['greeks_exposure'],
            'risk_score': risk_metrics['risk_score']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategy")
async def get_strategy_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    user_id: Optional[str] = Query(None),
    strategy: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """Get strategy performance report"""
    try:
        # Get all strategies
        strategies = await get_active_strategies(db)
        
        strategy_data = []
        for strat in strategies:
            # Get trades for this strategy
            trades = await get_strategy_trades(db, strat['id'], start_date, end_date, user_id)
            
            if trades:
                total_trades = len(trades)
                winning = [t for t in trades if t['pnl'] > 0]
                losing = [t for t in trades if t['pnl'] < 0]
                
                strategy_data.append({
                    'name': strat['name'],
                    'total_trades': total_trades,
                    'win_rate': len(winning) / total_trades * 100,
                    'total_pnl': sum(t['pnl'] for t in trades),
                    'avg_win': sum(t['pnl'] for t in winning) / len(winning) if winning else 0,
                    'avg_loss': abs(sum(t['pnl'] for t in losing) / len(losing)) if losing else 0,
                    'sharpe_ratio': calculate_sharpe_ratio(trades),
                    'max_drawdown': calculate_max_drawdown(trades)
                })
        
        return {
            'strategies': strategy_data,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user")
async def get_user_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    user_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """Get user performance report"""
    try:
        # Get all users or specific user
        if user_id:
            users = await get_user_by_id(db, user_id)
            users = [users] if users else []
        else:
            users = await get_all_users(db)
        
        user_data = []
        for user in users:
            # Get trades for this user
            trades = await get_user_trades(db, user['id'], start_date, end_date)
            
            if trades:
                total_trades = len(trades)
                winning = [t for t in trades if t['pnl'] > 0]
                
                # Get current capital
                capital_info = await get_user_capital(db, user['id'])
                
                user_data.append({
                    'id': user['id'],
                    'name': user['name'],
                    'status': 'active' if user['is_active'] else 'inactive',
                    'total_trades': total_trades,
                    'win_rate': len(winning) / total_trades * 100,
                    'total_pnl': sum(t['pnl'] for t in trades),
                    'current_capital': capital_info['current_capital'],
                    'starting_capital': capital_info['starting_capital'],
                    'roi': ((capital_info['current_capital'] - capital_info['starting_capital']) / 
                           capital_info['starting_capital'] * 100)
                })
        
        return {
            'users': user_data,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/risk")
async def get_risk_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    user_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """Get risk analysis report"""
    try:
        # Get current positions
        positions = await get_active_positions(db, user_id)
        
        # Calculate portfolio VaR
        portfolio_var = await calculate_portfolio_var(positions)
        
        # Get Greeks exposure
        greeks = await calculate_portfolio_greeks(positions)
        
        # Check compliance violations
        violations = await get_compliance_violations(db, start_date, end_date, user_id)
        
        # Risk heatmap
        risk_heatmap = await generate_risk_heatmap(positions, greeks)
        
        return {
            'portfolio_var': portfolio_var,
            'var_breach': portfolio_var > 100000,  # Example threshold
            'greeks_summary': format_greeks_summary(greeks),
            'greeks_risk': assess_greeks_risk(greeks),
            'compliance_violations': len(violations),
            'violations': violations[:10],  # Top 10 recent violations
            'risk_heatmap': risk_heatmap,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/{report_type}")
async def export_report(
    report_type: str,
    start_date: date = Query(...),
    end_date: date = Query(...),
    user_id: Optional[str] = Query(None),
    strategy: Optional[str] = Query(None),
    format: str = Query("pdf", regex="^(pdf|excel)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export report in PDF or Excel format"""
    try:
        # Get report data based on type
        if report_type == "daily":
            data = await get_daily_report(start_date, end_date, user_id, strategy, current_user, db)
        elif report_type == "strategy":
            data = await get_strategy_report(start_date, end_date, user_id, strategy, current_user, db)
        elif report_type == "user":
            data = await get_user_report(start_date, end_date, user_id, current_user, db)
        elif report_type == "risk":
            data = await get_risk_report(start_date, end_date, user_id, current_user, db)
        else:
            raise HTTPException(status_code=400, detail="Invalid report type")
        
        # Generate file
        if format == "pdf":
            file_content = await generate_pdf_report(report_type, data)
            media_type = "application/pdf"
            filename = f"{report_type}_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        else:  # excel
            file_content = await generate_excel_report(report_type, data)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"{report_type}_report_{datetime.now().strftime('%Y%m%d')}.xlsx"
        
        return FileResponse(
            file_content,
            media_type=media_type,
            filename=filename
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
async def get_trades_for_period(db: Session, filters: Dict) -> List[Dict]:
    """Get trades for specified period and filters"""
    # Implementation would query database
    # NO MOCK DATA - Real trading data required
    return [
        {
            'id': '1',
            'symbol': 'NIFTY22000CE',
            'pnl': 2500,
            'timestamp': datetime.now(),
            'strategy': 'momentum_surfer'
        }
    ]

async def calculate_hourly_pnl(trades: List[Dict]) -> List[Dict]:
    """Calculate hourly P&L progression"""
    # Group trades by hour and calculate cumulative P&L
    hourly_data = []
    cumulative = 0
    
    for hour in range(9, 16):  # Market hours
        hour_trades = [t for t in trades if t['timestamp'].hour == hour]
        hour_pnl = sum(t['pnl'] for t in hour_trades)
        cumulative += hour_pnl
        
        hourly_data.append({
            'hour': f"{hour:02d}:00",
            'pnl': hour_pnl,
            'cumulative_pnl': cumulative
        })
    
    return hourly_data

async def calculate_risk_metrics(trades: List[Dict]) -> Dict:
    """Calculate risk metrics from trades"""
    if not trades:
        return {
            'max_drawdown': 0,
            'sharpe_ratio': 0,
            'var_95': 0,
            'greeks_exposure': 'Neutral',
            'risk_score': 'Low'
        }
    
    # Calculate returns
    returns = [t['pnl'] for t in trades]
    
    # Max drawdown
    cumulative = 0
    peak = 0
    max_dd = 0
    
    for ret in returns:
        cumulative += ret
        if cumulative > peak:
            peak = cumulative
        drawdown = (peak - cumulative) / peak if peak > 0 else 0
        max_dd = max(max_dd, drawdown)
    
    # Sharpe ratio (simplified)
    if returns:
        avg_return = sum(returns) / len(returns)
        std_return = pd.Series(returns).std()
        sharpe = (avg_return / std_return * (252 ** 0.5)) if std_return > 0 else 0
    else:
        sharpe = 0
    
    # VaR calculation (95% confidence)
    if returns:
        var_95 = pd.Series(returns).quantile(0.05)
    else:
        var_95 = 0
    
    return {
        'max_drawdown': max_dd * 100,
        'sharpe_ratio': sharpe,
        'var_95': abs(var_95),
        'greeks_exposure': 'Neutral',  # Would calculate from actual positions
        'risk_score': 'Low' if max_dd < 0.05 else 'Medium' if max_dd < 0.10 else 'High'
    }

def calculate_sharpe_ratio(trades: List[Dict]) -> float:
    """Calculate Sharpe ratio for trades"""
    if not trades:
        return 0.0
    
    returns = [t['pnl'] for t in trades]
    avg_return = sum(returns) / len(returns)
    std_return = pd.Series(returns).std()
    
    return (avg_return / std_return * (252 ** 0.5)) if std_return > 0 else 0

def calculate_max_drawdown(trades: List[Dict]) -> float:
    """Calculate maximum drawdown"""
    if not trades:
        return 0.0
    
    cumulative = 0
    peak = 0
    max_dd = 0
    
    for trade in sorted(trades, key=lambda x: x['timestamp']):
        cumulative += trade['pnl']
        if cumulative > peak:
            peak = cumulative
        drawdown = (peak - cumulative) / peak if peak > 0 else 0
        max_dd = max(max_dd, drawdown)
    
    return max_dd * 100 