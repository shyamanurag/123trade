#!/usr/bin/env python3
"""
n8n Agent Implementation
Handles workflow automation for trading system
"""

import yaml
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import aiohttp
import schedule
import numpy as np
import pandas as pd
from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator

from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import backoff
from aiohttp import ClientTimeout
from cachetools import TTLCache

# Setup logging with structured format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class N8nAgent:
    def __init__(self):
        self.config = self._load_config('config/n8n_config.yaml')
        self.webhook_config = self._load_webhook_config('config/webhooks.json')
        self.session = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.cache = TTLCache(maxsize=1000, ttl=300)  # 5 minutes cache
        self.running = True

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load n8n configuration with caching"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def _load_webhook_config(self, webhook_config_path: str) -> Dict[str, Any]:
        """Load webhook configuration with caching"""
        with open(webhook_config_path, 'r') as f:
            return json.load(f)

    async def initialize(self):
        """Initialize n8n agent with connection pooling"""
        self.session = aiohttp.ClientSession(
            timeout=ClientTimeout(total=30),
            headers={'Content-Type': 'application/json'}
        )
        await self._setup_workflows()

    async def _setup_workflows(self):
        """Setup n8n workflows with parallel processing"""
        # Setup agent workflows
        self.workflows = {
            agent_name: {
                'name': agent_config['name'],
                'description': agent_config['description'],
                'triggers': agent_config['triggers'],
                'actions': agent_config['actions']
            }
            for agent_name, agent_config in self.config['agents'].items()
        }

        # Setup webhook workflows
        self.webhook_workflows = {
            workflow['id']: workflow
            for workflow in self.webhook_config['workflows']
        }

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3
    )
    async def _make_request(self, url: str, method: str = 'GET', **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        if not self.session:
            raise RuntimeError("Session not initialized")
        async with self.session.request(method, url, **kwargs) as response:
            response.raise_for_status()
            return await response.json()

    async def _process_workflow(self, workflow_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process workflow with caching"""
        cache_key = f"{workflow_id}:{json.dumps(data, sort_keys=True)}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]

        workflow = self.workflows[workflow_id]
        result = await self._execute_workflow(workflow, data)
        self.cache[cache_key] = result
        return result

    async def _execute_workflow(self, workflow: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow steps in parallel where possible"""
        tasks = []

        for action in workflow.get('actions', []):
            if action['type'] == 'http':
                task = self._make_request(
                    action['url'],
                    method=action['method'],
                    json=data,
                    headers=action.get('headers', {})
                )
                tasks.append(task)
            elif action['type'] == 'function':
                task = asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self._execute_function,
                    action['name'],
                    data
                )
                tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self._combine_results(results)

    def _execute_function(self, function_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute function in thread pool"""
        functions = {
            'process_market_data': self._process_market_data,
            'analyze_market_data': self._analyze_market_data,
            'validate_orders': self._validate_orders,
            'calculate_risk_metrics': self._calculate_risk_metrics,
            'generate_performance_report': self._generate_performance_report
        }

        if function_name in functions:
            return functions[function_name](data)
        return data

    def _process_market_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process market data with technical analysis"""
        try:
            # Convert price data to pandas DataFrame
            df = pd.DataFrame(data['prices'])
            
            # Calculate technical indicators
            sma_20 = SMAIndicator(close=df['close'], window=20).sma_indicator()
            rsi_14 = RSIIndicator(close=df['close'], window=14).rsi()
            macd = MACD(close=df['close'])
            
            # Detect patterns
            patterns = self._detect_patterns(df)
            
            # Generate signals
            signals = self._generate_signals(df, sma_20, rsi_14, macd, patterns)
            
            return {
                'symbol': data['symbol'],
                'timestamp': datetime.now().isoformat(),
                'indicators': {
                    'sma_20': sma_20.iloc[-1],
                    'rsi_14': rsi_14.iloc[-1],
                    'macd': {
                        'macd': macd.macd().iloc[-1],
                        'signal': macd.macd_signal().iloc[-1],
                        'histogram': macd.macd_diff().iloc[-1]
                    }
                },
                'patterns': patterns,
                'signals': signals
            }
        except Exception as e:
            logger.error(f"Error processing market data: {str(e)}")
            raise

    def _detect_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect chart patterns"""
        patterns = []
        
        # Simple pattern detection logic
        if len(df) >= 3:
            # Bullish engulfing
            if (df['close'].iloc[-1] > df['open'].iloc[-1] and
                df['close'].iloc[-2] < df['open'].iloc[-2] and
                df['close'].iloc[-1] > df['open'].iloc[-2] and
                df['open'].iloc[-1] < df['close'].iloc[-2]):
                patterns.append({
                    'type': 'bullish_engulfing',
                    'confidence': 0.7
                })
            
            # Bearish engulfing
            if (df['close'].iloc[-1] < df['open'].iloc[-1] and
                df['close'].iloc[-2] > df['open'].iloc[-2] and
                df['close'].iloc[-1] < df['open'].iloc[-2] and
                df['open'].iloc[-1] > df['close'].iloc[-2]):
                patterns.append({
                    'type': 'bearish_engulfing',
                    'confidence': 0.7
                })
        
        return patterns

    def _generate_signals(self, df: pd.DataFrame, sma_20: pd.Series, 
                         rsi_14: pd.Series, macd: MACD, 
                         patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate trading signals based on technical analysis"""
        signals = {
            'action': 'HOLD',
            'confidence': 0.5,
            'reasons': []
        }
        
        # RSI signals
        if rsi_14.iloc[-1] < 30:
            signals['reasons'].append('RSI oversold')
            signals['confidence'] += 0.2
        elif rsi_14.iloc[-1] > 70:
            signals['reasons'].append('RSI overbought')
            signals['confidence'] -= 0.2
        
        # MACD signals
        if macd.macd_diff().iloc[-1] > 0 and macd.macd_diff().iloc[-2] <= 0:
            signals['reasons'].append('MACD bullish crossover')
            signals['confidence'] += 0.3
        elif macd.macd_diff().iloc[-1] < 0 and macd.macd_diff().iloc[-2] >= 0:
            signals['reasons'].append('MACD bearish crossover')
            signals['confidence'] -= 0.3
        
        # Pattern signals
        for pattern in patterns:
            if pattern['type'] == 'bullish_engulfing':
                signals['reasons'].append('Bullish engulfing pattern')
                signals['confidence'] += 0.2
            elif pattern['type'] == 'bearish_engulfing':
                signals['reasons'].append('Bearish engulfing pattern')
                signals['confidence'] -= 0.2
        
        # Determine final action
        if signals['confidence'] >= 0.7:
            signals['action'] = 'BUY'
        elif signals['confidence'] <= 0.3:
            signals['action'] = 'SELL'
        
        return signals

    def _combine_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine results from parallel execution"""
        combined = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error in workflow execution: {str(result)}")
                continue
            combined.update(result)
        return combined

    async def start_market_data_processor(self):
        """Start market data processor with optimized scheduling"""
        workflow = self.workflows['market_data_processor']
        
        async def process_market_data():
            try:
                data = {'timestamp': datetime.now().isoformat()}
                result = await self._process_workflow('market_data_processor', data)
                logger.info(f"Processed market data: {json.dumps(result)}")
            except Exception as e:
                logger.error(f"Error in market data processor: {str(e)}")
        
        schedule.every(1).minutes.do(lambda: asyncio.create_task(process_market_data()))

    async def start(self):
        """Start all n8n agents with optimized scheduling"""
        await self.initialize()
        
        # Start webhook workflows
        await asyncio.gather(
            self.start_rbi_workflow(),
            self.start_nse_workflow()
        )
        
        # Start agent workflows
        await asyncio.gather(
            self.start_market_data_processor(),
            self.start_market_data_agent(),
            self.start_order_management_agent(),
            self.start_risk_monitoring_agent(),
            self.start_performance_tracking_agent()
        )
        
        # Run scheduler with optimized polling
        while self.running:
            schedule.run_pending()
            await asyncio.sleep(0.1)

    async def stop(self):
        """Stop all n8n agents with proper cleanup"""
        self.running = False
        if self.session:
            await self.session.close()
        self.cache.clear()
        self.executor.shutdown()

async def main():
    agent = N8nAgent()
    try:
        await agent.start()
    except KeyboardInterrupt:
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
