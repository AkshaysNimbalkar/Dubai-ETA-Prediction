"""Test cases for FastAPI application"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from api.main import app
from src.predictor import ETAPredictor
from src.data_generator import DubaiDataGenerator

@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)

@pytest.fixture
def trained_model(tmp_path):
    """Create and save a trained model"""
    # Generate sample data
    generator = DubaiDataGenerator()
    df = generator.generate_dataset(n_trips=500)
    train_df, val_df, _ = generator.split_data(df)
    
    # Train model
    predictor = ETAPredictor()
    predictor.train(train_df, val_df)
    
    # Save model
    model_dir = tmp_path / "models"
    predictor.save(model_dir)
    
    # Update app's predictor
    import api.main
    api.main.predictor = ETAPredictor.load(model_dir)
    
    return predictor

class TestAPI:
    """Test suite for FastAPI application"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert 'status' in data
        assert 'model_loaded' in data
        assert 'version' in data
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
    
    def test_zones_endpoint(self, client):
        """Test zones information endpoint"""
        response = client.get("/zones")
        assert response.status_code == 200
        data = response.json()
        assert 'zones' in data
        assert len(data['zones']) == 100
        
        # Check zone structure
        zone = data['zones'][0]
        assert 'id' in zone
        assert 'row' in zone
        assert 'col' in zone
        assert 'type' in zone
    
    def test_predict_without_model(self, client):
        """Test prediction without loaded model"""
        request_data = {
            "pickup_zone": 44,
            "dropoff_zone": 55,
            "request_time": "2024-01-15T08:30:00"
        }
        
        # Clear the predictor
        import api.main
        api.main.predictor = None
        
        response = client.post("/predict_eta", json=request_data)
        assert response.status_code == 503
        assert "not loaded" in response.json()['detail']
    
    def test_predict_success(self, client, trained_model):
        """Test successful prediction"""
        request_data = {
            "pickup_zone": 44,
            "dropoff_zone": 55,
            "request_time": "2024-01-15T08:30:00"
        }
        
        response = client.post("/predict_eta", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert 'estimated_duration_minutes' in data
        assert 'confidence_interval' in data
        assert 'factors' in data
        assert 'metadata' in data
        
        assert data['estimated_duration_minutes'] > 0
        assert len(data['confidence_interval']) == 2
        assert data['confidence_interval'][0] < data['confidence_interval'][1]
    
    def test_predict_validation_errors(self, client, trained_model):
        """Test prediction validation errors"""
        
        # Invalid pickup zone
        response = client.post("/predict_eta", json={
            "pickup_zone": 100,
            "dropoff_zone": 55,
            "request_time": "2024-01-15T08:30:00"
        })
        assert response.status_code == 422
        
        # Invalid dropoff zone
        response = client.post("/predict_eta", json={
            "pickup_zone": 44,
            "dropoff_zone": -1,
            "request_time": "2024-01-15T08:30:00"
        })
        assert response.status_code == 422
        
        # Same pickup and dropoff
        response = client.post("/predict_eta", json={
            "pickup_zone": 44,
            "dropoff_zone": 44,
            "request_time": "2024-01-15T08:30:00"
        })
        assert response.status_code == 422
        
        # Missing request time
        response = client.post("/predict_eta", json={
            "pickup_zone": 44,
            "dropoff_zone": 55
        })
        assert response.status_code == 422
    
    def test_predict_various_scenarios(self, client, trained_model):
        """Test predictions for various scenarios"""
        
        scenarios = [
            # Morning rush hour
            {
                "pickup_zone": 44,
                "dropoff_zone": 55,
                "request_time": "2024-01-15T08:30:00"
            },
            # Late night
            {
                "pickup_zone": 10,
                "dropoff_zone": 90,
                "request_time": "2024-01-15T02:00:00"
            },
            # Weekend
            {
                "pickup_zone": 33,
                "dropoff_zone": 88,
                "request_time": "2024-01-19T14:00:00"
            },
            # Airport trip
            {
                "pickup_zone": 11,
                "dropoff_zone": 99,
                "request_time": "2024-01-15T10:00:00"
            }
        ]
        
        for scenario in scenarios:
            response = client.post("/predict_eta", json=scenario)
            assert response.status_code == 200
            
            data = response.json()
            assert data['estimated_duration_minutes'] > 0
            
            # Check factors are present
            assert 'base_time' in data['factors']
            assert 'traffic_adjustment' in data['factors']
            assert 'zone_complexity' in data['factors']