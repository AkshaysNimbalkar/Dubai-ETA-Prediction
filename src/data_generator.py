"""Synthetic data generation for Dubai ETA prediction"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from typing import Dict, Tuple, Optional
import logging

from .config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DubaiDataGenerator:
    """Generate realistic synthetic ride-hailing data for Dubai"""
    
    def __init__(self):
        self.n_zones = config.get('data.n_zones', 100)
        self.grid_size = config.get('data.grid_size', 10)
        self.zone_types = self._define_zone_types()
        self.traffic_config = config.traffic_config
        self.weather_config = config.get('weather')
        
    def _define_zone_types(self) -> Dict[int, str]:
        """Define zone types based on configuration"""
        zone_types = {}
        zones_cfg = config.zones_config
        
        # Initialize all as residential
        for zone in range(self.n_zones):
            zone_types[zone] = 'residential'
        
        # Override with specific types
        for zone_type, zone_data in zones_cfg.items():
            if isinstance(zone_data, dict) and 'cells' in zone_data:
                # New format: zone_data is a dict with 'cells' key
                for zone in zone_data['cells']:
                    zone_types[zone] = zone_type
            elif isinstance(zone_data, list):
                # Old format: zone_data is a list of zones
                for zone_list in zone_data:
                    if isinstance(zone_list, list):
                        for zone in zone_list:
                            zone_types[zone] = zone_type
        
        return zone_types
    
    def calculate_dubai_distance(self, pickup: int, dropoff: int) -> int:
        """Calculate dubai distance between zones"""
        p_row, p_col = pickup // self.grid_size, pickup % self.grid_size
        d_row, d_col = dropoff // self.grid_size, dropoff % self.grid_size
        return abs(p_row - d_row) + abs(p_col - d_col)
    
    def calculate_base_duration(self, pickup: int, dropoff: int) -> float:
        """Calculate base travel duration"""
        distance = self.calculate_dubai_distance(pickup, dropoff)
        
        # Base: 3 minutes per zone
        base_time = distance * 3.0
        
        # Zone type adjustments
        pickup_type = self.zone_types.get(pickup, 'residential')
        dropoff_type = self.zone_types.get(dropoff, 'residential')
        
        zone_factors = {
            'business': 1.2,
            'airport': 1.3,
            'coastal': 1.1,
            'residential': 1.0
        }
        
        # Apply zone complexity
        pickup_factor = zone_factors.get(pickup_type, 1.0)
        dropoff_factor = zone_factors.get(dropoff_type, 1.0)
        base_time *= (pickup_factor + dropoff_factor) / 2
        
        # Add some randomness
        base_time += np.random.normal(0, 1)
        
        return max(1, base_time)
    
    def apply_temporal_factors(self, base_duration: float, 
                              hour: int, day_of_week: int) -> float:
        """Apply time-based traffic patterns"""
        duration = base_duration
        
        # Rush hour effects
        rush_hours_morning = self.traffic_config['rush_hours']['morning']
        rush_hours_evening = self.traffic_config['rush_hours']['evening']
        
        if hour in rush_hours_morning or hour in rush_hours_evening:
            factor = self.traffic_config['rush_hours']['slowdown_factor']
            duration *= np.random.uniform(factor * 0.9, factor * 1.1)
        
        # Late night speedup
        elif hour in self.traffic_config['late_night']['hours']:
            factor = self.traffic_config['late_night']['speedup_factor']
            duration *= np.random.uniform(factor * 0.9, factor * 1.1)
        
        # Friday prayer time (12:00-14:00) - Increased traffic congestion
        if day_of_week == 4 and 12 <= hour <= 13:  # Friday prayer time
            duration *= np.random.uniform(1.25, 1.35)  # 1.3x average slowdown
        
        # Weekend effects (Saturday=5, Sunday=6)
        if day_of_week >= 5:
            if 10 <= hour <= 14:  # Leisure time
                duration *= 1.2
            else:
                duration *= 0.9
        
        return duration
    
    def apply_weather_events(self, duration: float) -> Tuple[float, str]:
        """Apply weather impacts"""
        weather = 'clear'
        
        # Sandstorm
        if random.random() < self.weather_config['sandstorm_prob']:
            weather = 'sandstorm'
            impact = self.weather_config['sandstorm_impact']
            duration *= np.random.uniform(impact * 0.9, impact * 1.1)
        
        # Rain
        elif random.random() < self.weather_config['rain_prob']:
            weather = 'rain'
            impact = self.weather_config['rain_impact']
            duration *= np.random.uniform(impact * 0.9, impact * 1.1)
        
        return duration, weather
    
    def apply_special_events(self, duration: float, zone: int, 
                           timestamp: datetime) -> Tuple[float, bool]:
        """Apply special event impacts"""
        has_event = False
        
        # 10% chance of events, more likely in business/coastal zones
        event_prob = 0.1
        if self.zone_types[zone] in ['business', 'coastal']:
            event_prob = 0.15
        
        if random.random() < event_prob and 18 <= timestamp.hour <= 23:
            has_event = True
            duration *= np.random.uniform(1.5, 2.0)
        
        return duration, has_event
    
    def sample_zone_weighted(self, hour: int) -> int:
        """Sample zones with time-based weights"""
        weights = np.ones(self.n_zones)
        
        # Business districts popular during work hours
        if 7 <= hour <= 18:
            for zone, ztype in self.zone_types.items():
                if ztype == 'business':
                    weights[zone] *= 3
        
        # Coastal areas popular in evening
        if 18 <= hour <= 23:
            for zone, ztype in self.zone_types.items():
                if ztype == 'coastal':
                    weights[zone] *= 2.5
        
        # Airport zones have consistent traffic
        for zone, ztype in self.zone_types.items():
            if ztype == 'airport':
                weights[zone] *= 2
        
        weights = weights / weights.sum()
        return np.random.choice(self.n_zones, p=weights)
    
    def generate_dataset(self, n_trips: Optional[int] = None, 
                        start_date: Optional[str] = None) -> pd.DataFrame:
        """Generate complete synthetic dataset"""
        if n_trips is None:
            n_trips = config.get('data.n_trips', 50000)
        if start_date is None:
            start_date = config.get('data.start_date', '2024-01-01')
        
        logger.info(f"Generating {n_trips} trips starting from {start_date}")
        
        trips = []
        start = datetime.strptime(start_date, '%Y-%m-%d')
        
        for i in range(n_trips):
            if i % 10000 == 0:
                logger.info(f"Generated {i}/{n_trips} trips")
            
            # Random timestamp over 3 months
            days_offset = random.randint(0, 90)
            hours_offset = random.random() * 24
            timestamp = start + timedelta(days=days_offset, hours=hours_offset)
            
            # Sample zones
            pickup = self.sample_zone_weighted(timestamp.hour)
            dropoff = self.sample_zone_weighted(timestamp.hour)
            
            # Ensure different zones
            while dropoff == pickup:
                dropoff = self.sample_zone_weighted(timestamp.hour)
            
            # Calculate duration with all factors
            base_duration = self.calculate_base_duration(pickup, dropoff)
            duration = self.apply_temporal_factors(
                base_duration, timestamp.hour, timestamp.weekday()
            )
            duration, weather = self.apply_weather_events(duration)
            duration, has_event = self.apply_special_events(
                duration, pickup, timestamp
            )
            
            # Driver efficiency
            driver_efficiency = np.random.normal(1.0, 0.15)
            driver_efficiency = max(0.7, min(1.3, driver_efficiency))
            duration *= driver_efficiency
            
            # Create trip record
            trips.append({
                'trip_id': f'trip_{i:06d}',
                'pickup_zone': pickup,
                'dropoff_zone': dropoff,
                'request_datetime': timestamp,
                'actual_duration_minutes': max(1, duration),
                'dubai_distance': self.calculate_dubai_distance(pickup, dropoff),
                'hour': timestamp.hour,
                'day_of_week': timestamp.weekday(),
                'is_weekend': timestamp.weekday() >= 5,
                'is_rush_hour': self._is_rush_hour(timestamp.hour),
                'is_friday_prayer': timestamp.weekday() == 4 and 12 <= timestamp.hour <= 13,
                'zone_type_pickup': self.zone_types[pickup],
                'zone_type_dropoff': self.zone_types[dropoff],
                'weather': weather,
                'has_event': has_event,
                'driver_efficiency': driver_efficiency
            })
        
        logger.info("Dataset generation complete")
        return pd.DataFrame(trips)
    
    def _is_rush_hour(self, hour: int) -> bool:
        """Check if hour is rush hour"""
        rush_hours = (
            self.traffic_config['rush_hours']['morning'] + 
            self.traffic_config['rush_hours']['evening']
        )
        return hour in rush_hours
    
    def split_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Split data chronologically into train/val/test"""
        df = df.sort_values('request_datetime').reset_index(drop=True)
        
        n = len(df)
        train_size = int(n * config.get('data.train_ratio', 0.7))
        val_size = int(n * config.get('data.val_ratio', 0.15))
        
        train_df = df[:train_size]
        val_df = df[train_size:train_size + val_size]
        test_df = df[train_size + val_size:]
        
        logger.info(f"Data split: Train={len(train_df)}, Val={len(val_df)}, Test={len(test_df)}")
        
        return train_df, val_df, test_df