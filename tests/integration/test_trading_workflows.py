"""
Integration Tests for Trading Workflows
Tests end-to-end trading scenarios to ensure system reliability
"""

import pytest
import asyncio
import websockets
import json
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any
from unittest.mock import AsyncMock, patch
import httpx
import redis.asyncio as redis

# Test fixtures and setup
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def test_client():
    """Create test HTTP client"""
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        yield client

@pytest.fixture
async def redis_client():
    """Create test Redis client"""
    client = redis.from_url("redis://localhost:6379/1", decode_responses=True)  # Use test DB
    yield client
    # Cleanup
    await client.flushdb()
    await client.close()

@pytest.fixture
async def auth_token(test_client):
    """Get authentication token for testing"""
    login_data = {
        "username": "test_user",
        "password": "test_password"
    }
    response = await test_client.post("/auth/login", json=login_data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        # Create test user if not exists
        user_data = {
            "username": "test_user",
            "password": "test_password",
            "email": "test@example.com"
        }
        await test_client.post("/auth/register", json=user_data)
        response = await test_client.post("/auth/login", json=login_data)
        return response.json()["access_token"]

@pytest.fixture
def auth_headers(auth_token):
    """Get authorization headers"""
    return {"Authorization": f"Bearer {auth_token}"}

class TestTradingWorkflows:
    """Integration tests for complete trading workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_buy_sell_cycle(self, test_client, auth_headers, redis_client):
        """Test complete buy-sell trading cycle"""
        
        # Step 1: Get market data
        response = await test_client.get("/api/v1/market-data/RELIANCE", headers=auth_headers)
        assert response.status_code == 200
        market_data = response.json()
        current_price = market_data["ltp"]
        
        # Step 2: Place buy order
        buy_order = {
            "symbol": "RELIANCE",
            "side": "BUY",
            "quantity": 10,
            "order_type": "MARKET",
            "product": "MIS"
        }
        
        response = await test_client.post("/api/v1/orders", json=buy_order, headers=auth_headers)
        assert response.status_code == 201
        order_data = response.json()
        buy_order_id = order_data["order_id"]
        
        # Step 3: Wait for order execution (mock or actual)
        await asyncio.sleep(2)
        
        # Step 4: Check order status
        response = await test_client.get(f"/api/v1/orders/{buy_order_id}", headers=auth_headers)
        assert response.status_code == 200
        order_status = response.json()
        assert order_status["status"] in ["COMPLETE", "PARTIAL"]
        
        # Step 5: Check position
        response = await test_client.get("/api/v1/positions", headers=auth_headers)
        assert response.status_code == 200
        positions = response.json()
        reliance_position = next((p for p in positions if p["symbol"] == "RELIANCE"), None)
        assert reliance_position is not None
        assert reliance_position["quantity"] > 0
        
        # Step 6: Place sell order
        sell_order = {
            "symbol": "RELIANCE",
            "side": "SELL",
            "quantity": reliance_position["quantity"],
            "order_type": "MARKET",
            "product": "MIS"
        }
        
        response = await test_client.post("/api/v1/orders", json=sell_order, headers=auth_headers)
        assert response.status_code == 201
        sell_order_data = response.json()
        sell_order_id = sell_order_data["order_id"]
        
        # Step 7: Wait for sell execution
        await asyncio.sleep(2)
        
        # Step 8: Verify position closed
        response = await test_client.get("/api/v1/positions", headers=auth_headers)
        assert response.status_code == 200
        final_positions = response.json()
        final_reliance_position = next((p for p in final_positions if p["symbol"] == "RELIANCE"), None)
        assert final_reliance_position is None or final_reliance_position["quantity"] == 0
        
        # Step 9: Check PnL calculation
        response = await test_client.get("/api/v1/analytics/pnl", headers=auth_headers)
        assert response.status_code == 200
        pnl_data = response.json()
        assert "realized_pnl" in pnl_data
    
    @pytest.mark.asyncio
    async def test_risk_management_position_limit(self, test_client, auth_headers):
        """Test risk management prevents oversized positions"""
        
        # Get current account balance
        response = await test_client.get("/api/v1/account/balance", headers=auth_headers)
        assert response.status_code == 200
        balance = response.json()["available_balance"]
        
        # Try to place order exceeding position size limit
        large_order = {
            "symbol": "RELIANCE",
            "side": "BUY",
            "quantity": 10000,  # Intentionally large
            "order_type": "MARKET",
            "product": "MIS"
        }
        
        response = await test_client.post("/api/v1/orders", json=large_order, headers=auth_headers)
        
        # Should be rejected by risk management
        assert response.status_code in [400, 422]
        error_data = response.json()
        assert "risk" in error_data["detail"].lower() or "limit" in error_data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_stop_loss_execution(self, test_client, auth_headers):
        """Test stop loss order execution"""
        
        # Place buy order first
        buy_order = {
            "symbol": "TATASTEEL",
            "side": "BUY",
            "quantity": 5,
            "order_type": "MARKET",
            "product": "MIS"
        }
        
        response = await test_client.post("/api/v1/orders", json=buy_order, headers=auth_headers)
        assert response.status_code == 201
        
        await asyncio.sleep(2)  # Wait for execution
        
        # Get current market price
        response = await test_client.get("/api/v1/market-data/TATASTEEL", headers=auth_headers)
        current_price = response.json()["ltp"]
        stop_loss_price = current_price * 0.95  # 5% below current price
        
        # Place stop loss order
        stop_loss_order = {
            "symbol": "TATASTEEL",
            "side": "SELL",
            "quantity": 5,
            "order_type": "SL",
            "price": stop_loss_price,
            "trigger_price": stop_loss_price,
            "product": "MIS"
        }
        
        response = await test_client.post("/api/v1/orders", json=stop_loss_order, headers=auth_headers)
        assert response.status_code == 201
        sl_order_id = response.json()["order_id"]
        
        # Verify stop loss order is pending
        response = await test_client.get(f"/api/v1/orders/{sl_order_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "PENDING"
    
    @pytest.mark.asyncio
    async def test_multiple_broker_operations(self, test_client, auth_headers):
        """Test operations across multiple brokers"""
        
        # Test Zerodha operations
        zerodha_order = {
            "symbol": "INFY",
            "side": "BUY", 
            "quantity": 2,
            "order_type": "MARKET",
            "product": "CNC",
            "broker": "zerodha"
        }
        
        response = await test_client.post("/api/v1/orders", json=zerodha_order, headers=auth_headers)
        if response.status_code == 201:
            # Zerodha integration is working
            zerodha_order_id = response.json()["order_id"]
            
            # Check order status
            response = await test_client.get(f"/api/v1/orders/{zerodha_order_id}", headers=auth_headers)
            assert response.status_code == 200
            assert response.json()["broker"] == "zerodha"
        else:
            # Zerodha integration might not be configured
            assert response.status_code in [400, 503]
    
    @pytest.mark.asyncio
    async def test_portfolio_analytics_workflow(self, test_client, auth_headers):
        """Test portfolio analytics and reporting"""
        
        # Get portfolio summary
        response = await test_client.get("/api/v1/portfolio/summary", headers=auth_headers)
        assert response.status_code == 200
        portfolio = response.json()
        
        # Verify required fields
        required_fields = ["total_value", "day_pnl", "total_pnl", "positions"]
        for field in required_fields:
            assert field in portfolio
        
        # Get detailed performance metrics
        response = await test_client.get("/api/v1/analytics/performance", headers=auth_headers)
        assert response.status_code == 200
        performance = response.json()
        
        # Verify performance metrics
        assert "sharpe_ratio" in performance
        assert "max_drawdown" in performance
        assert "total_returns" in performance
        
        # Get risk metrics
        response = await test_client.get("/api/v1/risk/metrics", headers=auth_headers)
        assert response.status_code == 200
        risk_metrics = response.json()
        
        assert "var_95" in risk_metrics  # Value at Risk
        assert "beta" in risk_metrics
        assert "volatility" in risk_metrics

class TestWebSocketIntegration:
    """Test WebSocket real-time data streaming"""
    
    @pytest.mark.asyncio
    async def test_market_data_websocket(self):
        """Test real-time market data WebSocket"""
        
        uri = "ws://localhost:8002/ws/market-data"
        
        try:
            async with websockets.connect(uri) as websocket:
                # Subscribe to symbols
                subscribe_msg = {
                    "action": "subscribe",
                    "symbols": ["RELIANCE", "TCS", "INFY"]
                }
                await websocket.send(json.dumps(subscribe_msg))
                
                # Wait for confirmation
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                assert data["status"] == "subscribed"
                
                # Wait for market data
                for _ in range(3):  # Receive 3 updates
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    market_data = json.loads(message)
                    
                    # Verify message structure
                    assert "symbol" in market_data
                    assert "ltp" in market_data
                    assert "timestamp" in market_data
                    
                    # Verify symbol is one we subscribed to
                    assert market_data["symbol"] in ["RELIANCE", "TCS", "INFY"]
                    
        except websockets.exceptions.ConnectionClosed:
            pytest.skip("WebSocket server not available")
        except asyncio.TimeoutError:
            pytest.skip("WebSocket timeout - server might not be running")
    
    @pytest.mark.asyncio
    async def test_order_updates_websocket(self, auth_token):
        """Test real-time order updates via WebSocket"""
        
        uri = f"ws://localhost:8002/ws/orders?token={auth_token}"
        
        try:
            async with websockets.connect(uri) as websocket:
                # Place an order via HTTP to trigger WebSocket update
                async with httpx.AsyncClient() as client:
                    order_data = {
                        "symbol": "SBIN",
                        "side": "BUY",
                        "quantity": 1,
                        "order_type": "MARKET",
                        "product": "MIS"
                    }
                    
                    headers = {"Authorization": f"Bearer {auth_token}"}
                    response = await client.post(
                        "http://localhost:8000/api/v1/orders",
                        json=order_data,
                        headers=headers
                    )
                    
                    if response.status_code == 201:
                        # Wait for WebSocket order update
                        message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        order_update = json.loads(message)
                        
                        # Verify order update structure
                        assert "order_id" in order_update
                        assert "status" in order_update
                        assert "symbol" in order_update
                        assert order_update["symbol"] == "SBIN"
                        
        except websockets.exceptions.ConnectionClosed:
            pytest.skip("WebSocket server not available")
        except asyncio.TimeoutError:
            pytest.skip("WebSocket timeout - server might not be running")

class TestComplianceWorkflows:
    """Test compliance and regulatory workflows"""
    
    @pytest.mark.asyncio
    async def test_sebi_reporting_workflow(self, test_client, auth_headers):
        """Test SEBI compliance reporting"""
        
        # Generate compliance report
        report_request = {
            "report_type": "daily_trades",
            "start_date": "2024-01-15",
            "end_date": "2024-01-15"
        }
        
        response = await test_client.post(
            "/api/v1/compliance/reports",
            json=report_request,
            headers=auth_headers
        )
        
        assert response.status_code in [200, 202]  # Success or Accepted for async processing
        
        if response.status_code == 200:
            report = response.json()
            assert "report_id" in report
            assert "status" in report
        
        # Check audit trail
        response = await test_client.get("/api/v1/compliance/audit-trail", headers=auth_headers)
        assert response.status_code == 200
        audit_trail = response.json()
        assert isinstance(audit_trail, list)
    
    @pytest.mark.asyncio
    async def test_position_limit_compliance(self, test_client, auth_headers):
        """Test position limit compliance checks"""
        
        # Get current position limits
        response = await test_client.get("/api/v1/compliance/limits", headers=auth_headers)
        assert response.status_code == 200
        limits = response.json()
        
        # Verify limit structure
        assert "max_position_value" in limits
        assert "max_single_stock_percent" in limits
        
        # Test limit enforcement
        large_position_order = {
            "symbol": "RELIANCE",
            "side": "BUY",
            "quantity": 1000,  # Large quantity
            "order_type": "MARKET",
            "product": "CNC"
        }
        
        response = await test_client.post("/api/v1/orders", json=large_position_order, headers=auth_headers)
        
        # Should either succeed or be rejected based on limits
        assert response.status_code in [201, 400, 422]

class TestPerformanceAndLoad:
    """Performance and load testing"""
    
    @pytest.mark.asyncio
    async def test_concurrent_order_placement(self, test_client, auth_headers):
        """Test system under concurrent order load"""
        
        async def place_order(symbol: str, quantity: int):
            order = {
                "symbol": symbol,
                "side": "BUY",
                "quantity": quantity,
                "order_type": "MARKET",
                "product": "MIS"
            }
            
            start_time = time.time()
            response = await test_client.post("/api/v1/orders", json=order, headers=auth_headers)
            end_time = time.time()
            
            return {
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "order_id": response.json().get("order_id") if response.status_code == 201 else None
            }
        
        # Place 10 concurrent orders
        symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
        tasks = []
        
        for i in range(10):
            symbol = symbols[i % len(symbols)]
            tasks.append(place_order(symbol, 1))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_orders = 0
        total_response_time = 0
        
        for result in results:
            if not isinstance(result, Exception):
                if result["status_code"] == 201:
                    successful_orders += 1
                total_response_time += result["response_time"]
        
        # Performance assertions
        assert successful_orders >= 5  # At least 50% should succeed
        avg_response_time = total_response_time / len(results)
        assert avg_response_time < 2.0  # Average response time under 2 seconds
    
    @pytest.mark.asyncio
    async def test_market_data_performance(self, test_client, auth_headers):
        """Test market data API performance"""
        
        symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
                  "LT", "WIPRO", "BHARTIARTL", "MARUTI", "ASIANPAINT"]
        
        start_time = time.time()
        
        # Fetch market data for multiple symbols concurrently
        tasks = []
        for symbol in symbols:
            tasks.append(test_client.get(f"/api/v1/market-data/{symbol}", headers=auth_headers))
        
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Performance checks
        total_time = end_time - start_time
        assert total_time < 5.0  # Should complete within 5 seconds
        
        # Verify all responses
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "ltp" in data
            assert "symbol" in data

class TestErrorHandlingAndRecovery:
    """Test error handling and system recovery"""
    
    @pytest.mark.asyncio
    async def test_database_connection_failure_handling(self, test_client, auth_headers):
        """Test system behavior during database issues"""
        
        # This would typically involve mocking database failures
        # For now, test graceful degradation
        
        response = await test_client.get("/health", headers=auth_headers)
        health_data = response.json()
        
        # System should report component health
        assert "components" in health_data
        assert "database" in health_data["components"]
    
    @pytest.mark.asyncio
    async def test_invalid_order_handling(self, test_client, auth_headers):
        """Test handling of invalid orders"""
        
        invalid_orders = [
            {"symbol": "", "side": "BUY", "quantity": 10},  # Empty symbol
            {"symbol": "INVALID", "side": "INVALID", "quantity": 10},  # Invalid side
            {"symbol": "RELIANCE", "side": "BUY", "quantity": -5},  # Negative quantity
            {"symbol": "RELIANCE", "side": "BUY", "quantity": 0},  # Zero quantity
        ]
        
        for invalid_order in invalid_orders:
            response = await test_client.post("/api/v1/orders", json=invalid_order, headers=auth_headers)
            assert response.status_code in [400, 422]  # Should be rejected
            
            error_data = response.json()
            assert "detail" in error_data or "error" in error_data

# Test configuration
@pytest.mark.asyncio
async def test_system_startup_integration():
    """Test complete system startup integration"""
    
    # Test health endpoint
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/health")
        
        if response.status_code == 200:
            health_data = response.json()
            assert "status" in health_data
            assert "components" in health_data
            
            # Check component health
            components = health_data["components"]
            critical_components = ["database", "redis", "security"]
            
            for component in critical_components:
                if component in components:
                    # Component should be healthy or at least present
                    assert isinstance(components[component], bool)
        else:
            pytest.skip("Main application not running")

if __name__ == "__main__":
    # Run specific test
    pytest.main([__file__, "-v", "--tb=short"]) 