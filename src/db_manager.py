"""
Database manager for DuckDB operations.
Handles all database interactions for token storage.
"""

import duckdb
import pandas as pd
from logzero import logger
from typing import Optional, List, Dict, Any

class DBManager:
    """Manages DuckDB database operations."""
    
    def __init__(self, db_path: str = "market_data.duckdb"):
        """Initialize database connection."""
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
        self._init_tables()
    
    def _init_tables(self):
        """Initialize required database tables."""
        try:
            # Create table for current expiry futures stocks
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS current_expiry_futures_stocks (
                    token VARCHAR,
                    symbol VARCHAR,
                    name VARCHAR,
                    expiry DATE,
                    strike DECIMAL(18,6),
                    lotsize INTEGER,
                    instrumenttype VARCHAR,
                    exch_seg VARCHAR,
                    tick_size DECIMAL(18,6),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create table for corresponding equity spot tokens
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS equity_spot_tokens (
                    token VARCHAR,
                    symbol VARCHAR,
                    name VARCHAR,
                    lotsize INTEGER,
                    instrumenttype VARCHAR,
                    exch_seg VARCHAR,
                    tick_size DECIMAL(18,6),
                    futures_token VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            logger.info("✅ Database tables initialized successfully")
        except Exception as e:
            logger.error(f"❌ Error initializing database tables: {str(e)}")
            raise
    
    def store_futures_tokens(self, tokens_data: List[Dict[str, Any]]) -> bool:
        """Store futures tokens data."""
        try:
            # Convert to DataFrame and select only required columns
            df = pd.DataFrame(tokens_data)
            
            # Log sample data before storage
            logger.info("Sample data before storage:")
            logger.info(df[['symbol', 'expiry']].head())
            
            required_columns = [
                'token', 'symbol', 'name', 'expiry', 'strike', 
                'lotsize', 'instrumenttype', 'exch_seg', 'tick_size'
            ]
            df = df[required_columns]
            
            # Clear existing data and insert new
            self.conn.execute("DELETE FROM current_expiry_futures_stocks")
            self.conn.execute("INSERT INTO current_expiry_futures_stocks SELECT *, CURRENT_TIMESTAMP FROM df")
            
            # Verify the insertion
            count = self.conn.execute("SELECT COUNT(*) FROM current_expiry_futures_stocks").fetchone()[0]
            logger.info(f"✅ Stored {count} futures tokens")
            
            # Show sample data
            sample = self.conn.execute("""
                SELECT token, symbol, name, expiry, lotsize, instrumenttype 
                FROM current_expiry_futures_stocks 
                LIMIT 3
            """).fetchall()
            logger.info("Sample futures data from database:")
            for row in sample:
                logger.info(row)
            
            return True
        except Exception as e:
            logger.error(f"❌ Error storing futures tokens: {str(e)}")
            # Log the problematic data
            if isinstance(e, (ValueError, TypeError)):
                logger.error("Problematic data sample:")
                for token in tokens_data[:3]:
                    logger.error(f"Token: {token.get('symbol')}, Expiry: {token.get('expiry')}")
            return False
    
    def store_equity_tokens(self, tokens_data: List[Dict[str, Any]], futures_tokens: List[Dict[str, Any]]) -> bool:
        """Store equity spot tokens data with reference to futures tokens."""
        try:
            # Convert to DataFrame and select only required columns
            df = pd.DataFrame(tokens_data)
            required_columns = [
                'token', 'symbol', 'name', 'lotsize', 
                'instrumenttype', 'exch_seg', 'tick_size', 'futures_token'
            ]
            df = df[required_columns]
            
            # Clear existing data and insert new
            self.conn.execute("DELETE FROM equity_spot_tokens")
            self.conn.execute("INSERT INTO equity_spot_tokens SELECT *, CURRENT_TIMESTAMP FROM df")
            
            # Verify the insertion
            count = self.conn.execute("SELECT COUNT(*) FROM equity_spot_tokens").fetchone()[0]
            logger.info(f"✅ Stored {count} equity tokens")
            
            # Show sample data
            sample = self.conn.execute("""
                SELECT token, symbol, name, lotsize, futures_token 
                FROM equity_spot_tokens 
                LIMIT 3
            """).fetchall()
            logger.info("Sample equity data:")
            for row in sample:
                logger.info(row)
            
            return True
        except Exception as e:
            logger.error(f"❌ Error storing equity tokens: {str(e)}")
            return False
    
    def close(self):
        """Close database connection."""
        self.conn.close() 