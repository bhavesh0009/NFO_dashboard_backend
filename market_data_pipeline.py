#!/usr/bin/env python3
"""
Angel One Market Data Pipeline Orchestrator

This script orchestrates the complete data pipeline workflow:
1. Token refresh (runs at startup)
2. Historical equity data refresh (runs at startup)
3. Calculate technical indicators (runs after historical data refresh)
4. Waits until market open if necessary
5. Runs real-time market monitoring at specified intervals

Usage:
    python market_data_pipeline.py [options]

Options:
    --no-tokens         Skip token refresh step
    --no-history        Skip historical data refresh step
    --history-limit N   Limit historical data to N equity tokens
    --no-equity         Exclude equity from real-time monitoring
    --no-futures        Exclude futures from real-time monitoring
    --options           Include options in real-time monitoring
    --exact-atm         Use exact ATM strikes only (1 call + 1 put per future)
    --refresh N         Set real-time refresh interval in seconds (default: 60)
    --verbose           Enable verbose output
"""

import os
import sys
import time
import argparse
import signal
from datetime import datetime, time as dt_time
import logging
from logzero import logger, logfile

# Import required modules
from src.token_manager import TokenManager
from src.db_manager import DBManager
from src.equity_market_data_manager import EquityMarketDataManager
from src.angel_one_connector import AngelOneConnector
from src.realtime_market_data_manager import RealtimeMarketDataManager
from src.technical_indicator_manager import TechnicalIndicatorManager
from src.config_manager import config
from scripts.realtime_market_monitor import setup_console_logging, signal_handler

# Global flag for running state
running = True

def setup_logging():
    """Setup logging for the pipeline."""
    os.makedirs("logs", exist_ok=True)
    log_file = os.path.join("logs", f"market_data_pipeline_{datetime.now().strftime('%Y%m%d')}.log")
    logfile(log_file, maxBytes=1e6, backupCount=5)  # 1MB max size, 5 backup files
    logger.info(f"Logging to {log_file}")
    
    # Set logger level to INFO (or DEBUG for verbose)
    logger.setLevel(logging.INFO)

def refresh_tokens(hard_refresh=False):
    """
    Refresh token master data.
    
    Args:
        hard_refresh: Force refresh even if tokens are up to date
        
    Returns:
        bool: Success status
    """
    logger.info("Starting token refresh process...")
    
    db_manager = DBManager()
    token_manager = TokenManager(db_manager=db_manager)
    
    # Check if tokens need refresh
    if token_manager.needs_token_refresh(hard_refresh=hard_refresh):
        logger.info("Tokens need to be refreshed, starting refresh process...")
        success = token_manager.process_and_store_tokens(hard_refresh=hard_refresh)
        if success:
            logger.info("✅ Token refresh completed successfully")
        else:
            logger.error("❌ Token refresh failed")
        return success
    else:
        logger.info("✅ Tokens are already up to date, skipping refresh")
        return True

