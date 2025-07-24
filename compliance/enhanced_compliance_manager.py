"""
Enhanced compliance management with post-trade surveillance and reporting
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import pandas as pd
import numpy as np
from collections import defaultdict
import redis.asyncio as redis
import pytz
from cryptography.fernet import Fernet
from dataclasses import dataclass
import aiofiles
import zipfile

logger = logging.getLogger(__name__)

@dataclass
class ComplianceAlert:
    timestamp: datetime
    alert_type: str
    severity: str  # INFO, WARNING, CRITICAL
    symbol: str
    details: Dict
    action_taken: Optional[str] = None
    resolved: bool = False

class PostTradeSurveillance:
    """Post-trade surveillance and pattern detection"""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Surveillance parameters
        self.wash_trade_window = config.get('wash_trade_window', 300)  # 5 minutes
        self.layering_threshold = config.get('layering_threshold', 5)
        self.manipulation_patterns = config.get('manipulation_patterns', [])
        
        # Tracking
        self.trade_history = defaultdict(list)
        self.order_patterns = defaultdict(list)
        self.alerts = []

    async def analyze_trade(self, trade: Dict) -> List[ComplianceAlert]:
        """Analyze trade for compliance violations"""
        alerts = []
        
        # Check wash trading
        wash_alert = await self._check_wash_trading(trade)
        if wash_alert:
            alerts.append(wash_alert)
        
        # Check position limits
        limit_alert = await self._check_position_limits(trade)
        if limit_alert:
            alerts.append(limit_alert)
        
        # Check price manipulation
        manipulation_alert = await self._check_manipulation(trade)
        if manipulation_alert:
            alerts.append(manipulation_alert)
        
        # Check order-to-trade ratio
        ratio_alert = await self._check_order_trade_ratio(trade)
        if ratio_alert:
            alerts.append(ratio_alert)
        
        # Store trade for pattern analysis
        self.trade_history[trade['symbol']].append(trade)
        
        return alerts

    async def _check_wash_trading(self, trade: Dict) -> Optional[ComplianceAlert]:
        """Detect potential wash trading"""
        symbol = trade['symbol']
        trade_time = trade['timestamp']
        
        # Get recent trades for symbol
        recent_trades = [
            t for t in self.trade_history[symbol]
            if (trade_time - t['timestamp']).total_seconds() < self.wash_trade_window
        ]
        
        # Check for offsetting trades
        for prev_trade in recent_trades:
            if (prev_trade['side'] != trade['side'] and 
                abs(prev_trade['quantity'] - trade['quantity']) < 10 and
                abs(prev_trade['price'] - trade['price']) / trade['price'] < 0.001):
                
                return ComplianceAlert(
                    timestamp=datetime.now(),
                    alert_type='WASH_TRADING',
                    severity='CRITICAL',
                    symbol=symbol,
                    details={
                        'current_trade': trade,
                        'offsetting_trade': prev_trade,
                        'time_diff': (trade_time - prev_trade['timestamp']).total_seconds()
                    }
                )
        
        return None

    async def _check_position_limits(self, trade: Dict) -> Optional[ComplianceAlert]:
        """Check if trade violates position limits"""
        # This would check against exchange/regulatory limits
        # Simplified example
        if trade['quantity'] > 5000:  # Example limit
            return ComplianceAlert(
                timestamp=datetime.now(),
                alert_type='POSITION_LIMIT_BREACH',
                severity='WARNING',
                symbol=trade['symbol'],
                details={
                    'trade_quantity': trade['quantity'],
                    'limit': 5000,
                    'excess': trade['quantity'] - 5000
                }
            )
        
        return None

    async def _check_manipulation(self, trade: Dict) -> Optional[ComplianceAlert]:
        """Detect potential price manipulation patterns"""
        symbol = trade['symbol']
        
        # Check for rapid price movements
        recent_trades = self.trade_history[symbol][-20:]
        if len(recent_trades) >= 5:
            prices = [t['price'] for t in recent_trades]
            price_volatility = np.std(prices) / np.mean(prices)
            
            if price_volatility > 0.05:  # 5% volatility threshold
                return ComplianceAlert(
                    timestamp=datetime.now(),
                    alert_type='PRICE_MANIPULATION',
                    severity='WARNING',
                    symbol=symbol,
                    details={
                        'volatility': price_volatility,
                        'recent_prices': prices[-5:],
                        'trade_count': len(recent_trades)
                    }
                )
        
        return None

    async def _check_order_trade_ratio(self, trade: Dict) -> Optional[ComplianceAlert]:
        """Check order-to-trade ratio for layering/spoofing"""
        symbol = trade['symbol']
        
        # Get orders and trades in last hour
        recent_orders = self.order_patterns[symbol]
        recent_trades = [t for t in self.trade_history[symbol] 
                        if (datetime.now() - t['timestamp']).seconds < 3600]
        
        if len(recent_orders) > 0 and len(recent_trades) > 0:
            ratio = len(recent_orders) / len(recent_trades)
            
            if ratio > 10:  # High order-to-trade ratio
                return ComplianceAlert(
                    timestamp=datetime.now(),
                    alert_type='HIGH_ORDER_TRADE_RATIO',
                    severity='WARNING',
                    symbol=symbol,
                    details={
                        'order_count': len(recent_orders),
                        'trade_count': len(recent_trades),
                        'ratio': ratio
                    }
                )
        
        return None

class DataRetentionManager:
    """Manage data retention and archival with compliance requirements"""
    
    def __init__(self, config: Dict, redis_client):
        self.config = config
        self.redis = redis_client
        
        # Retention periods (in days)
        self.retention_periods = {
            'orders': config.get('order_retention_days', 2555),  # 7 years
            'trades': config.get('trade_retention_days', 2555),  # 7 years
            'positions': config.get('position_retention_days', 365),  # 1 year
            'market_data': config.get('market_data_retention_days', 90),  # 3 months
            'logs': config.get('log_retention_days', 180),  # 6 months
            'alerts': config.get('alert_retention_days', 1825)  # 5 years
        }
        
        # Archive settings
        self.archive_path = config.get('archive_path', './archives')
        self.compression_enabled = config.get('compression_enabled', True)
        self.encryption_enabled = config.get('encryption_enabled', True)
        
        # Ensure archive directory exists
        os.makedirs(self.archive_path, exist_ok=True)

    async def archive_daily_data(self, date: datetime):
        """Archive data for a specific date"""
        logger.info(f"Starting data archival for {date.date()}")
        
        try:
            # Archive different data types
            await self._archive_orders(date)
            await self._archive_trades(date)
            await self._archive_positions(date)
            await self._archive_market_data(date)
            await self._archive_logs(date)
            
            # Create compliance report
            await self._create_compliance_report(date)
            
            # Clean up old data
            await self._cleanup_expired_data()
            
            logger.info(f"Data archival completed for {date.date()}")
            
        except Exception as e:
            logger.error(f"Data archival failed: {e}")
            raise

    async def _archive_orders(self, date: datetime):
        """Archive order data"""
        date_str = date.strftime('%Y%m%d')
        
        # Get all orders for the date
        order_keys = await self.redis.keys(f"order:*:{date_str}")
        orders = []
        
        for key in order_keys:
            order_data = await self.redis.hgetall(key)
            if order_data:
                orders.append(order_data)
        
        if orders:
            # Save to file
            filename = f"orders_{date_str}.json"
            await self._save_archive(filename, {'orders': orders, 'date': date_str})
            
            logger.info(f"Archived {len(orders)} orders for {date_str}")

    async def _archive_trades(self, date: datetime):
        """Archive trade data"""
        date_str = date.strftime('%Y%m%d')
        
        # Get all trades for the date
        trades_key = f"trades:{date_str}"
        trades_data = await self.redis.lrange(trades_key, 0, -1)
        
        trades = []
        for trade_json in trades_data:
            trades.append(json.loads(trade_json))
        
        if trades:
            # Save to file
            filename = f"trades_{date_str}.json"
            await self._save_archive(filename, {'trades': trades, 'date': date_str})
            
            logger.info(f"Archived {len(trades)} trades for {date_str}")

    async def _archive_positions(self, date: datetime):
        """Archive position data"""
        date_str = date.strftime('%Y%m%d')
        
        # Get all positions for the date
        positions_key = f"positions:{date_str}"
        position_ids = await self.redis.smembers(positions_key)
        
        positions = []
        for position_id in position_ids:
            pos_data = await self.redis.hgetall(f"position:{position_id}")
            if pos_data:
                positions.append(pos_data)
        
        if positions:
            # Save to file
            filename = f"positions_{date_str}.json"
            await self._save_archive(filename, {'positions': positions, 'date': date_str})
            
            logger.info(f"Archived {len(positions)} positions for {date_str}")

    async def _archive_market_data(self, date: datetime):
        """Archive market data (candles, ticks)"""
        date_str = date.strftime('%Y%m%d')
        
        # This would archive market data stored in Redis/TimescaleDB
        # Simplified example
        market_data_keys = await self.redis.keys(f"market_data:*:{date_str}")
        
        if market_data_keys:
            # Process in batches to avoid memory issues
            batch_size = 1000
            for i in range(0, len(market_data_keys), batch_size):
                batch = market_data_keys[i:i+batch_size]
                
                data = []
                for key in batch:
                    tick_data = await self.redis.get(key)
                    if tick_data:
                        data.append(json.loads(tick_data))
                
                if data:
                    filename = f"market_data_{date_str}_batch_{i//batch_size}.json"
                    await self._save_archive(filename, {'data': data, 'date': date_str})

    async def _archive_logs(self, date: datetime):
        """Archive system logs"""
        date_str = date.strftime('%Y-%m-%d')
        log_file = f"logs/trading_{date_str}.log"
        
        if os.path.exists(log_file):
            archive_name = f"logs_{date_str.replace('-', '')}.log"
            
            # Compress log file
            if self.compression_enabled:
                with zipfile.ZipFile(f"{self.archive_path}/{archive_name}.zip", 'w', 
                                   zipfile.ZIP_DEFLATED) as zf:
                    zf.write(log_file, archive_name)
                
                # Remove original after compression
                os.remove(log_file)
            else:
                # Just move to archive
                os.rename(log_file, f"{self.archive_path}/{archive_name}")

    async def _save_archive(self, filename: str, data: Dict):
        """Save data to archive with optional compression and encryption"""
        filepath = os.path.join(self.archive_path, filename)
        
        # Convert to JSON
        json_data = json.dumps(data, indent=2)
        
        # Encrypt if enabled
        if self.encryption_enabled:
            # Use the security manager's encryption
            from ..security.secure_config import SecureConfigManager
            secure_config = SecureConfigManager()
            json_data = secure_config.cipher.encrypt(json_data.encode()).decode()
        
        # Save to file
        if self.compression_enabled:
            # Compress with zip
            with zipfile.ZipFile(f"{filepath}.zip", 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(filename, json_data)
        else:
            # Save as is
            async with aiofiles.open(filepath, 'w') as f:
                await f.write(json_data)

    async def _create_compliance_report(self, date: datetime):
        """Create daily compliance report"""
        date_str = date.strftime('%Y%m%d')
        
        report = {
            'date': date_str,
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_orders': 0,
                'total_trades': 0,
                'total_volume': 0,
                'unique_symbols': set(),
                'compliance_alerts': []
            },
            'details': {}
        }
        
        # Gather statistics
        # ... (implementation depends on your data structure)
        
        # Save report
        filename = f"compliance_report_{date_str}.json"
        await self._save_archive(filename, report)
        
        logger.info(f"Generated compliance report for {date_str}")

    async def _cleanup_expired_data(self):
        """Remove data that has exceeded retention period"""
        current_date = datetime.now()
        
        for data_type, retention_days in self.retention_periods.items():
            cutoff_date = current_date - timedelta(days=retention_days)
            
            logger.info(f"Cleaning {data_type} data older than {cutoff_date.date()}")
            
            # This would remove data from Redis/database
            # Implementation depends on your data structure

    async def retrieve_archived_data(self, data_type: str, date: datetime) -> Optional[Dict]:
        """Retrieve archived data for audit/compliance"""
        date_str = date.strftime('%Y%m%d')
        filename = f"{data_type}_{date_str}.json"
        
        # Check compressed file first
        filepath = os.path.join(self.archive_path, f"{filename}.zip")
        
        try:
            if os.path.exists(filepath):
                # Extract and read compressed file
                with zipfile.ZipFile(filepath, 'r') as zf:
                    json_data = zf.read(filename)
            else:
                # Check uncompressed file
                filepath = os.path.join(self.archive_path, filename)
                if os.path.exists(filepath):
                    async with aiofiles.open(filepath, 'r') as f:
                        json_data = await f.read()
                else:
                    return None
            
            # Decrypt if needed
            if self.encryption_enabled:
                from ..security.secure_config import SecureConfigManager
                secure_config = SecureConfigManager()
                json_data = secure_config.cipher.decrypt(json_data.encode()).decode()
            
            return json.loads(json_data)
            
        except Exception as e:
            logger.error(f"Failed to retrieve archived data: {e}")
            return None

class RegulatoryReporting:
    """Generate regulatory reports for compliance"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.report_templates = {
            'daily_trading': self._generate_daily_trading_report,
            'position_limits': self._generate_position_limit_report,
            'suspicious_activity': self._generate_sar,
            'order_audit': self._generate_order_audit_trail
        }

    async def generate_report(self, report_type: str, 
                            start_date: datetime, 
                            end_date: datetime) -> pd.DataFrame:
        """Generate specific regulatory report"""
        if report_type not in self.report_templates:
            raise ValueError(f"Unknown report type: {report_type}")
        
        return await self.report_templates[report_type](start_date, end_date)

    async def _generate_daily_trading_report(self, start_date: datetime, 
                                           end_date: datetime) -> pd.DataFrame:
        """Generate daily trading summary report"""
        # This would aggregate data from archives
        data = []
        
        current_date = start_date
        while current_date <= end_date:
            # Retrieve archived data
            # ... implementation
            current_date += timedelta(days=1)
        
        return pd.DataFrame(data)

    async def _generate_position_limit_report(self, start_date: datetime,
                                            end_date: datetime) -> pd.DataFrame:
        """Generate position limit compliance report"""
        # Check position limits throughout the period
        data = []
        
        # ... implementation
        
        return pd.DataFrame(data)

    async def _generate_sar(self, start_date: datetime,
                          end_date: datetime) -> pd.DataFrame:
        """Generate Suspicious Activity Report"""
        # Identify suspicious patterns
        data = []
        
        # ... implementation
        
        return pd.DataFrame(data)

    async def _generate_order_audit_trail(self, start_date: datetime,
                                        end_date: datetime) -> pd.DataFrame:
        """Generate complete order audit trail"""
        # Full lifecycle of all orders
        data = []
        
        # ... implementation
        
        return pd.DataFrame(data) 