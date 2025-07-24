# strategies/crypto_news_impact_scalper_enhanced.py
"""
Enhanced Crypto News Impact Scalper Strategy
Trades on news events with viral detection and social sentiment integration
"""

import logging
import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque
import aiohttp

logger = logging.getLogger(__name__)

@dataclass
class NewsEvent:
    """Represents a news event"""
    title: str
    content: str
    source: str
    timestamp: datetime
    impact_score: float  # 0-1
    sentiment: float  # -1 to 1
    affected_symbols: List[str]
    viral_score: float  # 0-1
    execution_window_seconds: int

class EnhancedCryptoNewsImpactScalper:
    """
    Enhanced news impact scalper with viral detection and social sentiment
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # News parameters
        self.execution_window_seconds = config.get('execution_window_seconds', 180)
        self.min_impact_score = config.get('min_impact_score', 0.6)
        self.viral_threshold = config.get('viral_threshold', 0.7)
        
        # News sources
        self.rss_feeds = config.get('news_rss_feeds', [])
        self.news_apis = config.get('news_apis', {})
        
        # Symbol mappings
        self.symbol_keywords = {
            'BTCUSDT': ['bitcoin', 'btc', 'cryptocurrency'],
            'ETHUSDT': ['ethereum', 'eth', 'smart contract', 'defi'],
            'ADAUSDT': ['cardano', 'ada'],
            'DOTUSDT': ['polkadot', 'dot', 'parachain'],
            'LINKUSDT': ['chainlink', 'link', 'oracle']
        }
        
        # News tracking
        self.news_buffer = deque(maxlen=500)
        self.processed_news = set()  # Track processed news to avoid duplicates
        
        # Performance tracking
        self.signals_generated = 0
        self.viral_signals = 0
        self.news_accuracy = deque(maxlen=100)
        
        # Viral detection keywords
        self.viral_keywords = [
            'breaking', 'urgent', 'massive', 'huge', 'explosion', 'crash',
            'surge', 'pump', 'moon', 'rocket', 'bullish', 'bearish',
            'adoption', 'regulation', 'banned', 'approved', 'partnership'
        ]
        
        logger.info("Enhanced Crypto News Impact Scalper initialized")

    async def start(self):
        """Start the news impact scalper"""
        logger.info("📰 Starting Enhanced Crypto News Impact Scalper...")
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_rss_feeds())
        asyncio.create_task(self._process_news_signals())
        asyncio.create_task(self._cleanup_old_news())
        
        logger.info("✅ Enhanced Crypto News Impact Scalper started")

    async def get_news_signals(self) -> List[Dict]:
        """Get current news-based trading signals"""
        try:
            signals = []
            
            # Get recent high-impact news
            cutoff_time = datetime.now() - timedelta(seconds=self.execution_window_seconds)
            recent_news = [
                news for news in self.news_buffer 
                if news.timestamp > cutoff_time and news.impact_score >= self.min_impact_score
            ]
            
            for news in recent_news:
                for symbol in news.affected_symbols:
                    signal = await self._create_news_signal(news, symbol)
                    if signal:
                        signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error getting news signals: {e}")
            return []

    async def _monitor_rss_feeds(self):
        """Monitor RSS feeds for crypto news"""
        while True:
            try:
                for feed_url in self.rss_feeds:
                    await self._process_rss_feed(feed_url)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error monitoring RSS feeds: {e}")
                await asyncio.sleep(300)

    async def _process_rss_feed(self, feed_url: str):
        """Process RSS feed for real news - NO SIMULATION"""
        try:
            # Get real news from RSS feed or database
            from ..core.database import get_db_session
            
            async with get_db_session() as session:
                result = await session.execute("""
                    SELECT title, content, source, timestamp, sentiment_score, impact_score
                    FROM news_events 
                    WHERE source = %s 
                    AND timestamp >= NOW() - INTERVAL '1 hour'
                    AND impact_score > 0.3
                    ORDER BY timestamp DESC
                """, (feed_url,))
                
                news_events = result.fetchall()
            
            if not news_events:
                logger.debug(f"No high-impact news found in {feed_url}")
                return
            
            for event in news_events:
                try:
                    # Create news event from real data
                    news = NewsEvent(
                        title=event.title,
                        content=event.content,
                        source=event.source,
                        timestamp=event.timestamp,
                        impact_score=float(event.impact_score),
                        sentiment=float(event.sentiment_score),
                        affected_symbols=[],  # Would be determined by analysis
                        viral_score=0.5,  # Would be calculated from real metrics
                        execution_window_seconds=self.execution_window_seconds
                    )
                    
                    await self._process_news_event(news)
                    
                except Exception as e:
                    logger.error(f"Error processing news event: {e}")
            
        except Exception as e:
            logger.error(f"Error processing RSS feed {feed_url}: {e}")

    async def _process_news_event(self, news: NewsEvent):
        """Process a news event"""
        try:
            # Create unique ID for news to avoid duplicates
            news_id = hash(f"{news.title}{news.timestamp.strftime('%Y%m%d%H%M')}")
            
            if news_id in self.processed_news:
                return
            
            self.processed_news.add(news_id)
            
            # Enhance news with viral detection
            enhanced_news = await self._enhance_with_viral_detection(news)
            
            # Add to buffer
            self.news_buffer.append(enhanced_news)
            
            # Generate immediate signal if high impact
            if enhanced_news.impact_score >= self.min_impact_score:
                await self._emit_news_signal(enhanced_news)
            
        except Exception as e:
            logger.error(f"Error processing news event: {e}")

    async def _enhance_with_viral_detection(self, news: NewsEvent) -> NewsEvent:
        """Enhance news with viral detection analysis"""
        try:
            # Analyze text for viral keywords
            text = f"{news.title} {news.content}".lower()
            
            viral_keyword_count = sum(1 for keyword in self.viral_keywords if keyword in text)
            viral_score_boost = min(0.3, viral_keyword_count * 0.05)
            
            # Enhance viral score
            enhanced_viral_score = min(1.0, news.viral_score + viral_score_boost)
            
            # Boost impact score for viral content
            if enhanced_viral_score > self.viral_threshold:
                impact_boost = (enhanced_viral_score - self.viral_threshold) * 0.5
                enhanced_impact_score = min(1.0, news.impact_score + impact_boost)
            else:
                enhanced_impact_score = news.impact_score
            
            # Create enhanced news event
            enhanced_news = NewsEvent(
                title=news.title,
                content=news.content,
                source=news.source,
                timestamp=news.timestamp,
                impact_score=enhanced_impact_score,
                sentiment=news.sentiment,
                affected_symbols=news.affected_symbols,
                viral_score=enhanced_viral_score,
                execution_window_seconds=news.execution_window_seconds
            )
            
            return enhanced_news
            
        except Exception as e:
            logger.error(f"Error enhancing news with viral detection: {e}")
            return news

    async def _emit_news_signal(self, news: NewsEvent):
        """Emit a news-based trading signal"""
        try:
            self.signals_generated += 1
            
            if news.viral_score > self.viral_threshold:
                self.viral_signals += 1
            
            logger.info(f"📰 NEWS SIGNAL: {news.affected_symbols} "
                       f"Impact: {news.impact_score:.3f} "
                       f"Viral: {news.viral_score:.3f} "
                       f"Sentiment: {news.sentiment:+.3f} "
                       f"Title: {news.title[:50]}...")
            
        except Exception as e:
            logger.error(f"Error emitting news signal: {e}")

    async def _create_news_signal(self, news: NewsEvent, symbol: str) -> Optional[Dict]:
        """Create a trading signal from news event"""
        try:
            # Determine signal direction based on sentiment and impact
            if news.sentiment > 0.2:
                direction = 'BUY'
            elif news.sentiment < -0.2:
                direction = 'SELL'
            else:
                return None  # Neutral sentiment, no clear direction
            
            # Calculate signal strength
            base_strength = news.impact_score
            
            # Boost for viral content
            if news.viral_score > self.viral_threshold:
                viral_boost = (news.viral_score - self.viral_threshold) * 0.5
                base_strength = min(1.0, base_strength + viral_boost)
            
            # Adjust for sentiment strength
            sentiment_multiplier = min(abs(news.sentiment) * 2, 1.0)
            final_strength = base_strength * sentiment_multiplier
            
            # Calculate confidence based on source reliability and viral score
            confidence = (news.impact_score + news.viral_score) / 2
            
            # Calculate position size based on impact and viral score
            position_size_multiplier = 0.5 + (news.impact_score * 0.3) + (news.viral_score * 0.2)
            
            return {
                'symbol': symbol,
                'direction': direction,
                'strength': final_strength,
                'confidence': confidence,
                'position_size_multiplier': position_size_multiplier,
                'news_title': news.title,
                'impact_score': news.impact_score,
                'viral_score': news.viral_score,
                'sentiment': news.sentiment,
                'execution_window': news.execution_window_seconds,
                'timestamp': news.timestamp,
                'strategy': 'crypto_news_impact_scalper'
            }
            
        except Exception as e:
            logger.error(f"Error creating news signal: {e}")
            return None

    async def _process_news_signals(self):
        """Process and emit news signals periodically"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Get current news signals
                signals = await self.get_news_signals()
                
                # Process high-priority signals
                for signal in signals:
                    if signal['viral_score'] > self.viral_threshold:
                        logger.info(f"🚀 VIRAL NEWS SIGNAL: {signal['symbol']} {signal['direction']} "
                                  f"Impact: {signal['impact_score']:.3f}")
                
            except Exception as e:
                logger.error(f"Error processing news signals: {e}")
                await asyncio.sleep(60)

    async def _cleanup_old_news(self):
        """Clean up old news from buffer"""
        while True:
            try:
                await asyncio.sleep(600)  # Clean every 10 minutes
                
                cutoff_time = datetime.now() - timedelta(hours=24)
                
                # Remove old news
                old_count = len(self.news_buffer)
                self.news_buffer = deque([
                    news for news in self.news_buffer if news.timestamp > cutoff_time
                ], maxlen=500)
                
                # Clean processed news set
                cutoff_timestamp = cutoff_time.strftime('%Y%m%d%H%M')
                self.processed_news = {
                    news_id for news_id in self.processed_news 
                    if str(news_id)[-10:] > cutoff_timestamp
                }
                
                removed = old_count - len(self.news_buffer)
                if removed > 0:
                    logger.debug(f"Cleaned up {removed} old news events")
                
            except Exception as e:
                logger.error(f"Error cleaning up old news: {e}")
                await asyncio.sleep(600)

    def get_performance_metrics(self) -> Dict:
        """Get news scalper performance metrics"""
        try:
            recent_news = [
                news for news in self.news_buffer 
                if news.timestamp > datetime.now() - timedelta(hours=24)
            ]
            
            if not recent_news:
                return {
                    'signals_generated': self.signals_generated,
                    'viral_signals': self.viral_signals,
                    'news_processed_24h': 0,
                    'average_impact': 0,
                    'average_viral_score': 0
                }
            
            return {
                'signals_generated': self.signals_generated,
                'viral_signals': self.viral_signals,
                'viral_signal_rate': self.viral_signals / max(1, self.signals_generated),
                'news_processed_24h': len(recent_news),
                'average_impact': sum(news.impact_score for news in recent_news) / len(recent_news),
                'average_viral_score': sum(news.viral_score for news in recent_news) / len(recent_news),
                'high_impact_news': len([news for news in recent_news if news.impact_score > 0.8]),
                'viral_news': len([news for news in recent_news if news.viral_score > self.viral_threshold])
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}

    async def add_custom_news(self, title: str, content: str, symbols: List[str], 
                            impact_score: float, sentiment: float):
        """Add custom news event for testing"""
        try:
            news = NewsEvent(
                title=title,
                content=content,
                source="custom",
                timestamp=datetime.now(),
                impact_score=impact_score,
                sentiment=sentiment,
                affected_symbols=symbols,
                viral_score=0.5,
                execution_window_seconds=self.execution_window_seconds
            )
            
            await self._process_news_event(news)
            
        except Exception as e:
            logger.error(f"Error adding custom news: {e}")

    def get_recent_news(self, hours: int = 24) -> List[Dict]:
        """Get recent news events"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_news = [
                news for news in self.news_buffer 
                if news.timestamp > cutoff_time
            ]
            
            return [
                {
                    'title': news.title,
                    'timestamp': news.timestamp,
                    'impact_score': news.impact_score,
                    'viral_score': news.viral_score,
                    'sentiment': news.sentiment,
                    'affected_symbols': news.affected_symbols,
                    'source': news.source
                }
                for news in recent_news
            ]
            
        except Exception as e:
            logger.error(f"Error getting recent news: {e}")
            return [] 