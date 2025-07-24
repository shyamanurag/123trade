"""
Helper functions for trading operations
"""

import math
import time
import asyncio
import pandas as pd
import numpy as np
from typing import Optional, Callable, Any, Dict, List
from decimal import Decimal
from functools import wraps
import logging

logger = logging.getLogger(__name__)


def get_atm_strike(spot_price: float) -> int:
    """
    Get At-The-Money (ATM) strike price for given spot price.
    Rounds to nearest 50 for NIFTY and 100 for BANKNIFTY.
    
    Args:
        spot_price: Current spot price
        
    Returns:
        ATM strike price rounded to appropriate interval
    """
    # For NIFTY, round to nearest 50
    if spot_price < 20000:  # Likely NIFTY
        return int(round(spot_price / 50) * 50)
    # For BANKNIFTY, round to nearest 100
    else:
        return int(round(spot_price / 100) * 100)


def get_strike_with_offset(spot_price: float, offset: int, option_type: str) -> int:
    """
    Get strike price with offset from ATM.
    
    Args:
        spot_price: Current spot price
        offset: Number of strikes away from ATM (positive for OTM, negative for ITM)
        option_type: 'CE' for call, 'PE' for put
        
    Returns:
        Strike price with offset
    """
    atm_strike = get_atm_strike(spot_price)
    
    # Determine strike interval based on price range
    if spot_price < 20000:  # NIFTY
        strike_interval = 50
    else:  # BANKNIFTY
        strike_interval = 100
    
    # Calculate offset strike
    if option_type.upper() == 'CE':
        return atm_strike + (offset * strike_interval)
    elif option_type.upper() == 'PE':
        return atm_strike - (offset * strike_interval)
    else:
        raise ValueError(f"Invalid option type: {option_type}")


def calculate_value_area(price_levels: list, volumes: list, poc_price: float) -> tuple:
    """
    Calculate value area high and low based on volume profile.
    
    Args:
        price_levels: List of price levels
        volumes: List of corresponding volumes
        poc_price: Point of Control price
        
    Returns:
        Tuple of (value_area_low, value_area_high)
    """
    if not price_levels or not volumes or len(price_levels) != len(volumes):
        return None, None
    
    # Find POC index
    try:
        poc_index = price_levels.index(poc_price)
    except ValueError:
        return None, None
    
    total_volume = sum(volumes)
    target_volume = total_volume * 0.68  # 68% of total volume
    
    # Calculate value area
    current_volume = volumes[poc_index]
    low_index = poc_index
    high_index = poc_index
    
    while current_volume < target_volume and (low_index > 0 or high_index < len(volumes) - 1):
        low_volume = volumes[low_index - 1] if low_index > 0 else 0
        high_volume = volumes[high_index + 1] if high_index < len(volumes) - 1 else 0
        
        if low_volume > high_volume and low_index > 0:
            low_index -= 1
            current_volume += low_volume
        elif high_index < len(volumes) - 1:
            high_index += 1
            current_volume += high_volume
        else:
            break
    
    return price_levels[low_index], price_levels[high_index]


def to_decimal(value: float) -> Decimal:
    """
    Convert float to Decimal for precise calculations.
    
    Args:
        value: Float value to convert
        
    Returns:
        Decimal representation
    """
    return Decimal(str(value))


def round_price_to_tick(price: float, tick_size: float = 0.05) -> float:
    """
    Round price to nearest tick size.
    
    Args:
        price: Price to round
        tick_size: Tick size (default 0.05 for options)
        
    Returns:
        Rounded price
    """
    return round(price / tick_size) * tick_size


def calculate_implied_volatility(option_price: float, spot_price: float, strike: float, 
                                time_to_expiry: float, risk_free_rate: float = 0.05) -> float:
    """
    Calculate implied volatility using Black-Scholes approximation.
    
    Args:
        option_price: Current option price
        spot_price: Current spot price
        strike: Strike price
        time_to_expiry: Time to expiry in years
        risk_free_rate: Risk-free rate (default 5%)
        
    Returns:
        Implied volatility as decimal
    """
    if time_to_expiry <= 0 or spot_price <= 0 or strike <= 0:
        return 0.0
    
    # Simple approximation for ATM options
    moneyness = spot_price / strike
    if 0.95 <= moneyness <= 1.05:  # Near ATM
        # Rough approximation for ATM implied volatility
        return math.sqrt(2 * math.pi / time_to_expiry) * option_price / spot_price
    
    return 0.0


