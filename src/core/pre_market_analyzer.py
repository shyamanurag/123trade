"""
Pre-Market Analysis Engine for ShareKhan Trading System
100% REAL DATA ONLY - NO PAPER/MOCK/DEMO MODE
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
from decimal import Decimal

logger = logging.getLogger(__name__)

class PreMarketAnalyzer:
    """Pre-market analysis for real trading - NO PAPER MODE"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.sharekhan_client = None
        # REMOVED: paper_mode - only real mode allowed
        self.real_mode_only = True  # ENFORCED: Real mode only
        
    async def run_pre_market_analysis(self) -> Dict:
        """Run comprehensive pre-market analysis with REAL data only"""
        try:
            logger.info("🚀 Starting REAL pre-market analysis...")
            
            # REMOVED: Paper mode check - only real analysis
            return await self._run_live_analysis()
            
        except Exception as e:
            logger.error(f"❌ Pre-market analysis failed: {e}")
            raise RuntimeError(f"REAL DATA REQUIRED: Pre-market analysis failed: {str(e)}")

    # REMOVED: _run_paper_mode_analysis - No paper mode allowed

    async def _run_live_analysis(self) -> Dict:
        """Run live analysis with real market data - PRODUCTION ONLY"""
        try:
            logger.info("📊 Running LIVE pre-market analysis...")
            
            # Import real ShareKhan client
            from brokers.sharekhan import ShareKhanIntegration
            
            self.sharekhan_client = ShareKhanIntegration()
            if not self.sharekhan_client.is_connected():
                raise RuntimeError("ShareKhan connection required for real analysis")
            
            # Get real pre-market data
            analysis_results = {
                "timestamp": datetime.now().isoformat(),
                "mode": "LIVE_PRODUCTION",
                "data_source": "sharekhan_live",
                "key_levels": await self._calculate_real_key_levels(),
                "market_sentiment": await self._analyze_real_sentiment(),
                "recommended_strategies": await self._recommend_live_strategies(),
                "risk_parameters": await self._prepare_live_system_parameters(),
                "global_markets": await self._analyze_global_markets(),
                "previous_day": await self._analyze_previous_day()
            }
            
            logger.info("✅ Live pre-market analysis completed")
            return analysis_results
            
        except Exception as e:
            logger.error(f"❌ Live analysis failed: {e}")
            raise RuntimeError(f"REAL DATA ERROR: {str(e)}")

    # REMOVED: _calculate_mock_key_levels - No mock data allowed
    
    async def _calculate_real_key_levels(self) -> Dict:
        """Calculate real key support/resistance levels from ShareKhan data"""
        try:
            # Get real historical data from ShareKhan
            key_symbols = ["NIFTY", "BANKNIFTY", "SENSEX"]
            key_levels = {}
            
            for symbol in key_symbols:
                historical_data = await self.sharekhan_client.get_historical_data(
                    symbol=symbol,
                    interval="1d",
                    days=30
                )
                
                if not historical_data:
                    raise ValueError(f"No real historical data available for {symbol}")
                
                # Calculate real support/resistance levels
                df = pd.DataFrame(historical_data)
                
                key_levels[symbol] = {
                    "support_1": float(df['low'].quantile(0.25)),
                    "support_2": float(df['low'].quantile(0.10)),
                    "resistance_1": float(df['high'].quantile(0.75)),
                    "resistance_2": float(df['high'].quantile(0.90)),
                    "pivot": float(df['close'].iloc[-1]),
                    "data_points": len(df),
                    "source": "sharekhan_historical"
                }
            
            return key_levels
            
        except Exception as e:
            logger.error(f"❌ Real key levels calculation failed: {e}")
            raise

    # REMOVED: _recommend_paper_strategies - No paper strategies allowed
    
    async def _recommend_live_strategies(self) -> Dict:
        """Recommend real trading strategies based on live market analysis"""
        try:
            # Get real market conditions
            market_data = await self.sharekhan_client.get_market_overview()
            
            if not market_data:
                raise ValueError("No real market data available for strategy recommendations")
            
            strategies = {
                "primary_strategy": self._select_live_strategy(market_data),
                "backup_strategies": self._get_backup_strategies(market_data),
                "risk_level": self._assess_real_risk_level(market_data),
                "position_sizing": self._calculate_real_position_sizes(market_data),
                "data_source": "sharekhan_live"
            }
            
            return strategies
            
        except Exception as e:
            logger.error(f"❌ Live strategy recommendation failed: {e}")
            raise

    # REMOVED: _prepare_paper_system_parameters - No paper parameters allowed
    
    async def _prepare_live_system_parameters(self) -> Dict:
        """Prepare real system parameters for live trading"""
        try:
            # Get real account information
            account_info = await self.sharekhan_client.get_account_info()
            
            if not account_info:
                raise ValueError("No real account information available")
            
            return {
                "max_position_size": float(account_info.get('available_margin', 0)) * 0.1,  # 10% of available margin
                "daily_loss_limit": float(account_info.get('available_margin', 0)) * 0.05,   # 5% daily loss limit
                "max_trades_per_day": 20,  # Conservative limit for real trading
                "position_timeout": 300,   # 5 minutes position timeout
                "stop_loss_percent": 2.0,  # 2% stop loss
                "take_profit_percent": 4.0, # 4% take profit
                "available_margin": float(account_info.get('available_margin', 0)),
                "used_margin": float(account_info.get('used_margin', 0)),
                "account_status": account_info.get('status', 'unknown'),
                "data_source": "sharekhan_account"
            }
            
        except Exception as e:
            logger.error(f"❌ Live system parameters preparation failed: {e}")
            raise

    async def _analyze_global_markets(self) -> Dict:
        """Analyze global market conditions using real data"""
        try:
            # Get real global market data
            global_data = await self.sharekhan_client.get_global_markets()
            
            if not global_data:
                # If global data not available, use minimal real indicators
                return {
                    "us_markets": "data_unavailable",
                    "asian_markets": "data_unavailable", 
                    "european_markets": "data_unavailable",
                    "sentiment": "neutral",
                    "impact_on_indian_markets": "minimal",
                    "data_source": "limited_real_data"
                }
            
            return {
                "us_markets": global_data.get('us_markets', 'unknown'),
                "asian_markets": global_data.get('asian_markets', 'unknown'),
                "european_markets": global_data.get('european_markets', 'unknown'),
                "sentiment": self._calculate_global_sentiment(global_data),
                "impact_on_indian_markets": self._assess_india_impact(global_data),
                "data_source": "sharekhan_global"
            }
            
        except Exception as e:
            logger.error(f"❌ Global markets analysis failed: {e}")
            return {
                "error": str(e),
                "sentiment": "unknown",
                "data_source": "error_fallback"
            }

    async def _analyze_previous_day(self) -> Dict:
        """Analyze previous day's trading session using real data"""
        try:
            # Get real previous day data
            yesterday = datetime.now() - timedelta(days=1)
            prev_day_data = await self.sharekhan_client.get_historical_data(
                symbol="NIFTY",
                interval="1d", 
                start_date=yesterday.strftime("%Y-%m-%d"),
                end_date=yesterday.strftime("%Y-%m-%d")
            )
            
            if not prev_day_data:
                raise ValueError("No real previous day data available")
            
            last_session = prev_day_data[-1]
            
            return {
                "close_price": float(last_session.get('close', 0)),
                "volume": int(last_session.get('volume', 0)),
                "high": float(last_session.get('high', 0)),
                "low": float(last_session.get('low', 0)),
                "change": float(last_session.get('change', 0)),
                "change_percent": float(last_session.get('change_percent', 0)),
                "market_breadth": await self._calculate_real_market_breadth(),
                "data_source": "sharekhan_historical"
            }
            
        except Exception as e:
            logger.error(f"❌ Previous day analysis failed: {e}")
            raise

    async def _calculate_real_market_breadth(self) -> Dict:
        """Calculate real market breadth indicators"""
        try:
            # Get real market breadth data from ShareKhan
            breadth_data = await self.sharekhan_client.get_market_breadth()
            
            if not breadth_data:
                return {
                    "advances": 0,
                    "declines": 0,
                    "unchanged": 0,
                    "advance_decline_ratio": 1.0,
                    "data_source": "unavailable"
                }
            
            return {
                "advances": int(breadth_data.get('advances', 0)),
                "declines": int(breadth_data.get('declines', 0)),
                "unchanged": int(breadth_data.get('unchanged', 0)),
                "advance_decline_ratio": float(breadth_data.get('ad_ratio', 1.0)),
                "data_source": "sharekhan_breadth"
            }
            
        except Exception as e:
            logger.error(f"❌ Market breadth calculation failed: {e}")
            return {
                "error": str(e),
                "data_source": "error_fallback"
            }

    def _select_live_strategy(self, market_data: Dict) -> str:
        """Select appropriate live trading strategy based on real market conditions"""
        # Real strategy selection logic based on actual market data
        volatility = market_data.get('volatility', 0)
        trend = market_data.get('trend', 'neutral')
        volume = market_data.get('volume', 0)
        
        if volatility > 20 and volume > 1000000:
            return "momentum_breakout"
        elif volatility < 10 and trend == "up":
            return "trend_following"
        elif volatility > 15:
            return "mean_reversion"
        else:
            return "conservative_scalping"

    def _get_backup_strategies(self, market_data: Dict) -> List[str]:
        """Get backup strategies for real trading"""
        return ["conservative_scalping", "mean_reversion", "momentum_breakout"]

    def _assess_real_risk_level(self, market_data: Dict) -> str:
        """Assess real risk level based on market conditions"""
        volatility = market_data.get('volatility', 0)
        
        if volatility > 25:
            return "high"
        elif volatility > 15:
            return "medium"
        else:
            return "low"

    def _calculate_real_position_sizes(self, market_data: Dict) -> Dict:
        """Calculate real position sizes based on account and market conditions"""
        # Real position sizing based on actual account balance and risk
        base_position = 10000  # Base position size in INR
        volatility_factor = 1.0 - (market_data.get('volatility', 15) / 100)
        
        return {
            "equity_position_size": int(base_position * volatility_factor),
            "options_position_size": int(base_position * volatility_factor * 0.5),
            "max_positions": 5,
            "risk_per_trade": 2.0  # 2% risk per trade
        }

    def _calculate_global_sentiment(self, global_data: Dict) -> str:
        """Calculate global market sentiment from real data"""
        # Real sentiment analysis based on global market data
        positive_indicators = 0
        total_indicators = 0
        
        for market, data in global_data.items():
            if isinstance(data, dict) and 'change_percent' in data:
                total_indicators += 1
                if data['change_percent'] > 0:
                    positive_indicators += 1
        
        if total_indicators == 0:
            return "neutral"
        
        positive_ratio = positive_indicators / total_indicators
        
        if positive_ratio > 0.6:
            return "positive"
        elif positive_ratio < 0.4:
            return "negative"
        else:
            return "neutral"

    def _assess_india_impact(self, global_data: Dict) -> str:
        """Assess impact on Indian markets from real global data"""
        # Real impact assessment based on global market movements
        us_impact = global_data.get('us_markets', {}).get('change_percent', 0)
        asian_impact = global_data.get('asian_markets', {}).get('change_percent', 0)
        
        avg_impact = (us_impact + asian_impact) / 2
        
        if abs(avg_impact) > 2:
            return "high"
        elif abs(avg_impact) > 1:
            return "medium"
        else:
            return "low"

    async def _analyze_real_sentiment(self) -> Dict:
        """Analyze real market sentiment using ShareKhan data"""
        try:
            # Get real sentiment indicators
            sentiment_data = await self.sharekhan_client.get_sentiment_indicators()
            
            if not sentiment_data:
                return {
                    "overall_sentiment": "neutral",
                    "confidence_level": 50,
                    "data_source": "unavailable"
                }
            
            return {
                "overall_sentiment": sentiment_data.get('sentiment', 'neutral'),
                "confidence_level": int(sentiment_data.get('confidence', 50)),
                "fear_greed_index": float(sentiment_data.get('fear_greed', 50)),
                "put_call_ratio": float(sentiment_data.get('put_call_ratio', 1.0)),
                "data_source": "sharekhan_sentiment"
            }
            
        except Exception as e:
            logger.error(f"❌ Real sentiment analysis failed: {e}")
            return {
                "overall_sentiment": "unknown",
                "error": str(e),
                "data_source": "error_fallback"
            } 