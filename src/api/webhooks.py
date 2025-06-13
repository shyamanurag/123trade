"""
Webhook handler and routes for processing incoming webhook requests
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Dict, Optional, Set, List
import logging
import hmac
import hashlib
import time
from datetime import datetime, timedelta
from collections import defaultdict

from ..core.orchestrator import Orchestrator
from ..core.order_manager import OrderManager
from ..core.position_tracker import PositionTracker
from ..core.risk_manager import RiskManager
from ..core.news_impact_scalper import NewsImpactScalper
from ..core.compliance_manager import ComplianceManager
from ..core.database_manager import DatabaseManager
from ..core.backup_manager import BackupManager
from ..core.dynamic_config_manager import DynamicConfigManager
from ..core.user_session_manager import UserSessionManager
from ..core.trade_execution_queue import TradeExecutionQueue
from ..auth import verify_webhook_signature
from ..core.notification_manager import NotificationManager

logger = logging.getLogger(__name__)

class WebhookHandler:
    def __init__(self, config: Optional[Dict] = None):
        """Initialize webhook handler with configuration"""
        self.config = config or {}
        self.rate_limit = self.config.get('rate_limit', 10)  # requests per minute
        self.rate_window = self.config.get('rate_window', 60)  # seconds
        self.request_timestamps = defaultdict(list)
        self.subscribers = set()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def validate_webhook_data(self, data: Dict) -> bool:
        """Validate incoming webhook data"""
        required_fields = ['type', 'symbol', 'price', 'quantity', 'timestamp']
        return all(field in data for field in required_fields)

    def is_rate_limited(self, client_id: str) -> bool:
        """Check if client has exceeded rate limit"""
        now = time.time()
        window_start = now - self.rate_window
        
        # Clean old timestamps
        self.request_timestamps[client_id] = [
            ts for ts in self.request_timestamps[client_id]
            if ts > window_start
        ]
        
        # Check rate limit
        return len(self.request_timestamps[client_id]) >= self.rate_limit

    def handle_webhook(self, data: Dict, client_id: str = 'default') -> Dict:
        """Handle incoming webhook request"""
        try:
            # Check rate limit
            if self.is_rate_limited(client_id):
                return {
                    "status": "error",
                    "error": "Rate limit exceeded"
                }
            
            # Record request timestamp
            self.request_timestamps[client_id].append(time.time())
            
            # Validate data
            if not self.validate_webhook_data(data):
                return {
                    "status": "error",
                    "error": "Invalid webhook data"
                }
            
            # Process webhook
            result = self.process_webhook(data)
            
            # Notify subscribers
            self.notify_subscribers(data)
            
            return {
                "status": "success",
                "result": result
            }
            
        except Exception as e:
            self.logger.error(f"Error handling webhook: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def process_webhook(self, data: Dict) -> Dict:
        """Process webhook data"""
        try:
            # Parse timestamp
            timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
            
            # Process based on type
            if data['type'] == 'trade':
                return self._process_trade(data, timestamp)
            elif data['type'] == 'order':
                return self._process_order(data, timestamp)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown webhook type: {data['type']}"
                }
                
        except Exception as e:
            self.logger.error(f"Error processing webhook: {e}")
            raise

    def _process_trade(self, data: Dict, timestamp: datetime) -> Dict:
        """Process trade webhook"""
        return {
            "type": "trade",
            "symbol": data['symbol'],
            "price": float(data['price']),
            "quantity": int(data['quantity']),
            "timestamp": timestamp.isoformat(),
            "processed_at": datetime.utcnow().isoformat()
        }

    def _process_order(self, data: Dict, timestamp: datetime) -> Dict:
        """Process order webhook"""
        return {
            "type": "order",
            "symbol": data['symbol'],
            "order_id": data.get('order_id'),
            "status": data.get('status'),
            "timestamp": timestamp.isoformat(),
            "processed_at": datetime.utcnow().isoformat()
        }

    def subscribe(self, callback):
        """Subscribe to webhook notifications"""
        self.subscribers.add(callback)

    def unsubscribe(self, callback):
        """Unsubscribe from webhook notifications"""
        self.subscribers.discard(callback)

    def notify_subscribers(self, data: Dict):
        """Notify all subscribers of webhook data"""
        for callback in self.subscribers:
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"Error notifying subscriber: {e}")

# Initialize router and webhook handler
router = APIRouter()
webhook_handler = WebhookHandler()

# Market Data Webhooks
@router.post("/webhooks/market-data")
async def receive_market_data(
    data: Dict,
    request: Request,
    orchestrator: Orchestrator = Depends(),
    db_manager: DatabaseManager = Depends()
):
    """Receive real-time market data from TrueData"""
    try:
        # Verify webhook signature
        await verify_webhook_signature(request)
        
        # Handle webhook with rate limiting and validation
        result = webhook_handler.handle_webhook(data, client_id=request.client.host)
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Process market data
        await orchestrator.process_market_data(data)
        
        # Store market data
        await db_manager.store_market_data(data)
        
        return {"status": "received", "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        logger.error(f"Error processing market data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhooks/option-chain")
async def receive_option_chain(
    data: Dict,
    request: Request,
    orchestrator: Orchestrator = Depends(),
    db_manager: DatabaseManager = Depends()
):
    """Receive option chain updates"""
    try:
        # Verify webhook signature
        await verify_webhook_signature(request)
        
        # Handle webhook with rate limiting and validation
        result = webhook_handler.handle_webhook(data, client_id=request.client.host)
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Process option chain
        await orchestrator.process_option_chain(data)
        
        # Store option chain data
        await db_manager.store_option_chain(data)
        
        return {"status": "processed", "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        logger.error(f"Error processing option chain: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Order & Position Webhooks
@router.post("/webhooks/zerodha/order-update")
async def receive_zerodha_order_update(
    data: Dict,
    request: Request,
    order_manager: OrderManager = Depends(),
    trade_queue: TradeExecutionQueue = Depends(),
    db_manager: DatabaseManager = Depends()
):
    """Receive order status updates from Zerodha"""
    try:
        # Verify webhook signature
        await verify_webhook_signature(request)
        
        # Handle webhook with rate limiting and validation
        result = webhook_handler.handle_webhook(data, client_id=request.client.host)
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Extract Zerodha-specific fields
        order_id = data.get("order_id")
        status = data.get("status")
        filled_quantity = data.get("filled_quantity", 0)
        pending_quantity = data.get("pending_quantity", 0)
        average_price = data.get("average_price", 0.0)
        order_type = data.get("order_type")
        transaction_type = data.get("transaction_type")
        
        # Process order update
        await order_manager.process_order_update({
            "order_id": order_id,
            "status": status,
            "filled_quantity": filled_quantity,
            "pending_quantity": pending_quantity,
            "average_price": average_price,
            "order_type": order_type,
            "transaction_type": transaction_type,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Update trade queue
        await trade_queue.process_order_update({
            "order_id": order_id,
            "status": status,
            "filled_quantity": filled_quantity,
            "average_price": average_price
        })
        
        # Store order update
        await db_manager.store_order_update({
            "order_id": order_id,
            "status": status,
            "filled_quantity": filled_quantity,
            "pending_quantity": pending_quantity,
            "average_price": average_price,
            "order_type": order_type,
            "transaction_type": transaction_type,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "zerodha"
        })
        
        return {"status": "processed", "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        logger.error(f"Error processing Zerodha order update: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhooks/zerodha/position-update")
async def receive_zerodha_position_update(
    data: Dict,
    request: Request,
    position_tracker: PositionTracker = Depends(),
    backup_manager: BackupManager = Depends(),
    db_manager: DatabaseManager = Depends()
):
    """Receive position updates from Zerodha"""
    try:
        # Verify webhook signature
        await verify_webhook_signature(request)
        
        # Extract Zerodha-specific fields
        trading_symbol = data.get("trading_symbol")
        product = data.get("product")
        quantity = data.get("quantity", 0)
        average_price = data.get("average_price", 0.0)
        unrealized_pnl = data.get("unrealized_pnl", 0.0)
        realized_pnl = data.get("realized_pnl", 0.0)
        
        # Update position
        await position_tracker.update_position({
            "symbol": trading_symbol,
            "product": product,
            "quantity": quantity,
            "average_price": average_price,
            "unrealized_pnl": unrealized_pnl,
            "realized_pnl": realized_pnl,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Backup position
        await backup_manager.backup_positions()
        
        # Store position update
        await db_manager.store_position_update({
            "symbol": trading_symbol,
            "product": product,
            "quantity": quantity,
            "average_price": average_price,
            "unrealized_pnl": unrealized_pnl,
            "realized_pnl": realized_pnl,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "zerodha"
        })
        
        return {"status": "updated", "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        logger.error(f"Error processing Zerodha position update: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhooks/zerodha/trade-update")
async def receive_zerodha_trade_update(
    data: Dict,
    request: Request,
    order_manager: OrderManager = Depends(),
    position_tracker: PositionTracker = Depends(),
    db_manager: DatabaseManager = Depends()
):
    """Receive trade updates from Zerodha"""
    try:
        # Verify webhook signature
        await verify_webhook_signature(request)
        
        # Extract Zerodha-specific fields
        trade_id = data.get("trade_id")
        order_id = data.get("order_id")
        trading_symbol = data.get("trading_symbol")
        quantity = data.get("quantity", 0)
        price = data.get("price", 0.0)
        transaction_type = data.get("transaction_type")
        product = data.get("product")
        
        # Process trade update
        await order_manager.process_trade_update({
            "trade_id": trade_id,
            "order_id": order_id,
            "symbol": trading_symbol,
            "quantity": quantity,
            "price": price,
            "transaction_type": transaction_type,
            "product": product,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Update position
        await position_tracker.update_position({
            "symbol": trading_symbol,
            "product": product,
            "quantity": quantity,
            "price": price,
            "transaction_type": transaction_type,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Store trade update
        await db_manager.store_trade_update({
            "trade_id": trade_id,
            "order_id": order_id,
            "symbol": trading_symbol,
            "quantity": quantity,
            "price": price,
            "transaction_type": transaction_type,
            "product": product,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "zerodha"
        })
        
        return {"status": "processed", "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        logger.error(f"Error processing Zerodha trade update: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhooks/zerodha/margin-update")
async def receive_zerodha_margin_update(
    data: Dict,
    request: Request,
    risk_manager: RiskManager = Depends(),
    db_manager: DatabaseManager = Depends()
):
    """Receive margin updates from Zerodha"""
    try:
        # Verify webhook signature
        await verify_webhook_signature(request)
        
        # Extract Zerodha-specific fields
        available_cash = data.get("available_cash", 0.0)
        used_margin = data.get("used_margin", 0.0)
        opening_balance = data.get("opening_balance", 0.0)
        net_balance = data.get("net_balance", 0.0)
        
        # Process margin update
        await risk_manager.update_margin({
            "available_cash": available_cash,
            "used_margin": used_margin,
            "opening_balance": opening_balance,
            "net_balance": net_balance,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Store margin update
        await db_manager.store_margin_update({
            "available_cash": available_cash,
            "used_margin": used_margin,
            "opening_balance": opening_balance,
            "net_balance": net_balance,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "zerodha"
        })
        
        return {"status": "updated", "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        logger.error(f"Error processing Zerodha margin update: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# News & Events Webhooks
@router.post("/webhooks/news-feed")
async def receive_news(
    data: Dict,
    request: Request,
    news_scalper: NewsImpactScalper = Depends(),
    db_manager: DatabaseManager = Depends()
):
    """Receive news events for news impact strategy"""
    try:
        # Verify webhook signature
        await verify_webhook_signature(request)
        
        # Process news event
        await news_scalper.process_news_event(data)
        
        # Store news event
        await db_manager.store_news_event(data)
        
        return {"status": "processed", "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        logger.error(f"Error processing news event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhooks/economic-calendar")
async def receive_economic_event(
    data: Dict,
    request: Request,
    orchestrator: Orchestrator = Depends(),
    db_manager: DatabaseManager = Depends()
):
    """Receive economic calendar events"""
    try:
        # Verify webhook signature
        await verify_webhook_signature(request)
        
        # Process economic event
        await orchestrator.process_economic_event(data)
        
        # Store economic event
        await db_manager.store_economic_event(data)
        
        return {"status": "scheduled", "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        logger.error(f"Error processing economic event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Risk Management Webhooks
@router.post("/webhooks/risk-alert")
async def receive_risk_alert(
    data: Dict,
    request: Request,
    risk_manager: RiskManager = Depends(),
    dynamic_config: DynamicConfigManager = Depends(),
    db_manager: DatabaseManager = Depends(),
    notification_manager: NotificationManager = Depends()
):
    """Receive external risk alerts with enhanced processing"""
    try:
        # Verify webhook signature
        await verify_webhook_signature(request)
        
        # Extract risk alert data
        alert_id = data.get("alert_id")
        alert_type = data.get("alert_type")
        severity = data.get("severity", "MEDIUM")
        symbol = data.get("symbol")
        user_id = data.get("user_id")
        message = data.get("message")
        threshold = data.get("threshold")
        current_value = data.get("current_value")
        timestamp = data.get("timestamp", datetime.utcnow().isoformat())
        
        # Process risk alert
        alert_result = await risk_manager.process_external_alert({
            "alert_id": alert_id,
            "alert_type": alert_type,
            "severity": severity,
            "symbol": symbol,
            "user_id": user_id,
            "message": message,
            "threshold": threshold,
            "current_value": current_value,
            "timestamp": timestamp
        })
        
        # Update risk configuration if needed
        if data.get("requires_config_update"):
            await dynamic_config.adjust_risk_limits(
                user_id=user_id,
                limits=data.get("new_limits", {})
            )
        
        # Send notification if alert is critical
        if severity == "HIGH":
            await notification_manager.send_notification(
                user_id=user_id,
                notification_type="RISK_ALERT",
                title=f"Risk Alert: {alert_type}",
                message=message,
                priority="HIGH"
            )
        
        # Store risk alert
        await db_manager.store_risk_alert({
            "alert_id": alert_id,
            "alert_type": alert_type,
            "severity": severity,
            "symbol": symbol,
            "user_id": user_id,
            "message": message,
            "threshold": threshold,
            "current_value": current_value,
            "timestamp": timestamp,
            "action_taken": alert_result.get("action_taken"),
            "status": alert_result.get("status")
        })
        
        return {
            "status": "alert_processed",
            "alert_id": alert_id,
            "action_taken": alert_result.get("action_taken"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing risk alert: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhooks/margin-call")
async def receive_margin_call(
    data: Dict,
    request: Request,
    risk_manager: RiskManager = Depends(),
    backup_manager: BackupManager = Depends(),
    db_manager: DatabaseManager = Depends(),
    notification_manager: NotificationManager = Depends()
):
    """Handle margin call notifications with enhanced processing"""
    try:
        # Verify webhook signature
        await verify_webhook_signature(request)
        
        # Extract margin call data
        call_id = data.get("call_id")
        user_id = data.get("user_id")
        account_id = data.get("account_id")
        required_margin = data.get("required_margin", 0.0)
        current_margin = data.get("current_margin", 0.0)
        deficit = data.get("deficit", 0.0)
        deadline = data.get("deadline")
        positions = data.get("positions", [])
        timestamp = data.get("timestamp", datetime.utcnow().isoformat())
        
        # Backup positions before any forced liquidation
        await backup_manager.backup_positions()
        
        # Handle margin call
        call_result = await risk_manager.handle_margin_call({
            "call_id": call_id,
            "user_id": user_id,
            "account_id": account_id,
            "required_margin": required_margin,
            "current_margin": current_margin,
            "deficit": deficit,
            "deadline": deadline,
            "positions": positions,
            "timestamp": timestamp
        })
        
        # Send notification
        await notification_manager.send_notification(
            user_id=user_id,
            notification_type="MARGIN_CALL",
            title="Margin Call Alert",
            message=f"Margin call received. Required: {required_margin}, Current: {current_margin}, Deficit: {deficit}",
            priority="HIGH"
        )
        
        # Store margin call event
        await db_manager.store_margin_call({
            "call_id": call_id,
            "user_id": user_id,
            "account_id": account_id,
            "required_margin": required_margin,
            "current_margin": current_margin,
            "deficit": deficit,
            "deadline": deadline,
            "positions": positions,
            "timestamp": timestamp,
            "action_taken": call_result.get("action_taken"),
            "status": call_result.get("status")
        })
        
        return {
            "status": "handled",
            "call_id": call_id,
            "action_taken": call_result.get("action_taken"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error handling margin call: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhooks/risk-limit-update")
async def receive_risk_limit_update(
    data: Dict,
    request: Request,
    risk_manager: RiskManager = Depends(),
    dynamic_config: DynamicConfigManager = Depends(),
    db_manager: DatabaseManager = Depends()
):
    """Handle risk limit updates"""
    try:
        # Verify webhook signature
        await verify_webhook_signature(request)
        
        # Extract risk limit data
        user_id = data.get("user_id")
        limit_type = data.get("limit_type")
        new_limit = data.get("new_limit")
        reason = data.get("reason")
        timestamp = data.get("timestamp", datetime.utcnow().isoformat())
        
        # Update risk limits
        await risk_manager.update_risk_limits(
            user_id=user_id,
            limit_type=limit_type,
            new_limit=new_limit
        )
        
        # Update dynamic configuration
        await dynamic_config.update_risk_limits(
            user_id=user_id,
            limits={limit_type: new_limit}
        )
        
        # Store risk limit update
        await db_manager.store_risk_limit_update({
            "user_id": user_id,
            "limit_type": limit_type,
            "new_limit": new_limit,
            "reason": reason,
            "timestamp": timestamp
        })
        
        return {
            "status": "updated",
            "user_id": user_id,
            "limit_type": limit_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error updating risk limits: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhooks/risk-exposure-update")
async def receive_risk_exposure_update(
    data: Dict,
    request: Request,
    risk_manager: RiskManager = Depends(),
    db_manager: DatabaseManager = Depends()
):
    """Handle risk exposure updates"""
    try:
        # Verify webhook signature
        await verify_webhook_signature(request)
        
        # Extract exposure data
        user_id = data.get("user_id")
        symbol = data.get("symbol")
        exposure_type = data.get("exposure_type")
        current_exposure = data.get("current_exposure", 0.0)
        max_exposure = data.get("max_exposure", 0.0)
        timestamp = data.get("timestamp", datetime.utcnow().isoformat())
        
        # Update risk exposure
        await risk_manager.update_exposure({
            "user_id": user_id,
            "symbol": symbol,
            "exposure_type": exposure_type,
            "current_exposure": current_exposure,
            "max_exposure": max_exposure
        })
        
        # Store exposure update
        await db_manager.store_exposure_update({
            "user_id": user_id,
            "symbol": symbol,
            "exposure_type": exposure_type,
            "current_exposure": current_exposure,
            "max_exposure": max_exposure,
            "timestamp": timestamp
        })
        
        return {
            "status": "updated",
            "user_id": user_id,
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error updating risk exposure: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# System Monitoring Webhooks
@router.post("/webhooks/system-health")
async def receive_health_update(
    data: Dict,
    request: Request,
    orchestrator: Orchestrator = Depends(),
    db_manager: DatabaseManager = Depends()
):
    """Receive system health updates"""
    try:
        # Verify webhook signature
        await verify_webhook_signature(request)
        
        # Update health status
        await orchestrator.update_health_status(data)
        
        # Store health update
        await db_manager.store_health_update(data)
        
        return {"status": "health_updated", "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        logger.error(f"Error processing health update: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhooks/compliance-update")
async def receive_compliance_update(
    data: Dict,
    request: Request,
    compliance_manager: ComplianceManager = Depends(),
    db_manager: DatabaseManager = Depends()
):
    """Receive compliance status updates"""
    try:
        # Verify webhook signature
        await verify_webhook_signature(request)
        
        # Process compliance update
        await compliance_manager.process_update(data)
        
        # Store compliance update
        await db_manager.store_compliance_update(data)
        
        return {"status": "compliance_updated", "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        logger.error(f"Error processing compliance update: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 