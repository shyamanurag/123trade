from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from ..core.order_manager import OrderManager, OrderType, OrderSide

router = APIRouter()
order_manager = OrderManager()

class OrderRequest(BaseModel):
    symbol: str
    quantity: int
    order_type: OrderType
    price: Optional[float] = None
    side: OrderSide = OrderSide.BUY

@router.post("/orders")
def create_order(order: OrderRequest):
    new_order = order_manager.create_order(
        symbol=order.symbol,
        quantity=order.quantity,
        order_type=order.order_type,
        price=order.price,
        side=order.side
    )
    return {"order_id": new_order.order_id, "status": new_order.status}

@router.get("/orders/{order_id}")
def get_order(order_id: str):
    order = order_manager.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order.__dict__

@router.get("/orders")
def list_orders():
    return [order.__dict__ for order in order_manager.list_orders()]

@router.post("/orders/{order_id}/cancel")
def cancel_order(order_id: str):
    success = order_manager.cancel_order(order_id)
    if not success:
        raise HTTPException(status_code=400, detail="Order cannot be cancelled")
    return {"order_id": order_id, "status": "CANCELLED"} 