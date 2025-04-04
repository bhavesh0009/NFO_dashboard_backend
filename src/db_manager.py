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
                    strike_distance DECIMAL(18,6),  -- Distance between adjacent strikes for options
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (token)
                )
            """)
            
            # Create real-time market data table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS realtime_market_data (
                    exchange VARCHAR,
                    trading_symbol VARCHAR,
                    symbol_token VARCHAR,
                    ltp DECIMAL(18,6),
                    open DECIMAL(18,6),
                    high DECIMAL(18,6),
                    low DECIMAL(18,6),
                    close DECIMAL(18,6),
                    last_trade_qty INTEGER,
                    exch_feed_time TIMESTAMP,
                    exch_trade_time TIMESTAMP,
                    net_change DECIMAL(18,6),
                    percent_change DECIMAL(18,6),
                    avg_price DECIMAL(18,6),
                    trade_volume BIGINT,
                    opn_interest BIGINT,
                    lower_circuit DECIMAL(18,6),
                    upper_circuit DECIMAL(18,6),
                    tot_buy_quan BIGINT,
                    tot_sell_quan BIGINT,
                    week_low_52 DECIMAL(18,6),
                    week_high_52 DECIMAL(18,6),
                    depth_json TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (symbol_token, timestamp)
                )
            """)
            
            # Create historical data table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS historical_data (
                    token VARCHAR,
                    symbol_name VARCHAR,
                    timestamp TIMESTAMP,
                    open DECIMAL(18,6),
                    high DECIMAL(18,6),
                    low DECIMAL(18,6),
                    close DECIMAL(18,6),
                    volume BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (token, timestamp)
                )
            """)
            
            # Create technical indicators table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS technical_indicators (
                    token VARCHAR,
                    symbol_name VARCHAR,
                    indicator_name VARCHAR,
                    timestamp TIMESTAMP,
                    value DECIMAL(18,6),
                    period INTEGER,
                    calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (token, indicator_name, period, timestamp)
                )
            """)
            
            # Create technical_indicators_summary table (wide format, latest values only)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS technical_indicators_summary (
                    token VARCHAR,
                    symbol_name VARCHAR,
                    trade_date DATE,
                    sma_50 DECIMAL(18,6),
                    sma_100 DECIMAL(18,6),
                    sma_200 DECIMAL(18,6),
                    ema_20 DECIMAL(18,6),
                    ema_50 DECIMAL(18,6),
                    ema_200 DECIMAL(18,6),
                    rsi_14 DECIMAL(18,6),
                    rsi_21 DECIMAL(18,6),
                    volatility_21 DECIMAL(18,6),
                    volatility_200 DECIMAL(18,6),
                    last_close DECIMAL(18,6),
                    last_volume BIGINT,
                    update_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (token)
                )
            """)
            
            # Initialize market summary view
            self._init_market_summary_view()
            
            # Check if strike_distance column exists, add it if not (for backward compatibility)
            # Instead of selecting from the column directly, we'll check the information schema
            try:
                # Check if the column exists using information schema
                column_check = self.conn.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'token_master' AND column_name = 'strike_distance'
                """).fetchall()
                
                if not column_check:
                    # Column doesn't exist, add it
                    logger.info("Adding strike_distance column to token_master table...")
                    self.conn.execute("""
                        ALTER TABLE token_master ADD COLUMN strike_distance DECIMAL(18,6)
                    """)
                    logger.info("✅ strike_distance column added successfully")
            except Exception as e:
                # Handle error during column check/addition
                logger.warning(f"⚠️ Note: Could not verify or add strike_distance column: {str(e)}")
                logger.warning("This may happen with a fresh database; proceeding with normal operation.")
            
            logger.info("✅ Database tables initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Error initializing tables: {str(e)}")
            # Check if we need to handle database corruption
            self._handle_corrupted_database()
            return False
    
    def _init_market_summary_view(self):
        """Initialize the market summary view."""
        try:
            # Check if the sql file exists
            sql_path = os.path.join("sqls", "market_summary_view.sql")
            if os.path.exists(sql_path):
                # Read SQL from file
                with open(sql_path, 'r') as f:
                    sql = f.read()
                
                # Execute the SQL to create/replace the view
                self.conn.execute(sql)
                logger.info("✅ Market summary view initialized successfully")
            else:
                logger.warning(f"⚠️ Market summary view SQL file not found: {sql_path}")
        except Exception as e:
            logger.error(f"❌ Error initializing market summary view: {str(e)}")
            
    def export_market_summary_to_parquet(self, output_path=None):
        """
        Export market summary data to a Parquet file.
        
        Args:
            output_path: Optional custom output path for the Parquet file
            
        Returns:
            bool: Success status
        """
        logger.info("Exporting market summary view to Parquet file...")
        try:
            # Check if the view exists
            check_result = self.conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='view' AND name='market_summary_view'
            """).fetchall()
            
            if not check_result:
                logger.warning("The market_summary_view does not exist, attempting to create it")
                self._init_market_summary_view()
                
                # Check again
                check_result = self.conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='view' AND name='market_summary_view'
                """).fetchall()
                
                if not check_result:
                    logger.error("Failed to create market_summary_view")
                    return False
            
            # Query the view
            result = self.conn.execute("SELECT * FROM market_summary_view").fetchdf()
            
            if result.empty:
                logger.warning("The market_summary_view is empty")
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
        except Exception as e:
            logger.error(f"❌ Failed to export market summary: {str(e)}")
            return False
    
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
                'futures_token', 'strike_distance'
            ]
            
            # Select and reorder columns - handle case where strike_distance might not exist
            # in older code still passing data to this method
            df_columns = tokens_data.columns.tolist()
            if 'strike_distance' not in df_columns:
                tokens_data['strike_distance'] = None
                logger.warning("⚠️ strike_distance column not found in input data, adding with NULL values")
            
            # Select and reorder columns
            tokens_data = tokens_data[required_columns].copy()
            
            # Log sample data before storage
            logger.info("\nSample data before storage:")
            logger.info(tokens_data[['symbol', 'token_type', 'expiry', 'futures_token', 'strike_distance']].head())
            
            # Clear existing data and insert new
            self.conn.execute("DELETE FROM token_master")
            
            # Insert with explicit column specification
            self.conn.execute("""
                INSERT INTO token_master (
                    token, symbol, name, expiry, strike, lotsize,
                    instrumenttype, exch_seg, tick_size, token_type,
                    futures_token, strike_distance, created_at
                )
                SELECT 
                    token, symbol, name, expiry, strike, lotsize,
                    instrumenttype, exch_seg, tick_size, token_type,
                    futures_token, strike_distance, CURRENT_TIMESTAMP
                FROM tokens_data
            """)
            
            # Log row count
            count = self.conn.execute("SELECT COUNT(*) FROM token_master").fetchone()[0]
            logger.info(f"✅ Stored {count} tokens in master table")
            
            # Get sample data for verification
            logger.info("\nSample FUTURES data from database:")
            futures_sample = self.conn.execute("""
                SELECT token, symbol, name, token_type, futures_token, expiry 
                FROM token_master 
                WHERE token_type = 'FUTURES' 
                LIMIT 3
            """).fetchall()
            for row in futures_sample:
                logger.info(row)
                
            logger.info("\nSample EQUITY data from database:")
            equity_sample = self.conn.execute("""
                SELECT token, symbol, name, token_type, futures_token, expiry 
                FROM token_master 
                WHERE token_type = 'EQUITY' 
                LIMIT 3
            """).fetchall()
            for row in equity_sample:
                logger.info(row)
                
            # New: Log sample options data to verify strike_distance
            logger.info("\nSample OPTIONS data from database with strike_distance:")
            options_sample = self.conn.execute("""
                SELECT token, symbol, name, token_type, strike, strike_distance 
                FROM token_master 
                WHERE token_type = 'OPTIONS' 
                AND strike_distance IS NOT NULL
                LIMIT 5
            """).fetchall()
            
            if options_sample:
                for row in options_sample:
                    logger.info(row)
            else:
                # Check if there are options without strike_distance
                no_distance_count = self.conn.execute("""
                    SELECT COUNT(*) FROM token_master 
                    WHERE token_type = 'OPTIONS' 
                    AND strike_distance IS NULL
                """).fetchone()[0]
                
                logger.warning(f"⚠️ No options found with strike_distance. {no_distance_count} options have NULL strike_distance.")
                
                # Check if there are any strike_distance values at all
                any_distance = self.conn.execute("""
                    SELECT COUNT(*) FROM token_master 
                    WHERE strike_distance IS NOT NULL
                """).fetchone()[0]
                
                if any_distance > 0:
                    some_distances = self.conn.execute("""
                        SELECT name, strike_distance 
                        FROM token_master 
                        WHERE strike_distance IS NOT NULL
                        GROUP BY name, strike_distance
                        LIMIT 5
                    """).fetchall()
                    logger.info("Some records do have strike_distance values:")
                    for row in some_distances:
                        logger.info(row)
                else:
                    logger.warning("⚠️ No records found with strike_distance values at all.")
                
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
        Truncate all database tables.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.conn.execute("TRUNCATE TABLE token_master")
            logger.info("✅ All tables truncated")
            return True
        except Exception as e:
            logger.error(f"❌ Error truncating tables: {str(e)}")
            return False
            
    def store_historical_data(self, token: str, name: str, data: List[Dict[str, Any]]) -> bool:
        """
        Store historical data for an equity token.
        
        Args:
            token: Symbol token
            name: Name of the equity token
            data: List of historical data records
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Table is now created in _init_tables, no need to create it here
            
            # Format data for insertion
            if not data:
                logger.warning(f"No historical data to store for {name} ({token})")
                return True
                
            # Convert data to dataframe for easier insertion
            # Angel One API typically returns data as:
            # [timestamp, open, high, low, close, volume]
            records = []
            for record in data:
                if len(record) >= 6:  # Ensure record has all required fields
                    records.append({
                        'token': token,
                        'symbol_name': name,
                        'timestamp': record[0],  # timestamp
                        'open': record[1],       # open
                        'high': record[2],       # high
                        'low': record[3],        # low
                        'close': record[4],      # close
                        'volume': record[5]      # volume
                    })
            
            if not records:
                logger.warning(f"Failed to parse historical data for {name} ({token})")
                return False
                
            # Convert to DataFrame and insert
            df = pd.DataFrame(records)
            
            # Insert data with conflict resolution 
            self.conn.execute("""
                INSERT INTO historical_data 
                (token, symbol_name, timestamp, open, high, low, close, volume)
                SELECT token, symbol_name, timestamp, open, high, low, close, volume
                FROM df
                ON CONFLICT(token, timestamp) DO UPDATE SET
                    symbol_name = EXCLUDED.symbol_name,
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume
            """)
            
            logger.info(f"✅ Successfully stored {len(records)} historical records for {name} ({token})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error storing historical data for {name} ({token}): {str(e)}")
            return False
    
    def get_technical_indicators_summary(self, token=None, symbol=None):
        """
        Get the technical indicators summary in wide format.
        
        Args:
            token: Optional token to filter by
            symbol: Optional symbol name to filter by (partial match)
            
        Returns:
            DataFrame with the technical indicators summary
        """
        try:
            query = "SELECT * FROM technical_indicators_summary"
            where_clauses = []
            
            if token:
                where_clauses.append(f"token = '{token}'")
            
            if symbol:
                where_clauses.append(f"symbol_name LIKE '%{symbol}%'")
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            # Add order by
            query += " ORDER BY symbol_name"
            
            # Execute and return as dataframe
            result = self.conn.execute(query).fetchdf()
            
            if result.empty:
                logger.warning("No technical indicators summary data found")
            else:
                logger.info(f"Retrieved {len(result)} records from technical_indicators_summary")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error retrieving technical indicators summary: {str(e)}")
            return pd.DataFrame() 