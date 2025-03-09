#!/usr/bin/env python3
"""
Main script to test Angel One API connector functionality.
This script serves as a testing ground for the Angel One API integration.
"""

import sys
from logzero import logger
from src.angel_one_connector import AngelOneConnector
from src.token_manager import TokenManager
from src.db_manager import DBManager

def test_connection():
    """Test the connection to Angel One API."""
    try:
        # Initialize the connector
        logger.info("Initializing Angel One connector...")
        connector = AngelOneConnector()
        
        # Test connection
        logger.info("Testing connection to Angel One API...")
        if connector.connect():
            logger.info("✅ Successfully connected to Angel One API")
        else:
            logger.error("❌ Failed to connect to Angel One API")
            
    except Exception as e:
        logger.error(f"❌ Error during testing: {str(e)}")
        sys.exit(1)

def test_token_processing():
    """Test the token processing functionality."""
    try:
        # Initialize managers
        logger.info("Initializing Token Manager...")
        db_manager = DBManager()
        token_manager = TokenManager(db_manager)
        
        # Fetch all tokens
        logger.info("Fetching token master data...")
        if not token_manager.fetch_tokens():
            logger.error("❌ Failed to fetch token data")
            return
        
        # Process and store required tokens
        logger.info("Processing and storing required tokens...")
        if token_manager.process_and_store_tokens():
            logger.info("✅ Successfully processed and stored required tokens")
        else:
            logger.error("❌ Failed to process and store tokens")
            
    except Exception as e:
        logger.error(f"❌ Error during token processing: {str(e)}")
        sys.exit(1)
    finally:
        db_manager.close()

def main():
    """Main function to run tests."""
    logger.info("Starting Angel One API tests...")
    
    # Test API connection
    test_connection()
    
    # Test token processing
    test_token_processing()
    
    logger.info("All tests completed.")

if __name__ == "__main__":
    main() 