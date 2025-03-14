"""
Database utilities for the API.
"""
import duckdb
import os
import pandas as pd
from logzero import logger
from src.config_manager import config
from typing import List, Dict, Any

def get_connection():
    """
    Get DuckDB connection from the default database path.
    Opens in read-only mode to allow access while other processes are writing.
    
    IMPORTANT: This function will never delete or recreate the database,
    even if it's corrupted. It will just return None if the database can't be opened.
    """
    db_path = config.get('database', 'default_path')
    
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return None
        
    try:
        # Open in read-only mode to allow concurrent access
        # and prevent any possibility of database modification
        conn = duckdb.connect(db_path, read_only=True)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database in read-only mode: {str(e)}")
        logger.error("The API will NOT attempt to recreate the database. Please fix the database manually.")
        return None

def read_market_summary_from_parquet() -> pd.DataFrame:
    """
    Read market summary data from the Parquet file.
    This avoids direct database access, preventing concurrency issues.
    
    Returns:
        pandas.DataFrame: Market summary data
    """
    parquet_file = os.path.join("exports", "market_summary.parquet")
    
    if not os.path.exists(parquet_file):
        logger.error(f"Market summary Parquet file not found: {parquet_file}")
        return pd.DataFrame()
        
    try:
        # Read the Parquet file into a pandas DataFrame
        df = pd.read_parquet(parquet_file)
        logger.info(f"Read {len(df)} records from {parquet_file}")
        return df
    except Exception as e:
        logger.error(f"Failed to read market summary from Parquet file: {str(e)}")
        return pd.DataFrame()

def get_market_summary() -> List[Dict[str, Any]]:
    """
    Get market summary data from the Parquet file.
    
    Returns:
        List of dictionaries with market summary data
    """
    try:
        # Read market summary from Parquet file
        df = read_market_summary_from_parquet()
        
        if df.empty:
            logger.warning("No market summary data available")
            return []
            
        # Convert DataFrame to list of dictionaries
        return df.to_dict(orient='records')
        
    except Exception as e:
        logger.error(f"Error processing market summary data: {str(e)}")
        return []

def get_market_summary_for_symbol(symbol: str) -> Dict[str, Any]:
    """
    Get market summary for a specific symbol from the Parquet file.
    
    Args:
        symbol: The symbol to get data for
        
    Returns:
        Dictionary with market summary data for the symbol
    """
    try:
        # Read market summary from Parquet file
        df = read_market_summary_from_parquet()
        
        if df.empty:
            logger.warning("No market summary data available")
            return {}
            
        # Filter DataFrame for the symbol
        filtered_df = df[df['symbol'] == symbol]
        
        if filtered_df.empty:
            logger.warning(f"Symbol {symbol} not found in market summary data")
            return {}
            
        # Convert first row to dictionary
        return filtered_df.iloc[0].to_dict()
        
    except Exception as e:
        logger.error(f"Error getting market summary for symbol {symbol}: {str(e)}")
        return {}

def ensure_market_summary_view_exists():
    """
    Check if the market summary Parquet file exists.
    This replaces the previous database view check with a Parquet file check.
    
    Returns:
        bool: True if the file exists, False otherwise
    """
    parquet_file = os.path.join("exports", "market_summary.parquet")
    
    if not os.path.exists(parquet_file):
        logger.error(f"Market summary Parquet file not found: {parquet_file}")
        logger.error("Please run the market data pipeline to generate the Parquet file")
        return False
        
    try:
        # Attempt to read the file to verify it's valid
        df = pd.read_parquet(parquet_file)
        record_count = len(df)
        logger.info(f"✅ Market summary Parquet file verified with {record_count} records")
        return True
    except Exception as e:
        logger.error(f"Failed to read market summary Parquet file: {str(e)}")
        return False 