"""
Comprehensive Search API for Trading System
Provides search functionality across all trading entities with autocomplete and filtering
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import text, and_, or_
from sqlalchemy.orm import Session
import re
import logging

from src.config.database import get_db
from src.api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Search configuration
SEARCH_LIMITS = {
    "default": 20,
    "autocomplete": 10,
    "max": 100
}

@router.get("/search/symbols")
async def search_symbols(
    query: str = Query(..., min_length=1, max_length=50),
    limit: int = Query(20, ge=1, le=100),
    include_options: bool = Query(False),
    exchange: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Search for trading symbols with autocomplete support"""
    try:
        # Build search query
        search_conditions = []
        
        # Main symbol search (case-insensitive)
        search_conditions.append(
            f"symbol ILIKE '%{query.upper()}%' OR name ILIKE '%{query}%'"
        )
        
        # Exchange filter
        if exchange:
            search_conditions.append(f"exchange = '{exchange}'")
        
        # Options filter
        if not include_options:
            search_conditions.append("symbol NOT LIKE '%CE%' AND symbol NOT LIKE '%PE%'")
        
        # Combine conditions
        where_clause = " AND ".join(search_conditions)
        
        # Execute search query
        search_query = text(f"""
            SELECT 
                symbol,
                name,
                exchange,
                symbol_type,
                lot_size,
                tick_size,
                is_active,
                CASE 
                    WHEN symbol ILIKE '{query.upper()}%' THEN 1
                    WHEN name ILIKE '{query}%' THEN 2
                    ELSE 3
                END as relevance_score
            FROM symbols
            WHERE {where_clause}
            ORDER BY relevance_score, symbol
            LIMIT :limit
        """)
        
        result = await db.execute(search_query, {"limit": limit})
        symbols = result.fetchall()
        
        # Format response
        symbol_list = []
        for symbol in symbols:
            symbol_list.append({
                "symbol": symbol.symbol,
                "name": symbol.name,
                "exchange": symbol.exchange,
                "type": symbol.symbol_type,
                "lot_size": symbol.lot_size,
                "tick_size": float(symbol.tick_size) if symbol.tick_size else 0.01,
                "is_active": symbol.is_active,
                "display_name": f"{symbol.symbol} ({symbol.name})" if symbol.name else symbol.symbol
            })
        
        return {
            "success": True,
            "data": symbol_list,
            "count": len(symbol_list),
            "query": query,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Symbol search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/search/trades")
async def search_trades(
    query: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    strategy: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Search through trade history with comprehensive filtering"""
    try:
        # Build search conditions
        conditions = []
        params = {"limit": limit, "offset": offset}
        
        # User filter (security check)
        if user_id and current_user.get("role") != "admin":
            conditions.append("user_id = :user_id")
            params["user_id"] = user_id
        elif not current_user.get("role") == "admin":
            conditions.append("user_id = :current_user_id")
            params["current_user_id"] = current_user.get("id")
        
        # Text search across multiple fields
        if query:
            conditions.append(
                "(symbol ILIKE :query OR strategy_name ILIKE :query OR trade_id ILIKE :query)"
            )
            params["query"] = f"%{query}%"
        
        # Specific filters
        if symbol:
            conditions.append("symbol = :symbol")
            params["symbol"] = symbol.upper()
        
        if strategy:
            conditions.append("strategy_name ILIKE :strategy")
            params["strategy"] = f"%{strategy}%"
        
        if status:
            conditions.append("status = :status")
            params["status"] = status.upper()
        
        # Date range filter
        if start_date:
            conditions.append("created_at >= :start_date")
            params["start_date"] = start_date
        
        if end_date:
            conditions.append("created_at <= :end_date")
            params["end_date"] = end_date
        
        # Build final query
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Main search query
        search_query = text(f"""
            SELECT 
                t.trade_id,
                t.user_id,
                t.symbol,
                t.side,
                t.quantity,
                t.price,
                t.pnl,
                t.status,
                t.strategy_name,
                t.created_at,
                t.executed_at,
                u.username,
                COUNT(*) OVER() as total_count
            FROM trades t
            LEFT JOIN users u ON t.user_id = u.id
            WHERE {where_clause}
            ORDER BY t.created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        result = await db.execute(search_query, params)
        trades = result.fetchall()
        
        # Format response
        trade_list = []
        total_count = 0
        
        for trade in trades:
            if total_count == 0:
                total_count = trade.total_count
            
            trade_list.append({
                "trade_id": trade.trade_id,
                "user_id": trade.user_id,
                "username": trade.username,
                "symbol": trade.symbol,
                "side": trade.side,
                "quantity": trade.quantity,
                "price": float(trade.price) if trade.price else 0,
                "pnl": float(trade.pnl) if trade.pnl else 0,
                "status": trade.status,
                "strategy": trade.strategy_name,
                "created_at": trade.created_at.isoformat() if trade.created_at else None,
                "executed_at": trade.executed_at.isoformat() if trade.executed_at else None
            })
        
        return {
            "success": True,
            "data": trade_list,
            "pagination": {
                "total": total_count,
                "count": len(trade_list),
                "offset": offset,
                "limit": limit,
                "has_more": (offset + limit) < total_count
            },
            "filters": {
                "query": query,
                "symbol": symbol,
                "strategy": strategy,
                "status": status,
                "start_date": start_date,
                "end_date": end_date
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Trade search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/search/strategies")
async def search_strategies(
    query: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search for trading strategies"""
    try:
        conditions = []
        params = {"limit": limit}
        
        # Text search
        if query:
            conditions.append("(name ILIKE :query OR description ILIKE :query)")
            params["query"] = f"%{query}%"
        
        # Active filter
        if is_active is not None:
            conditions.append("is_active = :is_active")
            params["is_active"] = is_active
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        search_query = text(f"""
            SELECT 
                strategy_id,
                name,
                description,
                parameters,
                is_active,
                created_at,
                updated_at
            FROM strategies
            WHERE {where_clause}
            ORDER BY name
            LIMIT :limit
        """)
        
        result = await db.execute(search_query, params)
        strategies = result.fetchall()
        
        # Format response
        strategy_list = []
        for strategy in strategies:
            strategy_list.append({
                "strategy_id": strategy.strategy_id,
                "name": strategy.name,
                "description": strategy.description,
                "parameters": strategy.parameters,
                "is_active": strategy.is_active,
                "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
                "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None
            })
        
        return {
            "success": True,
            "data": strategy_list,
            "count": len(strategy_list),
            "query": query,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Strategy search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/search/users")
async def search_users(
    query: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Search for users (admin only)"""
    try:
        # Security check
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        conditions = []
        params = {"limit": limit}
        
        # Text search
        if query:
            conditions.append("(username ILIKE :query OR email ILIKE :query OR full_name ILIKE :query)")
            params["query"] = f"%{query}%"
        
        # Active filter
        if is_active is not None:
            conditions.append("is_active = :is_active")
            params["is_active"] = is_active
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        search_query = text(f"""
            SELECT 
                id,
                username,
                email,
                full_name,
                current_balance,
                is_active,
                created_at,
                last_login
            FROM users
            WHERE {where_clause}
            ORDER BY username
            LIMIT :limit
        """)
        
        result = await db.execute(search_query, params)
        users = result.fetchall()
        
        # Format response
        user_list = []
        for user in users:
            user_list.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "current_balance": float(user.current_balance) if user.current_balance else 0,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None
            })
        
        return {
            "success": True,
            "data": user_list,
            "count": len(user_list),
            "query": query,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"User search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/search/recommendations")
async def search_recommendations(
    query: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    recommendation_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search for elite recommendations"""
    try:
        conditions = []
        params = {"limit": limit}
        
        # Text search
        if query:
            conditions.append("(symbol ILIKE :query OR strategy ILIKE :query OR reason ILIKE :query)")
            params["query"] = f"%{query}%"
        
        # Specific filters
        if symbol:
            conditions.append("symbol = :symbol")
            params["symbol"] = symbol.upper()
        
        if recommendation_type:
            conditions.append("recommendation_type = :rec_type")
            params["rec_type"] = recommendation_type.upper()
        
        if status:
            conditions.append("status = :status")
            params["status"] = status.upper()
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        search_query = text(f"""
            SELECT 
                recommendation_id,
                symbol,
                recommendation_type,
                entry_price,
                target_price,
                stop_loss,
                confidence,
                strategy,
                reason,
                status,
                validity_start,
                validity_end,
                created_at
            FROM recommendations
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        
        result = await db.execute(search_query, params)
        recommendations = result.fetchall()
        
        # Format response
        rec_list = []
        for rec in recommendations:
            rec_list.append({
                "recommendation_id": rec.recommendation_id,
                "symbol": rec.symbol,
                "type": rec.recommendation_type,
                "entry_price": float(rec.entry_price) if rec.entry_price else 0,
                "target_price": float(rec.target_price) if rec.target_price else 0,
                "stop_loss": float(rec.stop_loss) if rec.stop_loss else 0,
                "confidence": float(rec.confidence) if rec.confidence else 0,
                "strategy": rec.strategy,
                "reason": rec.reason,
                "status": rec.status,
                "validity_start": rec.validity_start.isoformat() if rec.validity_start else None,
                "validity_end": rec.validity_end.isoformat() if rec.validity_end else None,
                "created_at": rec.created_at.isoformat() if rec.created_at else None
            })
        
        return {
            "success": True,
            "data": rec_list,
            "count": len(rec_list),
            "query": query,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Recommendation search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/search/global")
async def global_search(
    query: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Global search across all entities"""
    try:
        results = {
            "symbols": [],
            "trades": [],
            "strategies": [],
            "recommendations": []
        }
        
        search_limit = min(limit // 4, 10)  # Distribute across categories
        
        # Search symbols
        try:
            symbol_query = text("""
                SELECT symbol, name, exchange, symbol_type
                FROM symbols
                WHERE symbol ILIKE :query OR name ILIKE :query
                ORDER BY 
                    CASE 
                        WHEN symbol ILIKE :exact_query THEN 1
                        WHEN symbol ILIKE :starts_query THEN 2
                        ELSE 3
                    END
                LIMIT :limit
            """)
            
            symbol_result = await db.execute(symbol_query, {
                "query": f"%{query}%",
                "exact_query": query.upper(),
                "starts_query": f"{query.upper()}%",
                "limit": search_limit
            })
            
            for symbol in symbol_result.fetchall():
                results["symbols"].append({
                    "symbol": symbol.symbol,
                    "name": symbol.name,
                    "exchange": symbol.exchange,
                    "type": symbol.symbol_type,
                    "category": "symbol"
                })
        except Exception as e:
            logger.warning(f"Symbol search in global search failed: {e}")
        
        # Search recent trades
        try:
            trade_query = text("""
                SELECT t.trade_id, t.symbol, t.side, t.quantity, t.price, t.strategy_name, t.created_at
                FROM trades t
                WHERE t.symbol ILIKE :query OR t.strategy_name ILIKE :query
                ORDER BY t.created_at DESC
                LIMIT :limit
            """)
            
            trade_result = await db.execute(trade_query, {
                "query": f"%{query}%",
                "limit": search_limit
            })
            
            for trade in trade_result.fetchall():
                results["trades"].append({
                    "trade_id": trade.trade_id,
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": trade.quantity,
                    "price": float(trade.price) if trade.price else 0,
                    "strategy": trade.strategy_name,
                    "created_at": trade.created_at.isoformat() if trade.created_at else None,
                    "category": "trade"
                })
        except Exception as e:
            logger.warning(f"Trade search in global search failed: {e}")
        
        # Search strategies
        try:
            strategy_query = text("""
                SELECT strategy_id, name, description, is_active
                FROM strategies
                WHERE name ILIKE :query OR description ILIKE :query
                ORDER BY name
                LIMIT :limit
            """)
            
            strategy_result = await db.execute(strategy_query, {
                "query": f"%{query}%",
                "limit": search_limit
            })
            
            for strategy in strategy_result.fetchall():
                results["strategies"].append({
                    "strategy_id": strategy.strategy_id,
                    "name": strategy.name,
                    "description": strategy.description,
                    "is_active": strategy.is_active,
                    "category": "strategy"
                })
        except Exception as e:
            logger.warning(f"Strategy search in global search failed: {e}")
        
        # Search recommendations
        try:
            rec_query = text("""
                SELECT recommendation_id, symbol, recommendation_type, entry_price, status, strategy
                FROM recommendations
                WHERE symbol ILIKE :query OR strategy ILIKE :query
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            
            rec_result = await db.execute(rec_query, {
                "query": f"%{query}%",
                "limit": search_limit
            })
            
            for rec in rec_result.fetchall():
                results["recommendations"].append({
                    "recommendation_id": rec.recommendation_id,
                    "symbol": rec.symbol,
                    "type": rec.recommendation_type,
                    "entry_price": float(rec.entry_price) if rec.entry_price else 0,
                    "status": rec.status,
                    "strategy": rec.strategy,
                    "category": "recommendation"
                })
        except Exception as e:
            logger.warning(f"Recommendation search in global search failed: {e}")
        
        # Calculate total results
        total_results = sum(len(results[key]) for key in results.keys())
        
        return {
            "success": True,
            "data": results,
            "total_results": total_results,
            "query": query,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Global search error: {e}")
        raise HTTPException(status_code=500, detail=f"Global search failed: {str(e)}")

@router.get("/search/autocomplete")
async def search_autocomplete(
    query: str = Query(..., min_length=1, max_length=50),
    category: str = Query("all", regex="^(all|symbols|trades|strategies|users)$"),
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """Fast autocomplete search for UI components with fallback for missing tables"""
    try:
        suggestions = []
        
        if category in ["all", "symbols"]:
            # Symbol autocomplete with fallback for missing table
            try:
                symbol_query = text("""
                    SELECT symbol, name, 'symbol' as type
                    FROM symbols
                    WHERE symbol ILIKE :query OR name ILIKE :query
                    ORDER BY 
                        CASE 
                            WHEN symbol ILIKE :exact_query THEN 1
                            WHEN symbol ILIKE :starts_query THEN 2
                            ELSE 3
                        END
                    LIMIT :limit
                """)
                
                symbol_result = await db.execute(symbol_query, {
                    "query": f"%{query}%",
                    "exact_query": query.upper(),
                    "starts_query": f"{query.upper()}%",
                    "limit": limit if category == "symbols" else limit // 2
                })
                
                for symbol in symbol_result.fetchall():
                    suggestions.append({
                        "value": symbol.symbol,
                        "label": f"{symbol.symbol} - {symbol.name}" if symbol.name else symbol.symbol,
                        "type": "symbol"
                    })
                    
            except Exception as symbol_error:
                logger.warning(f"Symbol table query failed: {symbol_error}")
                # CRITICAL: NO HARDCODED FALLBACK SYMBOLS - GET FROM DATABASE
                try:
                    from ..core.database import get_db_session
                    
                    async with get_db_session() as session:
                        # Get real symbols from database
                        result = await session.execute("""
                            SELECT symbol, name, exchange, is_active
                            FROM symbols 
                            WHERE symbol ILIKE %s OR name ILIKE %s
                            ORDER BY volume_24h DESC
                            LIMIT %s
                        """, (f"%{query}%", f"%{query}%", limit))
                        
                        db_symbols = []
                        for row in result:
                            db_symbols.append({
                                'symbol': row.symbol,
                                'name': row.name,
                                'exchange': row.exchange,
                                'is_active': row.is_active,
                                'source': 'database'
                            })
                        
                        if db_symbols:
                            return db_symbols
                    
                    # If no database results, return empty instead of hardcoded fallbacks
                    logger.warning(f"No symbols found in database for query: {query}")
                    return []
                    
                except Exception as e:
                    logger.error(f"Error searching symbols in database: {e}")
                    raise HTTPException(status_code=503, detail="Symbol search service unavailable")
        
        if category in ["all", "strategies"]:
            # Strategy autocomplete
            try:
                strategy_query = text("""
                    SELECT name, 'strategy' as type
                    FROM strategies
                    WHERE name ILIKE :query
                    ORDER BY name
                    LIMIT :limit
                """)
                
                strategy_result = await db.execute(strategy_query, {
                    "query": f"%{query}%",
                    "limit": limit if category == "strategies" else limit // 2
                })
                
                for strategy in strategy_result.fetchall():
                    suggestions.append({
                        "value": strategy.name,
                        "label": strategy.name,
                        "type": "strategy"
                    })
                    
            except Exception as strategy_error:
                logger.warning(f"Strategy table query failed: {strategy_error}")
                # CRITICAL: NO HARDCODED FALLBACK STRATEGIES - GET FROM DATABASE
                try:
                    from ..core.database import get_db_session
                    
                    async with get_db_session() as session:
                        # Get real strategies from database
                        result = await session.execute("""
                            SELECT name, description, is_active, strategy_type
                            FROM strategies 
                            WHERE name ILIKE %s OR description ILIKE %s
                            ORDER BY created_at DESC
                            LIMIT %s
                        """, (f"%{query}%", f"%{query}%", limit))
                        
                        db_strategies = []
                        for row in result:
                            db_strategies.append({
                                'name': row.name,
                                'description': row.description,
                                'is_active': row.is_active,
                                'strategy_type': row.strategy_type,
                                'source': 'database'
                            })
                        
                        if db_strategies:
                            return db_strategies
                    
                    # If no database results, return empty instead of hardcoded fallbacks
                    logger.warning(f"No strategies found in database for query: {query}")
                    return []
                    
                except Exception as e:
                    logger.error(f"Error searching strategies in database: {e}")
                    raise HTTPException(status_code=503, detail="Strategy search service unavailable")
        
        return {
            "success": True,
            "suggestions": suggestions[:limit],
            "query": query,
            "category": category,
            "fallback_used": True,  # Indicate fallback data was used
            "message": "Using fallback data - database table missing",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Autocomplete search error: {e}")
        # FINAL FALLBACK: Return empty but successful response
        return {
            "success": True,
            "suggestions": [],
            "query": query,
            "category": category,
            "error": "Search temporarily unavailable",
            "timestamp": datetime.now().isoformat()
        } 