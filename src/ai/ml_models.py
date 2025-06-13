"""
Advanced AI/ML Models for Professional Trading System
Production-ready machine learning models for real money trading
"""

import logging
import asyncio
import numpy as np
import pandas as pd
import joblib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import warnings
warnings.filterwarnings('ignore')

# ML Libraries - with graceful fallback
try:
    import sklearn
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingClassifier
    from sklearn.model_selection import train_test_split, GridSearchCV, TimeSeriesSplit
    from sklearn.preprocessing import StandardScaler, RobustScaler
    from sklearn.metrics import mean_squared_error, accuracy_score, precision_recall_fscore_support
    from sklearn.feature_selection import SelectKBest, f_regression
    SKLEARN_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("scikit-learn not available. ML features will be limited.")
    SKLEARN_AVAILABLE = False

# Deep Learning - optional
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential, Model
    from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization, Attention
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

# Technical Analysis
import talib
from scipy import stats
from scipy.signal import find_peaks

# Time Series
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX

logger = logging.getLogger(__name__)

@dataclass
class ModelMetrics:
    """Model performance metrics"""
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    mse: float = 0.0
    mae: float = 0.0
    rmse: float = 0.0
    r2_score: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0

@dataclass
class PredictionResult:
    """Model prediction result"""
    symbol: str
    prediction: float
    confidence: float
    probability: Optional[float] = None
    features: Dict[str, float] = field(default_factory=dict)
    model_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseMLModel(ABC):
    """Base class for all ML models"""
    
    def __init__(self, name: str, model_type: str):
        self.name = name
        self.model_type = model_type
        self.model = None
        self.scaler = None
        self.feature_selector = None
        self.is_trained = False
        self.metrics = ModelMetrics()
        self.feature_names = []
        
    @abstractmethod
    async def train(self, data: pd.DataFrame, target: pd.Series, **kwargs):
        """Train the model"""
        pass
        
    @abstractmethod
    async def predict(self, features: pd.DataFrame) -> List[PredictionResult]:
        """Make predictions"""
        pass
        
    @abstractmethod
    def save_model(self, filepath: str):
        """Save model to file"""
        pass
        
    @abstractmethod
    def load_model(self, filepath: str):
        """Load model from file"""
        pass
    
    def _prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for training/prediction"""
        # Remove any NaN values
        data = data.fillna(method='ffill').fillna(method='bfill')
        
        # Scale features if scaler exists
        if self.scaler is not None:
            scaled_data = self.scaler.transform(data)
            data = pd.DataFrame(scaled_data, columns=data.columns, index=data.index)
        
        # Select features if selector exists
        if self.feature_selector is not None:
            selected_data = self.feature_selector.transform(data)
            data = pd.DataFrame(selected_data, columns=self.feature_names, index=data.index)
            
        return data

class PricePredictionModel(BaseMLModel):
    """Advanced price prediction using ensemble methods"""
    
    def __init__(self, lookback_days: int = 30, prediction_horizon: int = 1):
        super().__init__("PricePrediction", "regression")
        self.lookback_days = lookback_days
        self.prediction_horizon = prediction_horizon
        self.models = {}  # Ensemble of models
        
    async def train(self, data: pd.DataFrame, target: pd.Series, **kwargs):
        """Train ensemble price prediction model"""
        logger.info(f"Training price prediction model with {len(data)} samples")
        
        try:
            # Feature engineering
            features = await self._engineer_features(data)
            
            # Prepare target (future returns)
            target_returns = target.pct_change(self.prediction_horizon).shift(-self.prediction_horizon)
            
            # Remove NaN values
            valid_mask = ~(features.isnull().any(axis=1) | target_returns.isnull())
            features = features[valid_mask]
            target_returns = target_returns[valid_mask]
            
            if len(features) < 100:
                raise ValueError("Insufficient data for training")
            
            # Split data with time series consideration
            split_idx = int(len(features) * 0.8)
            X_train, X_test = features[:split_idx], features[split_idx:]
            y_train, y_test = target_returns[:split_idx], target_returns[split_idx:]
            
            # Feature scaling
            self.scaler = RobustScaler()
            X_train_scaled = pd.DataFrame(
                self.scaler.fit_transform(X_train),
                columns=X_train.columns,
                index=X_train.index
            )
            X_test_scaled = pd.DataFrame(
                self.scaler.transform(X_test),
                columns=X_test.columns,
                index=X_test.index
            )
            
            # Feature selection
            self.feature_selector = SelectKBest(f_regression, k=min(20, len(X_train.columns)))
            X_train_selected = self.feature_selector.fit_transform(X_train_scaled, y_train)
            X_test_selected = self.feature_selector.transform(X_test_scaled)
            
            # Store feature names
            feature_mask = self.feature_selector.get_support()
            self.feature_names = X_train.columns[feature_mask].tolist()
            
            # Train ensemble models
            await self._train_ensemble(X_train_selected, y_train, X_test_selected, y_test)
            
            self.is_trained = True
            logger.info("Price prediction model training completed successfully")
            
        except Exception as e:
            logger.error(f"Error training price prediction model: {e}")
            raise
    
    async def _engineer_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Engineer comprehensive features for price prediction"""
        features = pd.DataFrame(index=data.index)
        
        # Assume data has OHLCV columns
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col not in data.columns:
                logger.warning(f"Missing column {col}, using close price")
                data[col] = data.get('close', data.iloc[:, 0])
        
        prices = data['close'].values
        highs = data['high'].values
        lows = data['low'].values
        volumes = data['volume'].values
        
        # Price-based features
        features['returns_1d'] = data['close'].pct_change(1)
        features['returns_3d'] = data['close'].pct_change(3)
        features['returns_7d'] = data['close'].pct_change(7)
        features['returns_14d'] = data['close'].pct_change(14)
        
        # Moving averages
        for period in [5, 10, 20, 50]:
            features[f'sma_{period}'] = data['close'].rolling(period).mean()
            features[f'ema_{period}'] = data['close'].ewm(span=period).mean()
            features[f'price_sma_ratio_{period}'] = data['close'] / features[f'sma_{period}']
        
        # Technical indicators
        try:
            features['rsi_14'] = talib.RSI(prices, timeperiod=14)
            features['macd'], features['macd_signal'], features['macd_hist'] = talib.MACD(prices)
            features['bb_upper'], features['bb_middle'], features['bb_lower'] = talib.BBANDS(prices)
            features['atr_14'] = talib.ATR(highs, lows, prices, timeperiod=14)
            features['adx_14'] = talib.ADX(highs, lows, prices, timeperiod=14)
            features['cci_14'] = talib.CCI(highs, lows, prices, timeperiod=14)
            features['williams_r'] = talib.WILLR(highs, lows, prices, timeperiod=14)
            features['stoch_k'], features['stoch_d'] = talib.STOCH(highs, lows, prices)
            
            # Volume indicators
            features['obv'] = talib.OBV(prices, volumes)
            features['ad'] = talib.AD(highs, lows, prices, volumes)
            features['mfi'] = talib.MFI(highs, lows, prices, volumes, timeperiod=14)
            
        except Exception as e:
            logger.warning(f"Error calculating technical indicators: {e}")
            # Fill with basic indicators if TA-Lib fails
            features['rsi_14'] = self._simple_rsi(prices, 14)
            features['sma_ratio'] = data['close'] / data['close'].rolling(20).mean()
        
        # Statistical features
        for period in [10, 20, 30]:
            features[f'volatility_{period}'] = data['close'].pct_change().rolling(period).std()
            features[f'skewness_{period}'] = data['close'].pct_change().rolling(period).skew()
            features[f'kurtosis_{period}'] = data['close'].pct_change().rolling(period).kurt()
        
        # Volume features
        features['volume_sma_20'] = data['volume'].rolling(20).mean()
        features['volume_ratio'] = data['volume'] / features['volume_sma_20']
        features['price_volume'] = data['close'] * data['volume']
        
        # Market microstructure
        features['high_low_ratio'] = data['high'] / data['low']
        features['close_open_ratio'] = data['close'] / data['open']
        features['intraday_return'] = (data['close'] - data['open']) / data['open']
        
        # Lag features
        for lag in [1, 2, 3, 5, 10]:
            features[f'close_lag_{lag}'] = data['close'].shift(lag)
            features[f'volume_lag_{lag}'] = data['volume'].shift(lag)
            features[f'returns_lag_{lag}'] = features['returns_1d'].shift(lag)
        
        return features
    
    def _simple_rsi(self, prices: np.ndarray, period: int = 14) -> pd.Series:
        """Simple RSI calculation fallback"""
        delta = pd.Series(prices).diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    async def _train_ensemble(self, X_train, y_train, X_test, y_test):
        """Train ensemble of models"""
        
        # Random Forest
        rf_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        rf_model.fit(X_train, y_train)
        self.models['random_forest'] = rf_model
        
        # Gradient Boosting
        from sklearn.ensemble import GradientBoostingRegressor
        gb_model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=6,
            random_state=42
        )
        gb_model.fit(X_train, y_train)
        self.models['gradient_boosting'] = gb_model
        
        # XGBoost (if available)
        try:
            import xgboost as xgb
            xgb_model = xgb.XGBRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            )
            xgb_model.fit(X_train, y_train)
            self.models['xgboost'] = xgb_model
        except ImportError:
            logger.warning("XGBoost not available, skipping")
        
        # LSTM Neural Network
        await self._train_lstm(X_train, y_train, X_test, y_test)
        
        # Calculate ensemble metrics
        predictions = await self._ensemble_predict(X_test)
        self._calculate_metrics(y_test, predictions)
    
    async def _train_lstm(self, X_train, y_train, X_test, y_test):
        """Train LSTM model for time series prediction"""
        try:
            # Reshape for LSTM (samples, timesteps, features)
            X_train_lstm = X_train.reshape((X_train.shape[0], 1, X_train.shape[1]))
            X_test_lstm = X_test.reshape((X_test.shape[0], 1, X_test.shape[1]))
            
            # Build LSTM model
            model = Sequential([
                LSTM(50, return_sequences=True, input_shape=(1, X_train.shape[1])),
                Dropout(0.2),
                LSTM(50, return_sequences=False),
                Dropout(0.2),
                Dense(25),
                Dense(1)
            ])
            
            model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
            
            # Train with early stopping
            early_stopping = EarlyStopping(monitor='val_loss', patience=10)
            reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.2, patience=5)
            
            history = model.fit(
                X_train_lstm, y_train,
                batch_size=32,
                epochs=100,
                validation_data=(X_test_lstm, y_test),
                callbacks=[early_stopping, reduce_lr],
                verbose=0
            )
            
            self.models['lstm'] = model
            logger.info("LSTM model trained successfully")
            
        except Exception as e:
            logger.warning(f"LSTM training failed: {e}")
    
    async def _ensemble_predict(self, X: np.ndarray) -> np.ndarray:
        """Make ensemble predictions"""
        predictions = []
        weights = []
        
        for name, model in self.models.items():
            try:
                if name == 'lstm':
                    X_lstm = X.reshape((X.shape[0], 1, X.shape[1]))
                    pred = model.predict(X_lstm, verbose=0).flatten()
                else:
                    pred = model.predict(X)
                
                predictions.append(pred)
                weights.append(1.0)  # Equal weights for now
                
            except Exception as e:
                logger.warning(f"Prediction failed for {name}: {e}")
        
        if not predictions:
            return np.zeros(X.shape[0])
        
        # Weighted average ensemble
        weights = np.array(weights) / np.sum(weights)
        ensemble_pred = np.average(predictions, axis=0, weights=weights)
        
        return ensemble_pred
    
    async def predict(self, features: pd.DataFrame) -> List[PredictionResult]:
        """Make price predictions"""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        try:
            # Engineer features
            engineered_features = await self._engineer_features(features)
            
            # Prepare features
            prepared_features = self._prepare_features(engineered_features)
            
            # Make ensemble predictions
            predictions = await self._ensemble_predict(prepared_features.values)
            
            # Calculate confidence based on model agreement
            individual_predictions = []
            for name, model in self.models.items():
                try:
                    if name == 'lstm':
                        X_lstm = prepared_features.values.reshape((prepared_features.shape[0], 1, prepared_features.shape[1]))
                        pred = model.predict(X_lstm, verbose=0).flatten()
                    else:
                        pred = model.predict(prepared_features.values)
                    individual_predictions.append(pred)
                except:
                    continue
            
            results = []
            for i, (idx, row) in enumerate(features.iterrows()):
                # Calculate confidence as inverse of prediction variance
                if individual_predictions:
                    pred_std = np.std([pred[i] for pred in individual_predictions])
                    confidence = max(0.1, 1.0 - min(pred_std, 1.0))
                else:
                    confidence = 0.5
                
                result = PredictionResult(
                    symbol=row.get('symbol', 'UNKNOWN'),
                    prediction=float(predictions[i]),
                    confidence=float(confidence),
                    model_name=self.name,
                    features=dict(row),
                    metadata={
                        'prediction_horizon': self.prediction_horizon,
                        'num_models': len(self.models)
                    }
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error making predictions: {e}")
            raise
    
    def _calculate_metrics(self, y_true, y_pred):
        """Calculate model performance metrics"""
        self.metrics.mse = mean_squared_error(y_true, y_pred)
        self.metrics.rmse = np.sqrt(self.metrics.mse)
        self.metrics.mae = np.mean(np.abs(y_true - y_pred))
        
        # R-squared
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        self.metrics.r2_score = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Direction accuracy
        direction_true = np.sign(y_true)
        direction_pred = np.sign(y_pred)
        self.metrics.accuracy = np.mean(direction_true == direction_pred)
    
    def save_model(self, filepath: str):
        """Save ensemble model"""
        model_data = {
            'models': {},
            'scaler': self.scaler,
            'feature_selector': self.feature_selector,
            'feature_names': self.feature_names,
            'metrics': self.metrics,
            'lookback_days': self.lookback_days,
            'prediction_horizon': self.prediction_horizon
        }
        
        # Save sklearn models
        for name, model in self.models.items():
            if name != 'lstm':
                model_data['models'][name] = model
        
        joblib.dump(model_data, filepath)
        
        # Save LSTM separately
        if 'lstm' in self.models:
            lstm_path = filepath.replace('.pkl', '_lstm.h5')
            self.models['lstm'].save(lstm_path)
        
        logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """Load ensemble model"""
        model_data = joblib.load(filepath)
        
        self.models = model_data['models']
        self.scaler = model_data['scaler']
        self.feature_selector = model_data['feature_selector']
        self.feature_names = model_data['feature_names']
        self.metrics = model_data['metrics']
        self.lookback_days = model_data['lookback_days']
        self.prediction_horizon = model_data['prediction_horizon']
        
        # Load LSTM if exists
        lstm_path = filepath.replace('.pkl', '_lstm.h5')
        try:
            from tensorflow.keras.models import load_model
            self.models['lstm'] = load_model(lstm_path)
        except:
            logger.warning("LSTM model not found or failed to load")
        
        self.is_trained = True
        logger.info(f"Model loaded from {filepath}")

class SentimentAnalysisModel(BaseMLModel):
    """News and social media sentiment analysis"""
    
    def __init__(self):
        super().__init__("SentimentAnalysis", "classification")
        self.vectorizer = None
        
    async def train(self, texts: List[str], sentiments: List[int], **kwargs):
        """Train sentiment analysis model"""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.naive_bayes import MultinomialNB
        from sklearn.pipeline import Pipeline
        
        # Create pipeline
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=5000, stop_words='english')),
            ('classifier', MultinomialNB())
        ])
        
        # Train model
        self.model.fit(texts, sentiments)
        self.is_trained = True
        
        logger.info("Sentiment analysis model trained successfully")
    
    async def predict(self, texts: List[str]) -> List[PredictionResult]:
        """Predict sentiment"""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        predictions = self.model.predict(texts)
        probabilities = self.model.predict_proba(texts)
        
        results = []
        for i, text in enumerate(texts):
            confidence = float(np.max(probabilities[i]))
            
            result = PredictionResult(
                symbol="SENTIMENT",
                prediction=float(predictions[i]),
                confidence=confidence,
                probability=confidence,
                model_name=self.name,
                metadata={'text': text[:100]}  # First 100 chars
            )
            results.append(result)
        
        return results
    
    def save_model(self, filepath: str):
        """Save sentiment model"""
        joblib.dump(self.model, filepath)
    
    def load_model(self, filepath: str):
        """Load sentiment model"""
        self.model = joblib.load(filepath)
        self.is_trained = True

