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
            # Create a single master table for all tokens
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS token_master (
                    token VARCHAR,
                    symbol VARCHAR,
                    name VARCHAR,
                    expiry DATE,
                    strike DECIMAL(18,6),
                    lotsize INTEGER,
                    instrumenttype VARCHAR,
                    exch_seg VARCHAR,
                    tick_size DECIMAL(18,6),
                    token_type VARCHAR,  -- 'FUTURES' or 'EQUITY'
                    futures_token VARCHAR,  -- Reference to futures token for equity
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (token)
                )
            """)
            
            logger.info("✅ Database tables initialized successfully")
        except Exception as e:
            logger.error(f"❌ Error initializing database tables: {str(e)}")
            raise
    
    def store_tokens(self, tokens_data: pd.DataFrame) -> bool:
        """
        Store filtered tokens data in master table.
        
        Args:
            tokens_data: DataFrame containing both futures and equity tokens
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Define required columns in correct order
            required_columns = [
                'token', 'symbol', 'name', 'expiry', 'strike', 'lotsize',
                'instrumenttype', 'exch_seg', 'tick_size', 'token_type',
                'futures_token'
            ]
            
            # Select and reorder columns
            tokens_data = tokens_data[required_columns].copy()
            
            # Log sample data before storage
            logger.info("\nSample data before storage:")
            logger.info(tokens_data[['symbol', 'token_type', 'expiry', 'futures_token']].head())
            
            # Clear existing data and insert new
            self.conn.execute("DELETE FROM token_master")
            
            # Insert with explicit column specification
            self.conn.execute("""
                INSERT INTO token_master (
                    token, symbol, name, expiry, strike, lotsize,
                    instrumenttype, exch_seg, tick_size, token_type,
                    futures_token, created_at
                )
                SELECT 
                    token, symbol, name, expiry, strike, lotsize,
                    instrumenttype, exch_seg, tick_size, token_type,
                    futures_token, CURRENT_TIMESTAMP
                FROM tokens_data
            """)
            
            # Verify the insertion
            count = self.conn.execute("SELECT COUNT(*) FROM token_master").fetchone()[0]
            logger.info(f"✅ Stored {count} tokens in master table")
            
            # Show sample data by token type
            for token_type in ['FUTURES', 'EQUITY']:
                sample = self.conn.execute(f"""
                    SELECT token, symbol, name, token_type, futures_token, expiry
                    FROM token_master 
                    WHERE token_type = '{token_type}'
                    LIMIT 3
                """).fetchall()
                logger.info(f"\nSample {token_type} data from database:")
                for row in sample:
                    logger.info(row)
            
            return True
        except Exception as e:
            logger.error(f"❌ Error storing tokens: {str(e)}")
            # Log the DataFrame info for debugging
            logger.error("\nDataFrame info:")
            logger.error(f"Columns: {list(tokens_data.columns)}")
            logger.error(f"Shape: {tokens_data.shape}")
            return False
    
    def close(self):
        """Close database connection."""
        self.conn.close() 