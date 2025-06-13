"""
TrueData API Configuration with Trial106 credentials
"""

import os
from typing import List, Dict, Optional

class TrueDataConfig:
    """TrueData API configuration for Trial106 account"""
    
    # Trial106 Account Credentials
    USERNAME = "Trial106"
    PASSWORD = "shyam106"
    REALTIME_PORT = 8086
    
    # Connection Settings
    STREAMING_TYPE = "Real-Time + History"
    TIMEFRAME = "Tick"
    SYMBOL_LIMIT = 50
    EXPIRY_DATE = "15/06/2025"
    
    # Available Segments for Trial106
    SEGMENTS = [
        "NSE Equity",
        "NSE F&O", 
        "Indices",
        "MCX",
        "BSE EQ",
        "BSE F&O",
        "BSE Indices"
    ]
    
    # Primary symbols to track (within 50 symbol limit for trial)
    PRIMARY_SYMBOLS = [
        # Major Indices (Priority 1)
        "NIFTY",
        "BANKNIFTY", 
        "FINNIFTY",
        
        # Top NSE Stocks (Priority 2)
        "RELIANCE",
        "TCS",
        "HDFCBANK", 
        "INFY",
        "HINDUNILVR",
        "ICICIBANK",
        "KOTAKBANK",
        "ITC",
        "LT",
        "SBIN",
        "BHARTIARTL",
        "ASIANPAINT",
        "HCLTECH",
        "AXISBANK",
        "MARUTI",
        "BAJFINANCE",
        
        # F&O Favorites (Priority 3)
        "WIPRO",
        "TECHM",
        "TITAN",
        "ULTRACEMCO",
        "NESTLEIND",
        "POWERGRID",
        "NTPC",
        "COALINDIA",
        "SUNPHARMA",
        "DRREDDY",
        
        # Additional tracking
        "BAJAJFINSV",
        "ONGC",
        "TATAMOTORS",
        "DIVISLAB",
        "BRITANNIA",
        "HINDALCO",
        "ADANIENT",
        "JSWSTEEL",
        "GRASIM",
        "CIPLA",
        "EICHERMOT",
        "BPCL",
        "SHREECEM",
        "TATACONSUM",
        "APOLLOHOSP",
        "TATASTEEL",
        "HEROMOTOCO",
        "UPL",
        "BAJAJ-AUTO"
    ]
    
    @classmethod
    def get_connection_config(cls) -> Dict:
        """Get connection configuration for TrueData"""
        return {
            'username': cls.USERNAME,
            'password': cls.PASSWORD,
            'live_port': cls.REALTIME_PORT,
            'url': 'push.truedata.in',
            'is_sandbox': False,  # Trial account is not sandbox
            'log_level': 'INFO',
            'max_connection_attempts': 3,
            'connection_timeout': 30,
            'max_symbols': cls.SYMBOL_LIMIT,
            'allowed_symbols': cls.PRIMARY_SYMBOLS,
            'segments': cls.SEGMENTS
        }
    
    @classmethod
    def get_symbols_within_limit(cls, additional_symbols: Optional[List[str]] = None) -> List[str]:
        """Get symbols within the 50 symbol limit"""
        symbols = cls.PRIMARY_SYMBOLS.copy()
        
        if additional_symbols is not None:
            # Add additional symbols up to limit
            remaining_slots = cls.SYMBOL_LIMIT - len(symbols)
            if remaining_slots > 0:
                symbols.extend(additional_symbols[:remaining_slots])
        
        return symbols[:cls.SYMBOL_LIMIT]
    
    @classmethod
    def validate_symbol_limit(cls, symbols: List[str]) -> bool:
        """Validate if symbols are within trial limit"""
        return len(symbols) <= cls.SYMBOL_LIMIT
    
    @classmethod
    def get_websocket_url(cls) -> str:
        """Get WebSocket URL for TrueData connection"""
        return f"wss://push.truedata.in:{cls.REALTIME_PORT}"
    
    @classmethod
    def is_symbol_allowed(cls, symbol: str) -> bool:
        """Check if symbol is in allowed list for trial"""
        return symbol in cls.PRIMARY_SYMBOLS
    
    @classmethod
    def get_api_endpoints(cls) -> Dict[str, str]:
        """Get API endpoints for TrueData"""
        return {
            'websocket': f"wss://push.truedata.in:{cls.REALTIME_PORT}",
            'rest_api': "https://api.truedata.in",
            'historical': "https://api.truedata.in/gethistoricaldata",
            'symbols': "https://api.truedata.in/getsymbollist",
            'symbol_info': "https://api.truedata.in/getsymbolinfo"
        }
    
    @classmethod
    def get_trial_info(cls) -> Dict:
        """Get trial account information"""
        return {
            'username': cls.USERNAME,
            'account_type': 'Trial',
            'symbol_limit': cls.SYMBOL_LIMIT,
            'expiry_date': cls.EXPIRY_DATE,
            'segments': cls.SEGMENTS,
            'streaming_type': cls.STREAMING_TYPE,
            'timeframe': cls.TIMEFRAME,
            'symbols_configured': len(cls.PRIMARY_SYMBOLS),
            'remaining_slots': cls.SYMBOL_LIMIT - len(cls.PRIMARY_SYMBOLS)
        }

# Export configuration
TRUEDATA_CONFIG = TrueDataConfig.get_connection_config()
AVAILABLE_SYMBOLS = TrueDataConfig.get_symbols_within_limit()
TRIAL_INFO = TrueDataConfig.get_trial_info() 