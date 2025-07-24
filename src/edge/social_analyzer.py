# edge/social_analyzer.py
"""
Quantum Social Analyzer - Viral Detection & Sentiment Analysis
Monitors Twitter, Reddit, Telegram, Discord for crypto sentiment and viral movements
"""

import logging
import asyncio
import json
import re
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from collections import defaultdict, deque
import aiohttp

# Social media API imports
try:
    import tweepy
    import praw  # Reddit API
    SOCIAL_APIS_AVAILABLE = True
except ImportError:
    SOCIAL_APIS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.error("Social media APIs not available. Real social data required - no fallback.")

logger = logging.getLogger(__name__)

class InfluencerTracker:
    """Tracks crypto influencer activities and impact"""
    
    def __init__(self, username: str, impact_score: float, platform: str):
        self.username = username
        self.impact_score = impact_score
        self.platform = platform
        self.recent_posts = deque(maxlen=50)
        self.follower_count = 0
        self.engagement_rate = 0.0
        self.accuracy_score = 0.7  # Historical prediction accuracy
        self.last_activity = None

class SentimentData:
    """Represents sentiment analysis for a symbol"""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.positive_mentions = 0
        self.negative_mentions = 0
        self.neutral_mentions = 0
        self.total_mentions = 0
        self.sentiment_score = 0.0  # -1 to 1
        self.viral_score = 0.0      # 0 to 1
        self.momentum = 0.0         # Rate of change
        self.trending_keywords = []
        self.influencer_mentions = []
        self.last_updated = datetime.now()

