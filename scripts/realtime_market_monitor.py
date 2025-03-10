#!/usr/bin/env python3
"""
Real-time market monitor script.
Continuously fetches real-time market data at regular intervals.
"""

import sys
import time
import argparse
from datetime import datetime, time as dt_time
import signal
from logzero import logger, logfile
import os
import logging

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.realtime_market_data_manager import RealtimeMarketDataManager
from src.db_manager import DBManager
from src.config_manager import config

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

# Global flag for graceful shutdown
running = True

def signal_handler(sig, frame):
    """Handle SIGINT (Ctrl+C) to gracefully shutdown."""
    global running
    logger.info("Received shutdown signal, finishing current cycle and exiting...")
    running = False

def is_market_hours():
    """Check if current time is within market hours."""
    now = datetime.now().time()
    
    # Get market hours from config
    market_start = dt_time.fromisoformat(config.get('market', 'trading_hours', 'start'))
    market_end = dt_time.fromisoformat(config.get('market', 'trading_hours', 'end'))
    
    # Check if current time is within market hours
    return market_start <= now <= market_end

def setup_logging(log_dir):
    """Setup logging with rotation."""
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"realtime_market_monitor_{datetime.now().strftime('%Y%m%d')}.log")
    logfile(log_file, maxBytes=1e6, backupCount=3)  # 1MB max size, 3 backup files
    logger.info(f"Logging to {log_file}")

def run_monitor(refresh_interval=60, include_equity=True, include_futures=True, include_options=False,
               equity_limit=None, futures_limit=None, options_limit=None, 
               atm_only=True, strike_buffer=1, exact_atm_only=False, log_dir="logs"):
    """
    Run continuous monitoring of real-time market data.
    
    Args:
        refresh_interval: Seconds between data refreshes
        include_equity: Whether to include equity tokens
        include_futures: Whether to include futures tokens
        include_options: Whether to include options tokens
        equity_limit: Maximum number of equity tokens to process
        futures_limit: Maximum number of futures tokens to process
        options_limit: Maximum number of options tokens to process
        atm_only: Whether to filter options to only ATM strikes
        strike_buffer: Number of strikes above and below ATM to include
        exact_atm_only: If True, only select the exact ATM strike per underlying
        log_dir: Directory to store log files
    """
    # Setup logging
    setup_logging(log_dir)
    
    # Create database manager
    db_manager = DBManager()
    
    # Create real-time market data manager
    realtime_manager = RealtimeMarketDataManager(db_manager=db_manager)
    
    # Initialize the global running flag
    global running
    running = True
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Log monitor parameters
    logger.info("=" * 60)
    logger.info(f"Starting real-time market monitor with parameters:")
    logger.info(f"- Refresh interval: {refresh_interval} seconds")
    logger.info(f"- Include equity: {include_equity}")
    logger.info(f"- Include futures: {include_futures}")
    logger.info(f"- Include options: {include_options}")
    if equity_limit:
        logger.info(f"- Equity limit: {equity_limit}")
    if futures_limit:
        logger.info(f"- Futures limit: {futures_limit}")
    if options_limit:
        logger.info(f"- Options limit: {options_limit}")
    if include_options:
        logger.info(f"- ATM only: {atm_only}")
        logger.info(f"- Strike buffer: {strike_buffer}")
        logger.info(f"- Exact ATM only: {exact_atm_only}")
    logger.info("=" * 60)
    
    # Main monitoring loop
    iterations = 0
    
    try:
        # Use the running flag instead of True for the while loop condition
        while running:
            iterations += 1
            
            # Check if we should exit
            if not running:
                logger.info("Stopping monitor due to interrupt signal...")
                break
                
            # Check if market is open
            market_open = is_market_hours()
            
            if market_open:
                logger.info(f"Iteration {iterations}: Market is open, fetching data...")
                
                # Fetch and store real-time data
                start_time = time.time()
                results = realtime_manager.fetch_and_store_realtime_data(
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
                elapsed_time = time.time() - start_time
                
                # Print results
                logger.info(f"Processed {results.get('total', 0)} tokens in {elapsed_time:.2f} seconds")
                logger.info(f"Success: {results.get('success', 0)}")
                logger.info(f"- Equity: {results.get('equity', 0)}")
                logger.info(f"- Futures: {results.get('futures', 0)}")
                logger.info(f"- Options: {results.get('options', 0)}")
                logger.info(f"Failures: {results.get('failures', 0)}")
                
                if results.get('errors', []):
                    logger.warning(f"Errors: {len(results.get('errors', []))}")
            else:
                logger.info(f"Iteration {iterations}: Market is closed, skipping data fetch.")
            
            # Wait for next iteration, but check for interrupt every second
            logger.info(f"Waiting {refresh_interval} seconds until next refresh...")
            for _ in range(refresh_interval):
                if not running:
                    logger.info("Stopping monitor due to interrupt signal...")
                    break
                time.sleep(1)
                
    except KeyboardInterrupt:
        # Set running to False if we catch a KeyboardInterrupt
        running = False
        logger.info("Monitor stopped by user.")
    except Exception as e:
        logger.error(f"Monitor stopped due to an error: {str(e)}")
    finally:
        # Close database connection
        if db_manager:
            db_manager.close()
        logger.info("Real-time market monitor shutdown complete.")

def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(description="Continuous real-time market data monitor")
    
    parser.add_argument("--refresh", type=int, default=60,
                        help="Refresh interval in seconds (default: 60)")
    
    parser.add_argument("--no-equity", action="store_true",
                        help="Exclude equity tokens")
    
    parser.add_argument("--no-futures", action="store_true",
                        help="Exclude futures tokens")
    
    parser.add_argument("--options", action="store_true",
                        help="Include options tokens")
    
    parser.add_argument("--equity-limit", type=int,
                        help="Maximum number of equity tokens to process")
    
    parser.add_argument("--futures-limit", type=int,
                        help="Maximum number of futures tokens to process")
    
    parser.add_argument("--options-limit", type=int,
                        help="Maximum number of options tokens to process")
    
    parser.add_argument("--all-options", action="store_true",
                        help="Include all options (not just ATM)")
    
    parser.add_argument("--strike-buffer", type=int, default=1,
                        help="Number of strikes above and below ATM to include (default: 1)")
    
    parser.add_argument("--exact-atm", action="store_true",
                        help="Select only the exact ATM strike (1 call and 1 put per future)")
    
    parser.add_argument("--log-dir", type=str, default="logs",
                        help="Directory to store log files (default: logs)")
    
    args = parser.parse_args()
    
    # Setup console logging
    setup_console_logging()
    
    # Run monitor with arguments
    run_monitor(
        refresh_interval=args.refresh,
        include_equity=not args.no_equity,
        include_futures=not args.no_futures,
        include_options=args.options,
        equity_limit=args.equity_limit,
        futures_limit=args.futures_limit,
        options_limit=args.options_limit,
        atm_only=not args.all_options,
        strike_buffer=args.strike_buffer,
        exact_atm_only=args.exact_atm,
        log_dir=args.log_dir
    )

if __name__ == "__main__":
    main() 