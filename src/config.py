"""Configuration management for the ETA system"""

import yaml
import os
from pathlib import Path

class Config:
    def __init__(self, config_path=None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
    
    def get(self, key_path, default=None):
        """Get config value using dot notation: 'data.n_zones'"""
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    @property
    def data_config(self):
        return self.config['data']
    
    @property
    def zones_config(self):
        return self.config['zones']
    
    @property
    def traffic_config(self):
        return self.config['traffic']
    
    @property
    def model_config(self):
        return self.config['model']

# Global config instance
config = Config()