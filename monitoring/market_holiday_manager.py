"""
Market Holiday Manager
Manages market holidays and trading sessions
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, date, timedelta
import json
import os
from pathlib import Path
import pytz

logger = logging.getLogger(__name__)

class MarketHolidayManager:
    """Manages market holidays and trading sessions"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.timezone = pytz.timezone(config.get('timezone', 'Asia/Kolkata'))
        self.holidays: Set[date] = set()
        self.special_sessions: Dict[date, Dict] = {}
        self.holiday_file = Path(config.get('holiday_file', 'config/holidays.json'))
        self._load_holidays()
    
    def _load_holidays(self):
        """Load holidays from file"""
        try:
            if self.holiday_file.exists():
                with open(self.holiday_file, 'r') as f:
                    data = json.load(f)
                    self.holidays = {date.fromisoformat(d) for d in data.get('holidays', [])}
                    self.special_sessions = {
                        date.fromisoformat(d): session
                        for d, session in data.get('special_sessions', {}).items()
                    }
                logger.info(f"Loaded {len(self.holidays)} holidays and {len(self.special_sessions)} special sessions")
            else:
                logger.warning(f"Holiday file not found: {self.holiday_file}")
        except Exception as e:
            logger.error(f"Error loading holidays: {e}")
    
    def _save_holidays(self):
        """Save holidays to file"""
        try:
            data = {
                'holidays': [d.isoformat() for d in sorted(self.holidays)],
                'special_sessions': {
                    d.isoformat(): session
                    for d, session in sorted(self.special_sessions.items())
                }
            }
            
            self.holiday_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.holiday_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info("Holidays saved successfully")
        except Exception as e:
            logger.error(f"Error saving holidays: {e}")
    
    def is_holiday(self, check_date: date) -> bool:
        """Check if date is a holiday"""
        return check_date in self.holidays
    
    def is_trading_day(self, check_date: date) -> bool:
        """Check if date is a trading day"""
        if self.is_holiday(check_date):
            return False
        
        # Check if it's a weekend
        if check_date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            return False
        
        return True
    
    def get_trading_hours(self, check_date: date) -> Optional[Dict]:
        """Get trading hours for a date"""
        if not self.is_trading_day(check_date):
            return None
        
        # Check for special session
        if check_date in self.special_sessions:
            return self.special_sessions[check_date]
        
        # Default trading hours
        return {
            'pre_market': '09:00',
            'market_open': '09:15',
            'market_close': '15:30',
            'post_market': '16:00'
        }
    
    def add_holiday(self, holiday_date: date, reason: str = None):
        """Add a holiday"""
        self.holidays.add(holiday_date)
        if reason:
            logger.info(f"Added holiday: {holiday_date} - {reason}")
        self._save_holidays()
    
    def remove_holiday(self, holiday_date: date):
        """Remove a holiday"""
        if holiday_date in self.holidays:
            self.holidays.remove(holiday_date)
            logger.info(f"Removed holiday: {holiday_date}")
            self._save_holidays()
    
    def add_special_session(self, session_date: date, hours: Dict):
        """Add a special trading session"""
        self.special_sessions[session_date] = hours
        logger.info(f"Added special session for {session_date}: {hours}")
        self._save_holidays()
    
    def remove_special_session(self, session_date: date):
        """Remove a special trading session"""
        if session_date in self.special_sessions:
            del self.special_sessions[session_date]
            logger.info(f"Removed special session for {session_date}")
            self._save_holidays()
    
    def get_next_trading_day(self, from_date: date = None) -> date:
        """Get the next trading day"""
        if from_date is None:
            from_date = datetime.now(self.timezone).date()
        
        check_date = from_date + timedelta(days=1)
        while not self.is_trading_day(check_date):
            check_date += timedelta(days=1)
        
        return check_date
    
    def get_previous_trading_day(self, from_date: date = None) -> date:
        """Get the previous trading day"""
        if from_date is None:
            from_date = datetime.now(self.timezone).date()
        
        check_date = from_date - timedelta(days=1)
        while not self.is_trading_day(check_date):
            check_date -= timedelta(days=1)
        
        return check_date
    
    def get_trading_days_between(self, start_date: date, end_date: date) -> List[date]:
        """Get all trading days between two dates"""
        trading_days = []
        current_date = start_date
        
        while current_date <= end_date:
            if self.is_trading_day(current_date):
                trading_days.append(current_date)
            current_date += timedelta(days=1)
        
        return trading_days
    
    def is_market_open(self, check_time: datetime = None) -> bool:
        """Check if market is currently open"""
        if check_time is None:
            check_time = datetime.now(self.timezone)
        
        check_date = check_time.date()
        if not self.is_trading_day(check_date):
            return False
        
        trading_hours = self.get_trading_hours(check_date)
        if not trading_hours:
            return False
        
        current_time = check_time.time()
        market_open = datetime.strptime(trading_hours['market_open'], '%H:%M').time()
        market_close = datetime.strptime(trading_hours['market_close'], '%H:%M').time()
        
        return market_open <= current_time <= market_close
    
    def get_market_status(self) -> Dict:
        """Get current market status"""
        now = datetime.now(self.timezone)
        today = now.date()
        
        status = {
            'date': today.isoformat(),
            'time': now.strftime('%H:%M:%S'),
            'is_trading_day': self.is_trading_day(today),
            'is_holiday': self.is_holiday(today),
            'is_market_open': self.is_market_open(now)
        }
        
        if status['is_trading_day']:
            trading_hours = self.get_trading_hours(today)
            status.update({
                'trading_hours': trading_hours,
                'next_trading_day': self.get_next_trading_day(today).isoformat(),
                'previous_trading_day': self.get_previous_trading_day(today).isoformat()
            })
        
        return status 