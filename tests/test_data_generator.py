"""Test cases for data generation module"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.data_generator import DubaiDataGenerator
from src.config import config

class TestDubaiDataGenerator:
    """Test suite for DubaiDataGenerator"""
    
    @pytest.fixture
    def generator(self):
        """Create generator instance"""
        return DubaiDataGenerator()
    
    def test_initialization(self, generator):
        """Test generator initialization"""
        assert generator.n_zones == 100
        assert generator.grid_size == 10
        assert len(generator.zone_types) == 100
        
        # Check zone type distribution
        zone_types = list(generator.zone_types.values())
        assert 'business' in zone_types
        assert 'coastal' in zone_types
        assert 'airport' in zone_types
        assert 'residential' in zone_types
    
    def test_dubai_distance_calculation(self, generator):
        """Test Dubai distance calculation"""
        # Test same zone
        assert generator.calculate_dubai_distance(0, 0) == 0
        
        # Test adjacent zones
        assert generator.calculate_dubai_distance(0, 1) == 1
        assert generator.calculate_dubai_distance(0, 10) == 1
        
        # Test diagonal zones
        assert generator.calculate_dubai_distance(0, 11) == 2
        
        # Test maximum distance
        assert generator.calculate_dubai_distance(0, 99) == 18
    
    def test_base_duration_calculation(self, generator):
        """Test base duration calculation"""
        # Test short trip
        duration = generator.calculate_base_duration(0, 1)
        assert 2 <= duration <= 5  # ~3 minutes base + variance
        
        # Test medium trip
        duration = generator.calculate_base_duration(0, 55)
        assert 15 <= duration <= 25  # Business zone adjustment
        
        # Test long trip
        duration = generator.calculate_base_duration(0, 99)
        assert 50 <= duration <= 80  # Airport zone adjustment
    
    def test_temporal_factors(self, generator):
        """Test temporal factor application"""
        base_duration = 20.0
        
        # Test rush hour
        rush_duration = generator.apply_temporal_factors(base_duration, 8, 1)
        assert rush_duration > base_duration * 1.2
        
        # Test late night
        night_duration = generator.apply_temporal_factors(base_duration, 2, 1)
        assert night_duration < base_duration
        
        # Test weekend (Saturday=5, Sunday=6)
        weekend_duration = generator.apply_temporal_factors(base_duration, 12, 6)
        assert weekend_duration != base_duration
    
    def test_weather_events(self, generator):
        """Test weather event application"""
        base_duration = 20.0
        
        # Run multiple times to test probabilistic events
        weather_types = set()
        for _ in range(1000):
            duration, weather = generator.apply_weather_events(base_duration)
            weather_types.add(weather)
            
            if weather == 'sandstorm':
                assert duration > base_duration * 1.2
            elif weather == 'rain':
                assert duration > base_duration * 1.15
            else:
                assert weather == 'clear'
                assert duration == base_duration
        
        # Check all weather types occurred
        assert 'clear' in weather_types
        assert 'sandstorm' in weather_types
        assert 'rain' in weather_types
    
    def test_zone_weighting(self, generator):
        """Test zone sampling weights"""
        # Business hours sampling
        business_hour_samples = []
        for _ in range(1000):
            zone = generator.sample_zone_weighted(9)
            business_hour_samples.append(zone)
        
        # Check business zones are more frequent
        business_zones = [44, 45, 54, 55]
        business_count = sum(1 for z in business_hour_samples if z in business_zones)
        assert business_count > 100  # Should be significantly more than random (40/1000)
        
        # Evening hours sampling
        evening_samples = []
        for _ in range(1000):
            zone = generator.sample_zone_weighted(20)
            evening_samples.append(zone)
        
        # Check coastal zones are more frequent
        coastal_count = sum(1 for z in evening_samples if z % 10 >= 8)
        assert coastal_count > 150  # Should be more than random (200/1000)
    
    def test_dataset_generation(self, generator):
        """Test complete dataset generation"""
        n_trips = 1000
        df = generator.generate_dataset(n_trips=n_trips)
        
        # Check shape and columns
        assert len(df) == n_trips
        expected_columns = [
            'trip_id', 'pickup_zone', 'dropoff_zone', 'request_datetime',
            'actual_duration_minutes', 'dubai_distance', 'hour',
            'day_of_week', 'is_weekend', 'is_rush_hour', 'is_friday_prayer', 'zone_type_pickup',
            'zone_type_dropoff', 'weather', 'has_event', 'driver_efficiency'
        ]
        assert all(col in df.columns for col in expected_columns)
        
        # Check data types
        assert df['pickup_zone'].dtype == 'int64'
        assert df['dropoff_zone'].dtype == 'int64'
        assert pd.api.types.is_datetime64_any_dtype(df['request_datetime'])
        assert df['actual_duration_minutes'].dtype == 'float64'
        
        # Check value ranges
        assert df['pickup_zone'].between(0, 99).all()
        assert df['dropoff_zone'].between(0, 99).all()
        assert (df['pickup_zone'] != df['dropoff_zone']).all()
        assert df['actual_duration_minutes'].min() >= 1
        assert df['hour'].between(0, 23).all()
        assert df['day_of_week'].between(0, 6).all()
        
        # Check boolean columns
        assert df['is_weekend'].isin([True, False]).all()
        assert df['is_rush_hour'].isin([True, False]).all()
        
        # Check categorical columns
        assert df['zone_type_pickup'].isin(['business', 'coastal', 'airport', 'residential']).all()
        assert df['zone_type_dropoff'].isin(['business', 'coastal', 'airport', 'residential']).all()
        assert df['weather'].isin(['clear', 'sandstorm', 'rain']).all()
        
        # Check driver efficiency
        assert df['driver_efficiency'].between(0.5, 1.5).all()
    
    def test_data_split(self, generator):
        """Test chronological data splitting"""
        df = generator.generate_dataset(n_trips=1000)
        train, val, test = generator.split_data(df)
        
        # Check split sizes
        assert len(train) == 700  # 70%
        assert len(val) == 150    # 15%
        assert len(test) == 150   # 15%
        
        # Check chronological order
        assert train['request_datetime'].max() <= val['request_datetime'].min()
        assert val['request_datetime'].max() <= test['request_datetime'].min()
        
    def test_rush_hour_identification(self, generator):
        """Test rush hour identification"""
        assert generator._is_rush_hour(7) == True
        assert generator._is_rush_hour(8) == True
        assert generator._is_rush_hour(9) == True
        assert generator._is_rush_hour(12) == False
        assert generator._is_rush_hour(17) == True
        assert generator._is_rush_hour(18) == True
        assert generator._is_rush_hour(19) == True
        assert generator._is_rush_hour(20) == True
        assert generator._is_rush_hour(21) == False