def refresh_historical_data(limit=None, interval="ONE_DAY", batch_size=5):
    """
    Refresh historical equity data and calculate technical indicators.
    
    Args:
        limit: Maximum number of equity tokens to process
        interval: Data interval to use
        batch_size: Number of tokens to process in each batch
        
    Returns:
        bool: Success status
    """
    logger.info(f"Starting historical data refresh process (limit={limit}, interval={interval})...")
    
    # Create connector and managers
    connector = AngelOneConnector()
    db_manager = DBManager()
    manager = EquityMarketDataManager(connector=connector, db_manager=db_manager)
    
    # Process in batches
    tokens = manager.get_equity_tokens(limit=limit)
    total_tokens = len(tokens)
    logger.info(f"Processing {total_tokens} equity tokens in batches of {batch_size}")
    
    # Calculate total batches
    total_batches = (total_tokens + batch_size - 1) // batch_size
    
    # Process each batch
    batch_delay = config.get('equity_market_data', 'rate_limiting', 'batch_delay') or 2
    
    success_count = 0
    error_count = 0
    
    for i in range(0, total_tokens, batch_size):
        # Check if we should exit
        if not running:
            logger.info("Stopping historical data refresh due to interrupt...")
            break
            
        batch_num = i // batch_size + 1
        batch_end = min(i + batch_size, total_tokens)
        batch_tokens = tokens.iloc[i:batch_end]
        
        logger.info(f"Processing batch {batch_num}/{total_batches} (tokens {i+1}-{batch_end} of {total_tokens})")
        
        for _, token_row in batch_tokens.iterrows():
            token = token_row['token']
            name = token_row['name']
            exchange = token_row['exch_seg']
            
            try:
                # Fetch and store data for this token
                result = manager.fetch_and_store_equity_market_data_for_token(
                    token=token,
                    name=name,
                    exchange=exchange,
                    interval=interval
                )
                
                if result.get('success', False):
                    success_count += 1
                else:
                    error_count += 1
                    
                # Small delay between API requests
                request_delay = config.get('equity_market_data', 'rate_limiting', 'request_delay') or 0.25
                time.sleep(request_delay)
                
            except Exception as e:
                error_count += 1
                logger.error(f"Error processing {name} ({token}): {str(e)}")
        
        # Delay between batches to avoid overloading the API
        if batch_num < total_batches and running:
            logger.info(f"Waiting {batch_delay} seconds before next batch...")
            time.sleep(batch_delay)
    
    # Summary
    logger.info(f"Historical data refresh completed: {success_count} succeeded, {error_count} failed")
    
    # Calculate and store technical indicators after historical data refresh
    if success_count > 0:
        logger.info("Starting technical indicators calculation for all configured indicators...")
        try:
            # Initialize technical indicator manager
            indicator_manager = TechnicalIndicatorManager(db_manager=db_manager)
            
            # Process all configured indicators with the same limit as historical data
            indicator_results = indicator_manager.process_multiple_indicators(limit=limit)
            
            # Log summary of technical indicators processed
            indicators_processed = indicator_results.get('indicators_processed', 0)
            overall_success = indicator_results.get('overall_success', 0)
            overall_errors = indicator_results.get('overall_errors', 0)
            
            logger.info(f"Technical indicators calculation completed:")
            logger.info(f"- Processed {indicators_processed} indicator configurations")
            logger.info(f"- Successfully calculated {overall_success} indicator values")
            logger.info(f"- Encountered {overall_errors} errors")
            
            # Log detailed results for each indicator
            for result in indicator_results.get('results', []):
                indicator_name = result.get('indicator_name', '')
                period = result.get('period', '')
                success = result.get('success', 0)
                total = result.get('total', 0)
                success_rate = (success / total) * 100 if total > 0 else 0
                
                logger.info(f"  - {indicator_name}({period}): {success}/{total} ({success_rate:.2f}%)")
            
            logger.info("Technical indicators processing completed successfully")
            
        except ImportError as e:
            logger.error(f"Failed to calculate technical indicators: {str(e)}")
            logger.error("Make sure pandas_ta is installed: pip install pandas_ta")
        except Exception as e:
            logger.error(f"Failed to calculate technical indicators: {str(e)}")
    else:
        logger.warning("Skipping technical indicators calculation as no historical data was successfully fetched")
    
    return success_count > 0

def is_market_hours():
    """Check if current time is within market hours."""
    now = datetime.now().time()
    
    # Get market hours from config
    market_start_str = config.get('market', 'trading_hours', 'start')
    market_end_str = config.get('market', 'trading_hours', 'end')
    
    # Parse market hours
    market_start = dt_time.fromisoformat(market_start_str)
    market_end = dt_time.fromisoformat(market_end_str)
    
    return market_start <= now <= market_end

