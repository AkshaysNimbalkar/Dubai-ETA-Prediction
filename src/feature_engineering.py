"""Feature engineering for ETA prediction"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class FeatureEngineer:
    """Engineer features for ETA prediction models"""
    
    def __init__(self):
        self.feature_stats = {}
        self.zone_pair_stats = {}
        self.training_columns = None
        self.fitted = False
    
    def fit(self, df: pd.DataFrame) -> 'FeatureEngineer':
        """Fit feature statistics on training data"""
        logger.info("Fitting feature statistics on training data")
        
        # Zone pair statistics
        self.zone_pair_stats = df.groupby(
            ['pickup_zone', 'dropoff_zone']
        )['actual_duration_minutes'].agg(['mean', 'std', 'count']).to_dict()
        
        # Hour statistics
        self.feature_stats['hour_mean'] = df.groupby('hour')[
            'actual_duration_minutes'
        ].mean().to_dict()
        
        # Day of week statistics
        self.feature_stats['dow_mean'] = df.groupby('day_of_week')[
            'actual_duration_minutes'
        ].mean().to_dict()
        
        # Zone type combinations
        self.feature_stats['zone_combo_mean'] = df.groupby(
            ['zone_type_pickup', 'zone_type_dropoff']
        )['actual_duration_minutes'].mean().to_dict()
        
        # Global statistics
        self.feature_stats['global_mean'] = df['actual_duration_minutes'].mean()
        self.feature_stats['global_std'] = df['actual_duration_minutes'].std()
        
        self.fitted = True
        logger.info("Feature engineering fitted successfully")
        return self
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform dataframe with engineered features"""
        if not self.fitted:
            raise ValueError("FeatureEngineer must be fitted before transform")
        
        logger.info(f"Transforming {len(df)} records")
        features = df.copy()
        
        # Temporal cyclic features
        features['hour_sin'] = np.sin(2 * np.pi * features['hour'] / 24)
        features['hour_cos'] = np.cos(2 * np.pi * features['hour'] / 24)
        features['dow_sin'] = np.sin(2 * np.pi * features['day_of_week'] / 7)
        features['dow_cos'] = np.cos(2 * np.pi * features['day_of_week'] / 7)
        
        # Zone pair features
        features['zone_pair_mean'] = features.apply(
            lambda x: self.zone_pair_stats.get(
                (x['pickup_zone'], x['dropoff_zone']), {}
            ).get('mean', self.feature_stats['global_mean']), axis=1
        )
        
        features['zone_pair_std'] = features.apply(
            lambda x: self.zone_pair_stats.get(
                (x['pickup_zone'], x['dropoff_zone']), {}
            ).get('std', self.feature_stats['global_std']), axis=1
        )
        
        features['zone_pair_count'] = features.apply(
            lambda x: self.zone_pair_stats.get(
                (x['pickup_zone'], x['dropoff_zone']), {}
            ).get('count', 0), axis=1
        )
        
        # Hour and day averages
        features['hour_mean'] = features['hour'].map(
            self.feature_stats['hour_mean']
        ).fillna(self.feature_stats['global_mean'])
        
        features['dow_mean'] = features['day_of_week'].map(
            self.feature_stats['dow_mean']
        ).fillna(self.feature_stats['global_mean'])
        
        # Zone type combination
        features['zone_combo_mean'] = features.apply(
            lambda x: self.feature_stats['zone_combo_mean'].get(
                (x['zone_type_pickup'], x['zone_type_dropoff']),
                self.feature_stats['global_mean']
            ), axis=1
        )
        
        # Interaction features
        features['distance_rush'] = features['dubai_distance'] * features['is_rush_hour']
        features['distance_weekend'] = features['dubai_distance'] * features['is_weekend']
        features['distance_squared'] = features['dubai_distance'] ** 2
        
        # Friday prayer time feature
        if 'is_friday_prayer' in features.columns:
            features['distance_friday_prayer'] = features['dubai_distance'] * features['is_friday_prayer']
        
        # Zone characteristics
        features['same_zone_type'] = (
            features['zone_type_pickup'] == features['zone_type_dropoff']
        ).astype(int)
        
        # Time windows
        features['is_morning'] = features['hour'].between(6, 10).astype(int)
        features['is_afternoon'] = features['hour'].between(12, 16).astype(int)
        features['is_evening'] = features['hour'].between(17, 21).astype(int)
        features['is_night'] = features['hour'].between(22, 23).astype(int) | features['hour'].between(0, 5).astype(int)
        
        # One-hot encoding for categorical features
        categorical_cols = ['zone_type_pickup', 'zone_type_dropoff', 'weather']
        features = pd.get_dummies(features, columns=categorical_cols, prefix_sep='_')
        
        # Ensure consistent columns with training data
        if self.training_columns is not None:
            # Add missing columns with 0s
            for col in self.training_columns:
                if col not in features.columns:
                    features[col] = 0
            # Remove extra columns and reorder
            features = features[self.training_columns]
        
        logger.info(f"Created {len(features.columns)} features")
        return features
    
    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform in one step"""
        self.fit(df)
        transformed = self.transform(df)
        # Store training columns for consistency during transform
        self.training_columns = transformed.columns.tolist()
        return transformed
    
    def get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """Get list of feature columns for modeling"""
        exclude_cols = [
            'trip_id', 'request_datetime', 'actual_duration_minutes',
            'driver_efficiency', 'has_event'
        ]
        
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        return feature_cols