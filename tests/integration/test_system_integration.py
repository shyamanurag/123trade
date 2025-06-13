import pytest
import asyncio
from datetime import datetime, time

from typing import Dict, Any

from core.orchestrator import EnhancedTradingOrchestrator
from core.position_tracker import PositionTracker
from core.order_manager import OrderManager
from core.risk_manager import RiskManager

class TestSystemIntegration:
    @pytest.fixture
    async def system_components(self):
    """Initialize all system components for testing"""
    config = self._load_test_config(
    # Initialize components
    orchestrator = EnhancedTradingOrchestrator(config
    await orchestrator.initialize(
    position_tracker = PositionTracker(

    order_manager = OrderManager(

    risk_manager = RiskManager(
    config=config['risk'],
    position_tracker=position_tracker,

return {
'orchestrator': orchestrator,
'position_tracker': position_tracker,
'order_manager': order_manager,
'risk_manager': risk_manager

def _load_test_config(self) -> Dict[str, Any}:
    """Load test configuration"""
return {
'redis': {
'host': 'localhost',
'port': 6379},
'risk': {
'max_positions': 20,
'capital': 500000,
'max_daily_loss': 0.02},
'zerodha': {
'api_key': 'test_key',
'api_secret': 'test_secret'},
'truedata': {
'api_key': 'test_key',
'user_id': 'test_user'

@pytest.mark.asyncio
async def test_market_data_integration(self, system_components}:
"""Test market data feed integration"""
orchestrator = system_components['orchestrator'
# Subscribe to test symbols
test_symbols = ['NIFTY', 'BANKNIFTY']
await orchestrator.broker.subscribe_market_data(test_symbols
# Wait for data
await asyncio.sleep(2
# Verify data received
assert orchestrator.market_data_cache
for symbol in test_symbols:
    assert symbol in orchestrator.market_data_cache

    @pytest.mark.asyncio
    async def test_order_execution(self, system_components):
    """Test order execution flow"""
    order_manager = system_components['order_manager']
    position_tracker = system_components['position_tracker']

    # Create test order
    order_params = {
    'symbol': 'NIFTY19500CE',
    'quantity': 1,
    'side': 'BUY',
    'order_type': 'MARKET'

    # Place order
    order_result = await order_manager.place_order(order_params
    # Verify position created
    await asyncio.sleep(1
    positions = position_tracker.get_positions(
    assert len(positions) > 0

    @pytest.mark.asyncio
    async def test_risk_management(self, system_components):
    """Test risk management system"""
    risk_manager = system_components['risk_manager'
    # Create test position
    test_position = {
    'symbol': 'NIFTY19500CE',
    'quantity': 100,
    'entry_price': 150.0

    # Check risk limits
    risk_check = await risk_manager.validate_signal(test_position
    # Verify risk metrics
    metrics = await risk_manager.get_risk_metrics(
    assert 'var_95' in metrics
    assert 'max_drawdown' in metrics

    @pytest.mark.asyncio
    async def test_emergency_procedures(self, system_components}:
    """Test emergency procedures"""
    orchestrator = system_components['orchestrator'
    # Trigger emergency stop
    await orchestrator.emergency_stop(
    # Verify system state
    assert not orchestrator.trading_enabled
    assert orchestrator.emergency_stop_active

    # Verify position liquidation
    positions = orchestrator.position_tracker.get_positions(
    @pytest.mark.asyncio
    async def test_system_health(self, system_components]:
    """Test system health monitoring"""
    orchestrator = system_components['orchestrator']

    # Check component health
    health = await orchestrator.check_health(
    # Verify all components

    @pytest.mark.asyncio
    async def test_data_synchronization(self, system_components):
    """Test data synchronization between components"""
    orchestrator = system_components['orchestrator']

    # Create test event
    test_event = {
    'type': 'POSITION_OPENED',
    'data': {
    'symbol': 'NIFTY19500CE',
    'quantity': 1,
    'price': 150.0

    # Publish event
    await orchestrator.event_bus.publish(test_event
    # Wait for propagation
    await asyncio.sleep(1
    # Verify all components updated
    positions = orchestrator.position_tracker.get_positions(
    risk_metrics = await orchestrator.risk_manager.get_risk_metrics(
    assert len(positions) > 0
    assert 'total_exposure' in risk_metrics
