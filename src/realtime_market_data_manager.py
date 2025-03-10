"""
Real-time market data manager for Angel One API.
Handles fetching and processing real-time price data for spot, futures, and options.
"""

import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from logzero import logger
import time
import json

from src.angel_one_connector import AngelOneConnector
from src.db_manager import DBManager
from src.config_manager import config

class RealtimeMarketDataManager:
    """Manages fetching and processing of real-time market data."""
    
    def __init__(self, connector: Optional[AngelOneConnector] = None, db_manager: Optional[DBManager] = None):
        """
        Initialize real-time market data manager.
        
        Args:
            connector: Optional Angel One connector instance
            db_manager: Optional database manager instance
        """
        self.connector = connector or AngelOneConnector()
        self.db_manager = db_manager or DBManager()
        
        # Connect to Angel One API if not already connected
        if not hasattr(self.connector, 'api') or self.connector.api is None:
            logger.info("Connecting to Angel One API")
            self.connector.connect()
        
        # Load configuration
        request_delay = config.get('realtime_market_data', 'rate_limiting', 'request_delay')
        self.rate_limit_delay = 1.0 if request_delay is None else request_delay
        
        max_tokens = config.get('realtime_market_data', 'max_tokens_per_request')
        self.max_tokens_per_request = 50 if max_tokens is None else max_tokens
        
        mode = config.get('realtime_market_data', 'mode')
        self.mode = "FULL" if mode is None else mode
    
    def get_equity_tokens(self, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Get equity tokens from database.
        
        Args:
            limit: Maximum number of tokens to fetch (None for all)
            
        Returns:
            pd.DataFrame: DataFrame with equity token information
        """
        try:
            query = """
                SELECT token, name, exch_seg
                FROM token_master
                WHERE token_type = 'EQUITY'
            """
            
            if limit is not None:
                query += f" LIMIT {limit}"
                
            result = self.db_manager.conn.execute(query).fetchdf()
            logger.info(f"Retrieved {len(result)} equity tokens from database")
            return result
        except Exception as e:
            logger.error(f"Error retrieving equity tokens: {str(e)}")
            return pd.DataFrame()
    
    def get_futures_tokens(self, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Get futures tokens from database.
        
        Args:
            limit: Maximum number of tokens to fetch (None for all)
            
        Returns:
            pd.DataFrame: DataFrame with futures token information
        """
        try:
            query = """
                SELECT token, name, exch_seg
                FROM token_master
                WHERE token_type = 'FUTURES'
            """
            
            if limit is not None:
                query += f" LIMIT {limit}"
                
            result = self.db_manager.conn.execute(query).fetchdf()
            logger.info(f"Retrieved {len(result)} futures tokens from database")
            return result
        except Exception as e:
            logger.error(f"Error retrieving futures tokens: {str(e)}")
            return pd.DataFrame()
    
    def get_options_tokens(self, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Get options tokens from database.
        
        Args:
            limit: Maximum number of tokens to fetch (None for all)
            
        Returns:
            pd.DataFrame: DataFrame with options token information
        """
        try:
            query = """
                SELECT token, name, exch_seg
                FROM token_master
                WHERE token_type = 'OPTIONS'
            """
            
            if limit is not None:
                query += f" LIMIT {limit}"
                
            result = self.db_manager.conn.execute(query).fetchdf()
            logger.info(f"Retrieved {len(result)} options tokens from database")
            return result
        except Exception as e:
            logger.error(f"Error retrieving options tokens: {str(e)}")
            return pd.DataFrame()
    
    def prepare_exchange_tokens(self, tokens_df: pd.DataFrame) -> Dict[str, List[str]]:
        """
        Prepare exchange tokens dictionary for API request.
        
        Args:
            tokens_df: DataFrame with token information
            
        Returns:
            Dict[str, List[str]]: Dictionary with exchange segments as keys and token lists as values
        """
        exchange_tokens = {}
        
        for _, row in tokens_df.iterrows():
            exchange = row['exch_seg']
            token = row['token']
            
            if exchange not in exchange_tokens:
                exchange_tokens[exchange] = []
                
            exchange_tokens[exchange].append(token)
        
        return exchange_tokens
    
    def batch_tokens(self, exchange_tokens: Dict[str, List[str]]) -> List[Dict[str, List[str]]]:
        """
        Split tokens into batches to respect API limits.
        
        Args:
            exchange_tokens: Dictionary with exchange segments as keys and token lists as values
            
        Returns:
            List[Dict[str, List[str]]]: List of exchange token dictionaries, each respecting the API limit
        """
        batches = []
        current_batch = {}
        current_count = 0
        
        for exchange, tokens in exchange_tokens.items():
            # Process tokens for this exchange
            exchange_batches = [tokens[i:i + self.max_tokens_per_request] 
                               for i in range(0, len(tokens), self.max_tokens_per_request)]
            
            for token_batch in exchange_batches:
                if current_count + len(token_batch) <= self.max_tokens_per_request:
                    # Add to current batch
                    if exchange not in current_batch:
                        current_batch[exchange] = []
                    current_batch[exchange].extend(token_batch)
                    current_count += len(token_batch)
                else:
                    # Start a new batch
                    if current_batch:
                        batches.append(current_batch)
                    current_batch = {exchange: token_batch}
                    current_count = len(token_batch)
        
        # Add the last batch if not empty
        if current_batch:
            batches.append(current_batch)
        
        logger.info(f"Split tokens into {len(batches)} batches")
        return batches
    
    def fetch_realtime_market_data(self, exchange_tokens: Dict[str, List[str]]) -> Optional[Dict[str, Any]]:
        """
        Fetch real-time market data for the given exchange tokens.
        
        Args:
            exchange_tokens: Dictionary with exchange segments as keys and token lists as values
            
        Returns:
            Optional[Dict[str, Any]]: Market data response if successful, None otherwise
        """
        try:
            # Ensure we're connected
            if not hasattr(self.connector, 'api') or self.connector.api is None:
                logger.warning("Not connected to Angel One API, attempting to connect...")
                if not self.connector.connect():
                    logger.error("Failed to connect to Angel One API")
                    return None
            
            # Make the API call
            logger.info(f"Fetching real-time market data for {sum(len(tokens) for tokens in exchange_tokens.values())} tokens")
            response = self.connector.api.getMarketData(self.mode, exchange_tokens)
            
            # Check response
            if response.get('status'):
                logger.info("Successfully fetched real-time market data")
                return response
            else:
                logger.error(f"Failed to fetch real-time market data: {response.get('message', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching real-time market data: {str(e)}")
            return None
    
    def process_market_data_response(self, response: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Process market data response.
        
        Args:
            response: Market data response from API
            
        Returns:
            Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]: Tuple of (fetched data, unfetched data)
        """
        fetched = response.get('data', {}).get('fetched', [])
        unfetched = response.get('data', {}).get('unfetched', [])
        
        logger.info(f"Processed market data response: {len(fetched)} fetched, {len(unfetched)} unfetched")
        return fetched, unfetched
    
    def store_realtime_market_data(self, market_data: List[Dict[str, Any]]) -> bool:
        """
        Store real-time market data in the database.
        
        Args:
            market_data: List of market data records
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not market_data:
                logger.warning("No market data to store")
                return False
            
            # Create the table if it doesn't exist
            self.db_manager.conn.execute("""
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
            
            # Process and insert each record
            for record in market_data:
                # Convert depth to JSON string
                depth_json = json.dumps(record.get('depth', {}))
                
                # Parse timestamps
                exch_feed_time = datetime.strptime(record.get('exchFeedTime', ''), '%d-%b-%Y %H:%M:%S') if record.get('exchFeedTime') else None
                exch_trade_time = datetime.strptime(record.get('exchTradeTime', ''), '%d-%b-%Y %H:%M:%S') if record.get('exchTradeTime') else None
                
                # Insert into database
                self.db_manager.conn.execute("""
                    INSERT INTO realtime_market_data (
                        exchange, trading_symbol, symbol_token, ltp, open, high, low, close,
                        last_trade_qty, exch_feed_time, exch_trade_time, net_change, percent_change,
                        avg_price, trade_volume, opn_interest, lower_circuit, upper_circuit,
                        tot_buy_quan, tot_sell_quan, week_low_52, week_high_52, depth_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (symbol_token, timestamp) DO UPDATE SET
                        ltp = excluded.ltp,
                        open = excluded.open,
                        high = excluded.high,
                        low = excluded.low,
                        close = excluded.close,
                        last_trade_qty = excluded.last_trade_qty,
                        net_change = excluded.net_change,
                        percent_change = excluded.percent_change,
                        avg_price = excluded.avg_price,
                        trade_volume = excluded.trade_volume,
                        opn_interest = excluded.opn_interest,
                        depth_json = excluded.depth_json
                """, (
                    record.get('exchange'),
                    record.get('tradingSymbol'),
                    record.get('symbolToken'),
                    record.get('ltp'),
                    record.get('open'),
                    record.get('high'),
                    record.get('low'),
                    record.get('close'),
                    record.get('lastTradeQty'),
                    exch_feed_time,
                    exch_trade_time,
                    record.get('netChange'),
                    record.get('percentChange'),
                    record.get('avgPrice'),
                    record.get('tradeVolume'),
                    record.get('opnInterest'),
                    record.get('lowerCircuit'),
                    record.get('upperCircuit'),
                    record.get('totBuyQuan'),
                    record.get('totSellQuan'),
                    record.get('52WeekLow'),
                    record.get('52WeekHigh'),
                    depth_json
                ))
            
            logger.info(f"Successfully stored {len(market_data)} real-time market data records")
            return True
            
        except Exception as e:
            logger.error(f"Error storing real-time market data: {str(e)}")
            return False
    
    def fetch_and_store_realtime_data(self, 
                                     include_equity: bool = True, 
                                     include_futures: bool = True, 
                                     include_options: bool = False,
                                     equity_limit: Optional[int] = None,
                                     futures_limit: Optional[int] = None,
                                     options_limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetch and store real-time market data for specified instrument types.
        
        Args:
            include_equity: Whether to include equity tokens
            include_futures: Whether to include futures tokens
            include_options: Whether to include options tokens
            equity_limit: Maximum number of equity tokens to process (None for all)
            futures_limit: Maximum number of futures tokens to process (None for all)
            options_limit: Maximum number of options tokens to process (None for all)
            
        Returns:
            Dict[str, Any]: Results dictionary with success and error counts
        """
        results = {
            'success': 0,
            'errors': 0,
            'fetched_tokens': 0,
            'unfetched_tokens': 0
        }
        
        try:
            # Collect tokens
            all_tokens = pd.DataFrame()
            
            if include_equity:
                equity_tokens = self.get_equity_tokens(equity_limit)
                all_tokens = pd.concat([all_tokens, equity_tokens])
            
            if include_futures:
                futures_tokens = self.get_futures_tokens(futures_limit)
                all_tokens = pd.concat([all_tokens, futures_tokens])
            
            if include_options:
                options_tokens = self.get_options_tokens(options_limit)
                all_tokens = pd.concat([all_tokens, options_tokens])
            
            if all_tokens.empty:
                logger.warning("No tokens to process")
                return results
            
            # Prepare exchange tokens
            exchange_tokens = self.prepare_exchange_tokens(all_tokens)
            
            # Split into batches
            batches = self.batch_tokens(exchange_tokens)
            
            # Process each batch
            for i, batch in enumerate(batches):
                logger.info(f"Processing batch {i+1}/{len(batches)}")
                
                # Fetch real-time data
                response = self.fetch_realtime_market_data(batch)
                
                if response:
                    # Process response
                    fetched, unfetched = self.process_market_data_response(response)
                    
                    # Store fetched data
                    if fetched:
                        if self.store_realtime_market_data(fetched):
                            results['success'] += 1
                        else:
                            results['errors'] += 1
                    
                    # Update counts
                    results['fetched_tokens'] += len(fetched)
                    results['unfetched_tokens'] += len(unfetched)
                else:
                    results['errors'] += 1
                
                # Respect rate limit
                if i < len(batches) - 1:  # Don't delay after the last batch
                    logger.info(f"Waiting {self.rate_limit_delay} seconds before next batch...")
                    time.sleep(self.rate_limit_delay)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in fetch_and_store_realtime_data: {str(e)}")
            results['errors'] += 1
            return results 