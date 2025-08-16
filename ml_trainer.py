#!/usr/bin/env python3
"""
ML Model Trainer for Bybit Trading Bot
Trains and optimizes machine learning models for trading predictions
"""

import os
import json
import pickle
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.metrics import classification_report, confusion_matrix
import xgboost as xgb
from data_collector import HistoricalDataCollector
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MLModelTrainer:
    """Trains and manages ML models for trading predictions"""
    
    def __init__(self, symbol: str = 'BTCUSDT'):
        """Initialize model trainer"""
        self.symbol = symbol
        self.data_collector = HistoricalDataCollector()
        self.models = {}
        self.scalers = {}
        self.feature_columns = []
        self.best_model = None
        self.best_score = 0
        
        # Model save directory
        self.model_dir = 'models'
        os.makedirs(self.model_dir, exist_ok=True)
        
        logger.info(f"ML Trainer initialized for {symbol}")
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for ML training"""
        # Technical indicator features
        feature_cols = [
            'open', 'high', 'low', 'close', 'volume',
            'sma_7', 'sma_25', 'sma_99',
            'ema_7', 'ema_25',
            'rsi', 'macd', 'macd_signal', 'macd_diff',
            'bb_upper', 'bb_middle', 'bb_lower',
            'volume_ratio', 'volatility'
        ]
        
        # Price ratio features
        df['close_to_open'] = df['close'] / df['open']
        df['high_to_low'] = df['high'] / df['low']
        df['close_to_sma7'] = df['close'] / df['sma_7']
        df['close_to_sma25'] = df['close'] / df['sma_25']
        df['volume_to_avg'] = df['volume'] / df['volume'].rolling(20).mean()
        
        feature_cols.extend([
            'close_to_open', 'high_to_low', 
            'close_to_sma7', 'close_to_sma25',
            'volume_to_avg'
        ])
        
        # Lag features
        for lag in [1, 2, 3, 5]:
            df[f'close_lag_{lag}'] = df['close'].shift(lag)
            df[f'volume_lag_{lag}'] = df['volume'].shift(lag)
            df[f'rsi_lag_{lag}'] = df['rsi'].shift(lag)
            feature_cols.extend([
                f'close_lag_{lag}', f'volume_lag_{lag}', f'rsi_lag_{lag}'
            ])
        
        # Remove any NaN values
        df = df.dropna()
        
        # Store feature columns
        self.feature_columns = [col for col in feature_cols if col in df.columns]
        
        return df[self.feature_columns + ['target']]
    
    def train_random_forest(self, X_train, y_train, X_test, y_test) -> Dict:
        """Train Random Forest model"""
        logger.info("Training Random Forest model...")
        
        # Hyperparameter tuning
        param_grid = {
            'n_estimators': [100, 200],
            'max_depth': [10, 20, None],
            'min_samples_split': [2, 5],
            'min_samples_leaf': [1, 2]
        }
        
        rf = RandomForestClassifier(random_state=42, n_jobs=-1)
        
        # Grid search with cross-validation
        grid_search = GridSearchCV(
            rf, param_grid, cv=5, 
            scoring='f1', n_jobs=-1, verbose=0
        )
        
        grid_search.fit(X_train, y_train)
        
        # Best model
        best_rf = grid_search.best_estimator_
        
        # Predictions
        y_pred = best_rf.predict(X_test)
        
        # Metrics
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1': f1_score(y_test, y_pred),
            'best_params': grid_search.best_params_
        }
        
        self.models['random_forest'] = best_rf
        
        logger.info(f"Random Forest F1 Score: {metrics['f1']:.4f}")
        
        return metrics
    
    def train_xgboost(self, X_train, y_train, X_test, y_test) -> Dict:
        """Train XGBoost model"""
        logger.info("Training XGBoost model...")
        
        # Hyperparameter tuning
        param_grid = {
            'max_depth': [3, 5, 7],
            'learning_rate': [0.01, 0.1, 0.3],
            'n_estimators': [100, 200],
            'subsample': [0.8, 1.0]
        }
        
        xgb_model = xgb.XGBClassifier(
            random_state=42,
            use_label_encoder=False,
            eval_metric='logloss'
        )
        
        # Grid search
        grid_search = GridSearchCV(
            xgb_model, param_grid, cv=5, 
            scoring='f1', n_jobs=-1, verbose=0
        )
        
        grid_search.fit(X_train, y_train)
        
        # Best model
        best_xgb = grid_search.best_estimator_
        
        # Predictions
        y_pred = best_xgb.predict(X_test)
        
        # Metrics
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1': f1_score(y_test, y_pred),
            'best_params': grid_search.best_params_
        }
        
        self.models['xgboost'] = best_xgb
        
        logger.info(f"XGBoost F1 Score: {metrics['f1']:.4f}")
        
        return metrics
    
    def train_gradient_boosting(self, X_train, y_train, X_test, y_test) -> Dict:
        """Train Gradient Boosting model"""
        logger.info("Training Gradient Boosting model...")
        
        # Hyperparameter tuning
        param_grid = {
            'n_estimators': [100, 200],
            'learning_rate': [0.05, 0.1, 0.15],
            'max_depth': [3, 5, 7],
            'min_samples_split': [2, 5]
        }
        
        gb = GradientBoostingClassifier(random_state=42)
        
        # Grid search
        grid_search = GridSearchCV(
            gb, param_grid, cv=5, 
            scoring='f1', n_jobs=-1, verbose=0
        )
        
        grid_search.fit(X_train, y_train)
        
        # Best model
        best_gb = grid_search.best_estimator_
        
        # Predictions
        y_pred = best_gb.predict(X_test)
        
        # Metrics
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1': f1_score(y_test, y_pred),
            'best_params': grid_search.best_params_
        }
        
        self.models['gradient_boosting'] = best_gb
        
        logger.info(f"Gradient Boosting F1 Score: {metrics['f1']:.4f}")
        
        return metrics
    
    def train_ensemble(self, X_train, y_train, X_test, y_test) -> Dict:
        """Create ensemble model from trained models"""
        logger.info("Creating ensemble model...")
        
        if len(self.models) < 2:
            logger.warning("Not enough models for ensemble")
            return {}
        
        # Get predictions from all models
        predictions = []
        for name, model in self.models.items():
            pred = model.predict_proba(X_test)[:, 1]
            predictions.append(pred)
        
        # Average predictions (simple ensemble)
        ensemble_pred = np.mean(predictions, axis=0)
        ensemble_pred_binary = (ensemble_pred > 0.5).astype(int)
        
        # Metrics
        metrics = {
            'accuracy': accuracy_score(y_test, ensemble_pred_binary),
            'precision': precision_score(y_test, ensemble_pred_binary),
            'recall': recall_score(y_test, ensemble_pred_binary),
            'f1': f1_score(y_test, ensemble_pred_binary)
        }
        
        logger.info(f"Ensemble F1 Score: {metrics['f1']:.4f}")
        
        return metrics
    
    def train_all_models(self, lookback_days: int = 90):
        """Train all models with historical data"""
        logger.info(f"Starting model training for {self.symbol}")
        
        # Get training data
        df = self.data_collector.get_training_data(
            self.symbol, '15m', lookback_days
        )
        
        if df.empty:
            logger.error("No training data available")
            return
        
        # Prepare features
        df = self.prepare_features(df)
        
        # Split features and target
        X = df[self.feature_columns]
        y = df['target']
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        self.scalers['standard'] = scaler
        
        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42, stratify=y
        )
        
        logger.info(f"Training set size: {len(X_train)}")
        logger.info(f"Test set size: {len(X_test)}")
        logger.info(f"Class distribution: {y.value_counts().to_dict()}")
        
        # Train models
        results = {}
        
        # Random Forest
        results['random_forest'] = self.train_random_forest(
            X_train, y_train, X_test, y_test
        )
        
        # XGBoost
        results['xgboost'] = self.train_xgboost(
            X_train, y_train, X_test, y_test
        )
        
        # Gradient Boosting
        results['gradient_boosting'] = self.train_gradient_boosting(
            X_train, y_train, X_test, y_test
        )
        
        # Ensemble
        results['ensemble'] = self.train_ensemble(
            X_train, y_train, X_test, y_test
        )
        
        # Select best model
        best_model_name = max(results, key=lambda x: results[x].get('f1', 0))
        self.best_model = self.models.get(best_model_name)
        self.best_score = results[best_model_name].get('f1', 0)
        
        logger.info(f"Best model: {best_model_name} with F1 score: {self.best_score:.4f}")
        
        # Save models
        self.save_models()
        
        # Save results
        self.save_training_results(results)
        
        return results
    
    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Make predictions using best model"""
        if self.best_model is None:
            logger.error("No trained model available")
            return np.array([])
        
        # Prepare features
        df = self.prepare_features(df)
        
        if df.empty:
            return np.array([])
        
        # Scale features
        X = df[self.feature_columns]
        X_scaled = self.scalers['standard'].transform(X)
        
        # Predict
        predictions = self.best_model.predict_proba(X_scaled)[:, 1]
        
        return predictions
    
    def save_models(self):
        """Save trained models to disk"""
        # Save models
        for name, model in self.models.items():
            model_path = os.path.join(self.model_dir, f"{name}_{self.symbol}.pkl")
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            logger.info(f"Saved model: {model_path}")
        
        # Save scalers
        scaler_path = os.path.join(self.model_dir, f"scaler_{self.symbol}.pkl")
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.scalers, f)
        
        # Save feature columns
        features_path = os.path.join(self.model_dir, f"features_{self.symbol}.json")
        with open(features_path, 'w') as f:
            json.dump(self.feature_columns, f)
        
        # Save metadata
        metadata = {
            'symbol': self.symbol,
            'best_model': type(self.best_model).__name__ if self.best_model else None,
            'best_score': self.best_score,
            'training_date': datetime.now().isoformat(),
            'n_features': len(self.feature_columns)
        }
        
        metadata_path = os.path.join(self.model_dir, f"metadata_{self.symbol}.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def load_models(self):
        """Load saved models from disk"""
        try:
            # Load metadata
            metadata_path = os.path.join(self.model_dir, f"metadata_{self.symbol}.json")
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Load models
            for model_type in ['random_forest', 'xgboost', 'gradient_boosting']:
                model_path = os.path.join(self.model_dir, f"{model_type}_{self.symbol}.pkl")
                if os.path.exists(model_path):
                    with open(model_path, 'rb') as f:
                        self.models[model_type] = pickle.load(f)
            
            # Load scalers
            scaler_path = os.path.join(self.model_dir, f"scaler_{self.symbol}.pkl")
            with open(scaler_path, 'rb') as f:
                self.scalers = pickle.load(f)
            
            # Load feature columns
            features_path = os.path.join(self.model_dir, f"features_{self.symbol}.json")
            with open(features_path, 'r') as f:
                self.feature_columns = json.load(f)
            
            # Set best model
            best_model_name = metadata.get('best_model', '').lower().replace('classifier', '')
            self.best_model = self.models.get(best_model_name)
            self.best_score = metadata.get('best_score', 0)
            
            logger.info(f"Loaded models for {self.symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            return False
    
    def save_training_results(self, results: Dict):
        """Save training results to file"""
        results_path = os.path.join(
            self.model_dir, 
            f"training_results_{self.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Saved training results to {results_path}")
    
    def get_feature_importance(self) -> pd.DataFrame:
        """Get feature importance from best model"""
        if self.best_model is None:
            return pd.DataFrame()
        
        if hasattr(self.best_model, 'feature_importances_'):
            importance = pd.DataFrame({
                'feature': self.feature_columns,
                'importance': self.best_model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            return importance
        
        return pd.DataFrame()

def main():
    """Main function to train models"""
    # Train models for multiple symbols
    symbols = ['BTCUSDT', 'ETHUSDT']
    
    for symbol in symbols:
        logger.info(f"\n{'='*50}")
        logger.info(f"Training models for {symbol}")
        logger.info(f"{'='*50}")
        
        trainer = MLModelTrainer(symbol)
        results = trainer.train_all_models(lookback_days=90)
        
        if results:
            # Display results
            print(f"\nTraining Results for {symbol}:")
            for model_name, metrics in results.items():
                if metrics:
                    print(f"\n{model_name.upper()}:")
                    print(f"  Accuracy: {metrics.get('accuracy', 0):.4f}")
                    print(f"  Precision: {metrics.get('precision', 0):.4f}")
                    print(f"  Recall: {metrics.get('recall', 0):.4f}")
                    print(f"  F1 Score: {metrics.get('f1', 0):.4f}")
            
            # Feature importance
            importance = trainer.get_feature_importance()
            if not importance.empty:
                print(f"\nTop 10 Important Features:")
                print(importance.head(10))

if __name__ == "__main__":
    main()