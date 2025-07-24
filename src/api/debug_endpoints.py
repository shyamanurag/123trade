"""
Debug API Endpoints
Reveals internal orchestrator state for troubleshooting
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from datetime import datetime
import logging
import os
import asyncio

from src.core.orchestrator import TradingOrchestrator
# Use shared dependency to fix singleton issue
from src.core.dependencies import get_orchestrator
from models.responses import BaseResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/debug")

@router.get("/orchestrator", response_model=Dict[str, Any])
async def get_orchestrator_debug(
    orchestrator: TradingOrchestrator = Depends(get_orchestrator)
):
    """Get detailed debug information about orchestrator state"""
    try:
        # Get all internal state
        debug_info = {
            "orchestrator_state": {
                "system_ready": getattr(orchestrator, 'system_ready', 'NOT_SET'),
                "is_active": getattr(orchestrator, 'is_active', 'NOT_SET'),
                "session_id": getattr(orchestrator, 'session_id', 'NOT_SET'),
                "start_time": str(getattr(orchestrator, 'start_time', 'NOT_SET')),
                "total_trades": getattr(orchestrator, 'total_trades', 'NOT_SET'),
                "active_strategies": len(getattr(orchestrator, 'active_strategies', [])),
                "active_positions": len(getattr(orchestrator, 'active_positions', [])),
            },
            "component_status": {
                "zerodha": "AVAILABLE" if getattr(orchestrator, 'zerodha', None) else "NOT_SET",
                "risk_manager": type(getattr(orchestrator, 'risk_manager', None)).__name__ if getattr(orchestrator, 'risk_manager', None) else "NOT_SET",
                "position_tracker": type(getattr(orchestrator, 'position_tracker', None)).__name__ if getattr(orchestrator, 'position_tracker', None) else "NOT_SET",
                "market_data": type(getattr(orchestrator, 'market_data', None)).__name__ if getattr(orchestrator, 'market_data', None) else "NOT_SET",
                "strategy_engine": type(getattr(orchestrator, 'strategy_engine', None)).__name__ if getattr(orchestrator, 'strategy_engine', None) else "NOT_SET",
                "trade_engine": type(getattr(orchestrator, 'trade_engine', None)).__name__ if getattr(orchestrator, 'trade_engine', None) else "NOT_SET",
                "connection_manager": type(getattr(orchestrator, 'connection_manager', None)).__name__ if getattr(orchestrator, 'connection_manager', None) else "NOT_SET",
                "pre_market_analyzer": type(getattr(orchestrator, 'pre_market_analyzer', None)).__name__ if getattr(orchestrator, 'pre_market_analyzer', None) else "NOT_SET",
            },
            "trading_readiness": {
                "market_open": orchestrator._is_market_open(),
                "can_start_trading": orchestrator._can_start_trading(),
            },
            "timestamps": {
                "current_time": datetime.now().isoformat(),
                "debug_generated": datetime.utcnow().isoformat()
            }
        }
        
        return debug_info
        
    except Exception as e:
        logger.error(f"Error getting debug info: {e}")
        raise HTTPException(status_code=500, detail=f"Debug error: {str(e)}")

@router.post("/force-initialize", response_model=BaseResponse)
async def force_initialize_system(
    orchestrator: TradingOrchestrator = Depends(get_orchestrator)
):
    """Force system initialization for debugging"""
    try:
        logger.info("🔧 Force initializing system...")
        
        # Reset state
        orchestrator.system_ready = False
        
        # Try to initialize
        result = await orchestrator.initialize_system()
        
        return BaseResponse(
            success=result,
            message=f"Force initialization {'succeeded' if result else 'failed'}"
        )
        
    except Exception as e:
        logger.error(f"Force initialization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/force-enable-trading", response_model=BaseResponse)
async def force_enable_trading(
    orchestrator: TradingOrchestrator = Depends(get_orchestrator)
):
    """Force enable trading for debugging"""
    try:
        logger.info("🔧 Force enabling trading...")
        
        # Bypass system_ready check temporarily
        original_system_ready = orchestrator.system_ready
        orchestrator.system_ready = True
        
        # Try to enable trading
        result = await orchestrator.enable_trading()
        
        # Restore original state if it failed
        if not result:
            orchestrator.system_ready = original_system_ready
        
        return BaseResponse(
            success=result,
            message=f"Force enable trading {'succeeded' if result else 'failed'}"
        )
        
    except Exception as e:
        logger.error(f"Force enable trading error: {e}")
        # Restore original state
        orchestrator.system_ready = original_system_ready
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-state-setting", response_model=Dict[str, Any])
async def test_state_setting(
    orchestrator: TradingOrchestrator = Depends(get_orchestrator)
):
    """Test basic state setting to isolate the issue"""
    try:
        logger.info("🧪 TEST: Starting basic state setting test")
        
        # Get initial state
        initial_active = getattr(orchestrator, 'is_active', 'MISSING')
        logger.info(f"   Initial is_active: {initial_active}")
        
        # Test 1: Direct assignment
        orchestrator.is_active = True
        after_direct = getattr(orchestrator, 'is_active', 'MISSING')
        logger.info(f"   After direct assignment: {after_direct}")
        
        # Test 2: setattr
        setattr(orchestrator, 'is_active', True)
        after_setattr = getattr(orchestrator, 'is_active', 'MISSING')
        logger.info(f"   After setattr: {after_setattr}")
        
        # Test 3: dict assignment
        orchestrator.__dict__['is_active'] = True
        after_dict = orchestrator.__dict__.get('is_active', 'MISSING')
        logger.info(f"   After dict assignment: {after_dict}")
        
        # Test 4: Check if it persists
        final_check = orchestrator.is_active
        logger.info(f"   Final check: {final_check}")
        
        return {
            "test_results": {
                "initial": initial_active,
                "after_direct": after_direct,
                "after_setattr": after_setattr,
                "after_dict": after_dict,
                "final_check": final_check,
                "success": final_check == True
            },
            "orchestrator_id": getattr(orchestrator, '_instance_id', 'unknown'),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"State setting test failed: {e}")
        return {
            "error": str(e),
            "test_results": None,
            "timestamp": datetime.utcnow().isoformat()
        }

@router.post("/test-enable-trading", response_model=Dict[str, Any])
async def test_enable_trading_direct(
    orchestrator: TradingOrchestrator = Depends(get_orchestrator)
):
    """Test enable_trading method directly with full exception handling"""
    try:
        logger.info("🧪 TEST: Calling enable_trading() directly")
        
        # Capture before state
        before_state = {
            "is_active": getattr(orchestrator, 'is_active', 'MISSING'),
            "session_id": getattr(orchestrator, 'session_id', 'MISSING'),
            "start_time": str(getattr(orchestrator, 'start_time', 'MISSING')),
            "system_ready": getattr(orchestrator, 'system_ready', 'MISSING')
        }
        logger.info(f"   Before state: {before_state}")
        
        # Call enable_trading with exception handling
        try:
            result = await orchestrator.enable_trading()
            logger.info(f"   enable_trading() returned: {result}")
        except Exception as enable_error:
            logger.error(f"   EXCEPTION in enable_trading(): {enable_error}")
            return {
                "error": f"Exception in enable_trading(): {str(enable_error)}",
                "before_state": before_state,
                "after_state": None,
                "result": None
            }
        
        # Capture after state
        after_state = {
            "is_active": getattr(orchestrator, 'is_active', 'MISSING'),
            "session_id": getattr(orchestrator, 'session_id', 'MISSING'),
            "start_time": str(getattr(orchestrator, 'start_time', 'MISSING')),
            "system_ready": getattr(orchestrator, 'system_ready', 'MISSING')
        }
        logger.info(f"   After state: {after_state}")
        
        # Analysis
        analysis = {
            "method_returned": result,
            "is_active_changed": before_state["is_active"] != after_state["is_active"],
            "session_created": after_state["session_id"] != "MISSING" and after_state["session_id"] is not None,
            "start_time_set": after_state["start_time"] != "MISSING" and after_state["start_time"] != "None"
        }
        
        return {
            "before_state": before_state,
            "after_state": after_state,
            "result": result,
            "analysis": analysis,
            "orchestrator_id": getattr(orchestrator, '_instance_id', 'unknown'),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Test enable trading failed: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.post("/test-minimal-enable", response_model=Dict[str, Any])
async def test_minimal_enable(
    orchestrator: TradingOrchestrator = Depends(get_orchestrator)
):
    """Minimal enable test - just set state and return immediately"""
    try:
        logger.info("🧪 MINIMAL TEST: Setting state and returning immediately")
        
        # Get before state
        before_active = getattr(orchestrator, 'is_active', 'MISSING')
        before_session = getattr(orchestrator, 'session_id', 'MISSING')
        
        # Set state (copy of bulletproof logic)
        logger.info("🔥 MINIMAL: Setting core state")
        orchestrator.is_active = True
        orchestrator.session_id = f"test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        orchestrator.start_time = datetime.utcnow()
        
        # Get after state immediately
        after_active = getattr(orchestrator, 'is_active', 'MISSING')
        after_session = getattr(orchestrator, 'session_id', 'MISSING')
        
        logger.info(f"🔍 MINIMAL RESULT: {before_active} -> {after_active}, session: {after_session}")
        
        return {
            "test_type": "minimal_enable",
            "before": {
                "is_active": before_active,
                "session_id": before_session
            },
            "after": {
                "is_active": after_active,
                "session_id": after_session
            },
            "success": after_active == True and after_session is not None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Minimal enable test failed: {e}")
        return {
            "error": str(e),
            "test_type": "minimal_enable_failed",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.post("/test-bulletproof-deployed", response_model=Dict[str, Any])
async def test_bulletproof_deployed(
    orchestrator: TradingOrchestrator = Depends(get_orchestrator)
):
    """Test if the bulletproof enable_trading code is actually deployed"""
    try:
        logger.info("🧪 TESTING: Checking if bulletproof code is deployed")
        
        # Try to call enable_trading and capture any specific logs
        import io
        import sys
        from contextlib import redirect_stderr, redirect_stdout
        
        # Capture logs during enable_trading call
        log_capture = io.StringIO()
        
        try:
            # Call enable_trading with logging capture
            result = await orchestrator.enable_trading()
            
            return {
                "test_type": "bulletproof_deployment_check",
                "enable_trading_result": result,
                "bulletproof_deployed": "BULLETPROOF: Setting core state" in str(log_capture.getvalue()),
                "current_is_active": getattr(orchestrator, 'is_active', 'MISSING'),
                "current_session_id": getattr(orchestrator, 'session_id', 'MISSING'),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as enable_error:
            return {
                "test_type": "bulletproof_deployment_check",
                "enable_trading_error": str(enable_error),
                "current_is_active": getattr(orchestrator, 'is_active', 'MISSING'),
                "current_session_id": getattr(orchestrator, 'session_id', 'MISSING'),
                "timestamp": datetime.utcnow().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Bulletproof deployment test failed: {e}")
        return {
            "error": str(e),
            "test_type": "bulletproof_deployment_check_failed",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/test-signal-generation")
async def test_signal_generation(orchestrator: TradingOrchestrator = Depends(get_orchestrator)):
    """Test if trading strategies are generating signals"""
    try:
        logger.info("🔍 TESTING SIGNAL GENERATION")
        
        result = {
            'timestamp': datetime.utcnow().isoformat(),
            'market_open': orchestrator._is_market_open(),
            'strategy_engine_exists': orchestrator.strategy_engine is not None,
            'market_data_exists': orchestrator.market_data is not None,
            'signals_generated': 0,
            'signal_details': [],
            'market_data_sample': {},
            'errors': []
        }
        
        # Test 1: Check if market data is available
        if orchestrator.market_data:
            try:
                symbols = ['BANKNIFTY', 'NIFTY', 'SBIN']
                market_data = await orchestrator.market_data.get_latest_data(symbols)
                
                # Handle MarketData objects properly
                if market_data:
                    sample_symbol = list(market_data.keys())[0]
                    sample_data = market_data[sample_symbol]
                    
                    # Check if it's a MarketData object or dictionary
                    if hasattr(sample_data, 'symbol'):  # MarketData object
                        result['market_data_sample'] = {
                            'symbols_returned': list(market_data.keys()),
                            'sample_data_keys': ['symbol', 'current_price', 'price_history', 'timestamp', 'volume'],
                            'price_history_type': type(sample_data.price_history).__name__,
                            'price_history_length': len(sample_data.price_history) if hasattr(sample_data, 'price_history') else 0,
                            'sample_data_type': type(sample_data).__name__,
                            'current_price': getattr(sample_data, 'current_price', None)
                        }
                    else:  # Dictionary format
                        result['market_data_sample'] = {
                            'symbols_returned': list(market_data.keys()),
                            'sample_data_keys': list(sample_data.keys()) if sample_data else [],
                            'price_history_type': type(sample_data.get('price_history', [])).__name__ if sample_data else None,
                            'price_history_length': len(sample_data.get('price_history', [])) if sample_data and 'price_history' in sample_data else 0
                        }
                else:
                    result['market_data_sample'] = {'error': 'No market data returned'}
                    
            except Exception as e:
                result['errors'].append(f"Market data error: {str(e)}")
                result['market_data_sample'] = {'error': str(e)}
        
        # Test 2: Try to generate signals
        if orchestrator.strategy_engine and orchestrator.market_data:
            try:
                symbols = ['BANKNIFTY', 'NIFTY', 'SBIN']
                market_data = await orchestrator.market_data.get_latest_data(symbols)
                
                if market_data:
                    # Try to generate signals
                    signals = await orchestrator.strategy_engine.generate_all_signals(market_data)
                    
                    result['signals_generated'] = len(signals)
                    result['signal_details'] = [
                        {
                            'symbol': signal.symbol,
                            'side': signal.side.value if hasattr(signal.side, 'value') else str(signal.side),
                            'quality_score': signal.quality_score,
                            'strategy_name': signal.strategy_name
                        }
                        for signal in signals[:5]  # First 5 signals
                    ]
                    
            except Exception as e:
                result['errors'].append(f"Signal generation error: {str(e)}")
        else:
            if not orchestrator.strategy_engine:
                result['errors'].append("Strategy engine not initialized")
            if not orchestrator.market_data:
                result['errors'].append("Market data not initialized")
        
        # Test 3: Check trading loop status
        result['trading_loop_info'] = {
            'is_active': orchestrator.is_active,
            'system_ready': orchestrator.system_ready,
            'active_strategies': orchestrator.active_strategies
        }
        
        logger.info(f"📊 Signal generation test results: {result['signals_generated']} signals, {len(result['errors'])} errors")
        
        return {"success": True, "data": result}
        
    except Exception as e:
        logger.error(f"Signal generation test failed: {e}")
        return {"success": False, "error": str(e)}

@router.get("/initialization-status")
async def check_initialization_status(orchestrator: TradingOrchestrator = Depends(get_orchestrator)):
    """Check detailed initialization status"""
    try:
        logger.info("🔍 CHECKING INITIALIZATION STATUS")
        
        result = {
            'timestamp': datetime.utcnow().isoformat(),
            'system_ready': orchestrator.system_ready,
            'initialization_attempted': hasattr(orchestrator, '_initialized'),
            'connection_manager_status': {},
            'component_initialization_attempts': {},
            'errors_during_init': []
        }
        
        # Check if system initialization was attempted
        if hasattr(orchestrator, 'connection_manager') and orchestrator.connection_manager:
            try:
                # Get connection status
                connections = ['zerodha', 'database', 'redis', 'truedata']
                for conn in connections:
                    try:
                        status = orchestrator.connection_manager.get_status(conn)
                        result['connection_manager_status'][conn] = status.value if hasattr(status, 'value') else str(status)
                    except Exception as e:
                        result['connection_manager_status'][conn] = f"Error: {str(e)}"
            except Exception as e:
                result['errors_during_init'].append(f"Connection manager error: {str(e)}")
        else:
            result['errors_during_init'].append("Connection manager not initialized")
        
        # Check component initialization status
        components = {
            'strategy_engine': orchestrator.strategy_engine,
            'market_data': orchestrator.market_data,
            'risk_manager': orchestrator.risk_manager,
            'position_tracker': orchestrator.position_tracker,
            'trade_engine': orchestrator.trade_engine,
            'pre_market_analyzer': orchestrator.pre_market_analyzer
        }
        
        for name, component in components.items():
            result['component_initialization_attempts'][name] = {
                'exists': component is not None,
                'type': type(component).__name__ if component else None,
                'is_mock': 'Mock' in type(component).__name__ if component else False
            }
        
        # Try to force initialize system if not ready
        if not orchestrator.system_ready:
            result['forcing_initialization'] = True
            try:
                init_result = await orchestrator.initialize_system()
                result['forced_init_result'] = init_result
                result['system_ready_after_force'] = orchestrator.system_ready
                
                # Re-check components after forced init
                result['components_after_force_init'] = {
                    'strategy_engine': orchestrator.strategy_engine is not None,
                    'market_data': orchestrator.market_data is not None,
                    'risk_manager': orchestrator.risk_manager is not None,
                    'position_tracker': orchestrator.position_tracker is not None
                }
                
            except Exception as e:
                result['forced_init_error'] = str(e)
                result['errors_during_init'].append(f"Forced initialization failed: {str(e)}")
        
        logger.info(f"📊 Initialization status: system_ready={result['system_ready']}, errors={len(result['errors_during_init'])}")
        
        return {"success": True, "data": result}
        
    except Exception as e:
        logger.error(f"Initialization status check failed: {e}")
        return {"success": False, "error": str(e)}

@router.get("/force-initialize")
async def force_initialize(orchestrator: TradingOrchestrator = Depends(get_orchestrator)):
    """Force system initialization regardless of system_ready flag"""
    try:
        logger.info("🔧 FORCE INITIALIZATION DEBUG")
        
        result = {
            'before_init': {
                'system_ready': orchestrator.system_ready,
                'strategy_engine': orchestrator.strategy_engine is not None,
                'market_data': orchestrator.market_data is not None,
                'connection_manager': orchestrator.connection_manager is not None
            }
        }
        
        # Force initialization regardless of system_ready flag
        logger.info("🔥 Forcing system initialization...")
        init_success = await orchestrator.initialize_system()
        
        result['init_success'] = init_success
        result['after_init'] = {
            'system_ready': orchestrator.system_ready,
            'strategy_engine': orchestrator.strategy_engine is not None,
            'market_data': orchestrator.market_data is not None,
            'connection_manager': orchestrator.connection_manager is not None,
            'strategy_engine_type': type(orchestrator.strategy_engine).__name__ if orchestrator.strategy_engine else None,
            'market_data_type': type(orchestrator.market_data).__name__ if orchestrator.market_data else None
        }
        
        # Test components immediately
        if orchestrator.strategy_engine and orchestrator.market_data:
            try:
                symbols = ['BANKNIFTY', 'NIFTY']
                market_data = await orchestrator.market_data.get_latest_data(symbols)
                result['component_test'] = {
                    'market_data_works': len(market_data) > 0,
                    'sample_symbol': list(market_data.keys())[0] if market_data else None,
                    'sample_data_type': type(list(market_data.values())[0]).__name__ if market_data else None
                }
                
                # Try to generate signals
                if market_data:
                    signals = await orchestrator.strategy_engine.generate_all_signals(market_data)
                    result['component_test']['signals_generated'] = len(signals)
                    
            except Exception as e:
                result['component_test'] = {'error': str(e)}
        
        return {"success": True, "data": result}
        
    except Exception as e:
        logger.error(f"Force initialization failed: {e}")
        return {"success": False, "error": str(e)}

@router.get("/check-system-ready-state")  
async def check_system_ready_state(orchestrator: TradingOrchestrator = Depends(get_orchestrator)):
    """Check why system_ready might be true but components are missing"""
    try:
        result = {
            'system_ready': orchestrator.system_ready,
            'components_status': {
                'strategy_engine': {
                    'exists': orchestrator.strategy_engine is not None,
                    'type': type(orchestrator.strategy_engine).__name__ if orchestrator.strategy_engine else None
                },
                'market_data': {
                    'exists': orchestrator.market_data is not None,
                    'type': type(orchestrator.market_data).__name__ if orchestrator.market_data else None
                },
                'connection_manager': {
                    'exists': orchestrator.connection_manager is not None,
                    'type': type(orchestrator.connection_manager).__name__ if orchestrator.connection_manager else None
                },
                'risk_manager': {
                    'exists': orchestrator.risk_manager is not None,
                    'type': type(orchestrator.risk_manager).__name__ if orchestrator.risk_manager else None
                }
            },
            'initialization_issue': None
        }
        
        # Diagnose the issue
        if orchestrator.system_ready and not orchestrator.strategy_engine:
            result['initialization_issue'] = "system_ready=True but strategy_engine=None - initialization incomplete"
        elif orchestrator.system_ready and not orchestrator.market_data:
            result['initialization_issue'] = "system_ready=True but market_data=None - initialization incomplete"
        elif not orchestrator.system_ready:
            result['initialization_issue'] = "system_ready=False - needs initialization"
        else:
            result['initialization_issue'] = "Components appear properly initialized"
            
        return {"success": True, "data": result}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/debug-initialization-steps")
async def debug_initialization_steps(orchestrator: TradingOrchestrator = Depends(get_orchestrator)):
    """Debug each step of initialization process to find where it fails"""
    try:
        logger.info("🔍 DETAILED INITIALIZATION DEBUGGING")
        
        result = {
            'initial_state': {
                'system_ready': orchestrator.system_ready,
                'connection_manager': orchestrator.connection_manager is not None,
                'strategy_engine': orchestrator.strategy_engine is not None,
                'market_data': orchestrator.market_data is not None
            },
            'steps': [],
            'final_state': {},
            'errors': []
        }
        
        # Force reset to debug cleanly
        logger.info("🔄 Resetting system state for clean debug")
        orchestrator.system_ready = False
        orchestrator.connection_manager = None
        orchestrator.strategy_engine = None
        orchestrator.market_data = None
        
        # Step 1: Basic initialization
        try:
            logger.info("📋 Step 1: Basic initialization")
            orchestrator._initialize()
            result['steps'].append({
                'step': 1,
                'name': 'Basic initialization',
                'success': True,
                'system_ready': orchestrator.system_ready,
                'connection_manager': orchestrator.connection_manager is not None
            })
        except Exception as e:
            result['steps'].append({
                'step': 1,
                'name': 'Basic initialization', 
                'success': False,
                'error': str(e)
            })
            result['errors'].append(f"Step 1 failed: {e}")
        
        # Step 2: Connection manager initialization
        try:
            logger.info("📋 Step 2: Connection manager initialization")
            if orchestrator.connection_manager:
                connections_ok = await orchestrator.connection_manager.initialize_all_connections()
            else:
                connections_ok = False
                
            result['steps'].append({
                'step': 2,
                'name': 'Connection manager initialization',
                'success': connections_ok,
                'connections_ok': connections_ok,
                'connection_manager_exists': orchestrator.connection_manager is not None
            })
        except Exception as e:
            result['steps'].append({
                'step': 2,
                'name': 'Connection manager initialization',
                'success': False,
                'error': str(e)
            })
            result['errors'].append(f"Step 2 failed: {e}")
        
        # Step 3: Trading components initialization
        try:
            logger.info("📋 Step 3: Trading components initialization")
            await orchestrator._initialize_trading_components()
            
            result['steps'].append({
                'step': 3,
                'name': 'Trading components initialization',
                'success': True,
                'strategy_engine': orchestrator.strategy_engine is not None,
                'market_data': orchestrator.market_data is not None,
                'risk_manager': orchestrator.risk_manager is not None
            })
        except Exception as e:
            result['steps'].append({
                'step': 3,
                'name': 'Trading components initialization',
                'success': False,
                'error': str(e)
            })
            result['errors'].append(f"Step 3 failed: {e}")
        
        # Step 4: Test market data if available
        if orchestrator.market_data:
            try:
                logger.info("📋 Step 4: Market data test")
                symbols = ['BANKNIFTY', 'NIFTY']
                market_data = await orchestrator.market_data.get_latest_data(symbols)
                
                result['steps'].append({
                    'step': 4,
                    'name': 'Market data test',
                    'success': len(market_data) > 0,
                    'symbols_returned': len(market_data),
                    'sample_data_available': len(market_data) > 0
                })
            except Exception as e:
                result['steps'].append({
                    'step': 4,
                    'name': 'Market data test',
                    'success': False,
                    'error': str(e)
                })
                result['errors'].append(f"Step 4 failed: {e}")
        
        # Step 5: Test signal generation if components available
        if orchestrator.strategy_engine and orchestrator.market_data:
            try:
                logger.info("📋 Step 5: Signal generation test")
                symbols = ['BANKNIFTY', 'NIFTY']
                market_data = await orchestrator.market_data.get_latest_data(symbols)
                
                if market_data:
                    signals = await orchestrator.strategy_engine.generate_all_signals(market_data)
                    result['steps'].append({
                        'step': 5,
                        'name': 'Signal generation test',
                        'success': len(signals) > 0,
                        'signals_generated': len(signals)
                    })
                else:
                    result['steps'].append({
                        'step': 5,
                        'name': 'Signal generation test',
                        'success': False,
                        'error': 'No market data available'
                    })
            except Exception as e:
                result['steps'].append({
                    'step': 5,
                    'name': 'Signal generation test',
                    'success': False,
                    'error': str(e)
                })
                result['errors'].append(f"Step 5 failed: {e}")
        
        # Final state
        result['final_state'] = {
            'system_ready': orchestrator.system_ready,
            'connection_manager': orchestrator.connection_manager is not None,
            'strategy_engine': orchestrator.strategy_engine is not None,
            'market_data': orchestrator.market_data is not None,
            'risk_manager': orchestrator.risk_manager is not None
        }
        
        # Summary
        successful_steps = sum(1 for step in result['steps'] if step.get('success', False))
        total_steps = len(result['steps'])
        
        result['summary'] = {
            'successful_steps': f"{successful_steps}/{total_steps}",
            'overall_success': successful_steps == total_steps and successful_steps > 0,
            'critical_failure_step': None
        }
        
        # Find critical failure
        for step in result['steps']:
            if not step.get('success', False) and step['step'] <= 3:  # Steps 1-3 are critical
                result['summary']['critical_failure_step'] = step['step']
                break
        
        return {"success": True, "data": result}
        
    except Exception as e:
        logger.error(f"Detailed initialization debug failed: {e}")
        return {"success": False, "error": str(e)}

@router.get("/redis-test")
async def test_redis_connection():
    """Test Redis connection with current environment variables"""
    try:
        import redis.asyncio as redis
        
        # Get Redis config from environment
        redis_config = {
            'host': os.getenv('REDIS_HOST', 'localhost'),
            'port': int(os.getenv('REDIS_PORT', '6379')),
            'password': os.getenv('REDIS_PASSWORD'),
            'username': os.getenv('REDIS_USERNAME', 'default'),
            'ssl': os.getenv('REDIS_SSL', 'false').lower() == 'true',
            'ssl_cert_reqs': None if os.getenv('REDIS_SSL', 'false').lower() == 'true' else 'required'
        }
        
        logger.info(f"Testing Redis connection: {redis_config['host']}:{redis_config['port']} (SSL: {redis_config['ssl']})")
        
        # Create Redis client
        redis_client = redis.Redis(
            host=redis_config['host'],
            port=redis_config['port'],
            password=redis_config['password'],
            username=redis_config['username'],
            ssl=redis_config['ssl'],
            ssl_cert_reqs=redis_config['ssl_cert_reqs'],
            decode_responses=True
        )
        
        # Test connection
        start_time = datetime.now()
        await redis_client.ping()
        connection_time = (datetime.now() - start_time).total_seconds()
        
        # Test basic operations
        await redis_client.set("test_key", "test_value", ex=60)
        test_value = await redis_client.get("test_key")
        await redis_client.delete("test_key")
        
        return {
            "success": True,
            "message": "Redis connection successful",
            "config": {
                "host": redis_config['host'],
                "port": redis_config['port'],
                "ssl": redis_config['ssl'],
                "username": redis_config['username']
            },
            "connection_time_seconds": connection_time,
            "test_operations": {
                "set_get_delete": "successful",
                "test_value_retrieved": test_value
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Redis connection test failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "config": {
                "host": os.getenv('REDIS_HOST', 'NOT_SET'),
                "port": os.getenv('REDIS_PORT', 'NOT_SET'),
                "ssl": os.getenv('REDIS_SSL', 'NOT_SET'),
                "username": os.getenv('REDIS_USERNAME', 'NOT_SET'),
                "password_set": bool(os.getenv('REDIS_PASSWORD'))
            },
            "timestamp": datetime.now().isoformat()
        }

@router.get("/orchestrator-debug")
async def debug_orchestrator_components():
    """Debug orchestrator component initialization"""
    try:
        from src.core.dependencies import get_orchestrator
        
        orchestrator = get_orchestrator()
        
        # Check component status - use actual attribute names from TradingOrchestrator
        components = {
            "zerodha": hasattr(orchestrator, 'zerodha_client') and orchestrator.zerodha_client is not None,
            "position_tracker": hasattr(orchestrator, 'position_tracker') and orchestrator.position_tracker is not None,
            "risk_manager": hasattr(orchestrator, 'risk_manager') and orchestrator.risk_manager is not None,
            "market_data": hasattr(orchestrator, 'market_data') and orchestrator.market_data is not None and len(orchestrator.market_data) > 0,
            "strategy_engine": hasattr(orchestrator, 'strategies') and len(orchestrator.strategies) > 0,
            "trade_engine": hasattr(orchestrator, 'trade_engine') and orchestrator.trade_engine is not None,
            "system_ready": getattr(orchestrator, 'is_initialized', False),
            "is_active": getattr(orchestrator, 'is_running', False)
        }
        
        # Also check the components dict if available
        if hasattr(orchestrator, 'components') and isinstance(orchestrator.components, dict):
            for key, value in orchestrator.components.items():
                if key in components:
                    components[key] = value
        
        # Try to get trading status
        try:
            status = await orchestrator.get_trading_status()
            status_keys = list(status.keys())
            has_symbol_count = 'symbol_count' in status
            has_system_ready = 'system_ready' in status
        except Exception as e:
            status_keys = []
            has_symbol_count = False
            has_system_ready = False
            logger.error(f"Error getting trading status: {e}")
        
        return {
            "success": True,
            "components": components,
            "components_ready_count": sum(components.values()),
            "total_components": len(components),
            "status_method": {
                "status_keys": status_keys,
                "has_symbol_count": has_symbol_count,
                "has_system_ready": has_system_ready,
                "using_new_handler": has_symbol_count and has_system_ready
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Orchestrator debug failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        } 