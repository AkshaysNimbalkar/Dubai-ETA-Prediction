"""Main predictor class that orchestrates the ETA prediction"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import logging

from .feature_engineering import FeatureEngineer
from .models import BaselineModel, AdvancedModel
from .config import config

logger = logging.getLogger(__name__)

class ETAPredictor:
    """Main class for ETA predictions"""
    
    def __init__(self):
        self.feature_engineer = FeatureEngineer()
        self.baseline_model = BaselineModel()
        self.advanced_model = AdvancedModel()
        self.metadata = {}
        self.fitted = False
    
    def train(self, train_df: pd.DataFrame, 
             val_df: Optional[pd.DataFrame] = None) -> 'ETAPredictor':
        """Train all models"""
        logger.info("Starting model training pipeline")
        
        # Feature engineering
        X_train = self.feature_engineer.fit_transform(train_df)
        y_train = train_df['actual_duration_minutes']
        
        # Get feature columns
        feature_cols = self.feature_engineer.get_feature_columns(X_train)
        X_train_features = X_train[feature_cols]
        
        # Train baseline model
        self.baseline_model.fit(X_train_features, y_train)
        
        # Prepare validation data if provided
        X_val_features = None
        y_val = None
        if val_df is not None:
            X_val = self.feature_engineer.transform(val_df)
            X_val_features = X_val[feature_cols]
            y_val = val_df['actual_duration_minutes']
        
        # Train advanced model
        self.advanced_model.fit(X_train_features, y_train, X_val_features, y_val)
        
        # Store metadata
        self.metadata = {
            'train_size': len(train_df),
            'val_size': len(val_df) if val_df is not None else 0,
            'features_count': len(feature_cols),
            'training_date': datetime.now().isoformat()
        }
        
        self.fitted = True
        logger.info("Model training complete")
        return self
    
    def predict(self, pickup_zone: int, dropoff_zone: int, 
               request_time: datetime, model_type: str = 'advanced') -> Dict[str, Any]:
        """Make a single prediction"""
        if not self.fitted:
            raise ValueError("Models must be trained before prediction")
        
        # Create input dataframe
        input_data = pd.DataFrame([{
            'pickup_zone': pickup_zone,
            'dropoff_zone': dropoff_zone,
            'request_datetime': request_time,
            'dubai_distance': self._calculate_dubai_distance(pickup_zone, dropoff_zone),
            'hour': request_time.hour,
            'day_of_week': request_time.weekday(),
            'is_weekend': request_time.weekday() >= 5,
            'is_rush_hour': self._is_rush_hour(request_time.hour),
            'is_friday_prayer': request_time.weekday() == 4 and 12 <= request_time.hour <= 13,
            'zone_type_pickup': self._get_zone_type(pickup_zone),
            'zone_type_dropoff': self._get_zone_type(dropoff_zone),
            'weather': 'clear',  # Default, would use real weather API
            'has_event': False   # Default, would check event calendar
        }])
        
        # Engineer features
        X = self.feature_engineer.transform(input_data)
        feature_cols = self.feature_engineer.get_feature_columns(X)
        X_features = X[feature_cols]
        
        # Get prediction
        if model_type == 'baseline':
            prediction = self.baseline_model.predict(X_features)[0]
            confidence_interval = self._simple_confidence_interval(prediction)
        else:
            predictions, confidence = self.advanced_model.predict_with_confidence(X_features)
            prediction = predictions[0]
            confidence_interval = confidence[0].tolist()
        
        # Prepare response
        result = {
            'estimated_duration_minutes': float(prediction),
            'confidence_interval': confidence_interval,
            'factors': self._decompose_factors(input_data.iloc[0], prediction),
            'metadata': {
                'model_type': model_type,
                'model_version': '1.0',
                'prediction_timestamp': datetime.now().isoformat()
            }
        }
        
        return result
    
    def evaluate_all(self, test_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """Evaluate all models on test data"""
        logger.info("Evaluating models on test set")
        
        X_test = self.feature_engineer.transform(test_df)
        y_test = test_df['actual_duration_minutes']
        feature_cols = self.feature_engineer.get_feature_columns(X_test)
        X_test_features = X_test[feature_cols]
        
        results = {
            'baseline': self.baseline_model.evaluate(X_test_features, y_test),
            'advanced': self.advanced_model.evaluate(X_test_features, y_test)
        }
        
        return results
    
    def save(self, model_dir: Path):
        """Save trained models"""
        model_dir = Path(model_dir)
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save all components
        joblib.dump(self.feature_engineer, model_dir / 'feature_engineer.pkl')
        joblib.dump(self.baseline_model, model_dir / 'baseline_model.pkl')
        joblib.dump(self.advanced_model, model_dir / 'advanced_model.pkl')
        joblib.dump(self.metadata, model_dir / 'metadata.pkl')
        
        logger.info(f"Models saved to {model_dir}")
    
    @classmethod
    def load(cls, model_dir: Path) -> 'ETAPredictor':
        """Load trained models"""
        model_dir = Path(model_dir)
        
        predictor = cls()
        predictor.feature_engineer = joblib.load(model_dir / 'feature_engineer.pkl')
        predictor.baseline_model = joblib.load(model_dir / 'baseline_model.pkl')
        predictor.advanced_model = joblib.load(model_dir / 'advanced_model.pkl')
        predictor.metadata = joblib.load(model_dir / 'metadata.pkl')
        predictor.fitted = True
        
        logger.info(f"Models loaded from {model_dir}")
        return predictor
    
    def _calculate_dubai_distance(self, pickup: int, dropoff: int) -> int:
        """Calculate Dubai distance between zones"""
        grid_size = config.get('data.grid_size', 10)
        p_row, p_col = pickup // grid_size, pickup % grid_size
        d_row, d_col = dropoff // grid_size, dropoff % grid_size
        return abs(p_row - d_row) + abs(p_col - d_col)
    
    def _is_rush_hour(self, hour: int) -> bool:
        """Check if hour is rush hour"""
        rush_hours = (
            config.get('traffic.rush_hours.morning', [7, 8, 9]) +
            config.get('traffic.rush_hours.evening', [17, 18, 19, 20])
        )
        return hour in rush_hours
    
    def _get_zone_type(self, zone: int) -> str:
        """Get zone type from config"""
        zones_config = config.zones_config
        
        for zone_type, zone_data in zones_config.items():
            if isinstance(zone_data, dict) and 'cells' in zone_data:
                # New format: zone_data is a dict with 'cells' key
                if zone in zone_data['cells']:
                    return zone_type
            elif isinstance(zone_data, list):
                # Old format: zone_data is a list of zones
                for zone_list in zone_data:
                    if isinstance(zone_list, list) and zone in zone_list:
                        return zone_type
        
        return 'residential'
    
    def _simple_confidence_interval(self, prediction: float, 
                                   confidence_level: float = 0.95) -> list:
        """Simple confidence interval calculation"""
        std = prediction * 0.15
        z = 1.96 if confidence_level == 0.95 else 2.58
        return [
            max(1, prediction - z * std),
            prediction + z * std
        ]
    
    def _decompose_factors(self, trip_data: pd.Series, 
                          prediction: float) -> Dict[str, float]:
        """Decompose prediction into factors
        
        Factors explained:
        - base_time: Distance-based travel time (3 min per zone)
        - traffic_adjustment: Rush hour or Friday prayer slowdown
        - zone_complexity: Route efficiency/complexity adjustments
          * Positive = slower routes (congested zones, complex navigation)
          * Negative = faster routes (highway access, efficient zones)
        - weather_impact: Weather-related delays (sandstorm, rain)
        """
        base_time = trip_data['dubai_distance'] * 3.0
        
        traffic_adjustment = 0
        if trip_data['is_rush_hour']:
            traffic_adjustment = prediction * 0.2
        elif trip_data.get('is_friday_prayer', False):
            traffic_adjustment = prediction * 0.15
        
        # Zone complexity = everything not explained by base + traffic
        # Negative means the route is more efficient than baseline
        zone_complexity = prediction - base_time - traffic_adjustment
        
        return {
            'base_time': round(base_time, 1),
            'traffic_adjustment': round(traffic_adjustment, 1),
            'weather_impact': 0.0,
            'zone_complexity': round(zone_complexity, 1)
        }