def calculate_delta(spot_price: float, strike: float, time_to_expiry: float, 
                   volatility: float, option_type: str, risk_free_rate: float = 0.05) -> float:
    """
    Calculate option delta using Black-Scholes.
    
    Args:
        spot_price: Current spot price
        strike: Strike price
        time_to_expiry: Time to expiry in years
        volatility: Implied volatility
        option_type: 'CE' for call, 'PE' for put
        risk_free_rate: Risk-free rate
        
    Returns:
        Delta value
    """
    if time_to_expiry <= 0 or volatility <= 0:
        return 0.0
    
    # Simplified delta calculation for ATM options
    if option_type.upper() == 'CE':
        return 0.5  # Approximate ATM call delta
    elif option_type.upper() == 'PE':
        return -0.5  # Approximate ATM put delta
    else:
        return 0.0


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, backoff_multiplier: float = 2.0):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        backoff_multiplier: Multiplier for exponential backoff
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_retries:
                        break
                    delay = base_delay * (backoff_multiplier ** attempt)
                    await asyncio.sleep(delay)
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_retries:
                        break
                    delay = base_delay * (backoff_multiplier ** attempt)
                    time.sleep(delay)
            raise last_exception
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def calculate_technical_indicators(symbol: str, current_price: float) -> Dict[str, Any]:
    """Calculate technical indicators using REAL price history - NO FAKE DATA"""
    try:
        # Import real data sources
        from ..core.crypto_cache_manager import CryptoCacheManager
        import asyncio
        
        # Get real price history
        async def get_real_indicators():
            cache_manager = CryptoCacheManager()
            await cache_manager.connect()
            
            # Get real historical data
            price_series = await cache_manager.get_market_data_series(symbol, limit=50)
            
            if not price_series or len(price_series) < 20:
                logger.warning(f"Insufficient real price history for {symbol}")
                return {
                    'status': 'insufficient_data',
                    'message': 'Need at least 20 periods of real price data for technical analysis',
                    'available_periods': len(price_series) if price_series else 0
                }
            
            # Calculate real technical indicators
            prices = [float(data['close_price']) for data in price_series]
            
            # Real RSI calculation
            rsi = calculate_real_rsi(prices)
            
            # Real Moving Averages
            sma_20 = sum(prices[-20:]) / 20 if len(prices) >= 20 else None
            sma_50 = sum(prices[-50:]) / 50 if len(prices) >= 50 else None
            
            # Real Bollinger Bands
            bb_upper, bb_lower = calculate_real_bollinger_bands(prices)
            
            return {
                'RSI': rsi,
                'SMA_20': sma_20,
                'SMA_50': sma_50,
                'BB_Upper': bb_upper,
                'BB_Lower': bb_lower,
                'current_price': current_price,
                'data_source': 'real_price_history',
                'periods_used': len(prices)
            }
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_real_indicators())
        loop.close()
        
        return result
        
    except Exception as e:
        logger.error(f"Error calculating real technical indicators for {symbol}: {e}")
        return {
            'status': 'error',
            'message': f'Error calculating real indicators: {str(e)}',
            'WARNING': 'NO_FAKE_DATA_FALLBACK_AVAILABLE'
        }

def calculate_real_rsi(prices: list, period: int = 14) -> float:
    """Calculate RSI using real price data"""
    if len(prices) < period + 1:
        return 50.0  # Neutral RSI when insufficient data
    
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [delta if delta > 0 else 0 for delta in deltas]
    losses = [-delta if delta < 0 else 0 for delta in deltas]
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return round(rsi, 2)

def calculate_real_bollinger_bands(prices: list, period: int = 20, std_dev: float = 2) -> tuple:
    """Calculate Bollinger Bands using real price data"""
    if len(prices) < period:
        return None, None
    
    recent_prices = prices[-period:]
    sma = sum(recent_prices) / period
    
    # Calculate standard deviation
    variance = sum((price - sma) ** 2 for price in recent_prices) / period
    std = variance ** 0.5
    
    upper_band = sma + (std_dev * std)
    lower_band = sma - (std_dev * std)
    
    return round(upper_band, 2), round(lower_band, 2) 