#!/usr/bin/env python3
"""
Real-time monitoring script for trading session
Runs continuous health checks and alerts on issues
"""

import asyncio
import aiohttp
import time
from datetime import datetime
from typing import Dict, List, Tuple
import json
import sys

# Configuration
BASE_URL = "https://algoauto-9gx56.ondigitalocean.app"
CHECK_INTERVAL = 30  # seconds
ALERT_THRESHOLD = 3  # consecutive failures before alert

# Critical endpoints to monitor
ENDPOINTS = {
    "health": "/health",
    "trading_status": "/api/v1/control/trading/status",
    "positions": "/api/v1/positions",
    "orders": "/api/v1/orders",
    "market_status": "/api/market/market-status",
    "users": "/api/v1/users/",
    "metrics": "/api/v1/monitoring/metrics"
}

class TradingMonitor:
    def __init__(self):
        self.failures = {}
        self.last_status = {}
        self.start_time = time.time()
        
    async def check_endpoint(self, session: aiohttp.ClientSession, name: str, path: str) -> Tuple[bool, str]:
        """Check if an endpoint is healthy"""
        try:
            async with session.get(f"{BASE_URL}{path}", timeout=10) as response:
                if response.status == 200:
                    return True, "OK"
                else:
                    return False, f"Status {response.status}"
        except asyncio.TimeoutError:
            return False, "Timeout"
        except Exception as e:
            return False, str(e)
    
    async def check_websocket(self, session: aiohttp.ClientSession) -> Tuple[bool, str]:
        """Check WebSocket connectivity"""
        try:
            ws_url = BASE_URL.replace("https://", "wss://") + "/ws"
            async with session.ws_connect(ws_url, timeout=5) as ws:
                await ws.close()
                return True, "Connected"
        except Exception as e:
            return False, str(e)
    
    def print_status(self, results: Dict[str, Tuple[bool, str]]):
        """Print formatted status update"""
        # Clear screen
        print("\033[2J\033[H")  # ANSI escape codes to clear screen
        
        print("=" * 60)
        print(f"  TRADING SYSTEM MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print(f"Uptime: {int(time.time() - self.start_time)} seconds")
        print()
        
        # Status table
        print(f"{'Endpoint':<20} {'Status':<10} {'Details':<30}")
        print("-" * 60)
        
        for name, (success, message) in results.items():
            status = "✅ OK" if success else "❌ FAIL"
            print(f"{name:<20} {status:<10} {message:<30}")
            
            # Track failures
            if not success:
                self.failures[name] = self.failures.get(name, 0) + 1
            else:
                self.failures[name] = 0
        
        # Alerts
        print("\n" + "=" * 60)
        print("  ALERTS")
        print("=" * 60)
        
        alerts = []
        for name, count in self.failures.items():
            if count >= ALERT_THRESHOLD:
                alerts.append(f"🚨 {name} has failed {count} times!")
        
        if alerts:
            for alert in alerts:
                print(alert)
        else:
            print("✅ No alerts - all systems operational")
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        async with aiohttp.ClientSession() as session:
            while True:
                results = {}
                
                # Check all endpoints
                for name, path in ENDPOINTS.items():
                    success, message = await self.check_endpoint(session, name, path)
                    results[name] = (success, message)
                
                # Check WebSocket
                ws_success, ws_message = await self.check_websocket(session)
                results["websocket"] = (ws_success, ws_message)
                
                # Print status
                self.print_status(results)
                
                # Wait for next check
                await asyncio.sleep(CHECK_INTERVAL)
    
    def run(self):
        """Start the monitor"""
        print("Starting Trading System Monitor...")
        print(f"Checking endpoints every {CHECK_INTERVAL} seconds")
        print(f"Alert threshold: {ALERT_THRESHOLD} consecutive failures")
        print("\nPress Ctrl+C to stop\n")
        
        try:
            asyncio.run(self.monitor_loop())
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped.")
            sys.exit(0)

if __name__ == "__main__":
    monitor = TradingMonitor()
    monitor.run() 