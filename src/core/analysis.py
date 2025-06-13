from typing import Dict, Any
import numpy as np
from datetime import datetime, timedelta

def calculate_moving_averages(prices: list, periods: list = [20, 50, 200]) -> Dict[int, float]:
    """Calculate moving averages for given periods."""
    return {period: np.mean(prices[-period:]) for period in periods if len(prices) >= period}

def calculate_rsi(prices: list, period: int = 14) -> float:
    """Calculate Relative Strength Index."""
    if len(prices) < period + 1:
        return 50.0
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_macd(prices: list) -> Dict[str, float]:
    """Calculate MACD (Moving Average Convergence Divergence)."""
    if len(prices) < 26:
        return {'macd': 0, 'signal': 0, 'histogram': 0}
    
    ema12 = np.mean(prices[-12:])
    ema26 = np.mean(prices[-26:])
    macd = ema12 - ema26
    signal = np.mean(prices[-9:])
    histogram = macd - signal
    
    return {
        'macd': macd,
        'signal': signal,
        'histogram': histogram
    }

def analyze_volume(volumes: list) -> str:
    """Analyze volume trend."""
    if len(volumes) < 20:
        return "NEUTRAL"
    
    recent_volume = np.mean(volumes[-5:])
    historical_volume = np.mean(volumes[-20:])
    
    if recent_volume > historical_volume * 1.5:
        return "HIGH"
    elif recent_volume < historical_volume * 0.5:
        return "LOW"
    else:
        return "NORMAL"

def analyze_stock(market_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Analyze stock data and return analysis results.
    
    Args:
        market_data: Dictionary containing price and volume data
        
    Returns:
        Dictionary containing analysis results
    """
    prices = market_data['prices']
    volumes = market_data['volumes']
    
    # Calculate technical indicators
    ma = calculate_moving_averages(prices)
    rsi = calculate_rsi(prices)
    macd = calculate_macd(prices)
    
    # Determine trend
    current_price = prices[-1]
    trend = "NEUTRAL"
    strength = "MODERATE"
    
    if current_price > ma[200]:
        trend = "BULLISH"
        if current_price > ma[50] and current_price > ma[20]:
            strength = "STRONG"
    elif current_price < ma[200]:
        trend = "BEARISH"
        if current_price < ma[50] and current_price < ma[20]:
            strength = "STRONG"
    
    # Determine momentum
    momentum = "NEUTRAL"
    if rsi > 70:
        momentum = "OVERBOUGHT"
    elif rsi < 30:
        momentum = "OVERSOLD"
    elif rsi > 50:
        momentum = "BULLISH"
    else:
        momentum = "BEARISH"
    
    # Analyze volume
    volume_trend = analyze_volume(volumes)
    
    return {
        'trend': trend,
        'strength': strength,
        'momentum': momentum,
        'volume_trend': volume_trend,
        'rsi': rsi,
        'macd': macd
    }

def calculate_trade_quality(
    market_data: Dict[str, Any],
    analysis: Dict[str, Any],
    risk_metrics: Dict[str, float],
    risk_reward_ratio: float
) -> float:
    """
    Calculate trade quality score (0-10).
    Only returns 10 for perfect setups.
    
    Args:
        market_data: Market data dictionary
        analysis: Technical analysis results
        risk_metrics: Risk metrics dictionary
        risk_reward_ratio: Risk to reward ratio
        
    Returns:
        Float between 0 and 10
    """
    score = 0.0
    
    # 1. Trend Alignment (2 points)
    if analysis['trend'] in ['BULLISH', 'BEARISH'] and analysis['strength'] == 'STRONG':
        score += 2.0
    
    # 2. Volume Confirmation (2 points)
    if analysis['volume_trend'] == 'HIGH':
        score += 2.0
    
    # 3. Risk/Reward Ratio (2 points)
    if risk_reward_ratio >= 3.0:
        score += 2.0
    
    # 4. Market Conditions (2 points)
    if risk_metrics['market_correlation'] < 0.3:
        score += 2.0
    
    # 5. Technical Indicators (2 points)
    if (analysis['momentum'] in ['BULLISH', 'BEARISH'] and 
        abs(analysis['rsi'] - 50) > 20 and 
        abs(analysis['macd']['histogram']) > 0):
        score += 2.0
    
    # Only return 10 if all criteria are met
    return 10.0 if score == 10.0 else score 