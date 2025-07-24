"""
N8N Integration Module
Handles communication with n8n webhooks for trading signals
"""

import aiohttp
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SignalMetadata:
    """Metadata for trading signals"""
    quality_score: float = 0.0
    timeframe: str = 'unknown'
    confidence: float = 0.0
    indicators: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.indicators is None:
            self.indicators = {}

@dataclass
class TradingSignal:
    """Trading signal data structure"""
    symbol: str
    action: str  # "BUY" or "SELL"
    quantity: int
    entry_price: float
    strategy_name: str
    signal_id: str
    metadata: Optional[SignalMetadata] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = SignalMetadata()

class N8NIntegration:
    def __init__(self, config: Dict):
        """
        Initialize N8N integration
        
        Args:
            config: Configuration dictionary containing webhook settings
        """
        self.webhook_url = config['webhooks']['n8n']['url']
        self.timeout = config['webhooks']['n8n'].get('timeout', 5)
        self.retry_attempts = config['webhooks']['n8n'].get('retry_attempts', 3)
        self.retry_delay = config['webhooks']['n8n'].get('retry_delay', 1)
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self):
        """Initialize HTTP session"""
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
            
    async def shutdown(self):
        """Cleanup resources"""
        if self._session:
            await self._session.close()
            self._session = None
            
    def _prepare_payload(self, signal: TradingSignal) -> Dict:
        """Prepare webhook payload from signal"""
        return {
            "symbol": signal.symbol,
            "action": signal.action,
            "quantity": signal.quantity,
            "price": signal.entry_price,
            "strategy": signal.strategy_name,
            "signal_id": signal.signal_id,
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "quality_score": signal.metadata.quality_score,
                "timeframe": signal.metadata.timeframe,
                "confidence": signal.metadata.confidence,
                "indicators": signal.metadata.indicators
            }
        }
        
    async def send_signal(self, signal: TradingSignal) -> bool:
        """
        Send trading signal to n8n with retry logic
        
        Args:
            signal: TradingSignal object containing signal data
            
        Returns:
            bool: True if signal was sent successfully
        """
        if not self._session:
            await self.initialize()
            
        payload = self._prepare_payload(signal)
        
        for attempt in range(self.retry_attempts):
            try:
                async with self._session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        result = await response.text()
                        logger.info(f"✅ Signal sent to n8n: {signal.signal_id}")
                        return True
                    else:
                        error_msg = f"n8n error: {response.status}"
                        if attempt < self.retry_attempts - 1:
                            logger.warning(f"Attempt {attempt + 1} failed: {error_msg}")
                            await asyncio.sleep(self.retry_delay)
                        else:
                            logger.error(error_msg)
                            return False
                            
            except asyncio.TimeoutError:
                error_msg = "n8n webhook timeout"
                if attempt < self.retry_attempts - 1:
                    logger.warning(f"Attempt {attempt + 1} failed: {error_msg}")
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(error_msg)
                    return False
                    
            except Exception as e:
                error_msg = f"n8n error: {str(e)}"
                if attempt < self.retry_attempts - 1:
                    logger.warning(f"Attempt {attempt + 1} failed: {error_msg}")
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(error_msg)
                    return False
                    
        return False

async def test_integration():
    """Test the N8N integration"""
    # Test configuration
    config = {
        'webhooks': {
            'n8n': {
                'url': 'https://shyamanurag.app.n8n.cloud/webhook/78893dc5-746b-439d-aad4-fbc6396c3164',
                'timeout': 5,
                'retry_attempts': 3,
                'retry_delay': 1
            }
        }
    }
    
    # Initialize integration
    n8n = N8NIntegration(config)
    await n8n.initialize()
    
    try:
        # Create test signal
        signal = TradingSignal(
            symbol="NIFTY24500CE",
            action="BUY",
            quantity=100,
            entry_price=250.50,
            strategy_name="momentum",
            signal_id=f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            metadata=SignalMetadata(
                quality_score=85.5,
                timeframe="5min",
                confidence=0.8,
                indicators={
                    "rsi": 65.5,
                    "macd": "bullish",
                    "volume": "above_average"
                }
            )
        )
        
        # Send signal
        success = await n8n.send_signal(signal)
        
        if success:
            print("✅ Integration test passed")
        else:
            print("❌ Integration test failed")
            
    finally:
        # Cleanup
        await n8n.shutdown()

if __name__ == "__main__":
    asyncio.run(test_integration()) 