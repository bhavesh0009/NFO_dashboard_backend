#!/usr/bin/env python3
"""
Main script for the Angel One Data Pipeline.
Provides functionality for testing and running different components of the pipeline.
"""

import sys
import argparse
import logging
from logzero import logger
from src.angel_one_connector import AngelOneConnector
from src.token_manager import TokenManager
from src.db_manager import DBManager
from src.equity_market_data_manager import EquityMarketDataManager
from src.realtime_market_data_manager import RealtimeMarketDataManager

# Fix logging for Windows consoles
def setup_console_logging():
    """Configure the root logger to prevent Unicode errors in Windows console."""
    # Replace Unicode characters with ASCII equivalents for console output
    class AsciiFormatter(logging.Formatter):
        def format(self, record):
            msg = super().format(record)
            # Replace Unicode characters with ASCII equivalents
            return (msg.replace('✅', '[OK]')
                      .replace('❌', '[ERROR]')
                      .replace('✓', '[Y]')
                      .replace('✗', '[N]'))
    
    # Configure the console handler with the ASCII formatter
    console = logging.StreamHandler()
    console.setFormatter(AsciiFormatter('%(levelname)s %(message)s'))
    logging.getLogger().addHandler(console)
    
    # Remove existing handlers from the root logger
    for handler in logging.getLogger().handlers[:]:
        if isinstance(handler, logging.StreamHandler) and handler != console:
            logging.getLogger().removeHandler(handler)

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

def test_realtime_market_data(include_equity=True, include_futures=True, include_options=False, 
                             equity_limit=None, futures_limit=None, options_limit=None, 
                             store=True, verbose=False, atm_only=True, strike_buffer=1, exact_atm_only=False):
    """
    Test real-time market data functionality.
    
    Args:
        include_equity: Whether to include equity tokens
        include_futures: Whether to include futures tokens
        include_options: Whether to include options tokens
        equity_limit: Maximum number of equity tokens to process
        futures_limit: Maximum number of futures tokens to process
        options_limit: Maximum number of options tokens to process
        store: Whether to store data in database
        verbose: Whether to print sample data
        atm_only: Whether to filter options to only ATM strikes
        strike_buffer: Number of strikes above and below ATM to include
        exact_atm_only: If True, only select the exact ATM strike per underlying
        
    Returns:
        bool: Success status
    """
    try:
        logger.info("Testing real-time market data functionality...")
        
        # Set debug logging if verbose
        if verbose:
            import logging
            logger.setLevel(logging.DEBUG)
            logger.debug("Debug logging enabled")
        
        # Create DBManager instance
        db_manager = DBManager()
        
        # Create RealtimeMarketDataManager instance
        manager = RealtimeMarketDataManager(db_manager=db_manager)
        
        # Fetch and store real-time market data
        results = manager.fetch_and_store_realtime_data(
            include_equity=include_equity,
            include_futures=include_futures,
            include_options=include_options,
            equity_limit=equity_limit,
            futures_limit=futures_limit,
            options_limit=options_limit,
            atm_only=atm_only,
            strike_buffer=strike_buffer,
            exact_atm_only=exact_atm_only
        )
        
        # Print results
        logger.info(f"Processed {results.get('total', 0)} tokens")
        logger.info(f"Success: {results.get('success', 0)}")
        logger.info(f"- Equity: {results.get('equity', 0)}")
        logger.info(f"- Futures: {results.get('futures', 0)}")
        logger.info(f"- Options: {results.get('options', 0)}")
        logger.info(f"Failures: {results.get('failures', 0)}")
        
        # If there were errors, log them
        if results.get('errors'):
            for error in results.get('errors'):
                logger.error(f"Error: {error}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing real-time market data: {str(e)}")
        return False

def main():
    """Main function with argument parsing for different tasks."""
    # Setup console logging for Windows compatibility
    setup_console_logging()
    
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
    
    # Real-time market data command
    realtime_parser = subparsers.add_parser('realtime', help='Fetch real-time market data')
    realtime_parser.add_argument('--no-equity', action='store_true', help='Exclude equity tokens')
    realtime_parser.add_argument('--no-futures', action='store_true', help='Exclude futures tokens')
    realtime_parser.add_argument('--options', action='store_true', help='Include options tokens')
    realtime_parser.add_argument('--equity-limit', type=int, help='Maximum number of equity tokens to process')
    realtime_parser.add_argument('--futures-limit', type=int, help='Maximum number of futures tokens to process')
    realtime_parser.add_argument('--options-limit', type=int, help='Maximum number of options tokens to process')
    realtime_parser.add_argument('--store', action='store_true', help='Store data in database (default)')
    realtime_parser.add_argument('--no-store', action='store_true', help='Do not store data in database')
    realtime_parser.add_argument('--verbose', action='store_true', help='Print sample data')
    realtime_parser.add_argument('--all-options', action='store_true', help='Include all options (not just ATM)')
    realtime_parser.add_argument('--strike-buffer', type=int, default=1, help='Number of strikes above and below ATM to include (default: 1)')
    realtime_parser.add_argument('--exact-atm', action='store_true', help='Select only the exact ATM strike (1 call and 1 put per future)')
    
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
    elif args.command == 'realtime':
        logger.info(f"Running real-time market data command...")
        success = test_realtime_market_data(
            include_equity=not args.no_equity,
            include_futures=not args.no_futures,
            include_options=args.options,
            equity_limit=args.equity_limit,
            futures_limit=args.futures_limit,
            options_limit=args.options_limit,
            store=not args.no_store,
            verbose=args.verbose,
            atm_only=not args.all_options,
            strike_buffer=args.strike_buffer,
            exact_atm_only=args.exact_atm
        )
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