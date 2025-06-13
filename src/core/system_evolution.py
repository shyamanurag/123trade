import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import pandas as pd

from .models import Order, OrderStatus
from .exceptions import OrderError

logger = logging.getLogger(__name__)

class SystemEvolution:
    """Handles system self-learning and evolution based on performance data"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.performance_history = {}  # strategy -> List[Dict]
        self.user_performance = {}  # user_id -> List[Dict]
        self.strategy_weights = {}  # strategy -> float
        self.user_weights = {}  # user_id -> float
        self.learning_models = {}  # strategy -> model
        self.feature_scalers = {}  # strategy -> scaler
        
        # Initialize learning parameters
        self.learning_window = timedelta(days=config.get('evolution', {}).get('learning_window_days', 30))
        self.min_samples = config.get('evolution', {}).get('min_samples_for_learning', 100)
        self.retraining_interval = timedelta(hours=config.get('evolution', {}).get('retraining_interval_hours', 24))
        self.last_training = {}  # strategy -> timestamp
        
        # Initialize models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize learning models for each strategy"""
        for strategy in self.config.get('strategies', []):
            self.learning_models[strategy] = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            self.feature_scalers[strategy] = StandardScaler()
            self.strategy_weights[strategy] = 1.0
    
    async def record_trade_performance(self, strategy_name: str, trade_data: Dict[str, Any]):
        """Record trade performance for learning"""
        try:
            if strategy_name not in self.performance_history:
                self.performance_history[strategy_name] = []
            
            # Add timestamp if not present
            if 'timestamp' not in trade_data:
                trade_data['timestamp'] = datetime.now()
            
            # Record performance
            self.performance_history[strategy_name].append(trade_data)
            
            # Clean old data
            self._clean_old_data()
            
            # Check if retraining is needed
            await self._check_retraining(strategy_name)
            
        except Exception as e:
            logger.error(f"Error recording trade performance: {str(e)}")
    
    async def record_user_performance(self, user_id: str, performance_data: Dict[str, Any]):
        """Record user performance for learning"""
        try:
            if user_id not in self.user_performance:
                self.user_performance[user_id] = []
            
            # Add timestamp if not present
            if 'timestamp' not in performance_data:
                performance_data['timestamp'] = datetime.now()
            
            # Record performance
            self.user_performance[user_id].append(performance_data)
            
            # Update user weights
            await self._update_user_weights(user_id)
            
        except Exception as e:
            logger.error(f"Error recording user performance: {str(e)}")
    
    async def get_strategy_weight(self, strategy_name: str) -> float:
        """Get current weight for a strategy"""
        return self.strategy_weights.get(strategy_name, 1.0)
    
    async def get_user_weight(self, user_id: str) -> float:
        """Get current weight for a user"""
        return self.user_weights.get(user_id, 1.0)
    
    async def predict_trade_outcome(self, strategy_name: str, trade_features: Dict[str, Any]) -> Dict[str, Any]:
        """Predict outcome of a potential trade"""
        try:
            if strategy_name not in self.learning_models:
                return {'confidence': 0.0, 'predicted_return': 0.0}
            
            # Prepare features
            features = self._prepare_features(trade_features)
            if features is None:
                return {'confidence': 0.0, 'predicted_return': 0.0}
            
            # Scale features
            scaled_features = self.feature_scalers[strategy_name].transform([features])
            
            # Make prediction
            model = self.learning_models[strategy_name]
            predicted_return = model.predict(scaled_features)[0]
            
            # Calculate confidence based on feature importance
            feature_importance = model.feature_importances_
            confidence = np.mean(feature_importance)
            
            return {
                'confidence': float(confidence),
                'predicted_return': float(predicted_return)
            }
            
        except Exception as e:
            logger.error(f"Error predicting trade outcome: {str(e)}")
            return {'confidence': 0.0, 'predicted_return': 0.0}
    
    async def _check_retraining(self, strategy_name: str):
        """Check if model retraining is needed"""
        try:
            current_time = datetime.now()
            last_training = self.last_training.get(strategy_name, datetime.min)
            
            if (current_time - last_training) >= self.retraining_interval:
                await self._retrain_model(strategy_name)
                self.last_training[strategy_name] = current_time
                
        except Exception as e:
            logger.error(f"Error checking retraining: {str(e)}")
    
    async def _retrain_model(self, strategy_name: str):
        """Retrain learning model for a strategy"""
        try:
            # Get performance data
            performance_data = self.performance_history.get(strategy_name, [])
            if len(performance_data) < self.min_samples:
                return
            
            # Prepare training data
            X, y = self._prepare_training_data(performance_data)
            if X is None or y is None:
                return
            
            # Scale features
            X_scaled = self.feature_scalers[strategy_name].fit_transform(X)
            
            # Train model
            model = self.learning_models[strategy_name]
            model.fit(X_scaled, y)
            
            # Update strategy weight based on recent performance
            await self._update_strategy_weight(strategy_name)
            
        except Exception as e:
            logger.error(f"Error retraining model: {str(e)}")
    
    def _prepare_training_data(self, performance_data: List[Dict[str, Any]]) -> tuple:
        """Prepare training data from performance history"""
        try:
            # Convert to DataFrame
            df = pd.DataFrame(performance_data)
            
            # Extract features and target
            feature_columns = [
                'market_volatility', 'volume', 'price_momentum',
                'time_of_day', 'day_of_week', 'position_size'
            ]
            target_column = 'return'
            
            # Check if required columns exist
            if not all(col in df.columns for col in feature_columns + [target_column]):
                return None, None
            
            X = df[feature_columns].values
            y = df[target_column].values
            
            return X, y
            
        except Exception as e:
            logger.error(f"Error preparing training data: {str(e)}")
            return None, None
    
    def _prepare_features(self, trade_features: Dict[str, Any]) -> Optional[np.ndarray]:
        """Prepare features for prediction"""
        try:
            required_features = [
                'market_volatility', 'volume', 'price_momentum',
                'time_of_day', 'day_of_week', 'position_size'
            ]
            
            if not all(feature in trade_features for feature in required_features):
                return None
            
            return np.array([trade_features[feature] for feature in required_features])
            
        except Exception as e:
            logger.error(f"Error preparing features: {str(e)}")
            return None
    
    async def _update_strategy_weight(self, strategy_name: str):
        """Update strategy weight based on recent performance"""
        try:
            # Get recent performance
            recent_data = self._get_recent_performance(strategy_name)
            if not recent_data:
                return
            
            # Calculate performance metrics
            returns = [trade['return'] for trade in recent_data]
            win_rate = sum(1 for r in returns if r > 0) / len(returns)
            avg_return = np.mean(returns)
            sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
            
            # Update weight based on metrics
            weight = (win_rate * 0.4 + 
                     (1 if avg_return > 0 else 0) * 0.3 + 
                     (1 if sharpe_ratio > 1 else 0) * 0.3)
            
            self.strategy_weights[strategy_name] = weight
            
        except Exception as e:
            logger.error(f"Error updating strategy weight: {str(e)}")
    
    async def _update_user_weights(self, user_id: str):
        """Update user weights based on performance"""
        try:
            # Get recent performance
            recent_data = self._get_recent_user_performance(user_id)
            if not recent_data:
                return
            
            # Calculate performance metrics
            returns = [trade['return'] for trade in recent_data]
            win_rate = sum(1 for r in returns if r > 0) / len(returns)
            avg_return = np.mean(returns)
            risk_adjusted_return = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
            
            # Update weight based on metrics
            weight = (win_rate * 0.4 + 
                     (1 if avg_return > 0 else 0) * 0.3 + 
                     (1 if risk_adjusted_return > 1 else 0) * 0.3)
            
            self.user_weights[user_id] = weight
            
        except Exception as e:
            logger.error(f"Error updating user weight: {str(e)}")
    
    def _get_recent_performance(self, strategy_name: str) -> List[Dict[str, Any]]:
        """Get recent performance data for a strategy"""
        try:
            current_time = datetime.now()
            performance_data = self.performance_history.get(strategy_name, [])
            
            return [
                trade for trade in performance_data
                if (current_time - trade['timestamp']) <= self.learning_window
            ]
            
        except Exception as e:
            logger.error(f"Error getting recent performance: {str(e)}")
            return []
    
    def _get_recent_user_performance(self, user_id: str) -> List[Dict[str, Any]]:
        """Get recent performance data for a user"""
        try:
            current_time = datetime.now()
            performance_data = self.user_performance.get(user_id, [])
            
            return [
                trade for trade in performance_data
                if (current_time - trade['timestamp']) <= self.learning_window
            ]
            
        except Exception as e:
            logger.error(f"Error getting recent user performance: {str(e)}")
            return []
    
    def _clean_old_data(self):
        """Clean old performance data"""
        try:
            current_time = datetime.now()
            
            # Clean strategy performance data
            for strategy in self.performance_history:
                self.performance_history[strategy] = [
                    trade for trade in self.performance_history[strategy]
                    if (current_time - trade['timestamp']) <= self.learning_window
                ]
            
            # Clean user performance data
            for user_id in self.user_performance:
                self.user_performance[user_id] = [
                    trade for trade in self.user_performance[user_id]
                    if (current_time - trade['timestamp']) <= self.learning_window
                ]
                
        except Exception as e:
            logger.error(f"Error cleaning old data: {str(e)}") 