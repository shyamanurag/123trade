# api/rest_api.py
"""
Enhanced REST API for F&O Scalping System
Production-ready with authentication, rate limiting, and comprehensive endpoints
"""

from flask import Flask, jsonify, request, abort, Response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from functools import wraps
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import redis

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__
# Initialize Flask app
app=Flask(__name__
# Initialize extensions
jwt=JWTManager(app
# Rate limiting
limiter=Limiter(
app=app,

# Redis client for caching
redis_client=redis.Redis(host='localhost', port=6379, decode_responses=True
# Thread pool for async operations
executor=ThreadPoolExecutor(max_workers=10
# Global instances (initialized in main
orchestrator=None
position_tracker=None
order_manager=None
risk_manager=None
event_bus=None

# Custom decorators
def async_route(f):
    """Decorator to run route handlers asynchronously"""
    @ wraps(f
    def decorated_function(*args, **kwargs):
        loop=asyncio.new_event_loop(
        asyncio.set_event_loop(loop
        try:
        return loop.run_until_complete(f(*args, **kwargs
        finally:
        loop.close(
    return decorated_function

    def require_permission(permission):
        """Decorator to check user permissions"""
        def decorator(f):
            @ wraps(f
            @ jwt_required(
            def decorated_function(*args, **kwargs):
                user_id=get_jwt_identity(
                # Check permission (implement based on your auth system
                if not check_user_permission(user_id, permission):
                return f(*args, **kwargs
            return decorated_function
        return decorator

        """Cache response decorator"""
        def decorator(f):
            @ wraps(f
            def decorated_function(*args, **kwargs):
                cache_key=f"api:{request.endpoint}:{request.args}"
                cached=redis_client.get(cache_key
                if cached:
                return json.loads(cached
                result=f(*args, **kwargs
                redis_client.setex(cache_key, timeout, json.dumps(result
            return result
        return decorated_function
    return decorator

    # Error handlers
    @ app.errorhandler(400
    def bad_request(error):
    return jsonify({
    'error': 'Bad Request',
    'message': error.description,
    'timestamp': datetime.now().isoformat(}), 400

    @ app.errorhandler(401
    def unauthorized(error):
    return jsonify({
    'error': 'Unauthorized',
    'message': error.description,
    'timestamp': datetime.now().isoformat(}), 401

    @ app.errorhandler(403
    def forbidden(error):
    return jsonify({
    'error': 'Forbidden',
    'message': error.description,
    'timestamp': datetime.now().isoformat(}), 403

    @ app.errorhandler(404
    def not_found(error):
    return jsonify({
    'error': 'Not Found',
    'message': 'The requested resource was not found',
    'timestamp': datetime.now().isoformat(}), 404

    @ app.errorhandler(429
    def rate_limit_exceeded(error):
    return jsonify({
    'error': 'Too Many Requests',
    'message': 'Rate limit exceeded. Please try again later.',
    'timestamp': datetime.now().isoformat(}), 429

    @ app.errorhandler(500
    def internal_error(error):
        logger.error(f"Internal server error: {error}"
    return jsonify({
    'error': 'Internal Server Error',
    'message': 'An unexpected error occurred',
    'timestamp': datetime.now().isoformat(}), 500

    # Health and monitoring endpoints
    def health_check():
        """Comprehensive health check endpoint"""
        try:
            health={
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '2.0.0',
            'components': {

            # Check orchestrator
            if orchestrator:
                'status': 'up' if orchestrator.is_running else 'down',
                'trading_enabled': orchestrator.trading_enabled

                # Check position tracker
                if position_tracker:
                    'status': 'up',
                    'open_positions': len(position_tracker.positions),
                    'daily_pnl': position_tracker.daily_pnl

                    # Check Redis connection
                    try:
                        redis_client.ping(
                        except:

                        # Check broker connection
                        if orchestrator and orchestrator.broker:
                            broker_connected=asyncio.run(orchestrator.broker.is_connected(
                            'status': 'up' if broker_connected else 'down'

                            # Overall health determination

                        return jsonify(health
                        except Exception as e:
                            logger.error(f"Health check failed: {e}"
                        return jsonify({
                        'status': 'error',
                        'message': str(e),
                        'timestamp': datetime.now().isoformat(}), 500

                        @ require_permission('view_metrics'
                        def prometheus_metrics():
                            """Expose Prometheus metrics"""

                            # Authentication endpoints
                            @ limiter.limit("5 per minute"
                            def login():
                                """User authentication endpoint"""
                                try:
                                    data=request.get_json(
                                    if not data:

                                        username=data.get('username'
                                    password=data.get('password'
                                    if not username or not password:

                                        # Validate credentials (implement your auth logic
                                        user=validate_user_credentials(username, password
                                        if not user:

                                            # Create JWT token
                                            access_token=create_access_token(
                                            identity=user['id'],
                                            'username': user['username'],
                                            'permissions': user.get('permissions', []

                                            # Log successful login
                                            logger.info(f"User {username} logged in successfully"
                                        return jsonify({
                                        'access_token': access_token,
                                        'token_type': 'Bearer',
                                        'expires_in': 86400,  # 24 hours
                                        'user': {
                                        'id': user['id'],
                                        'username': user['username'],
                                        'email': user.get('email'),
                                        'capital': user.get('capital', 500000),
                                        'is_active': user.get('is_active', True),
                                        'permissions': user.get('permissions', []

                                        except Exception as e:
                                            logger.error(f"Login error: {e}"
                                            abort(500
                                            def refresh_token():
                                                """Refresh JWT token"""
                                                identity=get_jwt_identity(
                                                access_token=create_access_token(identity=identity
                                            return jsonify({'access_token': access_token
                                            @ jwt_required(
                                            def logout():
                                                """Logout endpoint (invalidate token)"""
                                                # Add token to blacklist (implement if needed
                                            return jsonify({'message': 'Successfully logged out'
                                            # Dashboard endpoints
                                            @ jwt_required(
                                            @ async_route
                                            async def get_dashboard_overview():
                                            """Get comprehensive dashboard data"""
                                            try:
                                                overview={
                                                'timestamp': datetime.now().isoformat(),
                                                'market_status': 'open' if is_market_open() else 'closed',
                                                'system_status': 'active' if orchestrator and orchestrator.is_running else 'inactive'

                                                # P&L metrics
                                                if position_tracker:
                                                    pnl_data= position_tracker.get_real_time_pnl(
                                                    'daily_pnl': pnl_data['daily_pnl'],
                                                    'daily_pnl_percent': pnl_data['pnl_percent'],
                                                    'realized_pnl': pnl_data['realized_pnl'],
                                                    'unrealized_pnl': pnl_data['unrealized_pnl'],
                                                    'total_pnl': pnl_data['total_pnl'],
                                                    'open_positions': pnl_data['open_positions'],
                                                    'total_trades': pnl_data['total_trades'],
                                                    'win_rate': pnl_data['win_rate']

                                                    # Risk metrics
                                                    if risk_manager:
                                                        risk_metrics=await risk_manager.get_risk_metrics(
                                                        'total_exposure': risk_metrics['total_exposure'],
                                                        'exposure_percent': risk_metrics['exposure_percent'],
                                                        'max_drawdown': risk_metrics.get('max_drawdown', 0),
                                                        'current_var': risk_metrics.get('var_95', 0),
                                                        'risk_score': risk_metrics.get('risk_score', 0

                                                        # Order metrics
                                                        if order_manager:
                                                            order_metrics=await order_manager.get_order_metrics(
                                                            'pending_orders': order_metrics.get('orders_queued', 0),
                                                            'avg_latency_ms': order_metrics.get('avg_latency_ms', 0),
                                                            'orders_per_second': order_metrics.get('current_ops', 0),
                                                            'daily_orders': order_metrics.get('daily_orders', 0

                                                            # Strategy performance
                                                            if orchestrator:
                                                                strategies=await orchestrator.get_strategy_performance(
                                                            return jsonify(overview
                                                            except Exception as e:
                                                                logger.error(f"Error getting dashboard overview: {e}"
                                                                abort(500
                                                                # Position management endpoints
                                                                @ jwt_required(
                                                                @ async_route
                                                                async def get_positions():
                                                                """Get positions with filtering"""
                                                                try:
                                                                    if not position_tracker:

                                                                        # Get query parameters
                                                                        status=request.args.get('status', 'open'
                                                                        strategy=request.args.get('strategy'
                                                                        symbol=request.args.get('symbol'
                                                                        sort_by=request.args.get('sort_by', 'entry_time'
                                                                        sort_order=request.args.get('sort_order', 'desc'
                                                                        # Get positions
                                                                        positions=position_tracker.get_open_positions(
                                                                        positions=position_tracker.position_history[-100:]  # Last 100
                                                                        else:
                                                                            positions=(position_tracker.get_open_positions() +
                                                                            position_tracker.position_history[-50:]
                                                                            # Apply filters
                                                                            if strategy:
                                                                                positions=[p for p in positions if p.strategy_name == strategy]

                                                                                if symbol:
                                                                                    positions=[p for p in positions if symbol in p.symbol]

                                                                                    # Sort positions
                                                                                    positions.sort(

                                                                                    # Convert to dict
                                                                                    positions_data=[p.to_dict(] for p in positions]

                                                                                return jsonify({
                                                                                'positions': positions_data,
                                                                                'count': len(positions_data),
                                                                                'filters': {
                                                                                'status': status,
                                                                                'strategy': strategy,
                                                                                'symbol': symbol},
                                                                                'timestamp': datetime.now().isoformat(

                                                                                except Exception as e:
                                                                                    logger.error(f"Error getting positions: {e}"
                                                                                    abort(500
                                                                                    @ jwt_required(
                                                                                    def get_position_details(position_id):
                                                                                        """Get detailed position information"""
                                                                                        try:
                                                                                            if not position_tracker:

                                                                                                # Find position
                                                                                                position=position_tracker.get_position(position_id
                                                                                                if not position:
                                                                                                    # Check history
                                                                                                    position=next(
                                                                                                    None

                                                                                                    if not position:

                                                                                                        # Get detailed data
                                                                                                        position_data=position.to_dict(
                                                                                                        # Add order history if available
                                                                                                        if order_manager:
                                                                                                            orders=[o for o in order_manager.orders.values(
                                                                                                            if position_id in o.metadata.get('position_id', '']]

                                                                                                            return jsonify(position_data
                                                                                                            except Exception as e:
                                                                                                                logger.error(f"Error getting position details: {e}"
                                                                                                                abort(500
                                                                                                                @ jwt_required(
                                                                                                                @ require_permission('close_positions'
                                                                                                                @ async_route
                                                                                                                async def close_position(position_id):
                                                                                                                """Close a specific position"""
                                                                                                                try:
                                                                                                                    if not position_tracker or not order_manager:

                                                                                                                        data=request.get_json(
                                                                                                                        # Validate position exists
                                                                                                                        position=position_tracker.get_position(position_id
                                                                                                                        if not position:

                                                                                                                            # Close position
                                                                                                                            order_id=await order_manager.close_position(
                                                                                                                            position,

                                                                                                                            if not order_id:

                                                                                                                            return jsonify({
                                                                                                                            'success': True,
                                                                                                                            'message': 'Position close order created',
                                                                                                                            'order_id': order_id,
                                                                                                                            'position_id': position_id

                                                                                                                            except Exception as e:
                                                                                                                                logger.error(f"Error closing position: {e}"
                                                                                                                                abort(500
                                                                                                                                # Order management endpoints
                                                                                                                                @ jwt_required(
                                                                                                                                def get_orders():
                                                                                                                                    """Get orders with filtering"""
                                                                                                                                    try:
                                                                                                                                        if not order_manager:

                                                                                                                                            # Get parameters
                                                                                                                                            status=request.args.get('status', 'all'
                                                                                                                                            limit=min(int(request.args.get('limit', 100)), 1000
                                                                                                                                            offset=int(request.args.get('offset', 0
                                                                                                                                            # Filter orders
                                                                                                                                            orders=list(order_manager.orders.values(
                                                                                                                                            orders=[o for o in orders if o.status.value.lower(] ==
                                                                                                                                            status.lower()]

                                                                                                                                            # Sort by timestamp (newest first
                                                                                                                                            # Paginate
                                                                                                                                            total_count=len(orders
                                                                                                                                            orders=orders[offset:offset + limit]

                                                                                                                                        return jsonify({
                                                                                                                                        'orders': [o.to_dict(} for o in orders},
                                                                                                                                        'pagination': {
                                                                                                                                        'total': total_count,
                                                                                                                                        'limit': limit,
                                                                                                                                        'offset': offset,
                                                                                                                                        'has_more': (offset + limit] < total_count},
                                                                                                                                        'timestamp': datetime.now().isoformat(

                                                                                                                                        except Exception as e:
                                                                                                                                            logger.error(f"Error getting orders: {e}"
                                                                                                                                            abort(500
                                                                                                                                            @ jwt_required(
                                                                                                                                            @ require_permission('place_orders'
                                                                                                                                            @ limiter.limit("10 per minute"
                                                                                                                                            @ async_route
                                                                                                                                            async def create_manual_order():
                                                                                                                                            """Create manual order"""
                                                                                                                                            try:
                                                                                                                                                if not order_manager:

                                                                                                                                                    data=request.get_json(
                                                                                                                                                    # Validate required fields
                                                                                                                                                    required_fields=['symbol', 'quantity', 'order_type', 'side']
                                                                                                                                                    for field in required_fields:
                                                                                                                                                        if field not in data:

                                                                                                                                                            # Create manual signal
                                                                                                                                                            from ..models import Signal, OptionType, OrderSide

                                                                                                                                                            signal=Signal(
                                                                                                                                                            strategy_name='manual',
                                                                                                                                                            symbol=data['symbol'],
                                                                                                                                                            'user_id': get_jwt_identity(),
                                                                                                                                                            'manual': True,
                                                                                                                                                            'notes': data.get('notes', ''

                                                                                                                                                            # Execute through order manager
                                                                                                                                                            result=await order_manager.execute_signal(signal
                                                                                                                                                        return jsonify({
                                                                                                                                                        'success': True,
                                                                                                                                                        'order_id': result['order_id'},
                                                                                                                                                        'status': result['status'],
                                                                                                                                                        'message': 'Order queued successfully'

                                                                                                                                                        except Exception as e:
                                                                                                                                                            logger.error(f"Error creating manual order: {e}"
                                                                                                                                                            abort(500
                                                                                                                                                            @ jwt_required(
                                                                                                                                                            @ require_permission('cancel_orders'
                                                                                                                                                            @ async_route
                                                                                                                                                            async def cancel_order(order_id):
                                                                                                                                                            """Cancel pending order"""
                                                                                                                                                            try:
                                                                                                                                                                if not order_manager:

                                                                                                                                                                    success=await order_manager.cancel_order(order_id
                                                                                                                                                                    if not success:

                                                                                                                                                                    return jsonify({
                                                                                                                                                                    'success': True,
                                                                                                                                                                    'message': 'Order cancelled successfully',
                                                                                                                                                                    'order_id': order_id

                                                                                                                                                                    except Exception as e:
                                                                                                                                                                        logger.error(f"Error cancelling order: {e}"
                                                                                                                                                                        abort(500
                                                                                                                                                                        # Strategy management endpoints
                                                                                                                                                                        @ jwt_required(
                                                                                                                                                                        @ async_route
                                                                                                                                                                        async def get_strategies():
                                                                                                                                                                        """Get all strategies with their status"""
                                                                                                                                                                        try:
                                                                                                                                                                            if not orchestrator:

                                                                                                                                                                                strategies=[]

                                                                                                                                                                                for name, strategy in orchestrator.strategies.items():
                                                                                                                                                                                    strategy_data={
                                                                                                                                                                                    'name': name,
                                                                                                                                                                                    'enabled': strategy.is_enabled,
                                                                                                                                                                                    'allocation': strategy.allocation,
                                                                                                                                                                                    'metrics': strategy.get_strategy_metrics(),
                                                                                                                                                                                    'health': 'healthy' if strategy.is_healthy() else 'unhealthy'

                                                                                                                                                                                    strategies.append(strategy_data
                                                                                                                                                                                return jsonify({
                                                                                                                                                                                'strategies': strategies,
                                                                                                                                                                                'total_allocation': sum(s['allocation'} for s in strategies if s['enabled']),
                                                                                                                                                                                'timestamp': datetime.now().isoformat(

                                                                                                                                                                                except Exception as e:
                                                                                                                                                                                    logger.error(f"Error getting strategies: {e}"
                                                                                                                                                                                    abort(500
                                                                                                                                                                                    @ jwt_required(
                                                                                                                                                                                    def get_strategy_details(strategy_name):
                                                                                                                                                                                        """Get detailed strategy information"""
                                                                                                                                                                                        try:
                                                                                                                                                                                            if not orchestrator:

                                                                                                                                                                                                strategy=orchestrator.strategies.get(strategy_name
                                                                                                                                                                                                if not strategy:

                                                                                                                                                                                                    # Get detailed metrics
                                                                                                                                                                                                    metrics=strategy.get_strategy_metrics(
                                                                                                                                                                                                    # Get recent signals
                                                                                                                                                                                                    recent_signals=[s.to_dict(] for s in strategy.recent_signals]

                                                                                                                                                                                                    # Get positions
                                                                                                                                                                                                    if position_tracker:
                                                                                                                                                                                                        positions=position_tracker.get_positions_by_strategy(strategy_name
                                                                                                                                                                                                        positions_data=[p.to_dict(] for p in positions]
                                                                                                                                                                                                        else:
                                                                                                                                                                                                            positions_data=[]

                                                                                                                                                                                                        return jsonify({
                                                                                                                                                                                                        'name': strategy_name,
                                                                                                                                                                                                        'enabled': strategy.is_enabled,
                                                                                                                                                                                                        'allocation': strategy.allocation,
                                                                                                                                                                                                        'config': strategy.config,
                                                                                                                                                                                                        'metrics': metrics,
                                                                                                                                                                                                        'recent_signals': recent_signals[-20:},  # Last 20
                                                                                                                                                                                                        'active_positions': positions_data,
                                                                                                                                                                                                        'health': 'healthy' if strategy.is_healthy(] else 'unhealthy',
                                                                                                                                                                                                        'timestamp': datetime.now().isoformat(

                                                                                                                                                                                                        except Exception as e:
                                                                                                                                                                                                            logger.error(f"Error getting strategy details: {e}"
                                                                                                                                                                                                            abort(500
                                                                                                                                                                                                            @ jwt_required(
                                                                                                                                                                                                            @ require_permission('manage_strategies'
                                                                                                                                                                                                            @ async_route
                                                                                                                                                                                                            async def toggle_strategy(strategy_name):
                                                                                                                                                                                                            """Enable or disable a strategy"""
                                                                                                                                                                                                            try:
                                                                                                                                                                                                                if not orchestrator:

                                                                                                                                                                                                                    data=request.get_json(
                                                                                                                                                                                                                    enabled=data.get('enabled', True
                                                                                                                                                                                                                    strategy=orchestrator.strategies.get(strategy_name
                                                                                                                                                                                                                    if not strategy:

                                                                                                                                                                                                                        # Toggle strategy

                                                                                                                                                                                                                        # Log action
                                                                                                                                                                                                                        logger.info(f"Strategy {strategy_name} {'enabled' if enabled else 'disabled'} "
                                                                                                                                                                                                                        f"by user {get_jwt_identity()}"
                                                                                                                                                                                                                    return jsonify({
                                                                                                                                                                                                                    'success': True,
                                                                                                                                                                                                                    'strategy': strategy_name,
                                                                                                                                                                                                                    'enabled': enabled,
                                                                                                                                                                                                                    'message': f"Strategy {'enabled' if enabled else 'disabled'} successfully"

                                                                                                                                                                                                                    except Exception as e:
                                                                                                                                                                                                                        logger.error(f"Error toggling strategy: {e}"
                                                                                                                                                                                                                        abort(500
                                                                                                                                                                                                                        # System control endpoints
                                                                                                                                                                                                                        @ jwt_required(
                                                                                                                                                                                                                        @ require_permission('emergency_stop'
                                                                                                                                                                                                                        @ limiter.limit("1 per minute"
                                                                                                                                                                                                                        @ async_route
                                                                                                                                                                                                                        async def emergency_stop():
                                                                                                                                                                                                                        """Emergency stop all trading activities"""
                                                                                                                                                                                                                        try:
                                                                                                                                                                                                                            logger.critical(f"EMERGENCY STOP initiated by user {get_jwt_identity()}"
                                                                                                                                                                                                                            results={
                                                                                                                                                                                                                            # Stop orchestrator
                                                                                                                                                                                                                            if orchestrator:
                                                                                                                                                                                                                                await orchestrator.emergency_shutdown(
                                                                                                                                                                                                                                # Cancel all orders
                                                                                                                                                                                                                                if order_manager:
                                                                                                                                                                                                                                    cancelled=await order_manager.cancel_all_pending_orders(
                                                                                                                                                                                                                                    # Close all positions
                                                                                                                                                                                                                                    if position_tracker:
                                                                                                                                                                                                                                        closed=await position_tracker.emergency_close_all("Emergency Stop"
                                                                                                                                                                                                                                    return jsonify({
                                                                                                                                                                                                                                    'success': True,
                                                                                                                                                                                                                                    'message': 'Emergency stop executed',
                                                                                                                                                                                                                                    'results': results,
                                                                                                                                                                                                                                    'timestamp': datetime.now().isoformat(

                                                                                                                                                                                                                                    except Exception as e:
                                                                                                                                                                                                                                        logger.error(f"Error during emergency stop: {e}"
                                                                                                                                                                                                                                        abort(500
                                                                                                                                                                                                                                        @ jwt_required(
                                                                                                                                                                                                                                        @ require_permission('control_system'
                                                                                                                                                                                                                                        @ async_route
                                                                                                                                                                                                                                        async def pause_trading():
                                                                                                                                                                                                                                        """Pause new trade generation"""
                                                                                                                                                                                                                                        try:
                                                                                                                                                                                                                                            if not orchestrator:

                                                                                                                                                                                                                                                data=request.get_json(
                                                                                                                                                                                                                                                duration_minutes=data.get('duration', 60
                                                                                                                                                                                                                                                await orchestrator.pause_trading(duration_minutes
                                                                                                                                                                                                                                            return jsonify({
                                                                                                                                                                                                                                            'success': True,
                                                                                                                                                                                                                                            'message': f'Trading paused for {duration_minutes} minutes',

                                                                                                                                                                                                                                            except Exception as e:
                                                                                                                                                                                                                                                logger.error(f"Error pausing trading: {e}"
                                                                                                                                                                                                                                                abort(500
                                                                                                                                                                                                                                                @ jwt_required(
                                                                                                                                                                                                                                                @ require_permission('control_system'
                                                                                                                                                                                                                                                @ async_route
                                                                                                                                                                                                                                                async def resume_trading():
                                                                                                                                                                                                                                                """Resume trading"""
                                                                                                                                                                                                                                                try:
                                                                                                                                                                                                                                                    if not orchestrator:

                                                                                                                                                                                                                                                        await orchestrator.resume_trading(
                                                                                                                                                                                                                                                    return jsonify({
                                                                                                                                                                                                                                                    'success': True,
                                                                                                                                                                                                                                                    'message': 'Trading resumed',
                                                                                                                                                                                                                                                    'timestamp': datetime.now().isoformat(

                                                                                                                                                                                                                                                    except Exception as e:
                                                                                                                                                                                                                                                        logger.error(f"Error resuming trading: {e}"
                                                                                                                                                                                                                                                        abort(500
                                                                                                                                                                                                                                                        # Report endpoints
                                                                                                                                                                                                                                                        @ jwt_required(
                                                                                                                                                                                                                                                        def get_daily_report():
                                                                                                                                                                                                                                                            """Get daily performance report"""
                                                                                                                                                                                                                                                            try:
                                                                                                                                                                                                                                                                date_str=request.args.get('date', datetime.now().strftime('%Y-%m-%d'
                                                                                                                                                                                                                                                                # Try to get from cache first
                                                                                                                                                                                                                                                                cache_key=f"daily_report:{date_str}"
                                                                                                                                                                                                                                                                cached_report=redis_client.get(cache_key
                                                                                                                                                                                                                                                                if cached_report:
                                                                                                                                                                                                                                                                return json.loads(cached_report
                                                                                                                                                                                                                                                                # Generate report
                                                                                                                                                                                                                                                                report_data=generate_daily_report(date_str
                                                                                                                                                                                                                                                                # Cache for 5 minutes
                                                                                                                                                                                                                                                                redis_client.setex(cache_key, 300, json.dumps(report_data
                                                                                                                                                                                                                                                            return jsonify(report_data
                                                                                                                                                                                                                                                            except Exception as e:
                                                                                                                                                                                                                                                                logger.error(f"Error generating daily report: {e}"
                                                                                                                                                                                                                                                                abort(500
                                                                                                                                                                                                                                                                @ jwt_required(
                                                                                                                                                                                                                                                                @ require_permission('export_data'
                                                                                                                                                                                                                                                                @limiter.limit("5 per hour"
                                                                                                                                                                                                                                                                @async_route
                                                                                                                                                                                                                                                                async def export_data():
                                                                                                                                                                                                                                                                """Export trading data"""
                                                                                                                                                                                                                                                                try:
                                                                                                                                                                                                                                                                    data = request.get_json(
                                                                                                                                                                                                                                                                    export_type = data.get('type', 'trades'
                                                                                                                                                                                                                                                                    format_type = data.get('format', 'json'
                                                                                                                                                                                                                                                                    date_from = data.get('date_from', datetime.now().strftime('%Y-%m-%d'
                                                                                                                                                                                                                                                                    date_to = data.get('date_to', datetime.now().strftime('%Y-%m-%d'
                                                                                                                                                                                                                                                                    # Generate export
                                                                                                                                                                                                                                                                    export_data = await export_trades(date_from, date_to, format_type
                                                                                                                                                                                                                                                                    export_data = await export_positions(date_from, date_to, format_type
                                                                                                                                                                                                                                                                    export_data = await export_orders(date_from, date_to, format_type
                                                                                                                                                                                                                                                                    else:

                                                                                                                                                                                                                                                                        filename = f"{export_type}_{date_from}_{date_to}.{format_type}"

                                                                                                                                                                                                                                                                    return jsonify({
                                                                                                                                                                                                                                                                    'success': True,
                                                                                                                                                                                                                                                                    'filename': filename,
                                                                                                                                                                                                                                                                    'download_url': f"/api/reports/download/{filename}",
                                                                                                                                                                                                                                                                    'expires_in': 3600  # 1 hour

                                                                                                                                                                                                                                                                    except Exception as e:
                                                                                                                                                                                                                                                                        logger.error(f"Error exporting data: {e}"
                                                                                                                                                                                                                                                                        abort(500
                                                                                                                                                                                                                                                                        # WebSocket info endpoint
                                                                                                                                                                                                                                                                        @jwt_required(
                                                                                                                                                                                                                                                                        def websocket_info():
                                                                                                                                                                                                                                                                            """Get WebSocket connection information"""
                                                                                                                                                                                                                                                                        return jsonify({
                                                                                                                                                                                                                                                                        'url': f"ws://{request.host}/ws",
                                                                                                                                                                                                                                                                        'protocols': ['market_data', 'order_updates', 'position_updates', 'system_events'],
                                                                                                                                                                                                                                                                        'heartbeat_interval': 30,
                                                                                                                                                                                                                                                                        'reconnect_interval': 5,
                                                                                                                                                                                                                                                                        'auth_required': True,
                                                                                                                                                                                                                                                                        'auth_method': 'jwt_token'

                                                                                                                                                                                                                                                                        # Risk management endpoints
                                                                                                                                                                                                                                                                        @jwt_required(
                                                                                                                                                                                                                                                                        @async_route
                                                                                                                                                                                                                                                                        async def get_risk_metrics():
                                                                                                                                                                                                                                                                        """Get current risk metrics"""
                                                                                                                                                                                                                                                                        try:
                                                                                                                                                                                                                                                                            if not risk_manager:

                                                                                                                                                                                                                                                                                metrics = await risk_manager.get_comprehensive_risk_metrics(
                                                                                                                                                                                                                                                                            return jsonify({
                                                                                                                                                                                                                                                                            'metrics': metrics,
                                                                                                                                                                                                                                                                            'timestamp': datetime.now().isoformat(

                                                                                                                                                                                                                                                                            except Exception as e:
                                                                                                                                                                                                                                                                                logger.error(f"Error getting risk metrics: {e}"
                                                                                                                                                                                                                                                                                abort(500
                                                                                                                                                                                                                                                                                @jwt_required(
                                                                                                                                                                                                                                                                                def get_risk_limits():
                                                                                                                                                                                                                                                                                    """Get current risk limits and usage"""
                                                                                                                                                                                                                                                                                    try:
                                                                                                                                                                                                                                                                                        if not risk_manager:

                                                                                                                                                                                                                                                                                            limits = risk_manager.get_risk_limits(
                                                                                                                                                                                                                                                                                            usage = risk_manager.get_risk_usage(
                                                                                                                                                                                                                                                                                        return jsonify({
                                                                                                                                                                                                                                                                                        'limits': limits,
                                                                                                                                                                                                                                                                                        'usage': usage,
                                                                                                                                                                                                                                                                                        'timestamp': datetime.now().isoformat(

                                                                                                                                                                                                                                                                                        except Exception as e:
                                                                                                                                                                                                                                                                                            logger.error(f"Error getting risk limits: {e}"
                                                                                                                                                                                                                                                                                            abort(500
                                                                                                                                                                                                                                                                                            # Market data endpoints
                                                                                                                                                                                                                                                                                            @jwt_required(
                                                                                                                                                                                                                                                                                            def get_market_status():
                                                                                                                                                                                                                                                                                                """Get current market status"""
                                                                                                                                                                                                                                                                                                try:
                                                                                                                                                                                                                                                                                                    status = {
                                                                                                                                                                                                                                                                                                    'is_open': is_market_open(),
                                                                                                                                                                                                                                                                                                    'current_time': datetime.now().isoformat(),
                                                                                                                                                                                                                                                                                                    'market_hours': {
                                                                                                                                                                                                                                                                                                    'open': '09:15',
                                                                                                                                                                                                                                                                                                    'close': '15:30',
                                                                                                                                                                                                                                                                                                    'pre_open': '09:00',
                                                                                                                                                                                                                                                                                                    'post_close': '15:40'

                                                                                                                                                                                                                                                                                                    # Add market data if available
                                                                                                                                                                                                                                                                                                    if orchestrator and orchestrator.data_provider:
                                                                                                                                                                                                                                                                                                        market_data = asyncio.run(orchestrator.data_provider.get_market_snapshot(
                                                                                                                                                                                                                                                                                                        'NIFTY': market_data.get('NIFTY', {}).get('ltp', 0),
                                                                                                                                                                                                                                                                                                        'BANKNIFTY': market_data.get('BANKNIFTY', {}).get('ltp', 0),
                                                                                                                                                                                                                                                                                                        'VIX': market_data.get('INDIAVIX', {}).get('ltp', 0

                                                                                                                                                                                                                                                                                                    return jsonify(status
                                                                                                                                                                                                                                                                                                    except Exception as e:
                                                                                                                                                                                                                                                                                                        logger.error(f"Error getting market status: {e}"
                                                                                                                                                                                                                                                                                                        abort(500
                                                                                                                                                                                                                                                                                                        # Compliance endpoints
                                                                                                                                                                                                                                                                                                        @jwt_required(
                                                                                                                                                                                                                                                                                                        @require_permission('view_compliance'
                                                                                                                                                                                                                                                                                                        @async_route
                                                                                                                                                                                                                                                                                                        async def get_compliance_status():
                                                                                                                                                                                                                                                                                                        """Get compliance status and metrics"""
                                                                                                                                                                                                                                                                                                        try:
                                                                                                                                                                                                                                                                                                            if not orchestrator:

                                                                                                                                                                                                                                                                                                                compliance_manager = orchestrator.compliance_manager
                                                                                                                                                                                                                                                                                                                if not compliance_manager:

                                                                                                                                                                                                                                                                                                                    metrics = await compliance_manager.get_metrics(
                                                                                                                                                                                                                                                                                                                return jsonify({
                                                                                                                                                                                                                                                                                                                'metrics': metrics,
                                                                                                                                                                                                                                                                                                                'timestamp': datetime.now().isoformat(

                                                                                                                                                                                                                                                                                                                except Exception as e:
                                                                                                                                                                                                                                                                                                                    logger.error(f"Error getting compliance status: {e}"
                                                                                                                                                                                                                                                                                                                    abort(500
                                                                                                                                                                                                                                                                                                                    # Helper functions
                                                                                                                                                                                                                                                                                                                    def check_user_permission(user_id: str, permission: str) -> bool:
                                                                                                                                                                                                                                                                                                                        """Check if user has specific permission"""
                                                                                                                                                                                                                                                                                                                        # Implement based on your permission system
                                                                                                                                                                                                                                                                                                                        # For now, allow all authenticated users
                                                                                                                                                                                                                                                                                                                    return True

                                                                                                                                                                                                                                                                                                                    def validate_user_credentials(username: str, password: str) -> Optional[Dict]:
                                                                                                                                                                                                                                                                                                                        """Validate user credentials against database or secure storage"""
                                                                                                                                                                                                                                                                                                                        try:
                                                                                                                                                                                                                                                                                                                            # Define valid production users (in production, this should be in database)
                                                                                                                                                                                                                                                                                                                            valid_users = {
                                                                                                                                                                                                                                                                                                                                'admin': {
                                                                                                                                                                                                                                                                                                                                    'password': 'admin123',
                                                                                                                                                                                                                                                                                                                    'id': '1',
                                                                                                                                                                                                                                                                                                                    'username': 'admin',
                                                                                                                                                                                                                                                                                                                                    'email': 'admin@trading-system.com',
                                                                                                                                                                                                                                                                                                                                    'permissions': ['all'],
                                                                                                                                                                                                                                                                                                                                    'capital': 1000000,
                                                                                                                                                                                                                                                                                                                                    'is_active': True,
                                                                                                                                                                                                                                                                                                                                    'role': 'administrator'
                                                                                                                                                                                                                                                                                                                                },
                                                                                                                                                                                                                                                                                                                                'trader': {
                                                                                                                                                                                                                                                                                                                                    'password': 'trading123',
                                                                                                                                                                                                                                                                                                                                    'id': '2',
                                                                                                                                                                                                                                                                                                                                    'username': 'trader',
                                                                                                                                                                                                                                                                                                                                    'email': 'trader@trading-system.com',
                                                                                                                                                                                                                                                                                                                                    'permissions': ['trade', 'view'],
                                                                                                                                                                                                                                                                                                                                    'capital': 500000,
                                                                                                                                                                                                                                                                                                                                    'is_active': True,
                                                                                                                                                                                                                                                                                                                                    'role': 'trader'
                                                                                                                                                                                                                                                                                                                                },
                                                                                                                                                                                                                                                                                                                                'demo': {
                                                                                                                                                                                                                                                                                                                                    'password': 'password',
                                                                                                                                                                                                                                                                                                                                    'id': '3',
                                                                                                                                                                                                                                                                                                                                    'username': 'demo',
                                                                                                                                                                                                                                                                                                                                    'email': 'demo@trading-system.com',
                                                                                                                                                                                                                                                                                                                                    'permissions': ['view'],
                                                                                                                                                                                                                                                                                                                                    'capital': 100000,
                                                                                                                                                                                                                                                                                                                                    'is_active': True,
                                                                                                                                                                                                                                                                                                                                    'role': 'demo'
                                                                                                                                                                                                                                                                                                                                },
                                                                                                                                                                                                                                                                                                                                'shyam': {
                                                                                                                                                                                                                                                                                                                                    'password': 'shyam@123',
                                                                                                                                                                                                                                                                                                                                    'id': '4',
                                                                                                                                                                                                                                                                                                                                    'username': 'shyam',
                                                                                                                                                                                                                                                                                                                                    'email': 'shyam@trading-system.com',
                                                                                                                                                                                                                                                                                                                                    'permissions': ['all'],
                                                                                                                                                                                                                                                                                                                    'capital': 500000,
                                                                                                                                                                                                                                                                                                                                    'is_active': True,
                                                                                                                                                                                                                                                                                                                                    'role': 'owner'
                                                                                                                                                                                                                                                                                                                                }
                                                                                                                                                                                                                                                                                                                            }
                                                                                                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                                                                            # Check if user exists
                                                                                                                                                                                                                                                                                                                            if username not in valid_users:
                                                                                                                                                                                                                                                                                                                                logger.warning(f"Login attempt with invalid username: {username}")
                                                                                                                                                                                                                                                                                                                                return None
                                                                                                                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                                                                                user = valid_users[username]
                                                                                                                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                                                                                # Verify password (in production, use proper password hashing)
                                                                                                                                                                                                                                                                                                                                if user['password'] != password:
                                                                                                                                                                                                                                                                                                                                    logger.warning(f"Failed login attempt for user: {username}")
                                                                                                                                                                                                                                                                                                                                    return None
                                                                                                                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                                                                                    # Check if user is active
                                                                                                                                                                                                                                                                                                                                    if not user.get('is_active', False):
                                                                                                                                                                                                                                                                                                                                        logger.warning(f"Login attempt for inactive user: {username}")
                                                                                                                                                                                                                                                                                                                                        return None
                                                                                                                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                                                                                        # Return user data without password
                                                                                                                                                                                                                                                                                                                                        user_data = user.copy()
                                                                                                                                                                                                                                                                                                                                        del user_data['password']
                                                                                                                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                                                                                        logger.info(f"Successful login for user: {username}")
                                                                                                                                                                                                                                                                                                                                        return user_data
                                                                                                                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                                                                                    except Exception as e:
                                                                                                                                                                                                                                                                                                                                        logger.error(f"Error validating user credentials: {str(e)}")
                                                                                                                                                                                                                                                                                                                return None

                                                                                                                                                                                                                                                                                                                def is_market_open(] -> bool:
                                                                                                                                                                                                                                                                                                                    """Check if market is currently open"""
                                                                                                                                                                                                                                                                                                                    now = datetime.now(
                                                                                                                                                                                                                                                                                                                return False

                                                                                                                                                                                                                                                                                                                current_time = now.time(
                                                                                                                                                                                                                                                                                                                market_open = datetime.strptime("09:15", "%H:%M").time(
                                                                                                                                                                                                                                                                                                                market_close = datetime.strptime("15:30", "%H:%M").time(
                                                                                                                                                                                                                                                                                                                def generate_daily_report(date_str: str) -> Dict:
                                                                                                                                                                                                                                                                                                                    """Generate daily report data"""
                                                                                                                                                                                                                                                                                                                    # Implement report generation logic
                                                                                                                                                                                                                                                                                                                return {
                                                                                                                                                                                                                                                                                                                'date': date_str,
                                                                                                                                                                                                                                                                                                                'summary': {
                                                                                                                                                                                                                                                                                                                'total_trades': 0,
                                                                                                                                                                                                                                                                                                                'pnl': 0,
                                                                                                                                                                                                                                                                                                                'win_rate': 0

                                                                                                                                                                                                                                                                                                                async def export_trades(date_from: str, date_to: str, format_type: str) -> str:
                                                                                                                                                                                                                                                                                                                """Export trades data"""
                                                                                                                                                                                                                                                                                                                # Implement export logic
                                                                                                                                                                                                                                                                                                            return f"trades_export_{date_from}_{date_to}.{format_type}"

                                                                                                                                                                                                                                                                                                            async def export_positions(date_from: str, date_to: str, format_type: str) -> str:
                                                                                                                                                                                                                                                                                                            """Export positions data"""
                                                                                                                                                                                                                                                                                                            # Implement export logic
                                                                                                                                                                                                                                                                                                        return f"positions_export_{date_from}_{date_to}.{format_type}"

                                                                                                                                                                                                                                                                                                        async def export_orders(date_from: str, date_to: str, format_type: str) -> str:
                                                                                                                                                                                                                                                                                                        """Export orders data"""
                                                                                                                                                                                                                                                                                                        # Implement export logic
                                                                                                                                                                                                                                                                                                    return f"orders_export_{date_from}_{date_to}.{format_type}"

                                                                                                                                                                                                                                                                                                    # Initialize API with system components
                                                                                                                                                                                                                                                                                                    def initialize_api(system_components: Dict):
                                                                                                                                                                                                                                                                                                        """Initialize API with trading system components"""
                                                                                                                                                                                                                                                                                                        global orchestrator, position_tracker, order_manager, risk_manager, event_bus

                                                                                                                                                                                                                                                                                                        orchestrator = system_components.get('orchestrator'
                                                                                                                                                                                                                                                                                                        position_tracker = system_components.get('position_tracker'
                                                                                                                                                                                                                                                                                                        order_manager = system_components.get('order_manager'
                                                                                                                                                                                                                                                                                                        risk_manager = system_components.get('risk_manager'
                                                                                                                                                                                                                                                                                                        event_bus = system_components.get('event_bus'
                                                                                                                                                                                                                                                                                                        logger.info("API initialized with system components"
                                                                                                                                                                                                                                                                                                        # Run the API server
                                                                                                                                                                                                                                                                                                        """Run the API server"""
                                                                                                                                                                                                                                                                                                        logger.info(f"Starting API server on {host}:{port}"
                                                                                                                                                                                                                                                                                                        # This is for testing only
