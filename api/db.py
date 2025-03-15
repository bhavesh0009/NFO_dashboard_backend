"""
Database utilities for the API.
"""
import duckdb
import os
import pandas as pd
from logzero import logger
from src.config_manager import config
from typing import List, Dict, Any, Optional

from src.db_manager import DBManager

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

def get_market_summary(symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get market summary data from the database.
    
    Args:
        symbol: Optional symbol to filter by
        
    Returns:
        List of market summary records
    """
    try:
        # Get market summary from parquet file (preferred) or fallback to database query
        exports_dir = 'exports'
        parquet_file = os.path.join(exports_dir, 'market_summary.parquet')
        
        if os.path.exists(parquet_file):
            # Read from parquet file
            df = pd.read_parquet(parquet_file)
            
            # Filter by symbol if provided
            if symbol:
                # Case-insensitive partial match
                symbol_lower = symbol.lower()
                df = df[df['symbol'].str.lower().str.contains(symbol_lower) | 
                         df['name'].str.lower().str.contains(symbol_lower)]
            
            # Convert to list of dictionaries
            return df.to_dict(orient='records')
        else:
            logger.warning(f"Parquet file not found at {parquet_file}, falling back to database query")
            
            # Fallback to database query
            db_manager = DBManager()
            if not db_manager.conn:
                logger.error("Failed to connect to database")
                return []
                
            # Ensure the market_summary_view exists
            db_manager._init_market_summary_view()
            
            # Build query
            query = "SELECT * FROM market_summary_view"
            if symbol:
                symbol_param = f"%{symbol}%"
                query += f" WHERE symbol LIKE '{symbol_param}' OR name LIKE '{symbol_param}'"
                
            # Execute query
            results = db_manager.conn.execute(query).fetchdf()
            db_manager.close()
            
            if results.empty:
                return []
                
            # Convert to list of dictionaries
            return results.to_dict(orient='records')
            
    except Exception as e:
        logger.error(f"Error retrieving market summary: {str(e)}")
        return []

def filter_market_summary(
    min_ltp: Optional[float] = None,
    max_ltp: Optional[float] = None,
    min_percent_change: Optional[float] = None,
    max_percent_change: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Filter market summary data based on criteria.
    
    Args:
        min_ltp: Minimum Last Traded Price
        max_ltp: Maximum Last Traded Price
        min_percent_change: Minimum percentage change
        max_percent_change: Maximum percentage change
        
    Returns:
        Filtered list of market summary records
    """
    try:
        # Get all market summary data
        all_data = get_market_summary()
        
        # No data or no filters
        if not all_data or (min_ltp is None and max_ltp is None and 
                           min_percent_change is None and max_percent_change is None):
            return all_data
            
        # Convert to pandas DataFrame for easier filtering
        df = pd.DataFrame(all_data)
        
        # Apply filters
        if min_ltp is not None:
            df = df[df['ltp'] >= min_ltp]
            
        if max_ltp is not None:
            df = df[df['ltp'] <= max_ltp]
            
        if min_percent_change is not None:
            df = df[df['percent_change'] >= min_percent_change]
            
        if max_percent_change is not None:
            df = df[df['percent_change'] <= max_percent_change]
            
        # Return filtered data
        return df.to_dict(orient='records')
        
    except Exception as e:
        logger.error(f"Error filtering market summary: {str(e)}")
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

def get_technical_indicators_summary(token=None, symbol=None) -> List[Dict[str, Any]]:
    """
    Get technical indicators summary from the database.
    
    Args:
        token: Optional token to filter by
        symbol: Optional symbol name to filter by (partial match)
        
    Returns:
        List of technical indicators summary records
    """
    try:
        db_manager = DBManager()
        results = db_manager.get_technical_indicators_summary(token=token, symbol=symbol)
        db_manager.close()
        
        if results.empty:
            return []
            
        # Convert DataFrame to list of dicts
        return results.to_dict(orient='records')
        
    except Exception as e:
        logger.error(f"Error retrieving technical indicators summary: {str(e)}")
        return [] 