def wait_until_market_open():
    """Wait until the market opens if current time is before market hours."""
    if is_market_hours():
        logger.info("Market is already open, proceeding with real-time monitoring")
        return
    
    # Get market open time
    market_start_str = config.get('market', 'trading_hours', 'start')
    market_start = dt_time.fromisoformat(market_start_str)
    
    # Get current time
    now = datetime.now()
    current_date = now.date()
    
    # Create a datetime object for market open today
    market_open_datetime = datetime.combine(current_date, market_start)
    
    # If market open is in the past (meaning we're after market close), skip waiting
    if now > market_open_datetime:
        logger.info("Current time is after market hours, proceeding without waiting")
        return
    
    # Calculate seconds to wait
    wait_seconds = (market_open_datetime - now).total_seconds()
    
    if wait_seconds <= 0:
        return
    
    # Wait until market open, checking every minute if we should exit
    logger.info(f"Market opens at {market_start_str}, waiting {wait_seconds:.1f} seconds ({wait_seconds/60:.1f} minutes)...")
    
    # Wait in smaller increments to allow for interruption
    wait_increment = 30  # seconds
    waited = 0
    
    while waited < wait_seconds and running:
        wait_time = min(wait_increment, wait_seconds - waited)
        time.sleep(wait_time)
        waited += wait_time
        
        remaining = wait_seconds - waited
        if remaining > 0:
            logger.info(f"Still waiting for market open: {remaining:.1f} seconds remaining ({remaining/60:.1f} minutes)")

def run_realtime_monitoring(
    refresh_interval=60,
    include_equity=True,
    include_futures=True,
    include_options=True,
    equity_limit=None,
    futures_limit=None,
    options_limit=None,
    atm_only=True,
    strike_buffer=1,
    exact_atm_only=False
):
    """
    Run real-time market data monitoring.
    
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
        
    Returns:
        bool: Success status
    """
    logger.info("Starting real-time market monitoring...")
    
    # Create database manager
    db_manager = DBManager()
    
    # Create real-time market data manager
    realtime_manager = RealtimeMarketDataManager(db_manager=db_manager)
    
    # Log monitor parameters
    logger.info("=" * 60)
    logger.info(f"Starting real-time market monitoring with parameters:")
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
    
    while running:
        iterations += 1
        
        # Check if we should exit
        if not running:
            logger.info("Stopping real-time monitoring due to interrupt...")
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
                
            # Export market summary after each successful data collection
            if results.get('success', 0) > 0:
                logger.info("Exporting market summary after data refresh...")
                export_success = export_market_summary_to_parquet()
                if not export_success:
                    logger.error("Failed to export market summary to Parquet after iteration")
        else:
            logger.info(f"Iteration {iterations}: Market is closed, skipping data fetch.")
        
        # Wait for next iteration, but check for interrupt every second
        logger.info(f"Waiting {refresh_interval} seconds until next refresh...")
        for _ in range(refresh_interval):
            if not running:
                logger.info("Stopping real-time monitoring due to interrupt...")
                break
            time.sleep(1)
    
    # Close database connection
    if db_manager:
        db_manager.close()
    
    logger.info("Real-time market monitoring stopped")
    return True

def handle_signal(sig, frame):
    """Handle interrupt signals."""
    global running
    logger.info("Received shutdown signal, gracefully shutting down...")
    running = False

def export_market_summary_to_parquet():
    """
    Export market summary view to a Parquet file for API consumption.
    
    Returns:
        bool: Success status
    """
    logger.info("Exporting market summary view to Parquet file for API consumption...")
    try:
        db_manager = DBManager()
        success = db_manager.export_market_summary_to_parquet()
        db_manager.close()
        return success
    except Exception as e:
        logger.error(f"Error exporting market summary to Parquet: {str(e)}")
        return False

