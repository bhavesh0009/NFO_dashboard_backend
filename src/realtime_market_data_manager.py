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
        Retrieve options tokens from the database.
        
        Args:
            limit: Maximum number of tokens to return
            
        Returns:
            DataFrame containing tokens
        """
        try:
            if not self.db_manager:
                logger.error("No database manager available")
                return pd.DataFrame()
            
            # Query options tokens
            query = """
                SELECT * FROM token_master
                WHERE token_type = 'OPTIONS'
                ORDER BY name, strike, expiry
            """
            
            if limit is not None:
                query += f" LIMIT {limit}"
            
            # Execute query
            tokens_df = self.db_manager.conn.execute(query).fetchdf()
            
            logger.info(f"Retrieved {len(tokens_df)} options tokens from database")
            
            # Debug info about the dataframe structure
            if not tokens_df.empty:
                logger.debug(f"Options dataframe columns: {tokens_df.columns.tolist()}")
                logger.debug(f"Sample options token row: {tokens_df.iloc[0].to_dict()}")
            
            return tokens_df
            
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
            
            # Table is now created in DBManager._init_tables(), so we don't need to create it here
            
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
    
    def get_atm_options_tokens(self, futures_data: List[Dict[str, Any]], strike_buffer: int = 1, exact_atm_only: bool = False) -> pd.DataFrame:
        """
        Get ATM option tokens based on futures prices.
        
        Args:
            futures_data: List of futures data dictionaries with LTP information
            strike_buffer: Number of strikes above and below ATM to include
            exact_atm_only: If True, only select the single closest strike to ATM for each underlying
            
        Returns:
            DataFrame containing only ATM option tokens
        """
        if not futures_data:
            logger.warning("No futures data available to determine ATM options")
            return pd.DataFrame()
            
        # Get all options tokens as base
        all_options = self.get_options_tokens()
        
        if all_options.empty:
            return pd.DataFrame()
            
        # Create mapping of underlying name to futures price using token_master table
        futures_prices = {}
        
        # First, get token IDs from futures data (camelCase in the API response, snake_case in DB)
        if futures_data and len(futures_data) > 0:
            logger.debug(f"Sample data keys: {list(futures_data[0].keys()) if futures_data else 'No data'}")
        
        # Direct lookup approach using futures data only
        if self.db_manager:
            try:
                # Query each token individually (more reliable)
                for data in futures_data:
                    if 'symbolToken' in data and 'ltp' in data:
                        symbol_token = data['symbolToken']
                        ltp = data['ltp']
                        
                        # Query token_master for this token
                        query = """
                            SELECT name FROM token_master
                            WHERE token = ? AND token_type = 'FUTURES'
                        """
                        result = self.db_manager.conn.execute(query, [symbol_token]).fetchone()
                        if result:
                            name = result[0]
                            futures_prices[name] = ltp
                            logger.debug(f"Found name {name} for token {symbol_token} with price {ltp}")
                
                logger.info(f"Direct lookup: Extracted futures prices for {len(futures_prices)} symbols")
                
            except Exception as e:
                logger.error(f"Error in direct futures price lookup: {str(e)}")
        
        if not futures_prices:
            logger.warning("Could not extract futures prices from data")
            return pd.DataFrame()
            
        logger.info(f"Total futures prices available: {len(futures_prices)}")
        for name, price in list(futures_prices.items())[:5]:  # Show first 5 for debugging
            logger.debug(f"Futures price for {name}: {price}")
        
        # Ensure the options dataframe has the correct columns
        required_columns = ['name', 'strike', 'strike_distance']
        missing_columns = [col for col in required_columns if col not in all_options.columns]
        if missing_columns:
            logger.error(f"Options dataframe missing required columns: {missing_columns}")
            # Create a sample row for debugging
            if not all_options.empty:
                logger.debug(f"Sample options row: {all_options.iloc[0].to_dict()}")
                logger.debug(f"Available columns: {all_options.columns.tolist()}")
            return pd.DataFrame()
        
        # Ensure strike column is numeric
        all_options['strike'] = pd.to_numeric(all_options['strike'], errors='coerce')
        
        if exact_atm_only:
            # For exact ATM, we'll find the closest strike per underlying and option type
            logger.info("Using exact ATM mode - selecting only the closest strike per underlying")
            
            # First, group options by name and option type (CE/PE)
            all_options['option_type'] = all_options['symbol'].str.extract(r'(CE|PE)$')
            
            # Create an empty dataframe to store the results
            atm_options = pd.DataFrame()
            
            # For each underlying name and option type
            for name, name_group in all_options.groupby('name'):
                if name not in futures_prices:
                    continue
                    
                future_price = futures_prices[name]
                
                # Get strike distance for this name
                strike_distance = name_group['strike_distance'].iloc[0]
                if pd.isna(strike_distance):
                    # Use default values
                    if name == 'NIFTY':
                        strike_distance = 50
                    elif name == 'BANKNIFTY':
                        strike_distance = 100
                    else:
                        strike_distance = 5
                
                # For each option type (CE/PE), find the closest strike
                for option_type, type_group in name_group.groupby('option_type'):
                    # Calculate distance to ATM for each strike
                    type_group['atm_distance'] = abs(type_group['strike'] - future_price)
                    
                    # Get the row with minimum distance
                    closest_strike = type_group.loc[type_group['atm_distance'].idxmin()]
                    
                    # Add to results
                    atm_options = pd.concat([atm_options, pd.DataFrame([closest_strike])])
            
            logger.info(f"Selected {len(atm_options)} exact ATM options (1 call + 1 put per underlying)")
            return atm_options
        else:
            # Function to determine if an option is ATM or near-ATM
            def is_near_atm(row):
                try:
                    name = row['name']
                    if pd.isna(name) or name not in futures_prices:
                        return False
                    
                    strike = row['strike']
                    if pd.isna(strike):
                        return False
                        
                    future_price = futures_prices[name]
                    strike_distance = row.get('strike_distance')
                    
                    # If strike_distance is not available, use a default value
                    if not strike_distance or pd.isna(strike_distance):
                        # Use common values based on index or stock
                        if name == 'NIFTY':
                            strike_distance = 50
                        elif name == 'BANKNIFTY':
                            strike_distance = 100
                        else:
                            strike_distance = 5  # Default for stocks
                    
                    # Calculate how many strike distances away from ATM
                    strikes_away = abs(future_price - strike) / strike_distance
                    
                    # Return True if within buffer range
                    return strikes_away <= strike_buffer
                except Exception as e:
                    logger.debug(f"Error in is_near_atm for row {row.get('name', 'unknown')}: {str(e)}")
                    return False
            
            try:
                # Filter options to only include ATM and near-ATM
                atm_options = all_options[all_options.apply(is_near_atm, axis=1)]
                
                logger.info(f"Filtered from {len(all_options)} to {len(atm_options)} ATM options (buffer={strike_buffer})")
                return atm_options
            except Exception as e:
                logger.error(f"Error filtering ATM options: {str(e)}")
                if not all_options.empty:
                    logger.debug(f"First few rows of all_options: {all_options.head().to_dict()}")
                return pd.DataFrame()

    def fetch_and_store_realtime_data(self, 
                                     include_equity: bool = True, 
                                     include_futures: bool = True, 
                                     include_options: bool = False,
                                     equity_limit: Optional[int] = None,
                                     futures_limit: Optional[int] = None,
                                     options_limit: Optional[int] = None,
                                     atm_only: bool = True,
                                     strike_buffer: int = 1,
                                     exact_atm_only: bool = False) -> Dict[str, Any]:
        """
        Fetch and store real-time market data for specified instrument types.
        
        Args:
            include_equity: Whether to include equity tokens
            include_futures: Whether to include futures tokens
            include_options: Whether to include options tokens
            equity_limit: Maximum number of equity tokens to include
            futures_limit: Maximum number of futures tokens to include
            options_limit: Maximum number of options tokens to include
            atm_only: Whether to filter options to only ATM strikes (only applies if include_options is True)
            strike_buffer: Number of strikes above and below ATM to include (only applies if atm_only is True)
            exact_atm_only: If True, only select the single closest strike per underlying (only applies if atm_only is True)
            
        Returns:
            Dictionary with results summary
        """
        results = {
            'total': 0,
            'success': 0,
            'equity': 0,
            'futures': 0,
            'options': 0,
            'failures': 0,
            'errors': []
        }
        
        try:
            # First pass: Process equity and futures to get prices
            futures_data = []
            
            if include_futures:
                # Collect futures tokens
                futures_tokens = self.get_futures_tokens(futures_limit)
                logger.info(f"Retrieved {len(futures_tokens)} futures tokens for ATM calculation")
                
                if not futures_tokens.empty:
                    # Prepare exchange tokens for futures
                    futures_exchange_tokens = self.prepare_exchange_tokens(futures_tokens)
                    
                    # Split into batches
                    futures_batches = self.batch_tokens(futures_exchange_tokens)
                    logger.info(f"Split futures tokens into {len(futures_batches)} batches")
                    
                    # Process each batch
                    for i, batch in enumerate(futures_batches):
                        logger.info(f"Processing futures batch {i+1}/{len(futures_batches)}")
                        
                        # Fetch real-time data
                        response = self.fetch_realtime_market_data(batch)
                        
                        if response:
                            # Process response
                            fetched, unfetched = self.process_market_data_response(response)
                            
                            # Store futures data for ATM calculation
                            futures_data.extend(fetched)
                            logger.info(f"Batch {i+1}: Added {len(fetched)} futures records to ATM calculation data")
                            
                            # Store fetched data
                            if fetched:
                                if self.store_realtime_market_data(fetched):
                                    results['success'] += len(fetched)
                                    results['futures'] += len(fetched)
                        else:
                            logger.warning(f"No response for futures batch {i+1}")
                else:
                    logger.warning("No futures tokens found in database")
            
            logger.info(f"Collected {len(futures_data)} total futures records for ATM calculation")
            
            # Log sample of futures data to help with debugging
            if futures_data and len(futures_data) > 0:
                sample = futures_data[0]
                logger.debug(f"Sample futures data: {sample}")
                if 'symbolToken' in sample:
                    logger.debug(f"Sample token: {sample['symbolToken']}")
                if 'tradingSymbol' in sample:
                    logger.debug(f"Sample trading symbol: {sample['tradingSymbol']}")
                if 'ltp' in sample:
                    logger.debug(f"Sample price: {sample['ltp']}")
            
            # Collect tokens
            all_tokens = pd.DataFrame()
            
            if include_equity:
                equity_tokens = self.get_equity_tokens(equity_limit)
                all_tokens = pd.concat([all_tokens, equity_tokens])
            
            # Second pass: Handle options (ATM only if specified) and any remaining equity
            if include_options:
                if atm_only and futures_data:
                    # Get ATM options tokens based on futures prices
                    logger.info(f"Attempting to get ATM options tokens with strike buffer {strike_buffer}, exact_atm_only={exact_atm_only}")
                    options_tokens = self.get_atm_options_tokens(
                        futures_data, 
                        strike_buffer=strike_buffer,
                        exact_atm_only=exact_atm_only
                    )
                    if not options_tokens.empty:
                        logger.info(f"Successfully retrieved {len(options_tokens)} ATM options tokens")
                    else:
                        logger.warning("No ATM options tokens found, check futures price extraction")
                else:
                    # Get all options tokens
                    options_tokens = self.get_options_tokens(options_limit)
                    logger.info(f"Retrieved all {len(options_tokens)} options tokens (not filtered for ATM)")
                
                all_tokens = pd.concat([all_tokens, options_tokens])
            
            # Skip futures since we've already processed them
            # This also prevents processing futures tokens twice
            
            if all_tokens.empty and not futures_data:
                logger.warning("No tokens to process")
                return results
            
            # Prepare exchange tokens if we have any tokens left to process
            if not all_tokens.empty:
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
                                results['success'] += len(fetched)
                                
                                # Count by instrument type
                                for item in fetched:
                                    symbol = item.get('tradingSymbol', '')
                                    if 'FUT' in symbol:
                                        results['futures'] += 1
                                    elif 'CE' in symbol or 'PE' in symbol:
                                        results['options'] += 1
                                    else:
                                        results['equity'] += 1
            
            results['total'] = results['success'] + results['failures']
            return results
            
        except Exception as e:
            error_msg = f"Error fetching and storing real-time data: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            results['failures'] += 1
            return results 