#!/usr/bin/env python3
"""
Utility script to export market summary data to a Parquet file.
This can be run independently of the market data pipeline.

Usage:
    python utils/export_market_summary.py
"""

import os
import sys
import argparse
from datetime import datetime

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logzero import logger
from src.db_manager import DBManager

def export_market_summary_to_parquet(output_path=None, sql_file=None):
    """
    Export market summary data to a Parquet file for API consumption.
    
    Args:
        output_path: Optional custom output path for the Parquet file
        sql_file: Path to SQL file containing the market summary query
        
    Returns:
        bool: Success status
    """
    logger.info("Exporting market summary data to Parquet file...")
    try:
        # Create database connection
        db_manager = DBManager()
        
        if sql_file:
            # If SQL file is provided, use the direct SQL approach
            if not os.path.exists(sql_file):
                logger.error(f"SQL file not found: {sql_file}")
                return False
                
            # Read SQL from file
            with open(sql_file, 'r') as f:
                sql = f.read()
                
            # Fix common SQL syntax issues - remove trailing parenthesis if present
            sql = sql.strip()
            if sql.endswith(')'):
                sql = sql[:-1]
                logger.info("Fixed trailing parenthesis in SQL query")
            
            logger.info("Executing SQL query directly...")
            
            # Execute SQL query directly
            try:
                result = db_manager.conn.execute(sql).fetchdf()
            except Exception as sql_error:
                logger.error(f"Error executing SQL query: {str(sql_error)}")
                logger.info("Attempting to fix common SQL issues...")
                
                # Try to fix more complex SQL issues
                fixed_sql = sql
                # Remove any invalid trailing characters
                while fixed_sql and fixed_sql[-1] in ',);':
                    fixed_sql = fixed_sql[:-1]
                    
                # Try again with fixed SQL
                try:
                    result = db_manager.conn.execute(fixed_sql).fetchdf()
                    logger.info("Successfully executed SQL with automatic fixes")
                except Exception as retry_error:
                    logger.error(f"Failed to execute SQL even after fixing: {str(retry_error)}")
                    return False
            
            if result.empty:
                logger.warning("The query returned no results")
                return False
                
            # Create exports directory if it doesn't exist
            os.makedirs("exports", exist_ok=True)
            
            # Save to Parquet file
            if output_path:
                parquet_file = output_path
            else:
                parquet_file = os.path.join("exports", "market_summary.parquet")
                
            result.to_parquet(parquet_file, index=False)
            
            logger.info(f"✅ Successfully exported {len(result)} records to {parquet_file}")
            return True
        else:
            # Use the DBManager's built-in export function
            return db_manager.export_market_summary_to_parquet(output_path=output_path)
    except Exception as e:
        logger.error(f"❌ Failed to export market summary: {str(e)}")
        return False
    finally:
        if 'db_manager' in locals() and db_manager:
            db_manager.close()

def main():
    """Script entry point with argument parsing."""
    parser = argparse.ArgumentParser(description="Export market summary to a Parquet file")
    parser.add_argument("--output", "-o", help="Custom output path for the Parquet file")
    parser.add_argument("--sql", "-s", help="Path to SQL file containing the market summary query")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Run the export
    start_time = datetime.now()
    logger.info(f"Starting export at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = export_market_summary_to_parquet(output_path=args.output, sql_file=args.sql)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    if success:
        logger.info(f"Export completed successfully in {duration:.2f} seconds")
        sys.exit(0)
    else:
        logger.error(f"Export failed after {duration:.2f} seconds")
        sys.exit(1)

if __name__ == "__main__":
    main() 