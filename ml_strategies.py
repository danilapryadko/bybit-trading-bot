"""
Machine Learning Trading Strategies for Bybit Trading Bot
LSTM, Random Forest, XGBoost and ensemble models
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
import pickle
import joblib
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

# TensorFlow imports
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, models, optimizers, callbacks
    from tensorflow.keras.models import Sequential, Model
    from tensorflow.keras.layers import LSTM, GRU, Dense, Dropout, Input, Conv1D, MaxPooling1D, Flatten
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    logger.warning("TensorFlow not available. LSTM models will be disabled.")


@dataclass
class MLConfig:
    """Machine Learning configuration"""
    model_type: str = "ensemble"  # lstm, random_forest, xgboost, ensemble
    lookback_period: int = 60  # Number of historical periods for features
    prediction_horizon: int = 5  # How many periods ahead to predict
    feature_engineering: bool = True
    use_technical_indicators: bool = True
    use_market_microstructure: bool = True
    use_sentiment: bool = False
    training_split: float = 0.8
    validation_split: float = 0.1
    batch_size: int = 32
    epochs: int = 100
    learning_rate: float = 0.001
    early_stopping_patience: int = 10
    model_save_path: str = "models/"
    retrain_frequency: int = 24  # Hours between retraining
    min_confidence: float = 0.6  # Minimum confidence for trading
    ensemble_weights: Dict[str, float] = field(default_factory=lambda: {
        "lstm": 0.4,
        "random_forest": 0.3,
        "xgboost": 0.3
    })


class FeatureEngineer:
    """Feature engineering for ML models"""
    
    def __init__(self, config: MLConfig):
        self.config = config
        self.scaler = StandardScaler()
        self.feature_names = []
        
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create features from raw price data"""
        features = pd.DataFrame(index=df.index)
        
        # Price-based features
        features['returns'] = df['close'].pct_change()
        features['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        features['price_range'] = (df['high'] - df['low']) / df['close']
        features['close_to_high'] = (df['high'] - df['close']) / df['high']
        features['close_to_low'] = (df['close'] - df['low']) / df['low']
        
        # Volume features
        features['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        features['volume_change'] = df['volume'].pct_change()
        features['price_volume'] = df['close'] * df['volume']
        
        # Rolling statistics
        for window in [5, 10, 20, 50]:
            features[f'sma_{window}'] = df['close'].rolling(window).mean()
            features[f'std_{window}'] = df['close'].rolling(window).std()
            features[f'return_mean_{window}'] = features['returns'].rolling(window).mean()
            features[f'return_std_{window}'] = features['returns'].rolling(window).std()
            features[f'volume_mean_{window}'] = df['volume'].rolling(window).mean()
        
        # Technical indicators (if enabled)
        if self.config.use_technical_indicators:
            features = self._add_technical_indicators(features, df)
        
        # Market microstructure features
        if self.config.use_market_microstructure:
            features = self._add_microstructure_features(features, df)
        
        # Lag features
        for lag in range(1, self.config.lookback_period):
            features[f'returns_lag_{lag}'] = features['returns'].shift(lag)
            if lag <= 10:
                features[f'volume_lag_{lag}'] = features['volume_ratio'].shift(lag)
        
        # Time-based features
        features['hour'] = df.index.hour
        features['day_of_week'] = df.index.dayofweek
        features['month'] = df.index.month
        
        # Clean up NaN values
        features = features.fillna(method='ffill').fillna(0)
        
        self.feature_names = features.columns.tolist()
        
        return features
    
    def _add_technical_indicators(self, features: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators as features"""
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        features['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        features['macd'] = ema12 - ema26
        features['macd_signal'] = features['macd'].ewm(span=9).mean()
        features['macd_histogram'] = features['macd'] - features['macd_signal']
        
        # Bollinger Bands
        sma20 = df['close'].rolling(20).mean()
        std20 = df['close'].rolling(20).std()
        features['bb_upper'] = sma20 + (std20 * 2)
        features['bb_lower'] = sma20 - (std20 * 2)
        features['bb_width'] = features['bb_upper'] - features['bb_lower']
        features['bb_position'] = (df['close'] - features['bb_lower']) / features['bb_width']
        
        # Stochastic Oscillator
        low14 = df['low'].rolling(14).min()
        high14 = df['high'].rolling(14).max()
        features['stochastic_k'] = 100 * ((df['close'] - low14) / (high14 - low14))
        features['stochastic_d'] = features['stochastic_k'].rolling(3).mean()
        
        # ATR (Average True Range)
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        features['atr'] = true_range.rolling(14).mean()
        
        # OBV (On-Balance Volume)
        obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        features['obv'] = obv
        features['obv_ema'] = obv.ewm(span=20).mean()
        
        return features
    
    def _add_microstructure_features(self, features: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
        """Add market microstructure features"""
        
        # Amihud illiquidity measure
        features['illiquidity'] = abs(features['returns']) / (df['volume'] * df['close'])
        features['illiquidity_ma'] = features['illiquidity'].rolling(20).mean()
        
        # Roll measure (bid-ask spread proxy)
        price_diff = df['close'].diff()
        features['roll_measure'] = 2 * np.sqrt(abs(price_diff.cov(price_diff.shift())))
        
        # Kyle's lambda (price impact)
        features['kyle_lambda'] = abs(features['returns']) / np.sqrt(df['volume'])
        
        # VPIN (Volume-Synchronized Probability of Informed Trading)
        # Simplified version
        buy_volume = df['volume'] * (df['close'] > df['open']).astype(int)
        sell_volume = df['volume'] * (df['close'] <= df['open']).astype(int)
        features['order_imbalance'] = (buy_volume - sell_volume) / (buy_volume + sell_volume)
        features['vpin'] = features['order_imbalance'].rolling(50).std()
        
        # Realized volatility
        features['realized_vol_5m'] = features['returns'].rolling(5).std() * np.sqrt(252 * 24 * 12)
        features['realized_vol_1h'] = features['returns'].rolling(60).std() * np.sqrt(252 * 24)
        
        return features
    
    def create_sequences(self, features: pd.DataFrame, target: pd.Series) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM training"""
        X, y = [], []
        
        for i in range(self.config.lookback_period, len(features) - self.config.prediction_horizon):
            X.append(features.iloc[i-self.config.lookback_period:i].values)
            y.append(target.iloc[i+self.config.prediction_horizon])
        
        return np.array(X), np.array(y)
    
    def prepare_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare data for ML models"""
        # Create features
        features = self.create_features(df)
        
        # Create target variable (future price direction)
        future_returns = df['close'].pct_change(self.config.prediction_horizon).shift(-self.config.prediction_horizon)
        target = (future_returns > 0).astype(int)  # Binary classification: 1 for up, 0 for down
        
        # Alternative targets
        # target = future_returns  # Regression
        # target = pd.qcut(future_returns, q=3, labels=[0, 1, 2])  # Multi-class
        
        return features, target


class LSTMModel:
    """LSTM model for price prediction"""
    
    def __init__(self, config: MLConfig):
        self.config = config
        self.model = None
        self.scaler_X = MinMaxScaler()
        self.scaler_y = MinMaxScaler()
        self.history = None
        
        if not TF_AVAILABLE:
            raise ImportError("TensorFlow is required for LSTM models")
    
    def build_model(self, input_shape: Tuple[int, int]):
        """Build LSTM model architecture"""
        model = Sequential([
            LSTM(128, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(64, return_sequences=True),
            Dropout(0.2),
            LSTM(32, return_sequences=False),
            Dropout(0.2),
            Dense(16, activation='relu'),
            Dense(1, activation='sigmoid')  # Binary classification
        ])
        
        model.compile(
            optimizer=optimizers.Adam(learning_rate=self.config.learning_rate),
            loss='binary_crossentropy',
            metrics=['accuracy', 'AUC']
        )
        
        self.model = model
        return model
    
    def build_advanced_model(self, input_shape: Tuple[int, int]):
        """Build advanced LSTM with attention mechanism"""
        inputs = Input(shape=input_shape)
        
        # CNN for feature extraction
        conv1 = Conv1D(filters=64, kernel_size=3, activation='relu')(inputs)
        conv1 = MaxPooling1D(pool_size=2)(conv1)
        
        # Bidirectional LSTM
        lstm1 = layers.Bidirectional(LSTM(128, return_sequences=True))(conv1)
        lstm1 = Dropout(0.2)(lstm1)
        
        # Attention mechanism
        attention = layers.MultiHeadAttention(num_heads=4, key_dim=32)(lstm1, lstm1)
        attention = layers.GlobalAveragePooling1D()(attention)
        
        # Dense layers
        dense1 = Dense(64, activation='relu')(attention)
        dense1 = Dropout(0.3)(dense1)
        dense2 = Dense(32, activation='relu')(dense1)
        outputs = Dense(1, activation='sigmoid')(dense2)
        
        model = Model(inputs=inputs, outputs=outputs)
        
        model.compile(
            optimizer=optimizers.Adam(learning_rate=self.config.learning_rate),
            loss='binary_crossentropy',
            metrics=['accuracy', 'AUC']
        )
        
        self.model = model
        return model
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray, X_val: np.ndarray, y_val: np.ndarray):
        """Train LSTM model"""
        # Scale data
        X_train_scaled = self.scaler_X.fit_transform(X_train.reshape(-1, X_train.shape[-1])).reshape(X_train.shape)
        X_val_scaled = self.scaler_X.transform(X_val.reshape(-1, X_val.shape[-1])).reshape(X_val.shape)
        
        # Callbacks
        early_stop = EarlyStopping(
            monitor='val_loss',
            patience=self.config.early_stopping_patience,
            restore_best_weights=True
        )
        
        reduce_lr = ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=0.00001
        )
        
        checkpoint = ModelCheckpoint(
            f"{self.config.model_save_path}lstm_best.h5",
            monitor='val_accuracy',
            save_best_only=True
        )
        
        # Train model
        self.history = self.model.fit(
            X_train_scaled, y_train,
            validation_data=(X_val_scaled, y_val),
            epochs=self.config.epochs,
            batch_size=self.config.batch_size,
            callbacks=[early_stop, reduce_lr, checkpoint],
            verbose=1
        )
        
        return self.history
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions"""
        X_scaled = self.scaler_X.transform(X.reshape(-1, X.shape[-1])).reshape(X.shape)
        predictions = self.model.predict(X_scaled)
        return predictions
    
    def save(self, path: str):
        """Save model"""
        self.model.save(f"{path}_model.h5")
        joblib.dump(self.scaler_X, f"{path}_scaler_X.pkl")
        joblib.dump(self.scaler_y, f"{path}_scaler_y.pkl")
    
    def load(self, path: str):
        """Load model"""
        self.model = keras.models.load_model(f"{path}_model.h5")
        self.scaler_X = joblib.load(f"{path}_scaler_X.pkl")
        self.scaler_y = joblib.load(f"{path}_scaler_y.pkl")


class RandomForestModel:
    """Random Forest model for trading signals"""
    
    def __init__(self, config: MLConfig):
        self.config = config
        self.model = None
        self.scaler = StandardScaler()
        self.feature_importance = None
    
    def build_model(self):
        """Build Random Forest model"""
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            max_features='sqrt',
            random_state=42,
            n_jobs=-1
        )
        return self.model
    
    def train(self, X_train: pd.DataFrame, y_train: pd.Series, X_val: pd.DataFrame, y_val: pd.Series):
        """Train Random Forest model"""
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        
        # Train model
        self.model.fit(X_train_scaled, y_train)
        
        # Get feature importance
        self.feature_importance = pd.DataFrame({
            'feature': X_train.columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        # Evaluate
        train_score = self.model.score(X_train_scaled, y_train)
        val_score = self.model.score(X_val_scaled, y_val)
        
        logger.info(f"Random Forest - Train accuracy: {train_score:.4f}, Val accuracy: {val_score:.4f}")
        
        return {
            'train_score': train_score,
            'val_score': val_score,
            'feature_importance': self.feature_importance
        }
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions"""
        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict_proba(X_scaled)[:, 1]  # Probability of class 1
        return predictions
    
    def save(self, path: str):
        """Save model"""
        joblib.dump(self.model, f"{path}_rf_model.pkl")
        joblib.dump(self.scaler, f"{path}_rf_scaler.pkl")
        self.feature_importance.to_csv(f"{path}_rf_importance.csv", index=False)
    
    def load(self, path: str):
        """Load model"""
        self.model = joblib.load(f"{path}_rf_model.pkl")
        self.scaler = joblib.load(f"{path}_rf_scaler.pkl")


class XGBoostModel:
    """XGBoost model for trading signals"""
    
    def __init__(self, config: MLConfig):
        self.config = config
        self.model = None
        self.scaler = StandardScaler()
        self.feature_importance = None
    
    def build_model(self):
        """Build XGBoost model"""
        self.model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            objective='binary:logistic',
            eval_metric='auc',
            random_state=42,
            use_label_encoder=False
        )
        return self.model
    
    def train(self, X_train: pd.DataFrame, y_train: pd.Series, X_val: pd.DataFrame, y_val: pd.Series):
        """Train XGBoost model"""
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        
        # Train model with early stopping
        self.model.fit(
            X_train_scaled, y_train,
            eval_set=[(X_val_scaled, y_val)],
            early_stopping_rounds=10,
            verbose=False
        )
        
        # Get feature importance
        importance = self.model.feature_importances_
        self.feature_importance = pd.DataFrame({
            'feature': X_train.columns,
            'importance': importance
        }).sort_values('importance', ascending=False)
        
        # Evaluate
        train_pred = self.model.predict(X_train_scaled)
        val_pred = self.model.predict(X_val_scaled)
        
        train_score = accuracy_score(y_train, train_pred)
        val_score = accuracy_score(y_val, val_pred)
        
        logger.info(f"XGBoost - Train accuracy: {train_score:.4f}, Val accuracy: {val_score:.4f}")
        
        return {
            'train_score': train_score,
            'val_score': val_score,
            'feature_importance': self.feature_importance
        }
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions"""
        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict_proba(X_scaled)[:, 1]  # Probability of class 1
        return predictions
    
    def save(self, path: str):
        """Save model"""
        self.model.save_model(f"{path}_xgb_model.json")
        joblib.dump(self.scaler, f"{path}_xgb_scaler.pkl")
        self.feature_importance.to_csv(f"{path}_xgb_importance.csv", index=False)
    
    def load(self, path: str):
        """Load model"""
        self.model = xgb.XGBClassifier()
        self.model.load_model(f"{path}_xgb_model.json")
        self.scaler = joblib.load(f"{path}_xgb_scaler.pkl")


class EnsembleModel:
    """Ensemble of multiple ML models"""
    
    def __init__(self, config: MLConfig):
        self.config = config
        self.models = {}
        self.feature_engineer = FeatureEngineer(config)
        self.predictions_history = []
        self.last_train_time = None
        
        # Initialize models
        if TF_AVAILABLE:
            self.models['lstm'] = LSTMModel(config)
        self.models['random_forest'] = RandomForestModel(config)
        self.models['xgboost'] = XGBoostModel(config)
    
    def train(self, df: pd.DataFrame):
        """Train all models in the ensemble"""
        logger.info("Training ensemble models...")
        
        # Prepare data
        features, target = self.feature_engineer.prepare_data(df)
        
        # Remove NaN values
        mask = ~(features.isna().any(axis=1) | target.isna())
        features = features[mask]
        target = target[mask]
        
        # Split data
        split_idx = int(len(features) * self.config.training_split)
        val_idx = int(len(features) * (self.config.training_split + self.config.validation_split))
        
        X_train = features.iloc[:split_idx]
        y_train = target.iloc[:split_idx]
        X_val = features.iloc[split_idx:val_idx]
        y_val = target.iloc[split_idx:val_idx]
        X_test = features.iloc[val_idx:]
        y_test = target.iloc[val_idx:]
        
        results = {}
        
        # Train Random Forest
        if 'random_forest' in self.models:
            logger.info("Training Random Forest...")
            self.models['random_forest'].build_model()
            rf_results = self.models['random_forest'].train(X_train, y_train, X_val, y_val)
            results['random_forest'] = rf_results
        
        # Train XGBoost
        if 'xgboost' in self.models:
            logger.info("Training XGBoost...")
            self.models['xgboost'].build_model()
            xgb_results = self.models['xgboost'].train(X_train, y_train, X_val, y_val)
            results['xgboost'] = xgb_results
        
        # Train LSTM (if TensorFlow available)
        if 'lstm' in self.models and TF_AVAILABLE:
            logger.info("Training LSTM...")
            # Create sequences for LSTM
            X_seq, y_seq = self.feature_engineer.create_sequences(features, target)
            
            if len(X_seq) > 100:  # Need enough data for LSTM
                split_idx_seq = int(len(X_seq) * self.config.training_split)
                val_idx_seq = int(len(X_seq) * (self.config.training_split + self.config.validation_split))
                
                X_train_seq = X_seq[:split_idx_seq]
                y_train_seq = y_seq[:split_idx_seq]
                X_val_seq = X_seq[split_idx_seq:val_idx_seq]
                y_val_seq = y_seq[split_idx_seq:val_idx_seq]
                
                self.models['lstm'].build_model((X_train_seq.shape[1], X_train_seq.shape[2]))
                lstm_history = self.models['lstm'].train(X_train_seq, y_train_seq, X_val_seq, y_val_seq)
                results['lstm'] = {'history': lstm_history}
        
        # Evaluate ensemble on test set
        ensemble_predictions = self.predict(X_test)
        ensemble_accuracy = accuracy_score(y_test, (ensemble_predictions > 0.5).astype(int))
        
        logger.info(f"Ensemble test accuracy: {ensemble_accuracy:.4f}")
        results['ensemble'] = {'test_accuracy': ensemble_accuracy}
        
        self.last_train_time = datetime.now(timezone.utc)
        
        return results
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make ensemble predictions"""
        predictions = {}
        weights_sum = 0
        
        # Get predictions from each model
        if 'random_forest' in self.models and self.models['random_forest'].model is not None:
            predictions['random_forest'] = self.models['random_forest'].predict(X)
            weights_sum += self.config.ensemble_weights.get('random_forest', 0.33)
        
        if 'xgboost' in self.models and self.models['xgboost'].model is not None:
            predictions['xgboost'] = self.models['xgboost'].predict(X)
            weights_sum += self.config.ensemble_weights.get('xgboost', 0.33)
        
        # LSTM predictions would need sequence data
        # Skipping for simplicity in this context
        
        # Weighted average ensemble
        if predictions:
            ensemble_pred = np.zeros(len(X))
            for model_name, pred in predictions.items():
                weight = self.config.ensemble_weights.get(model_name, 0.33) / weights_sum
                ensemble_pred += pred * weight
            
            return ensemble_pred
        
        return np.zeros(len(X))
    
    def generate_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate trading signals from ML predictions"""
        # Check if retraining is needed
        if self.last_train_time is None or \
           (datetime.now(timezone.utc) - self.last_train_time).total_seconds() > self.config.retrain_frequency * 3600:
            self.train(df)
        
        # Prepare current features
        features, _ = self.feature_engineer.prepare_data(df)
        
        if features.empty:
            return {}
        
        # Get latest features
        latest_features = features.iloc[-1:] if len(features) > 0 else features
        
        # Get predictions
        prediction = self.predict(latest_features)
        
        if len(prediction) == 0:
            return {}
        
        confidence = abs(prediction[0] - 0.5) * 2  # Convert to confidence score
        
        # Generate signal
        signal = {
            'timestamp': df.index[-1] if not df.empty else datetime.now(timezone.utc),
            'prediction': prediction[0],
            'confidence': confidence,
            'signal': 'neutral'
        }
        
        # Determine signal based on prediction and confidence
        if confidence >= self.config.min_confidence:
            if prediction[0] > 0.5:
                signal['signal'] = 'buy'
                signal['strength'] = (prediction[0] - 0.5) * 2
            else:
                signal['signal'] = 'sell'
                signal['strength'] = (0.5 - prediction[0]) * 2
        
        # Add feature importance info
        if 'random_forest' in self.models and self.models['random_forest'].feature_importance is not None:
            top_features = self.models['random_forest'].feature_importance.head(5)
            signal['top_features'] = top_features.to_dict('records')
        
        # Store prediction for analysis
        self.predictions_history.append(signal)
        
        return signal
    
    def backtest_predictions(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Backtest ML predictions"""
        # Prepare data
        features, target = self.feature_engineer.prepare_data(df)
        
        # Remove NaN values
        mask = ~(features.isna().any(axis=1) | target.isna())
        features = features[mask]
        target = target[mask]
        
        if len(features) < 100:
            return {}
        
        # Use time series split for more realistic backtesting
        tscv = TimeSeriesSplit(n_splits=5)
        
        results = []
        for train_idx, test_idx in tscv.split(features):
            X_train, X_test = features.iloc[train_idx], features.iloc[test_idx]
            y_train, y_test = target.iloc[train_idx], target.iloc[test_idx]
            
            # Train models
            if 'random_forest' in self.models:
                self.models['random_forest'].build_model()
                self.models['random_forest'].model.fit(
                    self.models['random_forest'].scaler.fit_transform(X_train),
                    y_train
                )
            
            # Predict
            predictions = self.predict(X_test)
            pred_binary = (predictions > 0.5).astype(int)
            
            # Calculate metrics
            accuracy = accuracy_score(y_test, pred_binary)
            precision = precision_score(y_test, pred_binary, zero_division=0)
            recall = recall_score(y_test, pred_binary, zero_division=0)
            f1 = f1_score(y_test, pred_binary, zero_division=0)
            
            results.append({
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1': f1
            })
        
        # Average results
        avg_results = {
            'avg_accuracy': np.mean([r['accuracy'] for r in results]),
            'avg_precision': np.mean([r['precision'] for r in results]),
            'avg_recall': np.mean([r['recall'] for r in results]),
            'avg_f1': np.mean([r['f1'] for r in results]),
            'std_accuracy': np.std([r['accuracy'] for r in results])
        }
        
        logger.info(f"Backtest results: Accuracy={avg_results['avg_accuracy']:.4f} "
                   f"(±{avg_results['std_accuracy']:.4f})")
        
        return avg_results
    
    def save_models(self):
        """Save all models"""
        for name, model in self.models.items():
            if hasattr(model, 'save'):
                model.save(f"{self.config.model_save_path}{name}")
                logger.info(f"Saved {name} model")
    
    def load_models(self):
        """Load all models"""
        for name, model in self.models.items():
            if hasattr(model, 'load'):
                try:
                    model.load(f"{self.config.model_save_path}{name}")
                    logger.info(f"Loaded {name} model")
                except Exception as e:
                    logger.warning(f"Could not load {name} model: {e}")


class MLStrategyExecutor:
    """Execute trades based on ML signals"""
    
    def __init__(self, ml_config: MLConfig):
        self.config = ml_config
        self.ensemble = EnsembleModel(ml_config)
        self.signal_history = []
        self.performance_metrics = {}
    
    def execute_strategy(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Execute ML-based trading strategy"""
        signals = {}
        
        for symbol, df in market_data.items():
            # Generate ML signals
            ml_signal = self.ensemble.generate_signals(df)
            
            if ml_signal and ml_signal['signal'] != 'neutral':
                signals[symbol] = {
                    'action': ml_signal['signal'],
                    'confidence': ml_signal['confidence'],
                    'strength': ml_signal.get('strength', 0.5),
                    'prediction': ml_signal['prediction'],
                    'timestamp': ml_signal['timestamp']
                }
                
                # Log signal
                logger.info(f"ML Signal for {symbol}: {ml_signal['signal']} "
                          f"(confidence: {ml_signal['confidence']:.2f})")
        
        return signals
    
    def update_performance(self, trade_result: Dict[str, Any]):
        """Update performance metrics based on trade results"""
        # Track signal accuracy
        if trade_result['pnl'] > 0:
            self.performance_metrics['correct_signals'] = \
                self.performance_metrics.get('correct_signals', 0) + 1
        else:
            self.performance_metrics['incorrect_signals'] = \
                self.performance_metrics.get('incorrect_signals', 0) + 1
        
        # Calculate signal accuracy
        total_signals = (self.performance_metrics.get('correct_signals', 0) +
                        self.performance_metrics.get('incorrect_signals', 0))
        
        if total_signals > 0:
            self.performance_metrics['accuracy'] = \
                self.performance_metrics['correct_signals'] / total_signals
        
        logger.info(f"ML Strategy Performance: {self.performance_metrics}")