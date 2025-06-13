"""
Integration tests for the market data system
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

from core.models import (
    TimeFrame,
    MarketData,
    OrderBook,
    Trade,
    Ticker
)
from core.exceptions import DataError
from data.market_data import MarketDataProvider

@pytest.fixture
def data_config() -> Dict:
    """Create market data configuration"""
    return {
        "symbols": ["BTC/USD", "ETH/USD"],
        "timeframes": [
            TimeFrame.MINUTE_1,
            TimeFrame.MINUTE_5,
            TimeFrame.MINUTE_15,
            TimeFrame.HOUR_1,
            TimeFrame.HOUR_4,
            TimeFrame.DAY_1
        ],
        "update_interval": 1.0,
        "max_retries": 3,
        "retry_delay": 1.0,
        "cache_ttl": 60,
        "websocket_enabled": True,
        "rest_api_enabled": True
    }

@pytest.fixture
def market_data() -> Dict:
    """Create market data"""
    return {
        "BTC/USD": {
            "timestamp": datetime.utcnow(),
            "open": Decimal("50000.0"),
            "high": Decimal("51000.0"),
            "low": Decimal("49000.0"),
            "close": Decimal("50500.0"),
            "volume": Decimal("100.0")
        }
    }

@pytest.fixture
def order_book() -> OrderBook:
    """Create order book"""
    return OrderBook(
        symbol="BTC/USD",
        timestamp=datetime.utcnow(),
        bids=[
            {"price": Decimal("50400.0"), "quantity": Decimal("0.1")},
            {"price": Decimal("50300.0"), "quantity": Decimal("0.2")}
        ],
        asks=[
            {"price": Decimal("50600.0"), "quantity": Decimal("0.1")},
            {"price": Decimal("50700.0"), "quantity": Decimal("0.2")}
        ]
    )

@pytest.fixture
def trades() -> List[Trade]:
    """Create trades"""
    return [
        Trade(
            symbol="BTC/USD",
            timestamp=datetime.utcnow(),
            price=Decimal("50500.0"),
            quantity=Decimal("0.1"),
            side="buy",
            trade_id="123"
        ),
        Trade(
            symbol="BTC/USD",
            timestamp=datetime.utcnow(),
            price=Decimal("50510.0"),
            quantity=Decimal("0.2"),
            side="sell",
            trade_id="124"
        )
    ]

@pytest.fixture
def ticker() -> Ticker:
    """Create ticker"""
    return Ticker(
        symbol="BTC/USD",
        timestamp=datetime.utcnow(),
        last_price=Decimal("50500.0"),
        bid=Decimal("50400.0"),
        ask=Decimal("50600.0"),
        volume_24h=Decimal("1000.0"),
        high_24h=Decimal("51000.0"),
        low_24h=Decimal("49000.0")
    )

@pytest.mark.asyncio
async def test_market_data_initialization(data_config: Dict):
    """Test market data initialization"""
    provider = MarketDataProvider(data_config)
    
    # Verify initialization
    assert provider.symbols == data_config["symbols"]
    assert provider.timeframes == data_config["timeframes"]
    assert provider.update_interval == data_config["update_interval"]

@pytest.mark.asyncio
async def test_ohlcv_data_retrieval(
    data_config: Dict,
    market_data: Dict
):
    """Test OHLCV data retrieval"""
    provider = MarketDataProvider(data_config)
    
    # Get OHLCV data
    data = await provider.get_ohlcv(
        "BTC/USD",
        TimeFrame.HOUR_1,
        limit=100
    )
    
    # Verify data
    assert isinstance(data, list)
    for candle in data:
        assert isinstance(candle, MarketData)
        assert candle.symbol == "BTC/USD"
        assert candle.timeframe == TimeFrame.HOUR_1
        assert candle.open > 0
        assert candle.high >= candle.open
        assert candle.low <= candle.open
        assert candle.close > 0
        assert candle.volume >= 0

@pytest.mark.asyncio
async def test_order_book_retrieval(
    data_config: Dict,
    order_book: OrderBook
):
    """Test order book retrieval"""
    provider = MarketDataProvider(data_config)
    
    # Get order book
    book = await provider.get_order_book("BTC/USD", limit=10)
    
    # Verify order book
    assert isinstance(book, OrderBook)
    assert book.symbol == "BTC/USD"
    assert len(book.bids) > 0
    assert len(book.asks) > 0
    assert book.bids[0]["price"] < book.asks[0]["price"]

@pytest.mark.asyncio
async def test_trades_retrieval(
    data_config: Dict,
    trades: List[Trade]
):
    """Test trades retrieval"""
    provider = MarketDataProvider(data_config)
    
    # Get trades
    trade_list = await provider.get_trades("BTC/USD", limit=100)
    
    # Verify trades
    assert isinstance(trade_list, list)
    for trade in trade_list:
        assert isinstance(trade, Trade)
        assert trade.symbol == "BTC/USD"
        assert trade.price > 0
        assert trade.quantity > 0
        assert trade.side in ["buy", "sell"]

@pytest.mark.asyncio
async def test_ticker_retrieval(
    data_config: Dict,
    ticker: Ticker
):
    """Test ticker retrieval"""
    provider = MarketDataProvider(data_config)
    
    # Get ticker
    ticker_data = await provider.get_ticker("BTC/USD")
    
    # Verify ticker
    assert isinstance(ticker_data, Ticker)
    assert ticker_data.symbol == "BTC/USD"
    assert ticker_data.last_price > 0
    assert ticker_data.bid > 0
    assert ticker_data.ask > 0
    assert ticker_data.volume_24h >= 0

@pytest.mark.asyncio
async def test_websocket_subscription(data_config: Dict):
    """Test WebSocket subscription"""
    provider = MarketDataProvider(data_config)
    
    # Subscribe to market data
    await provider.subscribe_market_data("BTC/USD")
    
    # Verify subscription
    assert "BTC/USD" in provider.subscriptions
    
    # Unsubscribe
    await provider.unsubscribe_market_data("BTC/USD")
    assert "BTC/USD" not in provider.subscriptions

@pytest.mark.asyncio
async def test_data_caching(
    data_config: Dict,
    market_data: Dict
):
    """Test data caching"""
    provider = MarketDataProvider(data_config)
    
    # Get data (should be cached)
    data1 = await provider.get_ohlcv("BTC/USD", TimeFrame.HOUR_1)
    data2 = await provider.get_ohlcv("BTC/USD", TimeFrame.HOUR_1)
    
    # Verify caching
    assert data1 == data2

@pytest.mark.asyncio
async def test_data_validation(data_config: Dict):
    """Test data validation"""
    provider = MarketDataProvider(data_config)
    
    # Test invalid symbol
    with pytest.raises(DataError):
        await provider.get_ohlcv("INVALID", TimeFrame.HOUR_1)
    
    # Test invalid timeframe
    with pytest.raises(DataError):
        await provider.get_ohlcv("BTC/USD", "INVALID")

@pytest.mark.asyncio
async def test_data_update_mechanism(
    data_config: Dict,
    market_data: Dict
):
    """Test data update mechanism"""
    provider = MarketDataProvider(data_config)
    
    # Start data updates
    await provider.start_updates()
    assert provider.is_updating
    
    # Stop data updates
    await provider.stop_updates()
    assert not provider.is_updating

@pytest.mark.asyncio
async def test_data_error_handling(data_config: Dict):
    """Test data error handling"""
    provider = MarketDataProvider(data_config)
    
    # Test connection error
    with patch.object(provider, '_fetch_data', side_effect=ConnectionError):
        with pytest.raises(DataError):
            await provider.get_ohlcv("BTC/USD", TimeFrame.HOUR_1)
    
    # Test timeout error
    with patch.object(provider, '_fetch_data', side_effect=TimeoutError):
        with pytest.raises(DataError):
            await provider.get_ohlcv("BTC/USD", TimeFrame.HOUR_1)

@pytest.mark.asyncio
async def test_data_aggregation(
    data_config: Dict,
    market_data: Dict
):
    """Test data aggregation"""
    provider = MarketDataProvider(data_config)
    
    # Get aggregated data
    data = await provider.get_aggregated_data(
        "BTC/USD",
        TimeFrame.HOUR_1,
        indicators=["sma", "ema", "rsi"]
    )
    
    # Verify aggregated data
    assert isinstance(data, dict)
    assert "ohlcv" in data
    assert "indicators" in data
    assert "sma" in data["indicators"]
    assert "ema" in data["indicators"]
    assert "rsi" in data["indicators"]

@pytest.mark.asyncio
async def test_data_export(
    data_config: Dict,
    market_data: Dict
):
    """Test data export"""
    provider = MarketDataProvider(data_config)
    
    # Export data
    data = await provider.export_data(
        "BTC/USD",
        TimeFrame.HOUR_1,
        start_time=datetime.utcnow() - timedelta(days=1),
        end_time=datetime.utcnow(),
        format="csv"
    )
    
    # Verify exported data
    assert isinstance(data, str)
    assert len(data) > 0 