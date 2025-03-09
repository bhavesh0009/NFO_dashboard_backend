#!/usr/bin/env python3
"""
Equity Market Data Batch Processing Module

This module provides functionality for batch processing equity market data.
It can be run directly as a script or imported and used by other modules.

Usage:
    # Import and use in other code:
    from scripts.fetch_all_equity_data import fetch_all_equity_data
    fetch_all_equity_data(batch_size=10, limit=50, verbose=True)
    
    # Run as a script:
    python scripts/fetch_all_equity_data.py --batch-size 10 --limit 50 --verbose
"""

import os
import sys
import time
import argparse
from datetime import datetime
from logzero import logger, logfile

# Add the parent directory to the path to allow imports from src
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.equity_market_data_manager import EquityMarketDataManager
from src.db_manager import DBManager
from src.config_manager import config

def setup_logging():
    """Setup logging with file output."""
    log_dir = os.path.join(parent_dir, 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    today = datetime.now().strftime('%Y%m%d')
    logfile(os.path.join(log_dir, f'equity_market_data_{today}.log'))

def fetch_all_equity_data(batch_size=5, limit=None, verbose=False, interval=None):
    """
    Fetch and store equity market data for all equity tokens.
    
    Args:
        batch_size: Number of tokens to process in each batch
        limit: Maximum number of tokens to process (None for all)
        verbose: Whether to print sample data
        interval: Data interval (ONE_MINUTE, ONE_DAY, etc.) If None, uses config default
    
    Returns:
        dict: Results summary
    """
    try:
        setup_logging()
        
        # Use default interval from config if none provided
        if interval is None:
            interval = config.get('equity_market_data', 'default_interval')
        
        logger.info("=== Starting Equity Market Data Fetch ===")
        logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Initialize managers
        db_manager = DBManager()
        manager = EquityMarketDataManager(db_manager=db_manager)
        
        # Get all equity tokens
        query = """
            SELECT token, name, exch_seg
            FROM token_master
            WHERE token_type = 'EQUITY'
        """
        if limit:
            query += f" LIMIT {limit}"
            
        all_tokens = db_manager.conn.execute(query).fetchdf()
        total_tokens = len(all_tokens)
        logger.info(f"Found {total_tokens} equity tokens to process")
        
        if total_tokens == 0:
            logger.error("No equity tokens found in database")
            return {"success": 0, "errors": 0, "total": 0, "message": "No equity tokens found"}
        
        results = {
            "success": 0,
            "errors": 0,
            "total": total_tokens,
            "batches": []
        }
        
        # Get rate limiting configurations
        request_delay = config.get('equity_market_data', 'rate_limiting', 'request_delay')
        batch_delay = config.get('equity_market_data', 'rate_limiting', 'batch_delay')
        
        # Process in batches
        for i in range(0, total_tokens, batch_size):
            batch = all_tokens.iloc[i:i+batch_size]
            batch_size_actual = len(batch)
            
            logger.info(f"Processing batch {i//batch_size + 1}/{(total_tokens+batch_size-1)//batch_size} ({i+1}-{min(i+batch_size_actual, total_tokens)} of {total_tokens})")
            
            batch_results = {
                "success": 0,
                "errors": 0,
                "tokens": []
            }
            
            # Process each token in the batch
            for _, row in batch.iterrows():
                token = row['token']
                exchange = row['exch_seg']
                name = row['name']
                
                logger.info(f"Processing: {name} ({token})")
                
                # Fetch market data
                market_data = manager.fetch_equity_market_data(token, exchange, name, interval=interval)
                
                if market_data and market_data.get('status'):
                    data = market_data.get('data', [])
                    records_count = len(data)
                    
                    # Store in database
                    if db_manager.store_historical_data(token, name, data):
                        batch_results["success"] += 1
                        results["success"] += 1
                        
                        token_result = {
                            "token": token,
                            "name": name,
                            "records": records_count,
                            "status": "success"
                        }
                        
                        if verbose and data:
                            token_result["sample"] = data[:2]
                            
                        batch_results["tokens"].append(token_result)
                        logger.info(f"✅ Successfully processed {name}: {records_count} records")
                    else:
                        batch_results["errors"] += 1
                        results["errors"] += 1
                        batch_results["tokens"].append({
                            "token": token,
                            "name": name,
                            "status": "store_failed"
                        })
                        logger.error(f"❌ Failed to store data for {name}")
                else:
                    batch_results["errors"] += 1
                    results["errors"] += 1
                    batch_results["tokens"].append({
                        "token": token,
                        "name": name,
                        "status": "fetch_failed"
                    })
                    logger.error(f"❌ Failed to fetch data for {name}")
                
                # Add a small delay to avoid API rate limits
                time.sleep(request_delay)
            
            results["batches"].append(batch_results)
            
            # Log batch summary
            logger.info(f"Batch {i//batch_size + 1} complete: {batch_results['success']} successful, {batch_results['errors']} errors")
            
            # Add a larger delay between batches
            if i + batch_size < total_tokens:
                logger.info(f"Waiting {batch_delay} seconds before next batch...")
                time.sleep(batch_delay)
        
        # Log final summary
        success_rate = (results["success"] / results["total"]) * 100 if results["total"] > 0 else 0
        logger.info("=== Equity Market Data Fetch Complete ===")
        logger.info(f"Total tokens: {results['total']}")
        logger.info(f"Successful: {results['success']} ({success_rate:.2f}%)")
        logger.info(f"Errors: {results['errors']}")
        logger.info(f"Completion time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Close database connection
        db_manager.close()
        return results
        
    except Exception as e:
        logger.error(f"❌ Error fetching equity market data: {str(e)}")
        return {"success": 0, "errors": 0, "total": 0, "error": str(e)}

def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description="Fetch and store equity market data for all equity tokens")
    parser.add_argument("--batch-size", type=int, default=5, help="Number of tokens to process in each batch")
    parser.add_argument("--limit", type=int, help="Maximum number of tokens to process (None for all)")
    parser.add_argument("--verbose", action="store_true", help="Print sample data")
    parser.add_argument("--interval", type=str, help="Data interval (ONE_MINUTE, FIVE_MINUTE, FIFTEEN_MINUTE, THIRTY_MINUTE, ONE_HOUR, ONE_DAY)")
    
    args = parser.parse_args()
    
    # Run the fetch process
    results = fetch_all_equity_data(args.batch_size, args.limit, args.verbose, args.interval)
    
    # Exit with success code if at least one token was processed successfully
    sys.exit(0 if results.get("success", 0) > 0 else 1)

# This allows the module to be imported or run directly
if __name__ == "__main__":
    main() 