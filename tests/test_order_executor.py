"""
Integration tests for the order execution system
"""

import pytest
from datetime import datetime
from decimal import Decimal
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

from core.models import (
    OrderType,
    OrderSide,
    OrderStatus,
    TimeFrame,
    Order,
    Position,
    MarketData
)
from core.exceptions import OrderError
from execution.order_executor import OrderExecutor

@pytest.fixture
def executor_config() -> Dict:
    """Create order executor configuration"""
    return {
        "max_retries": 3,
        "retry_delay": 1.0,
        "timeout": 30.0,
        "slippage_tolerance": Decimal("0.001"),
        "min_order_size": Decimal("0.001"),
        "max_order_size": Decimal("10.0"),
        "price_impact_limit": Decimal("0.01"),
        "execution_priority": ["maker", "taker"],
        "fee_structure": {
            "maker": Decimal("0.001"),
            "taker": Decimal("0.002")
        }
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
            "volume": Decimal("100.0"),
            "bid": Decimal("50400.0"),
            "ask": Decimal("50600.0")
        }
    }

@pytest.fixture
def test_order() -> Order:
    """Create test order"""
    return Order(
        order_id="test-123",
        symbol="BTC/USD",
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=Decimal("0.1"),
        price=Decimal("50000.0")
    )

@pytest.mark.asyncio
async def test_order_validation(executor_config: Dict, test_order: Order):
    """Test order validation"""
    executor = OrderExecutor(executor_config)
    
    # Test valid order
    assert await executor.validate_order(test_order)
    
    # Test invalid order size
    test_order.quantity = Decimal("0.0001")
    with pytest.raises(OrderError):
        await executor.validate_order(test_order)
    
    # Test invalid order size
    test_order.quantity = Decimal("20.0")
    with pytest.raises(OrderError):
        await executor.validate_order(test_order)

@pytest.mark.asyncio
async def test_market_order_execution(
    executor_config: Dict,
    market_data: Dict
):
    """Test market order execution"""
    executor = OrderExecutor(executor_config)
    
    # Create market order
    order = Order(
        order_id="test-123",
        symbol="BTC/USD",
        order_type=OrderType.MARKET,
        side=OrderSide.BUY,
        quantity=Decimal("0.1")
    )
    
    # Execute order
    result = await executor.execute_order(order, market_data)
    
    # Verify execution
    assert result.status == OrderStatus.FILLED
    assert result.filled_quantity == order.quantity
    assert result.average_fill_price is not None
    assert result.average_fill_price >= market_data["BTC/USD"]["bid"]
    assert result.average_fill_price <= market_data["BTC/USD"]["ask"]

@pytest.mark.asyncio
async def test_limit_order_execution(
    executor_config: Dict,
    market_data: Dict,
    test_order: Order
):
    """Test limit order execution"""
    executor = OrderExecutor(executor_config)
    
    # Execute order
    result = await executor.execute_order(test_order, market_data)
    
    # Verify execution
    assert result.status in [OrderStatus.FILLED, OrderStatus.PENDING]
    if result.status == OrderStatus.FILLED:
        assert result.filled_quantity == test_order.quantity
        assert result.average_fill_price == test_order.price

@pytest.mark.asyncio
async def test_stop_order_execution(
    executor_config: Dict,
    market_data: Dict
):
    """Test stop order execution"""
    executor = OrderExecutor(executor_config)
    
    # Create stop order
    order = Order(
        order_id="test-123",
        symbol="BTC/USD",
        order_type=OrderType.STOP,
        side=OrderSide.SELL,
        quantity=Decimal("0.1"),
        stop_price=Decimal("49000.0")
    )
    
    # Execute order
    result = await executor.execute_order(order, market_data)
    
    # Verify execution
    assert result.status in [OrderStatus.FILLED, OrderStatus.PENDING]
    if result.status == OrderStatus.FILLED:
        assert result.filled_quantity == order.quantity
        assert result.average_fill_price is not None

