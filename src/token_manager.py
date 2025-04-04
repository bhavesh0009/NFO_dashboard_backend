"""
Token Manager for Angel One API.
Handles fetching and processing of token master data.
"""

import json
import requests
import pandas as pd
from datetime import datetime, time
from typing import Optional, Dict, List, Any, Tuple
from logzero import logger
from src.db_manager import DBManager
from src.config_manager import config

class TokenManager:
    """Manages token data from Angel One API."""
    
    def __init__(self, db_manager: Optional[DBManager] = None):
        """Initialize TokenManager."""
        self.tokens_df: Optional[pd.DataFrame] = None
        self.db_manager = db_manager or DBManager()
    
    def needs_token_refresh(self, hard_refresh: bool = False) -> bool:
        """
        Check if tokens need to be refreshed.
        
        Tokens need refresh if:
        1. hard_refresh is True, OR
        2. No tokens exist in database, OR
        3. Last update time is earlier than pre-market start time of current day
        
        Args:
            hard_refresh: Force refresh regardless of last update time
            
        Returns:
            bool: True if tokens need refresh, False otherwise
        """
        if hard_refresh:
            logger.info("Hard refresh requested, will refresh tokens.")
            return True
            
        # Get latest token update time
        latest_update = self.db_manager.get_latest_token_update_time()
        
        # If no tokens exist, need refresh
        if latest_update is None:
            logger.info("No tokens found in database, refresh needed.")
            return True
            
        # Get current date and pre-market start time
        current_date = datetime.now().date()
        pre_market_start_str = config.get('market', 'pre_market', 'start')
        
        try:
            # Parse pre-market start time
            pre_market_hour, pre_market_minute = map(int, pre_market_start_str.split(':'))
            pre_market_start_time = time(pre_market_hour, pre_market_minute)
            
            # Combine current date with pre-market start time
            pre_market_start_datetime = datetime.combine(current_date, pre_market_start_time)
            
            # Check if last update is before pre-market start
            if latest_update < pre_market_start_datetime:
                logger.info(f"Token data last updated at {latest_update}, which is before today's pre-market start ({pre_market_start_datetime}). Refresh needed.")
                return True
            else:
                logger.info(f"Token data already refreshed at {latest_update}, which is after today's pre-market start ({pre_market_start_datetime}). No refresh needed. Skipping API call for 120K+ tokens.")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error checking token refresh need: {str(e)}")
            # Default to refresh on error
            return True
    
    def fetch_tokens(self) -> bool:
        """
        Fetch token master data from Angel One API.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Fetching token master data from Angel One API...")
            url = config.get('api', 'angel_one', 'token_master_url')
            response = requests.get(url)
            response.raise_for_status()
            
            # Convert to DataFrame immediately
            self.tokens_df = pd.DataFrame(response.json())
            logger.info(f"✅ Successfully fetched {len(self.tokens_df)} tokens")
            
            return True
            
        except requests.RequestException as e:
            logger.error(f"❌ Failed to fetch token data: {str(e)}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse token data: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error while fetching tokens: {str(e)}")
            return False
    
    def process_futures_tokens(self) -> Optional[pd.DataFrame]:
        """
        Process F&O stocks with nearest expiry date.
        
        Returns:
            Optional[pd.DataFrame]: Filtered futures tokens
        """
        if self.tokens_df is None:
            logger.error("❌ No token data available. Call fetch_tokens() first.")
            return None
            
        try:
            # Get configuration values
            futures_type = config.get('instrument_types', 'futures_stock')
            nfo_segment = config.get('exchange_segments', 'nfo')
            expiry_format = config.get('date_formats', 'expiry')
            db_date_format = config.get('date_formats', 'db_date')
            
            # Filter futures stocks
            futures_df = self.tokens_df[
                (self.tokens_df['instrumenttype'] == futures_type) & 
                (self.tokens_df['exch_seg'] == nfo_segment)
            ].copy()
            
            if futures_df.empty:
                logger.error("❌ No futures tokens found")
                return None
            
            # Check all distinct expiry formats
            distinct_expiry_formats = futures_df['expiry'].unique()
            logger.info("\nAll distinct expiry formats found in futures:")
            for expiry in sorted(distinct_expiry_formats):
                logger.info(f"Expiry format: {expiry}")
            
            # Convert expiry strings to dates
            futures_df['expiry_date'] = pd.to_datetime(
                futures_df['expiry'], 
                format=expiry_format
            ).dt.date
            
            # Find minimum expiry and filter
            min_expiry = futures_df['expiry_date'].min()
            current_expiry_futures = futures_df[
                futures_df['expiry_date'] == min_expiry
            ].copy()
            
            # Convert expiry to standard format
            current_expiry_futures['expiry'] = current_expiry_futures['expiry_date'].apply(
                lambda x: x.strftime(db_date_format)
            )
            
            # Add token type and futures token reference
            current_expiry_futures['token_type'] = config.get('token_types', 'futures')
            current_expiry_futures['futures_token'] = None
            
            # Ensure numeric columns are properly typed
            current_expiry_futures['strike'] = pd.to_numeric(current_expiry_futures['strike'], errors='coerce')
            current_expiry_futures['lotsize'] = pd.to_numeric(current_expiry_futures['lotsize'], errors='coerce')
            current_expiry_futures['tick_size'] = pd.to_numeric(current_expiry_futures['tick_size'], errors='coerce')
            
            # Drop temporary column
            current_expiry_futures.drop('expiry_date', axis=1, inplace=True)
            
            logger.info(f"✅ Found {len(current_expiry_futures)} current expiry futures")
            return current_expiry_futures
            
        except Exception as e:
            logger.error(f"❌ Error processing futures tokens: {str(e)}")
            return None
    
    def process_options_tokens(self) -> Optional[pd.DataFrame]:
        """
        Process options stocks with nearest expiry date.
        
        Returns:
            Optional[pd.DataFrame]: Filtered options tokens
        """
        if self.tokens_df is None:
            logger.error("❌ No token data available. Call fetch_tokens() first.")
            return None
            
        try:
            # Get configuration values
            options_type = config.get('instrument_types', 'options_stock')
            nfo_segment = config.get('exchange_segments', 'nfo')
            expiry_format = config.get('date_formats', 'expiry')
            db_date_format = config.get('date_formats', 'db_date')
            
            # Filter options stocks
            options_df = self.tokens_df[
                (self.tokens_df['instrumenttype'] == options_type) & 
                (self.tokens_df['exch_seg'] == nfo_segment)
            ].copy()
            
            if options_df.empty:
                logger.error("❌ No options tokens found")
                return None
            
            # Check all distinct expiry formats
            distinct_expiry_formats = options_df['expiry'].unique()
            logger.info("\nAll distinct expiry formats found in options:")
            for expiry in sorted(distinct_expiry_formats):
                logger.info(f"Expiry format: {expiry}")
            
            # Convert expiry strings to dates
            options_df['expiry_date'] = pd.to_datetime(
                options_df['expiry'], 
                format=expiry_format
            ).dt.date
            
            # Find minimum expiry and filter
            min_expiry = options_df['expiry_date'].min()
            current_expiry_options = options_df[
                options_df['expiry_date'] == min_expiry
            ].copy()
            
            # Convert expiry to standard format
            current_expiry_options['expiry'] = current_expiry_options['expiry_date'].apply(
                lambda x: x.strftime(db_date_format)
            )
            
            # Add token type and futures token reference
            current_expiry_options['token_type'] = config.get('token_types', 'options')
            current_expiry_options['futures_token'] = None  # Will be mapped later
            
            # Ensure numeric columns are properly typed
            current_expiry_options['strike'] = pd.to_numeric(current_expiry_options['strike'], errors='coerce')
            # Divide strike by 100 as the API returns strike with two additional zeroes
            current_expiry_options['strike'] = current_expiry_options['strike'] / 100
            current_expiry_options['lotsize'] = pd.to_numeric(current_expiry_options['lotsize'], errors='coerce')
            current_expiry_options['tick_size'] = pd.to_numeric(current_expiry_options['tick_size'], errors='coerce')
            
            # Calculate strike distance for each name
            strike_distances = {}
            for name, group in current_expiry_options.groupby('name'):
                # Get unique strikes and sort them
                unique_strikes = sorted(group['strike'].unique())
                
                if len(unique_strikes) > 1:
                    # Calculate differences between adjacent strikes
                    differences = [round(unique_strikes[i+1] - unique_strikes[i], 2) for i in range(len(unique_strikes)-1)]
                    
                    if differences:
                        # Find the most common difference (mode)
                        from collections import Counter
                        counter = Counter(differences)
                        strike_distance = counter.most_common(1)[0][0]
                        strike_distances[name] = strike_distance
            
            # Add strike_distance to dataframe
            current_expiry_options['strike_distance'] = current_expiry_options['name'].map(strike_distances)
            
            # Log strike distances
            logger.info("\nCalculated strike distances:")
            strike_distance_df = pd.DataFrame(list(strike_distances.items()), columns=['name', 'strike_distance'])
            logger.info(strike_distance_df.head())
            
            # Drop temporary column
            current_expiry_options.drop('expiry_date', axis=1, inplace=True)
            
            # Log some statistics about the options
            logger.info(f"✅ Found {len(current_expiry_options)} current expiry options")
            logger.info("\nOptions strike price distribution:")
            logger.info(current_expiry_options.groupby('name')['strike'].agg(['count', 'min', 'max']).head())
            
            return current_expiry_options
            
        except Exception as e:
            logger.error(f"❌ Error processing options tokens: {str(e)}")
            return None
    
    def process_equity_tokens(self, futures_df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Get corresponding equity spot tokens for futures.
        
        Args:
            futures_df: DataFrame of futures tokens
            
        Returns:
            Optional[pd.DataFrame]: Filtered equity tokens
        """
        if self.tokens_df is None:
            logger.error("❌ No token data available. Call fetch_tokens() first.")
            return None
            
        try:
            # Get configuration values
            nse_segment = config.get('exchange_segments', 'nse')
            
            # Create equity symbols from futures names
            futures_names = set(futures_df['name'])
            equity_symbols = {f"{name}-EQ" for name in futures_names}
            
            # Filter equity tokens
            equity_df = self.tokens_df[
                (self.tokens_df['exch_seg'] == nse_segment) & 
                (self.tokens_df['symbol'].isin(equity_symbols))
            ].copy()
            
            if equity_df.empty:
                logger.error("❌ No matching equity tokens found")
                return None
            
            # Add token type
            equity_df['token_type'] = config.get('token_types', 'equity')
            
            # Map futures tokens
            equity_df['base_name'] = equity_df['symbol'].str.replace('-EQ', '')
            futures_token_map = futures_df.set_index('name')['token'].to_dict()
            equity_df['futures_token'] = equity_df['base_name'].map(futures_token_map)
            
            # Ensure numeric columns are properly typed
            equity_df['strike'] = 0.0  # Equity tokens don't have strike price
            equity_df['lotsize'] = pd.to_numeric(equity_df['lotsize'], errors='coerce')
            equity_df['tick_size'] = pd.to_numeric(equity_df['tick_size'], errors='coerce')
            
            # Set expiry to NULL for equity tokens
            equity_df['expiry'] = None
            
            # Drop temporary column
            equity_df.drop('base_name', axis=1, inplace=True)
            
            logger.info(f"✅ Found {len(equity_df)} corresponding equity tokens")
            return equity_df
            
        except Exception as e:
            logger.error(f"❌ Error processing equity tokens: {str(e)}")
            return None
    
    def process_and_store_tokens(self, hard_refresh: bool = False) -> bool:
        """
        Process and store futures, options, and equity tokens.
        
        Args:
            hard_refresh: Force refresh regardless of last update time
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if tokens need refresh before doing any API calls
            if not self.needs_token_refresh(hard_refresh):
                logger.info("✅ Skipping token refresh as tokens are already up to date.")
                return True
            
            # Only fetch tokens if we actually need to refresh
            if not self.fetch_tokens():
                logger.error("❌ Failed to fetch token data")
                return False
            
            # Process futures tokens
            futures_df = self.process_futures_tokens()
            if futures_df is None:
                return False
            
            # Process options tokens
            options_df = self.process_options_tokens()
            if options_df is None:
                return False
            
            # Process equity tokens
            equity_df = self.process_equity_tokens(futures_df)
            if equity_df is None:
                return False
            
            # Combine DataFrames
            combined_df = pd.concat([futures_df, options_df, equity_df], ignore_index=True)
            
            # Store in database
            return self.db_manager.store_tokens(combined_df)
            
        except Exception as e:
            logger.error(f"❌ Error in token processing pipeline: {str(e)}")
            return False 