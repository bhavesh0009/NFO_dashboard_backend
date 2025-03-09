"""
Database manager for DuckDB operations.
Handles all database interactions for token storage.
"""

import duckdb
import pandas as pd
from logzero import logger
from typing import Optional, List, Dict, Any
from src.config_manager import config
from datetime import datetime
import os

class DBManager:
    """Manages DuckDB database operations."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Optional database path, uses config value if not provided
        """
        self.db_path = db_path or config.get('database', 'default_path')
        try:
            self.conn = duckdb.connect(self.db_path)
            self._init_tables()
        except duckdb.duckdb.SerializationException as e:
            logger.error(f"❌ Database corruption detected: {str(e)}")
            self._handle_corrupted_database()
    
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
            for token_type in [config.get('token_types', 'futures'), config.get('token_types', 'equity')]:
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
    
    def get_latest_token_update_time(self) -> Optional[datetime]:
        """
        Get the timestamp of the most recent token update.
        
        Returns:
            Optional[datetime]: Timestamp of most recent update or None if no tokens exist
        """
        try:
            result = self.conn.execute("""
                SELECT MAX(created_at) 
                FROM token_master
            """).fetchone()
            
            # Return None if no tokens exist
            if result[0] is None:
                return None
                
            return result[0]
        except Exception as e:
            logger.error(f"❌ Error retrieving latest token update time: {str(e)}")
            return None
    
    def _handle_corrupted_database(self):
        """
        Handle corrupted database file by recreating it.
        This happens when the database file is corrupted, which can occur
        after improper shutdowns or direct SQL manipulation outside the API.
        """
        try:
            logger.warning("Attempting to recover by recreating the database...")
            
            # Close any existing connection
            try:
                if hasattr(self, 'conn') and self.conn:
                    self.conn.close()
            except:
                pass
                
            # Remove the corrupted file if it exists
            if os.path.exists(self.db_path):
                logger.warning(f"Removing corrupted database file: {self.db_path}")
                os.remove(self.db_path)
                
            # Create a fresh connection
            logger.info("Creating new database file...")
            self.conn = duckdb.connect(self.db_path)
            self._init_tables()
            logger.info("✅ Database recovery successful")
        except Exception as e:
            logger.error(f"❌ Failed to recover database: {str(e)}")
            raise
            
    def truncate_tables(self) -> bool:
        """
        Safely truncate all tables in the database.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Truncate the token_master table
            logger.info("Truncating token_master table...")
            self.conn.execute("TRUNCATE TABLE token_master")
            
            # Add any other tables that need truncating here as the application grows
            # self.conn.execute("TRUNCATE TABLE other_table")
            
            logger.info(f"✅ Successfully truncated all tables in database: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Error truncating database tables: {str(e)}")
            return False 