class RiskAssessmentModel(BaseMLModel):
    """Advanced risk assessment and anomaly detection"""
    
    def __init__(self):
        super().__init__("RiskAssessment", "classification")
        self.anomaly_detector = None
        
    async def train(self, market_data: pd.DataFrame, risk_labels: pd.Series, **kwargs):
        """Train risk assessment model"""
        from sklearn.ensemble import IsolationForest
        from sklearn.svm import OneClassSVM
        
        # Feature engineering for risk
        risk_features = await self._engineer_risk_features(market_data)
        
        # Train classification model for risk levels
        self.model = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=6,
            random_state=42
        )
        
        # Prepare features
        self.scaler = StandardScaler()
        scaled_features = self.scaler.fit_transform(risk_features)
        
        # Train model
        self.model.fit(scaled_features, risk_labels)
        
        # Train anomaly detector
        self.anomaly_detector = IsolationForest(
            contamination=0.1,
            random_state=42
        )
        self.anomaly_detector.fit(scaled_features)
        
        self.is_trained = True
        logger.info("Risk assessment model trained successfully")
    
    async def _engineer_risk_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Engineer risk-specific features"""
        features = pd.DataFrame(index=data.index)
        
        # Volatility features
        returns = data['close'].pct_change()
        features['volatility_1d'] = returns.rolling(1).std()
        features['volatility_7d'] = returns.rolling(7).std()
        features['volatility_30d'] = returns.rolling(30).std()
        
        # VaR features
        features['var_95'] = returns.rolling(30).quantile(0.05)
        features['var_99'] = returns.rolling(30).quantile(0.01)
        
        # Extreme price movements
        features['price_shock'] = np.abs(returns) > (returns.rolling(30).std() * 3)
        features['gap_up'] = (data['open'] - data['close'].shift(1)) / data['close'].shift(1)
        features['gap_down'] = features['gap_up'] * -1
        
        # Market stress indicators
        features['high_low_ratio'] = data['high'] / data['low']
        features['volume_surge'] = data['volume'] / data['volume'].rolling(20).mean()
        
        return features.fillna(0)
    
    async def predict(self, features: pd.DataFrame) -> List[PredictionResult]:
        """Assess risk levels and detect anomalies"""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Engineer risk features
        risk_features = await self._engineer_risk_features(features)
        
        # Scale features
        scaled_features = self.scaler.transform(risk_features)
        
        # Risk classification
        risk_predictions = self.model.predict(scaled_features)
        risk_probabilities = self.model.predict_proba(scaled_features)
        
        # Anomaly detection
        anomaly_scores = self.anomaly_detector.decision_function(scaled_features)
        is_anomaly = self.anomaly_detector.predict(scaled_features) == -1
        
        results = []
        for i, (idx, row) in enumerate(features.iterrows()):
            risk_level = int(risk_predictions[i])
            confidence = float(np.max(risk_probabilities[i]))
            anomaly_score = float(anomaly_scores[i])
            
            result = PredictionResult(
                symbol=row.get('symbol', 'UNKNOWN'),
                prediction=risk_level,
                confidence=confidence,
                model_name=self.name,
                metadata={
                    'anomaly_score': anomaly_score,
                    'is_anomaly': bool(is_anomaly[i]),
                    'risk_level': ['low', 'medium', 'high'][risk_level] if 0 <= risk_level <= 2 else 'unknown'
                }
            )
            results.append(result)
        
        return results
    
    def save_model(self, filepath: str):
        """Save risk model"""
        model_data = {
            'model': self.model,
            'anomaly_detector': self.anomaly_detector,
            'scaler': self.scaler
        }
        joblib.dump(model_data, filepath)
    
    def load_model(self, filepath: str):
        """Load risk model"""
        model_data = joblib.load(filepath)
        self.model = model_data['model']
        self.anomaly_detector = model_data['anomaly_detector']
        self.scaler = model_data['scaler']
        self.is_trained = True

class PortfolioOptimizationModel(BaseMLModel):
    """Modern Portfolio Theory with AI enhancements"""
    
    def __init__(self):
        super().__init__("PortfolioOptimization", "optimization")
        self.expected_returns = None
        self.covariance_matrix = None
        self.risk_aversion = 3.0
        
    async def train(self, returns_data: pd.DataFrame, **kwargs):
        """Train portfolio optimization model"""
        # Calculate expected returns using multiple methods
        self.expected_returns = await self._calculate_expected_returns(returns_data)
        
        # Calculate covariance matrix with shrinkage
        self.covariance_matrix = await self._calculate_covariance_matrix(returns_data)
        
        self.is_trained = True
        logger.info("Portfolio optimization model trained successfully")
    
    async def _calculate_expected_returns(self, returns_data: pd.DataFrame) -> pd.Series:
        """Calculate expected returns using ensemble of methods"""
        methods = {}
        
        # Historical mean
        methods['historical'] = returns_data.mean()
        
        # Exponentially weighted average
        methods['ewm'] = returns_data.ewm(span=30).mean().iloc[-1]
        
        # CAPM-based (if market data available)
        if 'market_return' in returns_data.columns:
            market_return = returns_data['market_return']
            betas = returns_data.corrwith(market_return) / market_return.var()
            risk_free_rate = 0.02 / 252  # Assume 2% annual risk-free rate
            methods['capm'] = risk_free_rate + betas * (market_return.mean() - risk_free_rate)
        
        # Ensemble of methods
        expected_returns = pd.DataFrame(methods).mean(axis=1)
        return expected_returns
    
    async def _calculate_covariance_matrix(self, returns_data: pd.DataFrame) -> pd.DataFrame:
        """Calculate covariance matrix with shrinkage"""
        from sklearn.covariance import LedoitWolf
        
        # Use Ledoit-Wolf shrinkage
        lw = LedoitWolf()
        lw.fit(returns_data.dropna())
        
        return pd.DataFrame(
            lw.covariance_,
            index=returns_data.columns,
            columns=returns_data.columns
        )
    
    async def predict(self, constraints: Dict = None) -> List[PredictionResult]:
        """Optimize portfolio allocation"""
        if not self.is_trained:
            raise ValueError("Model must be trained before optimization")
        
        from scipy.optimize import minimize
        
        n_assets = len(self.expected_returns)
        
        # Objective function (negative Sharpe ratio)
        def objective(weights):
            portfolio_return = np.dot(weights, self.expected_returns)
            portfolio_variance = np.dot(weights.T, np.dot(self.covariance_matrix, weights))
            portfolio_std = np.sqrt(portfolio_variance)
            sharpe_ratio = portfolio_return / portfolio_std if portfolio_std > 0 else 0
            return -sharpe_ratio
        
        # Constraints
        constraints_list = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]  # Weights sum to 1
        
        if constraints:
            # Add custom constraints
            for constraint in constraints.get('custom', []):
                constraints_list.append(constraint)
        
        # Bounds (no short selling by default)
        bounds = [(0, 1) for _ in range(n_assets)]
        
        # Initial guess (equal weights)
        x0 = np.array([1/n_assets] * n_assets)
        
        # Optimize
        result = minimize(
            objective,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints_list
        )
        
        optimal_weights = result.x
        
        # Calculate portfolio metrics
        portfolio_return = np.dot(optimal_weights, self.expected_returns)
        portfolio_variance = np.dot(optimal_weights.T, np.dot(self.covariance_matrix, optimal_weights))
        portfolio_std = np.sqrt(portfolio_variance)
        sharpe_ratio = portfolio_return / portfolio_std if portfolio_std > 0 else 0
        
        # Create results
        results = []
        for i, (asset, weight) in enumerate(zip(self.expected_returns.index, optimal_weights)):
            result = PredictionResult(
                symbol=asset,
                prediction=float(weight),
                confidence=0.8,  # Portfolio optimization confidence
                model_name=self.name,
                metadata={
                    'expected_return': float(self.expected_returns.iloc[i]),
                    'portfolio_return': float(portfolio_return),
                    'portfolio_volatility': float(portfolio_std),
                    'sharpe_ratio': float(sharpe_ratio)
                }
            )
            results.append(result)
        
        return results
    
    def save_model(self, filepath: str):
        """Save portfolio model"""
        model_data = {
            'expected_returns': self.expected_returns,
            'covariance_matrix': self.covariance_matrix,
            'risk_aversion': self.risk_aversion
        }
        joblib.dump(model_data, filepath)
    
    def load_model(self, filepath: str):
        """Load portfolio model"""
        model_data = joblib.load(filepath)
        self.expected_returns = model_data['expected_returns']
        self.covariance_matrix = model_data['covariance_matrix']
        self.risk_aversion = model_data['risk_aversion']
        self.is_trained = True

class MLModelManager:
    """Manage all ML models and their lifecycle"""
    
    def __init__(self):
        self.models = {}
        self.model_registry = {}
        self.training_scheduler = None
        
    async def initialize_models(self):
        """Initialize all ML models"""
        self.models = {
            'price_prediction': PricePredictionModel(),
            'sentiment_analysis': SentimentAnalysisModel(),
            'risk_assessment': RiskAssessmentModel(),
            'portfolio_optimization': PortfolioOptimizationModel()
        }
        
        logger.info("ML models initialized successfully")
    
    async def train_all_models(self, training_data: Dict[str, Any]):
        """Train all models with provided data"""
        tasks = []
        
        for name, model in self.models.items():
            if name in training_data:
                data = training_data[name]
                tasks.append(self._train_single_model(name, model, data))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log results
        for i, (name, result) in enumerate(zip(self.models.keys(), results)):
            if isinstance(result, Exception):
                logger.error(f"Training failed for {name}: {result}")
            else:
                logger.info(f"Training completed for {name}")
    
    async def _train_single_model(self, name: str, model: BaseMLModel, data: Dict):
        """Train a single model"""
        try:
            if name == 'price_prediction':
                await model.train(data['features'], data['target'])
            elif name == 'sentiment_analysis':
                await model.train(data['texts'], data['sentiments'])
            elif name == 'risk_assessment':
                await model.train(data['market_data'], data['risk_labels'])
            elif name == 'portfolio_optimization':
                await model.train(data['returns_data'])
            
            # Save trained model
            model_path = f"models/{name}_model.pkl"
            model.save_model(model_path)
            
            # Register model
            self.model_registry[name] = {
                'path': model_path,
                'trained_at': datetime.now(),
                'metrics': model.metrics,
                'version': '1.0'
            }
            
        except Exception as e:
            logger.error(f"Error training {name}: {e}")
            raise
    
    async def predict_all(self, input_data: Dict[str, Any]) -> Dict[str, List[PredictionResult]]:
        """Get predictions from all models"""
        predictions = {}
        
        for name, model in self.models.items():
            try:
                if name in input_data and model.is_trained:
                    predictions[name] = await model.predict(input_data[name])
            except Exception as e:
                logger.error(f"Prediction failed for {name}: {e}")
                predictions[name] = []
        
        return predictions
    
    async def load_models(self, model_dir: str = "models"):
        """Load all trained models"""
        import os
        from pathlib import Path
        
        model_dir = Path(model_dir)
        
        for name, model in self.models.items():
            model_path = model_dir / f"{name}_model.pkl"
            if model_path.exists():
                try:
                    model.load_model(str(model_path))
                    logger.info(f"Loaded model: {name}")
                except Exception as e:
                    logger.error(f"Failed to load {name}: {e}")
    
    def get_model_status(self) -> Dict[str, Dict]:
        """Get status of all models"""
        status = {}
        
        for name, model in self.models.items():
            status[name] = {
                'is_trained': model.is_trained,
                'model_type': model.model_type,
                'metrics': model.metrics.__dict__ if hasattr(model, 'metrics') else {},
                'registry_info': self.model_registry.get(name, {})
            }
        
        return status

# Global model manager instance
ml_manager = MLModelManager() 