@pytest.mark.asyncio
async def test_order_cancellation(
    executor_config: Dict,
    test_order: Order
):
    """Test order cancellation"""
    executor = OrderExecutor(executor_config)
    
    # Cancel order
    result = await executor.cancel_order(test_order.order_id)
    
    # Verify cancellation
    assert result.status == OrderStatus.CANCELLED

@pytest.mark.asyncio
async def test_order_modification(
    executor_config: Dict,
    test_order: Order
):
    """Test order modification"""
    executor = OrderExecutor(executor_config)
    
    # Modify order
    new_quantity = Decimal("0.2")
    new_price = Decimal("51000.0")
    result = await executor.modify_order(
        test_order.order_id,
        quantity=new_quantity,
        price=new_price
    )
    
    # Verify modification
    assert result.quantity == new_quantity
    assert result.price == new_price

@pytest.mark.asyncio
async def test_order_status_tracking(
    executor_config: Dict,
    test_order: Order
):
    """Test order status tracking"""
    executor = OrderExecutor(executor_config)
    
    # Track order status
    status = await executor.get_order_status(test_order.order_id)
    
    # Verify status
    assert isinstance(status, OrderStatus)
    assert status in [
        OrderStatus.PENDING,
        OrderStatus.FILLED,
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.CANCELLED,
        OrderStatus.REJECTED,
        OrderStatus.EXPIRED
    ]

@pytest.mark.asyncio
async def test_order_fee_calculation(
    executor_config: Dict,
    test_order: Order,
    market_data: Dict
):
    """Test order fee calculation"""
    executor = OrderExecutor(executor_config)
    
    # Calculate fees
    fees = await executor.calculate_fees(test_order, market_data)
    
    # Verify fees
    assert isinstance(fees, dict)
    assert "maker_fee" in fees
    assert "taker_fee" in fees
    assert "total_fee" in fees

@pytest.mark.asyncio
async def test_order_slippage_calculation(
    executor_config: Dict,
    test_order: Order,
    market_data: Dict
):
    """Test order slippage calculation"""
    executor = OrderExecutor(executor_config)
    
    # Calculate slippage
    slippage = await executor.calculate_slippage(test_order, market_data)
    
    # Verify slippage
    assert isinstance(slippage, Decimal)
    assert slippage >= Decimal("0")
    assert slippage <= executor_config["slippage_tolerance"]

@pytest.mark.asyncio
async def test_order_retry_mechanism(
    executor_config: Dict,
    test_order: Order,
    market_data: Dict
):
    """Test order retry mechanism"""
    executor = OrderExecutor(executor_config)
    
    # Mock failed execution
    with patch.object(executor, 'execute_order', side_effect=OrderError("Temporary error")):
        # Execute order with retry
        result = await executor.execute_order_with_retry(test_order, market_data)
        
        # Verify retry behavior
        assert result.status in [OrderStatus.FILLED, OrderStatus.REJECTED]

@pytest.mark.asyncio
async def test_order_execution_monitoring(
    executor_config: Dict,
    test_order: Order
):
    """Test order execution monitoring"""
    executor = OrderExecutor(executor_config)
    
    # Start monitoring
    await executor.start_monitoring()
    assert executor.is_monitoring
    
    # Stop monitoring
    await executor.stop_monitoring()
    assert not executor.is_monitoring

@pytest.mark.asyncio
async def test_order_execution_metrics(
    executor_config: Dict,
    test_order: Order,
    market_data: Dict
):
    """Test order execution metrics"""
    executor = OrderExecutor(executor_config)
    
    # Execute order
    await executor.execute_order(test_order, market_data)
    
    # Get metrics
    metrics = await executor.get_execution_metrics()
    
    # Verify metrics
    assert isinstance(metrics, dict)
    assert "total_orders" in metrics
    assert "successful_orders" in metrics
    assert "failed_orders" in metrics
    assert "average_execution_time" in metrics
    assert "average_slippage" in metrics 