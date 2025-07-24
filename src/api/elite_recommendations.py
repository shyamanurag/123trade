"""
Elite Trading Recommendations API - Using Real Strategies
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from datetime import datetime, timedelta
import asyncio
import os
import logging
import requests

router = APIRouter()
logger = logging.getLogger(__name__)

class AutonomousEliteScanner:
    """Scanner that uses the ACTUAL 6 trading strategies - NO CUSTOM CODE"""
    
    def __init__(self):
        self.last_scan_time = None
        self.scan_interval_minutes = 0.5  # Scan every 30 seconds
        self.min_confidence = 0.75  # Minimum confidence for elite recommendations
        self.cached_recommendations = []
        self.cache_duration_seconds = 30
        self.strategies = {}
        
    async def initialize_strategies(self):
        """Initialize the same 6 strategies used by the main trading system"""
        try:
            # Import and initialize all existing strategies
            from strategies.momentum_surfer import EnhancedMomentumSurfer
            from strategies.volatility_explosion import EnhancedVolatilityExplosion
            from strategies.volume_profile_scalper import EnhancedVolumeProfileScalper
            from strategies.news_impact_scalper import EnhancedNewsImpactScalper
            from strategies.regime_adaptive_controller import RegimeAdaptiveController
            from strategies.confluence_amplifier import ConfluenceAmplifier
            
            # Configuration for strategies (same as orchestrator)
            config = {
                'signal_cooldown_seconds': 1,
                'risk_per_trade': 0.02,
                'max_positions': 5
            }
            
            # Initialize all strategies
            self.strategies = {
                'momentum_surfer': EnhancedMomentumSurfer(config),
                'volatility_explosion': EnhancedVolatilityExplosion(config),
                'volume_profile_scalper': EnhancedVolumeProfileScalper(config),
                'news_impact_scalper': EnhancedNewsImpactScalper(config),
                'regime_adaptive_controller': RegimeAdaptiveController(config),
                'confluence_amplifier': ConfluenceAmplifier(config)
            }
            
            # Initialize all strategies
            for name, strategy in self.strategies.items():
                await strategy.initialize()
                logger.info(f"✅ Elite scanner initialized strategy: {name}")
                
            logger.info(f"🚀 Elite scanner initialized with {len(self.strategies)} real strategies")
            
        except Exception as e:
            logger.error(f"Error initializing strategies for elite scanner: {e}")
            self.strategies = {}

    async def get_market_data(self):
        """Get market data from the main system"""
        try:
            # Get market data from local API
            from src.api.market_data import get_all_market_data
            market_data_response = await get_all_market_data()
            
            if market_data_response.get('success') and market_data_response.get('data'):
                return market_data_response['data']
            else:
                logger.warning("No market data available from main system")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return {}

    async def scan_for_elite_setups(self):
        """Scan using the ACTUAL 6 strategies - FIXED: Don't consume signals from main orchestrator"""
        try:
            # CRITICAL FIX: Use shared strategies from orchestrator instead of separate instances
            try:
                from src.core.orchestrator import get_orchestrator
                orchestrator = await get_orchestrator()
                
                if orchestrator and hasattr(orchestrator, 'strategies') and orchestrator.strategies:
                    # Use the SAME strategy instances as the main orchestrator
                    shared_strategies = orchestrator.strategies
                    logger.info(f"🔗 Using shared strategies from orchestrator: {len(shared_strategies)} strategies")
                else:
                    # Fallback to separate instances if orchestrator not available
                    if not self.strategies:
                        await self.initialize_strategies()
                    shared_strategies = self.strategies
                    logger.info(f"⚠️ Using separate strategy instances: {len(shared_strategies)} strategies")
                    
            except Exception as e:
                logger.error(f"Error accessing orchestrator strategies: {e}")
                if not self.strategies:
                    await self.initialize_strategies()
                shared_strategies = self.strategies
                
            if not shared_strategies:
                logger.error("No strategies available for elite recommendations")
                return []
            
            # Get market data
            market_data = await self.get_market_data()
            if not market_data:
                logger.warning("No market data available for elite scan")
                return []
            
            logger.info(f"🔍 Elite scan using {len(shared_strategies)} REAL strategies on {len(market_data)} symbols")
            
            # Transform market data for strategies (same as orchestrator)
            transformed_data = self._transform_market_data_for_strategies(market_data)
            
            # Collect all signals from all strategies - FIXED: Don't clear signals
            all_signals = []
            
            for strategy_name, strategy_info in shared_strategies.items():
                try:
                    # Get strategy instance
                    strategy = strategy_info.get('instance') if isinstance(strategy_info, dict) else strategy_info
                    
                    if not strategy:
                        logger.warning(f"No strategy instance for {strategy_name}")
                        continue
                    
                    # FIXED: Read signals WITHOUT clearing them (let orchestrator handle clearing)
                    signals_generated = 0
                    if hasattr(strategy, 'current_positions'):
                        for symbol, signal in strategy.current_positions.items():
                            if isinstance(signal, dict) and 'action' in signal and signal.get('action') != 'HOLD':
                                # Add strategy info to signal
                                signal['strategy'] = strategy_name
                                
                                # Filter by confidence
                                if signal.get('confidence', 0) >= self.min_confidence:
                                    # CRITICAL FIX: Copy signal instead of consuming it
                                    all_signals.append(signal.copy())
                                    signals_generated += 1
                                    logger.info(f"✅ ELITE SIGNAL COPIED: {strategy_name} -> {signal['symbol']} {signal['action']}")
                                
                                # FIXED: DON'T clear the signal - let orchestrator handle it
                                # strategy.current_positions[symbol] = None  # REMOVED THIS LINE
                    
                    if signals_generated == 0:
                        logger.info(f"📝 {strategy_name}: No elite signals generated")
                        
                except Exception as e:
                    logger.error(f"Error processing strategy {strategy_name}: {e}")
                    continue
            
            # Convert signals to Elite recommendations format
            elite_recommendations = []
            for signal in all_signals:
                recommendation = self.convert_signal_to_recommendation(signal)
                if recommendation:
                    elite_recommendations.append(recommendation)
            
            self.last_scan_time = datetime.now()
            logger.info(f"🎯 Elite scan completed: {len(elite_recommendations)} recommendations from {len(all_signals)} real strategy signals")
            logger.info(f"🔄 Signals preserved for main orchestrator to execute trades")
            
            return elite_recommendations
            
        except Exception as e:
            logger.error(f"Error in elite scan: {e}")
            return []

    def _transform_market_data_for_strategies(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform market data for strategies - SAME AS ORCHESTRATOR"""
        try:
            transformed_data = {}
            current_time = datetime.now()
            
            for symbol, data in raw_data.items():
                # Use current price from different possible fields
                current_price = data.get('ltp', data.get('close', data.get('price', 0)))
                volume = data.get('volume', 0)
                
                # Extract OHLC data
                high = data.get('high', current_price)
                low = data.get('low', current_price)
                open_price = data.get('open', current_price)
                
                # Calculate price and volume changes (simple calculation for Elite)
                price_change = data.get('change_percent', 0)
                volume_change = 0  # Simple calculation for Elite
                
                # Create strategy-compatible data format
                strategy_data = {
                    'symbol': symbol,
                    'close': current_price,
                    'ltp': current_price,
                    'high': high,
                    'low': low,
                    'open': open_price,
                    'volume': volume,
                    'price_change': round(price_change, 4),
                    'volume_change': round(volume_change, 4),
                    'timestamp': data.get('timestamp', current_time.isoformat())
                }
                
                transformed_data[symbol] = strategy_data
            
            return transformed_data
            
        except Exception as e:
            logger.error(f"Error transforming market data: {e}")
            return raw_data

    def convert_signal_to_recommendation(self, signal):
        """Convert real strategy signal to Elite recommendation format"""
        try:
            current_price = signal.get('entry_price', 0)
            stop_loss = signal.get('stop_loss')
            target = signal.get('target')
            
            # Only use real strategy signals with proper risk management
            if not stop_loss or not target:
                logger.warning(f"Signal rejected: Missing stop_loss or target for {signal.get('symbol', 'UNKNOWN')}")
                return None
            
            # Calculate risk/reward using strategy's calculations
            risk_percent = abs((current_price - stop_loss) / current_price) * 100
            reward_percent = abs((target - current_price) / current_price) * 100
            risk_reward_ratio = reward_percent / risk_percent if risk_percent > 0 else 3.0
            
            return {
                "recommendation_id": f"ELITE_{signal['symbol']}_{signal['strategy']}_{datetime.now().strftime('%Y%m%d_%H%M')}",
                "symbol": signal['symbol'],
                "direction": "LONG" if signal['action'] == 'BUY' else "SHORT",
                "strategy": f"Real {signal['strategy']}",
                "confidence": round(signal['confidence'] * 100, 1),
                "entry_price": round(current_price, 2),
                "current_price": round(current_price, 2),
                "stop_loss": round(stop_loss, 2),
                "primary_target": round(target, 2),
                "secondary_target": self._calculate_secondary_target(target, current_price, signal['action']),
                "tertiary_target": self._calculate_tertiary_target(target, current_price, signal['action']),
                "risk_reward_ratio": round(risk_reward_ratio, 2),
                "risk_metrics": {
                    "risk_percent": round(risk_percent, 2),
                    "reward_percent": round(reward_percent, 2),
                    "position_size": 2.0,
                    "risk_calculation": "REAL_STRATEGY_CALCULATION"
                },
                "confluence_factors": [
                    f"Real Strategy: {signal['strategy']}",
                    f"Signal Confidence: {signal['confidence']:.2f}",
                    f"Entry Price: ₹{current_price:,.2f}",
                    f"Risk/Reward: {risk_reward_ratio:.2f}:1",
                    f"Strategy Generated: {signal['metadata'].get('timestamp', 'N/A')}",
                    "Generated by Real Production Trading Strategies"
                ],
                "entry_conditions": [
                    f"Real {signal['strategy']} strategy signal",
                    "Price at strategy-calculated entry level",
                    "Strategy-based risk management parameters",
                    "Market conditions favorable per strategy",
                    "Real strategy risk calculation applied"
                ],
                "timeframe": "5-10 days",
                "valid_until": (datetime.now() + timedelta(days=7)).isoformat(),
                "status": "ACTIVE",
                "generated_at": datetime.now().isoformat(),
                "data_source": "REAL_STRATEGY_GENERATED",
                "strategy_metadata": signal.get('metadata', {}),
                "autonomous": True,
                "WARNING": "REAL_STRATEGY_NON_INTRADAY_SIGNAL"
            }
            
        except Exception as e:
            logger.error(f"Error converting signal to recommendation: {e}")
            return None

    def _calculate_secondary_target(self, primary_target, entry_price, action):
        """Calculate secondary target based on position direction"""
        if action == 'SELL':  # SHORT position
            distance = abs(entry_price - primary_target)
            return round(primary_target - (distance * 0.5), 2)
        else:  # LONG position
            distance = abs(primary_target - entry_price)
            return round(primary_target + (distance * 0.5), 2)
    
    def _calculate_tertiary_target(self, primary_target, entry_price, action):
        """Calculate tertiary target based on position direction"""
        if action == 'SELL':  # SHORT position
            distance = abs(entry_price - primary_target)
            return round(primary_target - (distance * 1.0), 2)
        else:  # LONG position
            distance = abs(primary_target - entry_price)
            return round(primary_target + (distance * 1.0), 2)

# Global scanner instance
autonomous_scanner = AutonomousEliteScanner()

@router.get("/")
async def get_elite_recommendations():
    """Get current elite trading recommendations using REAL strategies"""
    try:
        # Use intelligent caching
        cache_duration_seconds = 30
        
        if autonomous_scanner.last_scan_time is None or \
           (datetime.now() - autonomous_scanner.last_scan_time).total_seconds() > cache_duration_seconds:
            logger.info("🔄 Running fresh elite scan using REAL strategies...")
            recommendations = await autonomous_scanner.scan_for_elite_setups()
            autonomous_scanner.cached_recommendations = recommendations
        else:
            logger.info("⚡ Using cached elite recommendations")
            recommendations = autonomous_scanner.cached_recommendations
        
        # Filter only ACTIVE recommendations
        active_recommendations = [r for r in recommendations if r.get('status') == 'ACTIVE']
        
        return {
            "success": True,
            "recommendations": active_recommendations,
            "total_count": len(active_recommendations),
            "status": "ACTIVE",
            "message": f"Found {len(active_recommendations)} elite recommendations from REAL strategies",
            "data_source": "REAL_STRATEGY_GENERATED",
            "scan_timestamp": autonomous_scanner.last_scan_time.isoformat() if autonomous_scanner.last_scan_time else datetime.now().isoformat(),
            "timestamp": datetime.now().isoformat(),
            "next_scan": (datetime.now() + timedelta(minutes=autonomous_scanner.scan_interval_minutes)).isoformat(),
            "strategies_used": list(autonomous_scanner.strategies.keys()) if autonomous_scanner.strategies else [],
            "cache_status": "REAL_STRATEGY_BASED_RECOMMENDATIONS"
        }
        
    except Exception as e:
        logger.error(f"Error fetching elite recommendations: {e}")
        return {
            "success": True,
            "recommendations": [],
            "total_count": 0,
            "status": "NO_RECOMMENDATIONS",
            "message": "No elite recommendations available from real strategies at this time",
            "data_source": "REAL_STRATEGY_SYSTEM",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/force-scan")
async def force_autonomous_scan():
    """Force an immediate scan using REAL strategies"""
    try:
        logger.info("🔄 Forcing immediate elite scan using REAL strategies...")
        recommendations = await autonomous_scanner.scan_for_elite_setups()
        
        return {
            "success": True,
            "message": "Forced elite scan using REAL strategies completed",
            "recommendations_found": len(recommendations),
            "recommendations": recommendations,
            "strategies_used": list(autonomous_scanner.strategies.keys()) if autonomous_scanner.strategies else [],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in forced scan: {e}")
        raise HTTPException(status_code=500, detail="Real strategy scan failed")

@router.get("/scanner-status")
async def get_scanner_status():
    """Get Elite scanner status"""
    try:
        return {
            "success": True,
            "scanner_active": bool(autonomous_scanner.strategies),
            "strategies_loaded": list(autonomous_scanner.strategies.keys()) if autonomous_scanner.strategies else [],
            "last_scan": autonomous_scanner.last_scan_time.isoformat() if autonomous_scanner.last_scan_time else None,
            "scan_interval_minutes": autonomous_scanner.scan_interval_minutes,
            "min_confidence": autonomous_scanner.min_confidence,
            "cache_duration": autonomous_scanner.cache_duration_seconds,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting scanner status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get scanner status")