def run_pipeline(
    skip_tokens=False,
    skip_history=False,
    history_limit=None,
    include_equity=True,
    include_futures=True,
    include_options=True,
    equity_limit=None,
    futures_limit=None,
    options_limit=None,
    atm_only=True,
    strike_buffer=1,
    exact_atm_only=False,
    refresh_interval=60,
    wait_for_market=True
):
    """
    Run the complete market data pipeline.
    
    Args:
        skip_tokens: Skip token refresh step
        skip_history: Skip historical data refresh step
        history_limit: Limit for historical data refresh
        include_equity: Whether to include equity in real-time monitoring
        include_futures: Whether to include futures in real-time monitoring
        include_options: Whether to include options in real-time monitoring
        equity_limit: Limit for equity tokens in real-time monitoring
        futures_limit: Limit for futures tokens in real-time monitoring
        options_limit: Limit for options tokens in real-time monitoring
        atm_only: Whether to filter options to only ATM strikes
        strike_buffer: Number of strikes above and below ATM to include
        exact_atm_only: Whether to select only the exact ATM strike
        refresh_interval: Seconds between real-time data refreshes
        wait_for_market: Whether to wait for market open before starting real-time monitoring
        
    Returns:
        bool: Success status
    """
    # Register signal handler
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    setup_logging()
    logger.info("=" * 80)
    logger.info(f"STARTING ANGEL ONE MARKET DATA PIPELINE AT {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    # Step 1: Refresh tokens if needed
    if not skip_tokens:
        token_success = refresh_tokens(hard_refresh=False)
        if not token_success:
            logger.error("Token refresh failed, continuing with pipeline...")
    else:
        logger.info("Skipping token refresh as requested")
    
    # Step 2: Refresh historical data if needed
    if not skip_history:
        history_success = refresh_historical_data(limit=history_limit)
        if not history_success:
            logger.error("Historical data refresh failed, continuing with pipeline...")
    else:
        logger.info("Skipping historical data refresh as requested")
    
    # Step 3: Wait for market open if needed
    if wait_for_market:
        wait_until_market_open()
    else:
        logger.info("Skipping wait for market open as requested")
    
    # Step 4: Run real-time monitoring
    if running:
        logger.info("Beginning real-time market monitoring...")
        monitoring_success = run_realtime_monitoring(
            refresh_interval=refresh_interval,
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
    else:
        logger.info("Pipeline interrupted before real-time monitoring could start")
        monitoring_success = False
    
    # Step 5: Export market summary to Parquet file for API consumption
    export_success = export_market_summary_to_parquet()
    if not export_success:
        logger.error("Failed to export market summary to Parquet, API may not have latest data")
    
    logger.info("=" * 80)
    logger.info(f"PIPELINE COMPLETED AT {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    return True

def main():
    """Main entry point with command-line parsing."""
    parser = argparse.ArgumentParser(description="Angel One Market Data Pipeline")
    
    # Token refresh options
    parser.add_argument("--no-tokens", action="store_true", help="Skip token refresh step")
    
    # Historical data options
    parser.add_argument("--no-history", action="store_true", help="Skip historical data refresh step")
    parser.add_argument("--history-limit", type=int, help="Limit historical data to N equity tokens")
    
    # Real-time monitoring options
    parser.add_argument("--no-wait", action="store_true", help="Don't wait for market open before starting real-time monitoring")
    parser.add_argument("--no-equity", action="store_true", help="Exclude equity from real-time monitoring")
    parser.add_argument("--no-futures", action="store_true", help="Exclude futures from real-time monitoring")
    parser.add_argument("--no-options", action="store_true", help="Exclude options from real-time monitoring")
    parser.add_argument("--equity-limit", type=int, help="Limit equity tokens in real-time monitoring")
    parser.add_argument("--futures-limit", type=int, help="Limit futures tokens in real-time monitoring")
    parser.add_argument("--options-limit", type=int, help="Limit options tokens in real-time monitoring")
    parser.add_argument("--all-options", action="store_true", help="Include all options (not just ATM)")
    parser.add_argument("--strike-buffer", type=int, default=1, help="Number of strikes above and below ATM to include (default: 1)")
    parser.add_argument("--exact-atm", action="store_true", help="Select only the exact ATM strike (1 call and 1 put per future)")
    parser.add_argument("--refresh", type=int, default=60, help="Real-time refresh interval in seconds (default: 60)")
    
    # General options
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Setup console logging for Windows compatibility
    setup_console_logging()
    
    # Set logger level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Run the pipeline
    success = run_pipeline(
        skip_tokens=args.no_tokens,
        skip_history=args.no_history,
        history_limit=args.history_limit,
        include_equity=not args.no_equity,
        include_futures=not args.no_futures,
        include_options=not args.no_options,
        equity_limit=args.equity_limit,
        futures_limit=args.futures_limit,
        options_limit=args.options_limit,
        atm_only=not args.all_options,
        strike_buffer=args.strike_buffer,
        exact_atm_only=args.exact_atm,
        refresh_interval=args.refresh,
        wait_for_market=not args.no_wait
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 