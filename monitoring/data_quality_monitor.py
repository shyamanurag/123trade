"""
Data Quality Monitor
Monitors and validates market data quality and integrity
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)

class DataQualityMonitor:
    """Monitors and validates market data quality"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.quality_thresholds = config.get('data_quality', {}).get('thresholds', {
            'missing_data_threshold': 0.01,  # 1% missing data allowed
            'price_deviation_threshold': 0.05,  # 5% price deviation
            'volume_spike_threshold': 3.0,  # 3x normal volume
            'latency_threshold': 1000,  # 1 second
            'gap_threshold': 300  # 5 minutes
        })
        
        self.metrics = defaultdict(lambda: {
            'missing_data_count': 0,
            'total_data_points': 0,
            'last_price': None,
            'price_deviations': [],
            'volume_spikes': [],
            'latencies': [],
            'gaps': []
        })
        
        self._monitoring_task = None
        self._alert_callbacks = []
    
    async def start(self):
        """Start data quality monitoring"""
        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._monitor_loop())
            logger.info("Data quality monitoring started")
    
    async def stop(self):
        """Stop data quality monitoring"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None
            logger.info("Data quality monitoring stopped")
    
    def add_alert_callback(self, callback):
        """Add callback for quality alerts"""
        self._alert_callbacks.append(callback)
    
    async def check_data_quality(self, symbol: str, data: Dict) -> bool:
        """Check quality of incoming data"""
        metrics = self.metrics[symbol]
        current_time = datetime.now()
        
        # Update total data points
        metrics['total_data_points'] += 1
        
        # Check for missing data
        if not self._validate_data_completeness(data):
            metrics['missing_data_count'] += 1
            await self._alert('missing_data', symbol, data)
        
        # Check price deviation
        if metrics['last_price'] is not None:
            deviation = abs(data['price'] - metrics['last_price']) / metrics['last_price']
            metrics['price_deviations'].append(deviation)
            
            if deviation > self.quality_thresholds['price_deviation_threshold']:
                await self._alert('price_deviation', symbol, {
                    'current_price': data['price'],
                    'last_price': metrics['last_price'],
                    'deviation': deviation
                })
        
        metrics['last_price'] = data['price']
        
        # Check volume spike
        if 'volume' in data:
            avg_volume = np.mean(metrics['volume_spikes'][-100:]) if metrics['volume_spikes'] else data['volume']
            volume_ratio = data['volume'] / avg_volume if avg_volume > 0 else 1.0
            
            metrics['volume_spikes'].append(volume_ratio)
            
            if volume_ratio > self.quality_thresholds['volume_spike_threshold']:
                await self._alert('volume_spike', symbol, {
                    'current_volume': data['volume'],
                    'average_volume': avg_volume,
                    'ratio': volume_ratio
                })
        
        # Check latency
        if 'timestamp' in data:
            latency = (current_time - data['timestamp']).total_seconds() * 1000
            metrics['latencies'].append(latency)
            
            if latency > self.quality_thresholds['latency_threshold']:
                await self._alert('high_latency', symbol, {
                    'latency_ms': latency,
                    'threshold': self.quality_thresholds['latency_threshold']
                })
        
        # Check for data gaps
        if 'timestamp' in data and metrics.get('last_timestamp'):
            gap = (data['timestamp'] - metrics['last_timestamp']).total_seconds()
            metrics['gaps'].append(gap)
            
            if gap > self.quality_thresholds['gap_threshold']:
                await self._alert('data_gap', symbol, {
                    'gap_seconds': gap,
                    'threshold': self.quality_thresholds['gap_threshold']
                })
        
        metrics['last_timestamp'] = data.get('timestamp')
        
        # Cleanup old metrics
        self._cleanup_metrics(symbol)
        
        return self._is_data_quality_acceptable(symbol)
    
    def _validate_data_completeness(self, data: Dict) -> bool:
        """Validate that all required fields are present"""
        required_fields = {'price', 'volume', 'timestamp'}
        return all(field in data for field in required_fields)
    
    def _is_data_quality_acceptable(self, symbol: str) -> bool:
        """Check if data quality is within acceptable thresholds"""
        metrics = self.metrics[symbol]
        
        # Check missing data ratio
        missing_ratio = metrics['missing_data_count'] / metrics['total_data_points']
        if missing_ratio > self.quality_thresholds['missing_data_threshold']:
            return False
        
        # Check price deviations
        if metrics['price_deviations']:
            avg_deviation = np.mean(metrics['price_deviations'][-100:])
            if avg_deviation > self.quality_thresholds['price_deviation_threshold']:
                return False
        
        # Check volume spikes
        if metrics['volume_spikes']:
            avg_spike = np.mean(metrics['volume_spikes'][-100:])
            if avg_spike > self.quality_thresholds['volume_spike_threshold']:
                return False
        
        # Check latencies
        if metrics['latencies']:
            avg_latency = np.mean(metrics['latencies'][-100:])
            if avg_latency > self.quality_thresholds['latency_threshold']:
                return False
        
        # Check gaps
        if metrics['gaps']:
            avg_gap = np.mean(metrics['gaps'][-100:])
            if avg_gap > self.quality_thresholds['gap_threshold']:
                return False
        
        return True
    
    def _cleanup_metrics(self, symbol: str):
        """Clean up old metrics data"""
        metrics = self.metrics[symbol]
        max_history = 1000  # Keep last 1000 data points
        
        for key in ['price_deviations', 'volume_spikes', 'latencies', 'gaps']:
            if len(metrics[key]) > max_history:
                metrics[key] = metrics[key][-max_history:]
    
    async def _alert(self, alert_type: str, symbol: str, details: Dict):
        """Send quality alert"""
        alert = {
            'type': alert_type,
            'symbol': symbol,
            'timestamp': datetime.now(),
            'details': details
        }
        
        logger.warning(f"Data quality alert: {alert}")
        
        for callback in self._alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while True:
            try:
                # Check overall data quality
                for symbol, metrics in self.metrics.items():
                    if not self._is_data_quality_acceptable(symbol):
                        await self._alert('overall_quality', symbol, {
                            'missing_ratio': metrics['missing_data_count'] / metrics['total_data_points'],
                            'avg_price_deviation': np.mean(metrics['price_deviations'][-100:]) if metrics['price_deviations'] else 0,
                            'avg_volume_spike': np.mean(metrics['volume_spikes'][-100:]) if metrics['volume_spikes'] else 0,
                            'avg_latency': np.mean(metrics['latencies'][-100:]) if metrics['latencies'] else 0,
                            'avg_gap': np.mean(metrics['gaps'][-100:]) if metrics['gaps'] else 0
                        })
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)
    
    def get_quality_metrics(self, symbol: Optional[str] = None) -> Dict:
        """Get current quality metrics"""
        if symbol:
            return self.metrics[symbol]
        return dict(self.metrics) 