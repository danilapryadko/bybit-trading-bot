"""
Machine Learning Price Prediction Engine
Uses multiple models for price prediction and signal generation
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
import joblib
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class PricePredictor:
    """Advanced ML-based price prediction system"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.models = {}
        self.scalers = {}
        self.feature_importance = {}
        self.prediction_history = []
        
        # Model parameters
        self.lookback_period = self.config.get('lookback_period', 100)
        self.prediction_horizon = self.config.get('prediction_horizon', 24)  # hours
        self.min_accuracy = self.config.get('min_accuracy', 0.65)
        
        # Initialize models
        self._initialize_models()
        
    def _initialize_models(self):
        """Initialize ML models"""
        # Random Forest for robust predictions
        self.models['rf'] = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42
        )
        
        # Gradient Boosting for accuracy
        self.models['gb'] = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        
        # Initialize scalers
        self.scalers['features'] = StandardScaler()
        self.scalers['target'] = StandardScaler()
        
    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract features from price data
        
        Features include:
        - Technical indicators
        - Price patterns
        - Volume metrics
        - Market microstructure
        """
        features = pd.DataFrame(index=df.index)
        
        # Price features
        features['returns'] = df['close'].pct_change()
        features['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        features['price_range'] = (df['high'] - df['low']) / df['close']
        features['close_to_high'] = (df['high'] - df['close']) / df['high']
        features['close_to_low'] = (df['close'] - df['low']) / df['low']
        
        # Moving averages
        for period in [5, 10, 20, 50]:
            features[f'sma_{period}'] = df['close'].rolling(period).mean()
            features[f'sma_ratio_{period}'] = df['close'] / features[f'sma_{period}']
            
        # Exponential moving averages
        for period in [12, 26]:
            features[f'ema_{period}'] = df['close'].ewm(span=period).mean()
            
        # MACD
        features['macd'] = features['ema_12'] - features['ema_26']
        features['macd_signal'] = features['macd'].ewm(span=9).mean()
        features['macd_hist'] = features['macd'] - features['macd_signal']
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        features['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        bb_period = 20
        bb_std = 2
        sma = df['close'].rolling(bb_period).mean()
        std = df['close'].rolling(bb_period).std()
        features['bb_upper'] = sma + (bb_std * std)
        features['bb_lower'] = sma - (bb_std * std)
        features['bb_width'] = features['bb_upper'] - features['bb_lower']
        features['bb_position'] = (df['close'] - features['bb_lower']) / features['bb_width']
        
        # Volume features
        features['volume_sma'] = df['volume'].rolling(20).mean()
        features['volume_ratio'] = df['volume'] / features['volume_sma']
        features['price_volume'] = df['close'] * df['volume']
        
        # Volatility
        features['volatility'] = df['close'].pct_change().rolling(20).std()
        features['atr'] = self._calculate_atr(df, 14)
        
        # Market microstructure
        features['spread'] = df['high'] - df['low']
        features['mid_price'] = (df['high'] + df['low']) / 2
        features['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        
        # Lag features
        for lag in [1, 2, 3, 5, 10]:
            features[f'returns_lag_{lag}'] = features['returns'].shift(lag)
            features[f'volume_lag_{lag}'] = features['volume_ratio'].shift(lag)
            
        # Time features
        features['hour'] = df.index.hour
        features['day_of_week'] = df.index.dayofweek
        features['month'] = df.index.month
        
        # Trend features
        features['trend_strength'] = self._calculate_trend_strength(df['close'], 20)
        features['support_distance'] = self._calculate_support_resistance(df, 'support')
        features['resistance_distance'] = self._calculate_support_resistance(df, 'resistance')
        
        # Drop NaN values
        features = features.dropna()
        
        return features
    
    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(period).mean()
        
        return atr
    
    def _calculate_trend_strength(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate trend strength using linear regression slope"""
        def calculate_slope(x):
            if len(x) < 2:
                return 0
            indices = np.arange(len(x))
            slope = np.polyfit(indices, x, 1)[0]
            return slope / x.mean() if x.mean() != 0 else 0
        
        return prices.rolling(period).apply(calculate_slope)
    
    def _calculate_support_resistance(self, df: pd.DataFrame, level_type: str) -> pd.Series:
        """Calculate distance to support/resistance levels"""
        period = 20
        
        if level_type == 'support':
            levels = df['low'].rolling(period).min()
        else:
            levels = df['high'].rolling(period).max()
        
        distance = (df['close'] - levels) / df['close']
        return distance
    
    def prepare_training_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare data for model training"""
        # Extract features
        features = self.extract_features(df)
        
        # Create target variable (future price change)
        target_shift = 1  # Predict next period
        target = df['close'].pct_change().shift(-target_shift)
        
        # Align features and target
        common_index = features.index.intersection(target.index)
        features = features.loc[common_index]
        target = target.loc[common_index]
        
        # Remove last row (no target)
        features = features[:-target_shift]
        target = target[:-target_shift]
        
        return features.values, target.values
    
    def train(self, df: pd.DataFrame, model_type: str = 'ensemble'):
        """
        Train prediction models
        
        Args:
            df: DataFrame with OHLCV data
            model_type: 'rf', 'gb', or 'ensemble'
        """
        logger.info(f"Training {model_type} model with {len(df)} samples")
        
        # Prepare data
        X, y = self.prepare_training_data(df)
        
        # Remove NaN and infinite values
        mask = np.isfinite(X).all(axis=1) & np.isfinite(y)
        X = X[mask]
        y = y[mask]
        
        if len(X) < 100:
            logger.warning("Insufficient data for training")
            return
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )
        
        # Scale features
        X_train_scaled = self.scalers['features'].fit_transform(X_train)
        X_test_scaled = self.scalers['features'].transform(X_test)
        
        # Train models
        if model_type in ['rf', 'ensemble']:
            self.models['rf'].fit(X_train_scaled, y_train)
            rf_score = self.models['rf'].score(X_test_scaled, y_test)
            logger.info(f"Random Forest R² Score: {rf_score:.4f}")
            
            # Feature importance
            self.feature_importance['rf'] = self.models['rf'].feature_importances_
            
        if model_type in ['gb', 'ensemble']:
            self.models['gb'].fit(X_train_scaled, y_train)
            gb_score = self.models['gb'].score(X_test_scaled, y_test)
            logger.info(f"Gradient Boosting R² Score: {gb_score:.4f}")
            
            # Feature importance
            self.feature_importance['gb'] = self.models['gb'].feature_importances_
    
    def predict(self, df: pd.DataFrame, confidence_threshold: float = 0.6) -> Dict[str, Any]:
        """
        Make price predictions
        
        Returns:
            Dictionary with predictions and metadata
        """
        try:
            # Extract features
            features = self.extract_features(df)
            
            if len(features) == 0:
                return self._empty_prediction()
            
            # Get latest features
            latest_features = features.iloc[-1:].values
            
            # Scale features
            latest_features_scaled = self.scalers['features'].transform(latest_features)
            
            # Make predictions
            predictions = {}
            
            if 'rf' in self.models:
                rf_pred = self.models['rf'].predict(latest_features_scaled)[0]
                predictions['rf'] = rf_pred
                
            if 'gb' in self.models:
                gb_pred = self.models['gb'].predict(latest_features_scaled)[0]
                predictions['gb'] = gb_pred
            
            # Ensemble prediction
            if len(predictions) > 0:
                ensemble_pred = np.mean(list(predictions.values()))
                prediction_std = np.std(list(predictions.values()))
            else:
                return self._empty_prediction()
            
            # Calculate confidence
            confidence = self._calculate_confidence(prediction_std, ensemble_pred)
            
            # Generate signal
            signal = self._generate_signal(ensemble_pred, confidence, confidence_threshold)
            
            # Store prediction
            prediction_data = {
                'timestamp': datetime.now(),
                'prediction': ensemble_pred,
                'confidence': confidence,
                'signal': signal,
                'models': predictions,
                'current_price': df['close'].iloc[-1],
                'predicted_change': ensemble_pred,
                'predicted_price': df['close'].iloc[-1] * (1 + ensemble_pred),
                'horizon': self.prediction_horizon,
                'features': self._get_top_features(latest_features[0])
            }
            
            self.prediction_history.append(prediction_data)
            
            return prediction_data
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return self._empty_prediction()
    
    def _calculate_confidence(self, std: float, prediction: float) -> float:
        """Calculate prediction confidence"""
        # Base confidence on prediction consistency
        base_confidence = max(0, 1 - (std / (abs(prediction) + 0.001)))
        
        # Adjust for prediction magnitude
        magnitude_factor = min(1, abs(prediction) * 100)
        
        confidence = base_confidence * magnitude_factor
        return min(1, max(0, confidence))
    
    def _generate_signal(self, prediction: float, confidence: float, threshold: float) -> str:
        """Generate trading signal from prediction"""
        if confidence < threshold:
            return 'HOLD'
        
        if prediction > 0.002:  # 0.2% threshold
            return 'BUY'
        elif prediction < -0.002:
            return 'SELL'
        else:
            return 'HOLD'
    
    def _get_top_features(self, features: np.ndarray) -> Dict[str, float]:
        """Get top contributing features"""
        if 'rf' not in self.feature_importance:
            return {}
        
        importance = self.feature_importance['rf']
        top_indices = np.argsort(importance)[-5:][::-1]
        
        # Feature names (simplified)
        feature_names = [f'feature_{i}' for i in range(len(features))]
        
        top_features = {
            feature_names[i]: float(features[i]) 
            for i in top_indices
        }
        
        return top_features
    
    def _empty_prediction(self) -> Dict[str, Any]:
        """Return empty prediction structure"""
        return {
            'timestamp': datetime.now(),
            'prediction': 0,
            'confidence': 0,
            'signal': 'HOLD',
            'models': {},
            'current_price': 0,
            'predicted_change': 0,
            'predicted_price': 0,
            'horizon': self.prediction_horizon,
            'features': {}
        }
    
    def evaluate_predictions(self, lookback_hours: int = 24) -> Dict[str, Any]:
        """Evaluate prediction accuracy"""
        if len(self.prediction_history) < 2:
            return {'mae': 0, 'direction_accuracy': 0, 'r2_score': 0, 'total_predictions': 0, 'evaluation_period': lookback_hours}
        
        cutoff = datetime.now() - timedelta(hours=lookback_hours)
        recent_predictions = [
            p for p in self.prediction_history 
            if p['timestamp'] > cutoff
        ]
        
        if len(recent_predictions) < 2:
            return {'mae': 0, 'direction_accuracy': 0, 'r2_score': 0, 'total_predictions': 0, 'evaluation_period': lookback_hours}
        
        # Calculate metrics
        errors = []
        direction_correct = 0
        actual_values = []
        predicted_values = []
        
        for i in range(len(recent_predictions) - 1):
            pred = recent_predictions[i]
            actual = recent_predictions[i + 1]
            
            # Price change
            actual_change = (actual['current_price'] - pred['current_price']) / pred['current_price']
            predicted_change = pred['predicted_change']
            
            actual_values.append(actual_change)
            predicted_values.append(predicted_change)
            
            # Error
            error = abs(actual_change - predicted_change)
            errors.append(error)
            
            # Direction accuracy
            if (actual_change > 0 and predicted_change > 0) or \
               (actual_change < 0 and predicted_change < 0):
                direction_correct += 1
        
        mae = np.mean(errors) if errors else 0
        direction_accuracy = direction_correct / len(errors) if errors else 0
        
        # Calculate R² properly
        r2 = 0
        if len(actual_values) > 1:
            actual_mean = np.mean(actual_values)
            ss_tot = sum((y - actual_mean)**2 for y in actual_values)
            ss_res = sum((y - pred)**2 for y, pred in zip(actual_values, predicted_values))
            if ss_tot > 0:
                r2 = 1 - (ss_res / ss_tot)
                r2 = max(-1, min(1, r2))  # Bound between -1 and 1
        
        return {
            'mae': float(mae),
            'direction_accuracy': float(direction_accuracy),
            'r2_score': float(r2),
            'total_predictions': len(recent_predictions),
            'evaluation_period': lookback_hours
        }
    
    def save_models(self, path: str):
        """Save trained models"""
        for name, model in self.models.items():
            joblib.dump(model, f"{path}/model_{name}.pkl")
        
        for name, scaler in self.scalers.items():
            joblib.dump(scaler, f"{path}/scaler_{name}.pkl")
        
        logger.info(f"Models saved to {path}")
    
    def load_models(self, path: str):
        """Load trained models"""
        import os
        
        for name in ['rf', 'gb']:
            model_path = f"{path}/model_{name}.pkl"
            if os.path.exists(model_path):
                self.models[name] = joblib.load(model_path)
                logger.info(f"Loaded {name} model")
        
        for name in ['features', 'target']:
            scaler_path = f"{path}/scaler_{name}.pkl"
            if os.path.exists(scaler_path):
                self.scalers[name] = joblib.load(scaler_path)
                logger.info(f"Loaded {name} scaler")