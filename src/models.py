"""Model implementations for ETA prediction"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
from typing import Dict, List, Optional, Tuple
import logging

from .config import config

logger = logging.getLogger(__name__)

class BaselineModel:
    """Simple baseline model using linear regression"""
    
    def __init__(self):
        self.model = LinearRegression()
        self.scaler = StandardScaler()
        self.feature_columns = [
            'dubai_distance', 'hour', 'day_of_week', 'is_rush_hour'
        ]
        self.fitted = False
    
    def fit(self, X: pd.DataFrame, y: pd.Series) -> 'BaselineModel':
        """Fit the baseline model"""
        logger.info("Training baseline model")
        
        X_baseline = X[self.feature_columns]
        X_scaled = self.scaler.fit_transform(X_baseline)
        
        self.model.fit(X_scaled, y)
        self.fitted = True
        
        logger.info("Baseline model trained successfully")
        return self
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions"""
        if not self.fitted:
            raise ValueError("Model must be fitted before prediction")
        
        X_baseline = X[self.feature_columns]
        X_scaled = self.scaler.transform(X_baseline)
        
        return self.model.predict(X_scaled)
    
    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """Evaluate model performance"""
        predictions = self.predict(X)
        
        metrics = {
            'mae': mean_absolute_error(y, predictions),
            'rmse': np.sqrt(mean_squared_error(y, predictions)),
            'r2': r2_score(y, predictions),
            'mape': np.mean(np.abs((y - predictions) / y)) * 100
        }
        
        logger.info(f"Baseline metrics: MAE={metrics['mae']:.2f}, RMSE={metrics['rmse']:.2f}")
        return metrics

class AdvancedModel:
    """Advanced XGBoost model with rich features"""
    
    def __init__(self):
        self.model = None
        self.feature_columns = None
        self.fitted = False
        self._init_params()
    
    def _init_params(self):
        """Initialize XGBoost parameters from config"""
        xgb_config = config.get('model.xgboost', {})
        
        self.params = {
            'objective': 'reg:squarederror',
            'n_estimators': xgb_config.get('n_estimators', 200),
            'max_depth': xgb_config.get('max_depth', 8),
            'learning_rate': xgb_config.get('learning_rate', 0.1),
            'subsample': xgb_config.get('subsample', 0.8),
            'colsample_bytree': xgb_config.get('colsample_bytree', 0.8),
            'random_state': xgb_config.get('random_state', 42),
            'n_jobs': -1
        }
    
    def fit(self, X_train: pd.DataFrame, y_train: pd.Series,
            X_val: Optional[pd.DataFrame] = None, 
            y_val: Optional[pd.Series] = None) -> 'AdvancedModel':
        """Fit the XGBoost model"""
        logger.info("Training advanced XGBoost model")
        
        # Store feature columns
        self.feature_columns = X_train.columns.tolist()
        
        # Initialize model
        self.model = xgb.XGBRegressor(**self.params)
        
        # Prepare evaluation set
        eval_set = None
        if X_val is not None and y_val is not None:
            eval_set = [(X_val, y_val)]
        
        # Train model - newer xgboost versions don't accept early_stopping_rounds
        # or callbacks directly in fit(). For early stopping, use model initialization params.
        fit_kwargs = {'verbose': False}
        if eval_set is not None:
            fit_kwargs['eval_set'] = eval_set
        
        self.model.fit(X_train, y_train, **fit_kwargs)
        
        self.fitted = True
        logger.info("Advanced model trained successfully")
        return self
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions"""
        if not self.fitted:
            raise ValueError("Model must be fitted before prediction")
        
        # Ensure columns match training
        X_pred = X[self.feature_columns]
        
        return self.model.predict(X_pred)
    
    def predict_with_confidence(self, X: pd.DataFrame, 
                               confidence_level: float = 0.95) -> Tuple[np.ndarray, np.ndarray]:
        """Predict with confidence intervals"""
        predictions = self.predict(X)
        
        # Simple confidence interval based on prediction variance
        # In production, use proper quantile regression or bootstrapping
        std_estimate = predictions * 0.15  # 15% coefficient of variation
        z_score = 1.96 if confidence_level == 0.95 else 2.58
        
        lower_bound = predictions - z_score * std_estimate
        upper_bound = predictions + z_score * std_estimate
        
        return predictions, np.column_stack([lower_bound, upper_bound])
    
    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """Evaluate model performance"""
        predictions = self.predict(X)
        
        metrics = {
            'mae': mean_absolute_error(y, predictions),
            'rmse': np.sqrt(mean_squared_error(y, predictions)),
            'r2': r2_score(y, predictions),
            'mape': np.mean(np.abs((y - predictions) / y)) * 100
        }
        
        logger.info(f"Advanced metrics: MAE={metrics['mae']:.2f}, RMSE={metrics['rmse']:.2f}")
        return metrics
    
    def get_feature_importance(self) -> pd.DataFrame:
        """Get feature importance scores"""
        if not self.fitted:
            raise ValueError("Model must be fitted first")
        
        importance = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        return importance