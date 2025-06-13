from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
import logging

from ..models.schema import Order, OrderCreate, OrderUpdate
from ..core.order_manager import OrderManager
from ..core.risk_manager import RiskManager
from ..core.capital_manager import CapitalManager
from ..auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/orders", response_model=Order)
async def create_order(
    order: OrderCreate,
    order_manager: OrderManager = Depends(),
    risk_manager: RiskManager = Depends(),
    capital_manager: CapitalManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Create a new order"""
    try:
        # Check risk limits
        risk_check = await risk_manager.check_order_risk(
            user_id=current_user.user_id,
            symbol=order.symbol,
            quantity=order.quantity,
            price=order.price
        )
        if not risk_check['allowed']:
            raise HTTPException(
                status_code=400,
                detail=f"Order rejected: {risk_check['reason']}"
            )

        # Check capital
        capital_check = await capital_manager.check_capital_for_order(
            user_id=current_user.user_id,
            symbol=order.symbol,
            quantity=order.quantity,
            price=order.price
        )
        if not capital_check['allowed']:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient capital: {capital_check['reason']}"
            )

        # Create order
        created_order = await order_manager.create_order(
            user_id=current_user.user_id,
            symbol=order.symbol,
            order_type=order.order_type,
            quantity=order.quantity,
            price=order.price,
            stop_price=order.stop_price,
            execution_strategy=order.execution_strategy,
            time_in_force=order.time_in_force,
            iceberg_quantity=order.iceberg_quantity
        )

        return created_order

    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orders/{order_id}", response_model=Order)
async def get_order(
    order_id: str,
    order_manager: OrderManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Get order details"""
    try:
        order = await order_manager.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Verify user owns the order
        if order.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view this order")
            
        return order

    except Exception as e:
        logger.error(f"Error getting order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/orders/{order_id}", response_model=Order)
async def update_order(
    order_id: str,
    order_update: OrderUpdate,
    order_manager: OrderManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Update order details"""
    try:
        # Get existing order
        order = await order_manager.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
            
        # Verify user owns the order
        if order.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this order")
            
        # Update order
        updated_order = await order_manager.update_order(
            order_id=order_id,
            status=order_update.status,
            filled_quantity=order_update.filled_quantity,
            average_fill_price=order_update.average_fill_price
        )
        
        return updated_order

    except Exception as e:
        logger.error(f"Error updating order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: str,
    order_manager: OrderManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Cancel an order"""
    try:
        # Get existing order
        order = await order_manager.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
            
        # Verify user owns the order
        if order.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to cancel this order")
            
        # Cancel order
        await order_manager.cancel_order(order_id)
        
        return {"message": f"Order {order_id} cancelled successfully"}

    except Exception as e:
        logger.error(f"Error cancelling order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}/orders", response_model=List[Order])
async def get_user_orders(
    user_id: str,
    status: Optional[str] = None,
    order_manager: OrderManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Get all orders for a user"""
    try:
        # Verify user is requesting their own orders
        if user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view these orders")
            
        orders = await order_manager.get_user_orders(user_id, status)
        return orders

    except Exception as e:
        logger.error(f"Error getting user orders: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orders/live", response_model=List[Order])
async def get_live_orders(
    order_manager: OrderManager = Depends(),
    current_user = Depends(get_current_user)
):
    """Get all live orders"""
    try:
        orders = await order_manager.get_live_orders()
        return orders

    except Exception as e:
        logger.error(f"Error getting live orders: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 