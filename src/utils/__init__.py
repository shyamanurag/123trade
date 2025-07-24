# Trading System Utilities

def get_atm_strike(spot_price: float, strike_interval: float = 50.0) -> float:
    """Get At-The-Money strike price"""
    return round(spot_price / strike_interval) * strike_interval

def get_strike_with_offset(atm_strike: float, offset: int, strike_interval: float = 50.0) -> float:
    """Get strike price with offset from ATM"""
    return atm_strike + (offset * strike_interval)