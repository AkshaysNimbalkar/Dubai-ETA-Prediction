"""Test cases for model implementations"""

import pytest
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error
from src.models import BaselineModel, AdvancedModel
from src.data_generator import DubaiDataGenerator
from src.feature_engineering import FeatureEngineer

class TestBaselineModel:
    """Test suite for BaselineModel"""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample dataset with features"""
        generator = DubaiDataGenerator()
        df = generator.generate_dataset(n_trips=500)
        engineer = FeatureEngineer()
        return engineer.fit_transform(df), df['actual_duration_minutes']
    
    @pytest.fixture
    def model(self):
        """Create baseline model instance"""
        return BaselineModel()
    
    def test_initialization(self, model):
        """Test model initialization"""
        assert model.model is not None
        assert model.scaler is not None
        assert model.fitted == False
        assert 'dubai_distance' in model.feature_columns
        assert 'hour' in model.feature_columns
        assert 'day_of_week' in model.feature_columns
        assert 'is_rush_hour' in model.feature_columns
    
    def test_fit(self, model, sample_data):
        """Test model fitting"""
        X, y = sample_data
        model.fit(X, y)
        
        assert model.fitted == True
        assert hasattr(model.model, 'coef_')
        assert hasattr(model.model, 'intercept_')
    
    def test_predict_requires_fit(self, model, sample_data):
        """Test prediction requires fitting"""
        X, _ = sample_data
        with pytest.raises(ValueError, match="must be fitted"):
            model.predict(X)
    
    def test_predict(self, model, sample_data):
        """Test prediction"""
        X, y = sample_data
        
        # Split data
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        # Fit and predict
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
        
        assert len(predictions) == len(X_test)
        assert predictions.min() > 0
        assert predictions.max() < 200  # Reasonable upper bound
        
        # Check performance is reasonable
        mae = mean_absolute_error(y_test, predictions)
        assert mae < 10  # Should be less than 10 minutes
    
    def test_evaluate(self, model, sample_data):
        """Test model evaluation"""
        X, y = sample_data
        
        # Split data
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        # Fit and evaluate
        model.fit(X_train, y_train)
        metrics = model.evaluate(X_test, y_test)
        
        assert 'mae' in metrics
        assert 'rmse' in metrics
        assert 'r2' in metrics
        assert 'mape' in metrics
        
        assert metrics['mae'] > 0
        assert metrics['rmse'] > metrics['mae']  # RMSE >= MAE
        assert 0 <= metrics['r2'] <= 1
        assert 0 <= metrics['mape'] <= 100

class TestAdvancedModel:
    """Test suite for AdvancedModel"""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample dataset with features"""
        generator = DubaiDataGenerator()
        df = generator.generate_dataset(n_trips=1000)
        engineer = FeatureEngineer()
        features = engineer.fit_transform(df)
        
        # Get feature columns
        feature_cols = engineer.get_feature_columns(features)
        
        return features[feature_cols], df['actual_duration_minutes']
    
    @pytest.fixture
    def model(self):
        """Create advanced model instance"""
        return AdvancedModel()
    
    def test_initialization(self, model):
        """Test model initialization"""
        assert model.model is None
        assert model.feature_columns is None
        assert model.fitted == False
        assert 'n_estimators' in model.params
        assert 'max_depth' in model.params
        assert 'learning_rate' in model.params
    
    def test_fit(self, model, sample_data):
        """Test model fitting"""
        X, y = sample_data
        
        # Split data
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        model.fit(X_train, y_train, X_val, y_val)
        
        assert model.fitted == True
        assert model.feature_columns is not None
        assert len(model.feature_columns) == X_train.shape[1]
    
    def test_predict(self, model, sample_data):
        """Test prediction"""
        X, y = sample_data
        
        # Split data
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        # Fit and predict
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
        
        assert len(predictions) == len(X_test)
        assert predictions.min() > 0
        assert predictions.max() < 200
        
        # Check performance is good
        mae = mean_absolute_error(y_test, predictions)
        assert mae < 6  # Advanced model should be better
    
    def test_predict_with_confidence(self, model, sample_data):
        """Test prediction with confidence intervals"""
        X, y = sample_data
        
        # Split data
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, _ = y[:split_idx], y[split_idx:]
        
        # Fit and predict with confidence
        model.fit(X_train, y_train)
        predictions, confidence = model.predict_with_confidence(X_test[:10])
        
        assert len(predictions) == 10
        assert confidence.shape == (10, 2)
        
        # Check confidence intervals make sense
        assert (confidence[:, 0] < predictions).all()  # Lower bound < prediction
        assert (confidence[:, 1] > predictions).all()  # Upper bound > prediction
        assert (confidence[:, 1] - confidence[:, 0] > 0).all()  # Positive width
    
    def test_evaluate(self, model, sample_data):
        """Test model evaluation"""
        X, y = sample_data
        
        # Split data
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        # Fit and evaluate
        model.fit(X_train, y_train)
        metrics = model.evaluate(X_test, y_test)
        
        assert 'mae' in metrics
        assert 'rmse' in metrics
        assert 'r2' in metrics
        assert 'mape' in metrics
        
        # Advanced model should perform well
        assert metrics['mae'] < 6
        assert metrics['r2'] > 0.6
        assert metrics['mape'] < 25
    
    def test_feature_importance(self, model, sample_data):
        """Test feature importance extraction"""
        X, y = sample_data
        
        # Fit model
        model.fit(X[:400], y[:400])
        
        # Get feature importance
        importance_df = model.get_feature_importance()
        
        assert 'feature' in importance_df.columns
        assert 'importance' in importance_df.columns
        assert len(importance_df) == X.shape[1]
        assert importance_df['importance'].sum() > 0
        
        # Check top features make sense
        top_features = importance_df.head(5)['feature'].tolist()
        assert any('distance' in f.lower() for f in top_features)