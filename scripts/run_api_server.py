"""
Script to run the API server.
"""
import uvicorn
import argparse
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logzero import logger
from src.config_manager import config
from src.db_manager import DBManager

def main():
    """
    Run the FastAPI server.
    """
    parser = argparse.ArgumentParser(description="Run the Market Data API server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    
    args = parser.parse_args()
    
    # Ensure the required data files exist
    try:
        # Check if the market summary Parquet file exists
        from api.db import ensure_market_summary_view_exists
        
        if not ensure_market_summary_view_exists():
            logger.warning("Market summary Parquet file not found or invalid")
            logger.warning("API will start, but data may not be available until the file is generated")
            logger.warning("Run the market data pipeline to generate the required data files")
        
    except Exception as e:
        logger.error(f"❌ Failed to verify data files: {str(e)}")
        logger.warning("API will start, but data may not be available")
    
    # Run the server
    logger.info(f"🚀 Starting API server at {args.host}:{args.port}")
    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )

if __name__ == "__main__":
    main() 