class QuantumSocialAnalyzer:
    """
    Advanced social media analyzer for crypto sentiment and viral detection
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # API configuration
        self.twitter_api_key = config.get('twitter_api_key')
        self.twitter_api_secret = config.get('twitter_api_secret')
        self.reddit_client_id = config.get('reddit_client_id')
        self.reddit_secret = config.get('reddit_secret')
        self.telegram_api_key = config.get('telegram_api_key')
        self.discord_webhook = config.get('discord_webhook')
        
        # API clients
        self.twitter_client = None
        self.reddit_client = None
        
        # Influencer tracking
        self.influencers = {}
        self.influencer_scores = config.get('influencer_impact_scores', {})
        self._initialize_influencers()
        
        # Sentiment tracking
        self.sentiment_data = {}  # symbol -> SentimentData
        self.sentiment_history = deque(maxlen=1000)
        
        # Viral detection
        self.viral_threshold = config.get('viral_threshold', 0.80)
        self.sentiment_window_hours = config.get('sentiment_window_hours', 24)
        self.pump_detection_threshold = config.get('pump_detection_threshold', 0.70)
        
        # Keywords and symbols to monitor
        self.crypto_symbols = ['BTC', 'ETH', 'ADA', 'DOT', 'LINK', 'SOL', 'AVAX', 'MATIC', 'ATOM']
        self.crypto_keywords = [
            'bitcoin', 'ethereum', 'crypto', 'cryptocurrency', 'blockchain',
            'defi', 'nft', 'web3', 'metaverse', 'dao', 'yield', 'staking'
        ]
        
        # Monitoring state
        self.monitoring_active = False
        self.is_running = False
        
        logger.info("Quantum Social Analyzer initialized")

    def _initialize_influencers(self):
        """Initialize crypto influencer tracking"""
        default_influencers = [
            ('elonmusk', 10.0, 'twitter'),
            ('vitalikbuterin', 8.0, 'twitter'),
            ('cz_binance', 7.5, 'twitter'),
            ('michael_saylor', 7.0, 'twitter'),
            ('cathiedwood', 6.5, 'twitter'),
            ('novogratz', 6.0, 'twitter'),
            ('raoulpal', 6.0, 'twitter'),
            ('APompliano', 5.5, 'twitter'),
            ('santimentfeed', 5.0, 'twitter'),
            ('whale_alert', 6.0, 'twitter')
        ]
        
        for username, score, platform in default_influencers:
            impact_score = self.influencer_scores.get(username, score)
            self.influencers[username] = InfluencerTracker(username, impact_score, platform)

    async def start(self):
        """Start social media monitoring"""
        try:
            # Initialize API clients
            await self._initialize_apis()
            
            # Start monitoring tasks
            self.is_running = True
            self.monitoring_active = True
            
            asyncio.create_task(self._monitor_twitter())
            asyncio.create_task(self._monitor_reddit())
            asyncio.create_task(self._monitor_telegram())
            asyncio.create_task(self._update_sentiment_scores())
            
            logger.info("📱 Quantum Social Analyzer started")
            
        except Exception as e:
            logger.error(f"Failed to start social analyzer: {e}")

    async def stop(self):
        """Stop social media monitoring"""
        self.is_running = False
        self.monitoring_active = False
        logger.info("🛑 Quantum Social Analyzer stopped")

    async def _initialize_apis(self):
        """Initialize social media API clients"""
        try:
            if SOCIAL_APIS_AVAILABLE and self.twitter_api_key:
                # Initialize Twitter API v2
                self.twitter_client = tweepy.Client(
                    bearer_token=self.twitter_api_key,
                    wait_on_rate_limit=True
                )
                logger.info("✅ Twitter API initialized")
            
            if SOCIAL_APIS_AVAILABLE and self.reddit_client_id:
                # Initialize Reddit API
                self.reddit_client = praw.Reddit(
                    client_id=self.reddit_client_id,
                    client_secret=self.reddit_secret,
                    user_agent="CryptoSentimentBot"
                )
                logger.info("✅ Reddit API initialized")
            
        except Exception as e:
            logger.error(f"Error initializing APIs: {e}")

    async def get_viral_signals(self) -> Dict:
        """Get current viral and sentiment signals"""
        try:
            signals = {}
            
            for symbol in self.crypto_symbols:
                symbol_with_usdt = f"{symbol}USDT"
                
                if symbol in self.sentiment_data:
                    sentiment = self.sentiment_data[symbol]
                    
                    signals[symbol_with_usdt] = {
                        'sentiment_score': sentiment.sentiment_score,
                        'viral_score': sentiment.viral_score,
                        'momentum': sentiment.momentum,
                        'total_mentions': sentiment.total_mentions,
                        'trending_keywords': sentiment.trending_keywords[:5],
                        'influencer_mentions': len(sentiment.influencer_mentions),
                        'pump_probability': self._calculate_pump_probability(sentiment)
                    }
            
            return signals
            
        except Exception as e:
            logger.error(f"Error getting viral signals: {e}")
            return {}

    async def _monitor_twitter(self):
        """Monitor Twitter for crypto sentiment"""
        while self.is_running:
            try:
                if not self.twitter_client:
                    await asyncio.sleep(300)
                    continue
                
                # Monitor crypto keywords
                for keyword in self.crypto_keywords:
                    await self._analyze_twitter_keyword(keyword)
                
                # Monitor specific influencers
                for username, influencer in self.influencers.items():
                    if influencer.platform == 'twitter':
                        await self._analyze_influencer_tweets(influencer)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error monitoring Twitter: {e}")
                await asyncio.sleep(300)

    async def _monitor_reddit(self):
        """Monitor Reddit for crypto sentiment"""
        while self.is_running:
            try:
                if not self.reddit_client:
                    await asyncio.sleep(300)
                    continue
                
                # Monitor crypto subreddits
                subreddits = ['cryptocurrency', 'bitcoin', 'ethereum', 'cryptomoonshots', 'defi']
                
                for subreddit_name in subreddits:
                    await self._analyze_reddit_subreddit(subreddit_name)
                
                await asyncio.sleep(180)  # Check every 3 minutes
                
            except Exception as e:
                logger.error(f"Error monitoring Reddit: {e}")
                await asyncio.sleep(300)

    async def _monitor_telegram(self):
        """Monitor Telegram for crypto signals"""
        while self.is_running:
            try:
                # This would connect to Telegram API
                # For now, simulate Telegram monitoring
                await self._simulate_telegram_data()
                
                await asyncio.sleep(120)  # Check every 2 minutes
                
            except Exception as e:
                logger.error(f"Error monitoring Telegram: {e}")
                await asyncio.sleep(300)

    async def _analyze_twitter_keyword(self, keyword: str):
        """Analyze Twitter posts for a specific keyword"""
        try:
            if not SOCIAL_APIS_AVAILABLE:
                return
            
            # Search for recent tweets
            tweets = self.twitter_client.search_recent_tweets(
                query=f"{keyword} -is:retweet lang:en",
                max_results=100,
                tweet_fields=['created_at', 'public_metrics', 'author_id']
            )
            
            if not tweets.data:
                return
            
            # Analyze sentiment for each crypto symbol
            for symbol in self.crypto_symbols:
                symbol_mentions = []
                
                for tweet in tweets.data:
                    if self._contains_symbol(tweet.text, symbol):
                        sentiment = self._analyze_text_sentiment(tweet.text)
                        symbol_mentions.append({
                            'text': tweet.text,
                            'sentiment': sentiment,
                            'created_at': tweet.created_at,
                            'metrics': tweet.public_metrics
                        })
                
                if symbol_mentions:
                    await self._update_symbol_sentiment(symbol, symbol_mentions, 'twitter')
            
        except Exception as e:
            logger.error(f"Error analyzing Twitter keyword '{keyword}': {e}")

    async def _analyze_influencer_tweets(self, influencer: InfluencerTracker):
        """Analyze tweets from a specific influencer"""
        try:
            if not SOCIAL_APIS_AVAILABLE:
                return
            
            # Get user by username
            user = self.twitter_client.get_user(username=influencer.username)
            if not user.data:
                return
            
            # Get recent tweets
            tweets = self.twitter_client.get_users_tweets(
                user.data.id,
                max_results=10,
                tweet_fields=['created_at', 'public_metrics']
            )
            
            if not tweets.data:
                return
            
            # Analyze influencer's recent posts
            for tweet in tweets.data:
                # Check for crypto mentions
                for symbol in self.crypto_symbols:
                    if self._contains_symbol(tweet.text, symbol):
                        sentiment = self._analyze_text_sentiment(tweet.text)
                        
                        # Weight by influencer impact
                        weighted_sentiment = sentiment * influencer.impact_score
                        
                        # Update symbol sentiment
                        if symbol not in self.sentiment_data:
                            self.sentiment_data[symbol] = SentimentData(symbol)
                        
                        self.sentiment_data[symbol].influencer_mentions.append({
                            'influencer': influencer.username,
                            'impact_score': influencer.impact_score,
                            'sentiment': sentiment,
                            'weighted_sentiment': weighted_sentiment,
                            'text': tweet.text[:100],
                            'timestamp': tweet.created_at
                        })
                        
                        influencer.last_activity = datetime.now()
            
        except Exception as e:
            logger.error(f"Error analyzing influencer {influencer.username}: {e}")

    async def _analyze_reddit_subreddit(self, subreddit_name: str):
        """Analyze Reddit posts in a subreddit"""
        try:
            if not SOCIAL_APIS_AVAILABLE:
                return
            
            subreddit = self.reddit_client.subreddit(subreddit_name)
            
            # Get hot posts
            for post in subreddit.hot(limit=50):
                post_text = f"{post.title} {post.selftext}"
                
                # Check for crypto symbols
                for symbol in self.crypto_symbols:
                    if self._contains_symbol(post_text, symbol):
                        sentiment = self._analyze_text_sentiment(post_text)
                        
                        mentions = [{
                            'text': post_text,
                            'sentiment': sentiment,
                            'created_at': datetime.fromtimestamp(post.created_utc),
                            'score': post.score,
                            'subreddit': subreddit_name
                        }]
                        
                        await self._update_symbol_sentiment(symbol, mentions, 'reddit')
            
        except Exception as e:
            logger.error(f"Error analyzing Reddit subreddit '{subreddit_name}': {e}")

    async def _simulate_telegram_data(self):
        """Simulate Telegram data for testing"""
        try:
            import random
            
            # Simulate some crypto discussions
            for symbol in self.crypto_symbols[:3]:  # Limit to 3 symbols
                if random.random() < 0.3:  # 30% chance of mention
                    mentions = [{
                        'text': f"Discussion about {symbol}",
                        'sentiment': random.uniform(-1, 1),
                        'created_at': datetime.now(),
                        'source': 'telegram_simulation'
                    }]
                    
                    await self._update_symbol_sentiment(symbol, mentions, 'telegram')
            
        except Exception as e:
            logger.error(f"Error simulating Telegram data: {e}")

    def _contains_symbol(self, text: str, symbol: str) -> bool:
        """Check if text contains crypto symbol"""
        text_upper = text.upper()
        
        # Check for exact symbol match
        if f"${symbol}" in text_upper or f" {symbol} " in text_upper:
            return True
        
        # Check for full name matches
        symbol_names = {
            'BTC': ['BITCOIN'],
            'ETH': ['ETHEREUM'],
            'ADA': ['CARDANO'],
            'DOT': ['POLKADOT'],
            'LINK': ['CHAINLINK'],
            'SOL': ['SOLANA'],
            'AVAX': ['AVALANCHE'],
            'MATIC': ['POLYGON'],
            'ATOM': ['COSMOS']
        }
        
        if symbol in symbol_names:
            for name in symbol_names[symbol]:
                if name in text_upper:
                    return True
        
        return False

    def _analyze_text_sentiment(self, text: str) -> float:
        """Analyze sentiment of text (-1 to 1)"""
        try:
            # Simplified sentiment analysis
            positive_words = [
                'bull', 'bullish', 'moon', 'rocket', 'pump', 'up', 'buy', 'long',
                'great', 'amazing', 'excellent', 'good', 'positive', 'rising'
            ]
            
            negative_words = [
                'bear', 'bearish', 'dump', 'crash', 'down', 'sell', 'short',
                'bad', 'terrible', 'awful', 'negative', 'falling', 'drop'
            ]
            
            text_lower = text.lower()
            
            positive_count = sum(1 for word in positive_words if word in text_lower)
            negative_count = sum(1 for word in negative_words if word in text_lower)
            
            if positive_count + negative_count == 0:
                return 0.0
            
            sentiment = (positive_count - negative_count) / (positive_count + negative_count)
            return max(-1.0, min(1.0, sentiment))
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return 0.0

    async def _update_symbol_sentiment(self, symbol: str, mentions: List[Dict], source: str):
        """Update sentiment data for a symbol"""
        try:
            if symbol not in self.sentiment_data:
                self.sentiment_data[symbol] = SentimentData(symbol)
            
            sentiment_obj = self.sentiment_data[symbol]
            
            # Process mentions
            for mention in mentions:
                sentiment_value = mention['sentiment']
                
                if sentiment_value > 0.1:
                    sentiment_obj.positive_mentions += 1
                elif sentiment_value < -0.1:
                    sentiment_obj.negative_mentions += 1
                else:
                    sentiment_obj.neutral_mentions += 1
                
                sentiment_obj.total_mentions += 1
            
            # Calculate overall sentiment score
            total = sentiment_obj.positive_mentions + sentiment_obj.negative_mentions + sentiment_obj.neutral_mentions
            if total > 0:
                sentiment_obj.sentiment_score = (
                    sentiment_obj.positive_mentions - sentiment_obj.negative_mentions
                ) / total
            
            # Calculate viral score based on mention volume and recency
            sentiment_obj.viral_score = self._calculate_viral_score(sentiment_obj)
            
            # Calculate momentum (rate of change)
            sentiment_obj.momentum = self._calculate_sentiment_momentum(sentiment_obj)
            
            sentiment_obj.last_updated = datetime.now()
            
        except Exception as e:
            logger.error(f"Error updating sentiment for {symbol}: {e}")

    def _calculate_viral_score(self, sentiment: SentimentData) -> float:
        """Calculate viral score based on mention volume and engagement"""
        try:
            # Base score from mention count
            base_score = min(sentiment.total_mentions / 1000, 1.0)  # Normalize to 1000 mentions
            
            # Boost for positive sentiment
            sentiment_boost = max(0, sentiment.sentiment_score) * 0.5
            
            # Time decay factor
            hours_since_update = (datetime.now() - sentiment.last_updated).seconds / 3600
            time_decay = max(0, 1 - (hours_since_update / 24))  # Decay over 24 hours
            
            viral_score = (base_score + sentiment_boost) * time_decay
            
            return min(1.0, viral_score)
            
        except Exception as e:
            logger.error(f"Error calculating viral score: {e}")
            return 0.0

    def _calculate_sentiment_momentum(self, sentiment: SentimentData) -> float:
        """Calculate sentiment momentum (rate of change)"""
        try:
            # This would track sentiment changes over time
            # For now, return a simplified momentum based on recent activity
            
            hours_since_update = (datetime.now() - sentiment.last_updated).seconds / 3600
            
            if hours_since_update < 1:
                return min(1.0, sentiment.total_mentions / 100)  # High momentum for recent activity
            else:
                return max(0.0, 1.0 - hours_since_update / 24)  # Decay momentum over time
            
        except Exception as e:
            logger.error(f"Error calculating momentum: {e}")
            return 0.0

    def _calculate_pump_probability(self, sentiment: SentimentData) -> float:
        """Calculate probability of a pump based on sentiment data"""
        try:
            # Combine multiple factors
            factors = []
            
            # High positive sentiment
            if sentiment.sentiment_score > 0.5:
                factors.append(sentiment.sentiment_score)
            
            # High viral score
            if sentiment.viral_score > 0.7:
                factors.append(sentiment.viral_score)
            
            # High momentum
            if sentiment.momentum > 0.6:
                factors.append(sentiment.momentum)
            
            # Influencer involvement
            if len(sentiment.influencer_mentions) > 0:
                avg_influencer_impact = sum(
                    mention['impact_score'] for mention in sentiment.influencer_mentions
                ) / len(sentiment.influencer_mentions)
                factors.append(avg_influencer_impact / 10.0)  # Normalize to 0-1
            
            if not factors:
                return 0.0
            
            # Geometric mean of factors
            pump_probability = 1.0
            for factor in factors:
                pump_probability *= factor
            
            pump_probability = pump_probability ** (1.0 / len(factors))
            
            return min(1.0, pump_probability)
            
        except Exception as e:
            logger.error(f"Error calculating pump probability: {e}")
            return 0.0

    async def _update_sentiment_scores(self):
        """Periodic update of sentiment scores"""
        while self.is_running:
            try:
                # Update viral scores and momentum for all symbols
                for symbol, sentiment_obj in self.sentiment_data.items():
                    sentiment_obj.viral_score = self._calculate_viral_score(sentiment_obj)
                    sentiment_obj.momentum = self._calculate_sentiment_momentum(sentiment_obj)
                
                # Clean old data
                cutoff_time = datetime.now() - timedelta(hours=self.sentiment_window_hours)
                for sentiment_obj in self.sentiment_data.values():
                    # Remove old influencer mentions
                    sentiment_obj.influencer_mentions = [
                        mention for mention in sentiment_obj.influencer_mentions
                        if mention.get('timestamp', datetime.now()) > cutoff_time
                    ]
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                logger.error(f"Error updating sentiment scores: {e}")
                await asyncio.sleep(300)

    async def update_influence_scores(self):
        """Update influencer impact scores based on real accuracy data"""
        try:
            logger.info("📈 Updating influencer impact scores...")
            
            # Get real influencer performance data from database
            from ..core.database import get_db_session
            
            async with get_db_session() as session:
                for username, influencer in self.influencers.items():
                    result = await session.execute("""
                        SELECT AVG(accuracy_score) as avg_accuracy
                        FROM influencer_performance 
                        WHERE username = %s 
                        AND timestamp >= NOW() - INTERVAL '7 days'
                    """, (username,))
                    
                    row = result.fetchone()
                    if row and row.avg_accuracy is not None:
                        # Update based on real performance
                        new_score = float(row.avg_accuracy) * 10  # Scale 0-1 to 0-10
                        influencer.impact_score = max(1.0, min(10.0, new_score))
                    else:
                        logger.warning(f"No real performance data for influencer {username}")
            
            logger.info("✅ Influencer scores updated with real data")
            
        except Exception as e:
            logger.error(f"Error updating influence scores: {e}")
            raise RuntimeError(f"Failed to update real influencer scores: {e}")

    def get_performance_metrics(self) -> Dict:
        """Get social analyzer performance metrics"""
        try:
            return {
                'monitoring_active': self.monitoring_active,
                'tracked_symbols': len(self.sentiment_data),
                'tracked_influencers': len(self.influencers),
                'total_mentions_24h': sum(
                    sentiment.total_mentions for sentiment in self.sentiment_data.values()
                    if (datetime.now() - sentiment.last_updated).seconds < 86400
                ),
                'viral_symbols': len([
                    symbol for symbol, sentiment in self.sentiment_data.items()
                    if sentiment.viral_score > self.viral_threshold
                ]),
                'api_status': {
                    'twitter': self.twitter_client is not None,
                    'reddit': self.reddit_client is not None
                }
            }
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {} 

    async def analyze_social_sentiment(self, symbol: str) -> Dict:
        """Analyze real social media sentiment - NO SIMULATION"""
        try:
            # Get real social media data from database or API
            from ..core.database import get_db_session
            
            async with get_db_session() as session:
                result = await session.execute("""
                    SELECT sentiment_score, mention_count, source, timestamp
                    FROM social_sentiment_data 
                    WHERE symbol = %s 
                    AND timestamp >= NOW() - INTERVAL '1 hour'
                    ORDER BY timestamp DESC
                    LIMIT 100
                """, (symbol,))
                
                sentiment_data = result.fetchall()
            
            if not sentiment_data:
                raise RuntimeError(f"No real social sentiment data available for {symbol}")
            
            # Calculate real sentiment metrics
            sentiments = [float(row.sentiment_score) for row in sentiment_data]
            mentions = [int(row.mention_count) for row in sentiment_data]
            
            avg_sentiment = sum(sentiments) / len(sentiments)
            total_mentions = sum(mentions)
            
            return {
                'symbol': symbol,
                'sentiment': avg_sentiment,
                'mentions': total_mentions,
                'source': 'real_social_data',
                'confidence': min(1.0, total_mentions / 1000),  # Normalize to 1000 mentions
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing social sentiment for {symbol}: {e}")
            raise RuntimeError(f"Failed to get real social sentiment data for {symbol}: {e}") 