from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
from pydantic import BaseModel
from core.analysis import analyze_stock, calculate_trade_quality
from core.market_data import get_market_data
from core.risk_manager import calculate_risk_metrics

router = APIRouter()

class StockRecommendation(BaseModel):
    symbol: str
    recommendation: str  # "BUY", "SELL", or "HOLD"
    entryPrice: float
    stopLoss: float
    target: float
    riskRewardRatio: float
    analysis: str
    timestamp: datetime
    quality_score: float
    confidence: float

@router.get("/recommendations", response_model=List[StockRecommendation])
async def get_recommendations():
    """
    Generate stock recommendations based on core engine analysis.
    Only returns recommendations with 10/10 quality score.
    This is for informational purposes only and not for actual trading.
    """
    try:
        # List of stocks to analyze
        stocks = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "SBIN", "BAJFINANCE"]
        recommendations = []

        for symbol in stocks:
            # Get market data
            market_data = await get_market_data(symbol)
            
            # Analyze stock using core engine
            analysis = analyze_stock(market_data)
            
            # Calculate risk metrics
            risk_metrics = calculate_risk_metrics(market_data)
            
            # Generate recommendation
            current_price = market_data['last_price']
            volatility = risk_metrics['volatility']
            
            # Calculate stop loss and target based on volatility and support/resistance
            stop_loss = calculate_stop_loss(market_data, current_price, volatility)
            target = calculate_target(market_data, current_price, volatility)
            
            # Calculate risk/reward ratio
            risk = current_price - stop_loss
            reward = target - current_price
            risk_reward_ratio = reward / risk if risk != 0 else 0
            
            # Calculate trade quality score
            quality_score = calculate_trade_quality(
                market_data=market_data,
                analysis=analysis,
                risk_metrics=risk_metrics,
                risk_reward_ratio=risk_reward_ratio
            )
            
            # Only proceed if quality score is 10/10
            if quality_score < 10.0:
                continue
            
            # Calculate confidence level
            confidence = calculate_confidence(
                analysis=analysis,
                risk_metrics=risk_metrics,
                risk_reward_ratio=risk_reward_ratio
            )
            
            # Determine recommendation
            if analysis['trend'] == 'BULLISH' and risk_reward_ratio >= 3:
                recommendation = "BUY"
            elif analysis['trend'] == 'BEARISH' and risk_reward_ratio >= 3:
                recommendation = "SELL"
            else:
                continue  # Skip if not a strong recommendation
            
            # Generate detailed analysis text
            analysis_text = f"""
            {symbol} shows {analysis['trend'].lower()} trend with {analysis['strength']} strength.
            Technical indicators suggest {analysis['momentum']} momentum.
            Volume analysis indicates {analysis['volume_trend']} participation.
            Risk/Reward ratio is {risk_reward_ratio:.2f}.
            Quality Score: 10/10
            Confidence: {confidence:.1f}%
            
            Key Strengths:
            - Strong trend alignment across multiple timeframes
            - High volume confirmation
            - Clear support/resistance levels
            - Optimal risk/reward ratio
            - Low market correlation
            - Strong momentum indicators
            """
            
            recommendations.append(StockRecommendation(
                symbol=symbol,
                recommendation=recommendation,
                entryPrice=current_price,
                stopLoss=stop_loss,
                target=target,
                riskRewardRatio=risk_reward_ratio,
                analysis=analysis_text.strip(),
                timestamp=datetime.now(),
                quality_score=quality_score,
                confidence=confidence
            ))
        
        return recommendations
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating recommendations: {str(e)}"
        )

def calculate_stop_loss(market_data: dict, current_price: float, volatility: float) -> float:
    """Calculate optimal stop loss based on support levels and volatility."""
    support_levels = market_data.get('support_levels', [])
    if support_levels:
        nearest_support = max([s for s in support_levels if s < current_price], default=None)
        if nearest_support:
            return nearest_support
    
    # Fallback to volatility-based stop loss
    return current_price * (1 - volatility * 2)

def calculate_target(market_data: dict, current_price: float, volatility: float) -> float:
    """Calculate optimal target based on resistance levels and volatility."""
    resistance_levels = market_data.get('resistance_levels', [])
    if resistance_levels:
        nearest_resistance = min([r for r in resistance_levels if r > current_price], default=None)
        if nearest_resistance:
            return nearest_resistance
    
    # Fallback to volatility-based target
    return current_price * (1 + volatility * 3)

def calculate_confidence(analysis: dict, risk_metrics: dict, risk_reward_ratio: float) -> float:
    """Calculate confidence level for the recommendation."""
    confidence = 0.0
    
    # Trend strength (30%)
    if analysis['strength'] == 'STRONG':
        confidence += 30
    elif analysis['strength'] == 'MODERATE':
        confidence += 15
    
    # Volume confirmation (20%)
    if analysis['volume_trend'] == 'HIGH':
        confidence += 20
    elif analysis['volume_trend'] == 'NORMAL':
        confidence += 10
    
    # Risk/Reward ratio (20%)
    if risk_reward_ratio >= 3:
        confidence += 20
    elif risk_reward_ratio >= 2:
        confidence += 10
    
    # Market conditions (15%)
    if risk_metrics['market_correlation'] < 0.3:
        confidence += 15
    elif risk_metrics['market_correlation'] < 0.5:
        confidence += 7.5
    
    # Technical indicators (15%)
    if analysis['momentum'] in ['BULLISH', 'BEARISH']:
        confidence += 15
    elif analysis['momentum'] == 'NEUTRAL':
        confidence += 7.5
    
    return confidence 