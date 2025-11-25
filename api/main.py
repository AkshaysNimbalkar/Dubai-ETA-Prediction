"""Main FastAPI application"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import logging
from datetime import datetime

from .schemas import ETARequest, ETAResponse, HealthResponse
from src.predictor import ETAPredictor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Dubai ETA Prediction API",
    description="Predict ride-hailing ETAs in Dubai",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load predictor
predictor = None

@app.on_event("startup")
async def startup_event():
    """Load models on startup"""
    global predictor
    
    model_dir = Path("data/models")
    if model_dir.exists():
        predictor = ETAPredictor.load(model_dir)
        logger.info("Models loaded successfully")
    else:
        logger.warning("No saved models found. Please train models first.")

@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint"""
    return HealthResponse(
        status="healthy",
        model_loaded=predictor is not None,
        version="1.0.0"
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        model_loaded=predictor is not None,
        version="1.0.0"
    )

@app.post("/predict_eta", response_model=ETAResponse)
async def predict_eta(request: ETARequest):
    """Predict ETA for a ride request"""
    
    if predictor is None:
        raise HTTPException(
            status_code=503,
            detail="Models not loaded. Please train models first."
        )
    
    try:
        # Get prediction
        result = predictor.predict(
            pickup_zone=request.pickup_zone,
            dropoff_zone=request.dropoff_zone,
            request_time=request.request_time,
            model_type='advanced'
        )
        
        return ETAResponse(**result)
    
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/zones")
async def get_zones():
    """Get information about all zones"""
    zones = []
    
    # Define zone types (simplified)
    for i in range(100):
        row, col = i // 10, i % 10
        
        # Check airport first (higher priority)
        if i in [98, 99, 88, 89]:
            zone_type = "airport"
        elif i in [44, 45, 54, 55]:
            zone_type = "business"
        elif col >= 8:
            zone_type = "coastal"
        else:
            zone_type = "residential"
        
        zones.append({
            "id": i,
            "row": row,
            "col": col,
            "type": zone_type
        })
    
    return {"zones": zones}