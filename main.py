#!/usr/bin/env python3
"""
Main script for the Angel One Data Pipeline.
Provides functionality for testing and running different components of the pipeline.
"""

import sys
import argparse
from logzero import logger
from src.angel_one_connector import AngelOneConnector
from src.token_manager import TokenManager
from src.db_manager import DBManager
from src.equity_market_data_manager import EquityMarketDataManager

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
            return True
        else:
            logger.error("❌ Failed to connect to Angel One API")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error during testing: {str(e)}")
        return False

def test_token_processing():
    """Test the token processing functionality."""
    # Initialize db_manager outside try block to ensure it's always defined
    db_manager = None
    try:
        # Initialize managers
        logger.info("Initializing Token Manager...")
        db_manager = DBManager()
        token_manager = TokenManager(db_manager)
        
        # Process and store required tokens
        # This will check if tokens need refreshing first and only fetch if necessary
        logger.info("Processing tokens...")
        if token_manager.process_and_store_tokens():
            logger.info("✅ Token processing completed successfully")
            return True
        else:
            logger.error("❌ Failed to process tokens")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error during token processing: {str(e)}")
        return False
    finally:
        # Only close if db_manager was successfully created
        if db_manager:
            db_manager.close()

def test_equity_market_data(limit=5, store=False, verbose=False, interval=None):
    """
    Test fetching market data for equity tokens.
    
    Args:
        limit: Maximum number of tokens to process
        store: Whether to store data in the database
        verbose: Whether to print sample data
        interval: Data interval (ONE_MINUTE, ONE_DAY, etc.) If None, uses config default
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"===== Testing Equity Market Data (%s%sprocessing %d tokens with {interval} interval) =====" % 
                   ('storing, ' if store else '', 'verbose, ' if verbose else '', limit))
        
        # Initialize managers
        db_manager = DBManager()
        manager = EquityMarketDataManager(db_manager=db_manager)
        
        # Process equity market data
        if store:
            logger.info("Fetching and storing equity market data...")
            results = manager.fetch_and_store_equity_market_data(limit=limit, interval=interval)
            operation = "fetch and store"
        else:
            logger.info("Fetching equity market data (without storing)...")
            results = manager.process_equity_market_data(limit=limit, interval=interval)
            operation = "fetch"
        
        # Print summary
        logger.info(f"=== Equity Market Data {operation.capitalize()} Results ===")
        logger.info(f"Tokens processed: {results['success'] + results['errors']}")
        logger.info(f"Successful: {results['success']}")
        logger.info(f"Errors: {results['errors']}")
        
        # Print sample data if verbose mode
        if verbose and results.get("data"):
            logger.info("\n=== Sample Data ===")
            for token, data in results.get("data", {}).items():
                logger.info(f"\nToken: {token}")
                logger.info(f"Name: {data['name']}")
                logger.info(f"Total records: {data['records']}")
                
                if data.get('sample'):
                    logger.info("Sample records:")
                    for idx, record in enumerate(data['sample']):
                        logger.info(f"  Record {idx+1}: {record}")
        
        db_manager.close()
        return results['success'] > 0
        
    except Exception as e:
        logger.error(f"❌ Error testing equity market data: {str(e)}")
        return False

def batch_equity_market_data(batch_size=5, limit=None, verbose=False, interval=None):
    """
    Fetch and store equity market data in batches.
    
    Args:
        batch_size: Number of tokens to process in each batch
        limit: Maximum number of tokens to process (None for all)
        verbose: Whether to print sample data
        interval: Data interval (ONE_MINUTE, ONE_DAY, etc.) If None, uses config default
        
    Returns:
        bool: True if at least one token was processed successfully
    """
    try:
        logger.info(f"===== Batch Processing Equity Market Data with {interval} interval =====")
        logger.info(f"Batch size: {batch_size}, Limit: {limit or 'All'}, Verbose: {verbose}")
        
        # Import here to avoid circular imports
        from scripts.fetch_all_equity_data import fetch_all_equity_data
        
        # Run the batch process
        results = fetch_all_equity_data(batch_size, limit, verbose, interval)
        
        return results.get('success', 0) > 0
        
    except Exception as e:
        logger.error(f"❌ Error in batch processing: {str(e)}")
        return False

def main():
    """Main function with argument parsing for different tasks."""
    parser = argparse.ArgumentParser(description="Angel One Data Pipeline")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Test connection command
    subparsers.add_parser('connection', help='Test connection to Angel One API')
    
    # Token processing command
    subparsers.add_parser('tokens', help='Process and store tokens')
    
    # Equity market data testing command
    equity_parser = subparsers.add_parser('equity', help='Test equity market data functionality')
    equity_parser.add_argument('--limit', type=int, default=5, help='Maximum number of tokens to process')
    equity_parser.add_argument('--store', action='store_true', help='Store data in the database')
    equity_parser.add_argument('--verbose', action='store_true', help='Print sample data')
    equity_parser.add_argument('--interval', type=str, default='ONE_DAY', 
                            help='Data interval (ONE_MINUTE, FIVE_MINUTE, FIFTEEN_MINUTE, THIRTY_MINUTE, ONE_HOUR, ONE_DAY)')
    
    # Batch processing command
    batch_parser = subparsers.add_parser('batch', help='Batch process equity market data')
    batch_parser.add_argument('--batch-size', type=int, default=5, help='Number of tokens to process in each batch')
    batch_parser.add_argument('--limit', type=int, help='Maximum number of tokens to process (None for all)')
    batch_parser.add_argument('--verbose', action='store_true', help='Print sample data')
    batch_parser.add_argument('--interval', type=str, default='ONE_DAY',
                            help='Data interval (ONE_MINUTE, FIVE_MINUTE, FIFTEEN_MINUTE, THIRTY_MINUTE, ONE_HOUR, ONE_DAY)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute the appropriate command
    if args.command == 'connection':
        success = test_connection()
    elif args.command == 'tokens':
        success = test_token_processing()
    elif args.command == 'equity':
        success = test_equity_market_data(args.limit, args.store, args.verbose, args.interval)
    elif args.command == 'batch':
        success = batch_equity_market_data(args.batch_size, args.limit, args.verbose, args.interval)
    else:
        # Default: run basic tests
        logger.info("Running basic tests (no command specified)...")
        logger.info("Tip: Use -h or --help to see available commands")
        
        # Test API connection
        connection_ok = test_connection()
        
        # Test token processing if connection is OK
        tokens_ok = test_token_processing() if connection_ok else False
        
        # Test equity market data with a small limit if tokens are OK
        equity_ok = test_equity_market_data(limit=2, verbose=True, interval="ONE_DAY") if tokens_ok else False
        
        success = connection_ok and tokens_ok and equity_ok
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 