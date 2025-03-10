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
               equity_limit=None, futures_limit=None, options_limit=None, log_dir="logs"):
    """
    Run the real-time market monitor.
    
    Args:
        refresh_interval: Seconds between data refreshes
        include_equity: Whether to include equity tokens
        include_futures: Whether to include futures tokens
        include_options: Whether to include options tokens
        equity_limit: Maximum number of equity tokens to process
        futures_limit: Maximum number of futures tokens to process
        options_limit: Maximum number of options tokens to process
        log_dir: Directory for log files
    """
    # Setup logging
    setup_logging(log_dir)
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize managers
    logger.info("Initializing database and market data managers...")
    db_manager = DBManager()
    manager = RealtimeMarketDataManager(db_manager=db_manager)
    
    # Log configuration
    logger.info("=== Real-time Market Monitor Configuration ===")
    logger.info(f"Refresh interval: {refresh_interval} seconds")
    logger.info(f"Equity: {'[Y]' if include_equity else '[N]'} (limit: {equity_limit or 'All'})")
    logger.info(f"Futures: {'[Y]' if include_futures else '[N]'} (limit: {futures_limit or 'All'})")
    logger.info(f"Options: {'[Y]' if include_options else '[N]'} (limit: {options_limit or 'All'})")
    
    # Main monitoring loop
    cycle_count = 0
    total_fetched = 0
    total_errors = 0
    
    logger.info("Starting real-time market monitor...")
    
    try:
        while running:
            cycle_start = datetime.now()
            cycle_count += 1
            
            # Check if within market hours
            if not is_market_hours():
                logger.info("Outside market hours, waiting for next check...")
                time.sleep(refresh_interval)
                continue
            
            logger.info(f"=== Starting data refresh cycle {cycle_count} at {cycle_start.strftime('%H:%M:%S')} ===")
            
            # Fetch and store real-time market data
            results = manager.fetch_and_store_realtime_data(
                include_equity=include_equity,
                include_futures=include_futures,
                include_options=include_options,
                equity_limit=equity_limit,
                futures_limit=futures_limit,
                options_limit=options_limit
            )
            
            # Update statistics
            total_fetched += results['fetched_tokens']
            total_errors += results['errors']
            
            # Log results
            logger.info(f"Cycle {cycle_count} results: {results['fetched_tokens']} tokens fetched, {results['unfetched_tokens']} unfetched")
            
            # Calculate time to wait until next cycle
            cycle_duration = (datetime.now() - cycle_start).total_seconds()
            wait_time = max(0, refresh_interval - cycle_duration)
            
            if wait_time > 0 and running:
                logger.info(f"Waiting {wait_time:.1f} seconds until next refresh cycle...")
                time.sleep(wait_time)
            
    except Exception as e:
        logger.error(f"❌ Error in market monitor: {str(e)}")
    finally:
        # Clean up
        logger.info("=== Real-time Market Monitor Summary ===")
        logger.info(f"Total cycles: {cycle_count}")
        logger.info(f"Total tokens fetched: {total_fetched}")
        logger.info(f"Total errors: {total_errors}")
        
        db_manager.close()
        logger.info("Real-time market monitor stopped")

def main():
    """Main function with argument parsing."""
    # Setup console logging for Windows compatibility
    setup_console_logging()
    
    parser = argparse.ArgumentParser(description="Real-time Market Monitor")
    
    parser.add_argument('--refresh', type=int, default=60, 
                        help='Refresh interval in seconds (default: 60)')
    parser.add_argument('--no-equity', action='store_true', 
                        help='Exclude equity tokens')
    parser.add_argument('--no-futures', action='store_true', 
                        help='Exclude futures tokens')
    parser.add_argument('--options', action='store_true', 
                        help='Include options tokens')
    parser.add_argument('--equity-limit', type=int, 
                        help='Maximum number of equity tokens to process')
    parser.add_argument('--futures-limit', type=int, 
                        help='Maximum number of futures tokens to process')
    parser.add_argument('--options-limit', type=int, 
                        help='Maximum number of options tokens to process')
    parser.add_argument('--log-dir', type=str, default='logs', 
                        help='Directory for log files')
    
    args = parser.parse_args()
    
    run_monitor(
        refresh_interval=args.refresh,
        include_equity=not args.no_equity,
        include_futures=not args.no_futures,
        include_options=args.options,
        equity_limit=args.equity_limit,
        futures_limit=args.futures_limit,
        options_limit=args.options_limit,
        log_dir=args.log_dir
    )

if __name__ == "__main__":
    main() 