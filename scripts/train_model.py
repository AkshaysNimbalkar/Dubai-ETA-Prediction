"""Train the ETA prediction models"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import logging
from pathlib import Path
from src.data_generator import DubaiDataGenerator
from src.predictor import ETAPredictor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main training pipeline"""
    
    # Create data directory
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Generate synthetic data
    logger.info("Generating synthetic data...")
    generator = DubaiDataGenerator()
    df = generator.generate_dataset()
    
    # Save raw data
    df.to_csv(data_dir / "raw" / "trips.csv", index=False)
    logger.info(f"Saved {len(df)} trips to data/raw/trips.csv")
    
    # Split data
    train_df, val_df, test_df = generator.split_data(df)
    
    # Save splits
    train_df.to_csv(data_dir / "processed" / "train.csv", index=False)
    val_df.to_csv(data_dir / "processed" / "val.csv", index=False)
    test_df.to_csv(data_dir / "processed" / "test.csv", index=False)
    
    # Train models
    logger.info("Training models...")
    predictor = ETAPredictor()
    predictor.train(train_df, val_df)
    
    # Evaluate models
    logger.info("Evaluating models...")
    results = predictor.evaluate_all(test_df)
    
    for model_name, metrics in results.items():
        logger.info(f"\n{model_name.upper()} Model Performance:")
        for metric, value in metrics.items():
            logger.info(f"  {metric.upper()}: {value:.2f}")
    
    # Save models
    model_dir = data_dir / "models"
    predictor.save(model_dir)
    logger.info(f"Models saved to {model_dir}")
    
    logger.info("Training complete!")

if __name__ == "__main__":
    main()