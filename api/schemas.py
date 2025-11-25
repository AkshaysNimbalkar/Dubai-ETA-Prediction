"""Pydantic schemas for API requests and responses"""

from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import List, Dict, Any

class ETARequest(BaseModel):
    """Request schema for ETA prediction"""
    
    pickup_zone: int = Field(..., ge=0, lt=100, description="Pickup zone ID (0-99)")
    dropoff_zone: int = Field(..., ge=0, lt=100, description="Dropoff zone ID (0-99)")
    request_time: datetime = Field(..., description="Time of ride request")
    
    @validator('dropoff_zone')
    def zones_different(cls, v, values):
        if 'pickup_zone' in values and v == values['pickup_zone']:
            raise ValueError('Pickup and dropoff zones must be different')
        return v

class ETAResponse(BaseModel):
    """Response schema for ETA prediction"""
    
    estimated_duration_minutes: float = Field(..., description="Predicted trip duration in minutes")
    confidence_interval: List[float] = Field(..., description="95% confidence interval [lower, upper]")
    factors: Dict[str, float] = Field(..., description="Breakdown of contributing factors")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")

class HealthResponse(BaseModel):
    """Health check response"""
    
    status: str
    model_loaded: bool
    version: str