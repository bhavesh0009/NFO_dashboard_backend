"""
Technical Indicator Manager

This module provides functionality for calculating and storing technical indicators
based on historical price data. It uses pandas-ta for indicator calculations.
"""

import os
import pandas as pd
from logzero import logger
from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import datetime, timedelta

# Import pandas_ta for technical indicators
try:
    import pandas_ta as ta
except ImportError:
    logger.error("pandas_ta package not installed. Please install it with: pip install pandas_ta")
    raise ImportError("pandas_ta package not installed")

from src.db_manager import DBManager
from src.config_manager import config

class TechnicalIndicatorManager:
    """Manages calculation and storage of technical indicators for equity data."""
    
    def __init__(self, db_manager: Optional[DBManager] = None):
        """
        Initialize the Technical Indicator Manager.
        
        Args:
            db_manager: Optional database manager instance
        """
        self.db_manager = db_manager or DBManager()
        self.config = self._load_config()
        logger.info("Technical Indicator Manager initialized")
        
    def _load_config(self) -> Dict[str, Any]:
        """
        Load technical indicators configuration from config file.
        
        Returns:
            Dictionary with technical indicators configuration
        """
        # Get technical indicators configuration or use defaults if not found
        ti_config = config.get('technical_indicators') or {}
        
        # Set default values if not in config
        default_config = {
            'default_indicator': 'sma',
            'default_period': 200,
            'max_fetch_multiplier': 1.5,
            'batch_size': 50,
            'enable_by_default': True,
            'indicators': {
                'sma': {
                    'periods': [50, 100, 200],
                    'description': 'Simple Moving Average'
                }
            }
        }
        
        # Merge the loaded config with defaults for any missing values
        for key, value in default_config.items():
            if key not in ti_config:
                ti_config[key] = value
                
        logger.debug(f"Loaded technical indicator configuration: {ti_config}")
        return ti_config
    
    def get_historical_data(self, token: str, symbol: str, period: int = None) -> pd.DataFrame:
        """
        Fetch historical data for a token with enough periods for calculation.
        
        Args:
            token: Token ID
            symbol: Symbol name
            period: Number of periods needed for calculation (gets from config if None)
            
        Returns:
            DataFrame with historical data
        """
        try:
            # Use default period from config if none provided
            if period is None:
                period = self.config['default_period']
                
            # Calculate how many periods to fetch using the multiplier from config
            fetch_periods = int(period * self.config['max_fetch_multiplier'])
            
            query = f"""
                SELECT token, symbol_name, timestamp, open, high, low, close, volume
                FROM historical_data
                WHERE token = '{token}'
                ORDER BY timestamp DESC
                LIMIT {fetch_periods}
            """
            
            data = self.db_manager.conn.execute(query).fetchdf()
            
            if len(data) < period:
                logger.warning(f"⚠️ Not enough historical data for {symbol} ({token}). "
                              f"Need at least {period} periods, but only found {len(data)}")
                return pd.DataFrame()
                
            # Sort by timestamp ascending (oldest first) for proper indicator calculation
            data = data.sort_values(by='timestamp')
            
            logger.debug(f"Got {len(data)} historical records for {symbol} ({token})")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error fetching historical data for {symbol} ({token}): {str(e)}")
            return pd.DataFrame()
    
    def calculate_moving_average(self, data: pd.DataFrame, period: int = None, indicator_type: str = None) -> pd.DataFrame:
        """
        Calculate Moving Average (Simple or Exponential).
        
        Args:
            data: DataFrame with historical price data (must have 'close' column)
            period: Period for calculation (gets from config if None)
            indicator_type: Type of moving average ('sma' or 'ema') (gets from config if None)
            
        Returns:
            DataFrame with original data plus indicator column
        """
        # Use defaults from config if parameters not provided
        if period is None:
            period = self.config['default_period']
            
        if indicator_type is None:
            indicator_type = self.config['default_indicator']
        
        if data.empty or len(data) < period:
            logger.warning(f"Not enough data to calculate {period}-period {indicator_type}. Need at least {period} records.")
            return pd.DataFrame()
            
        try:
            # Create a copy to avoid modifying the original dataframe
            result = data.copy()
            
            # Calculate indicator based on type
            if indicator_type.lower() == 'sma':
                # Simple Moving Average
                result[f'sma_{period}'] = result['close'].rolling(window=period).mean()
                logger.info(f"Calculated {period}-day SMA with {len(result.dropna())} valid values")
            elif indicator_type.lower() == 'ema':
                # Exponential Moving Average
                result[f'ema_{period}'] = result['close'].ewm(span=period, adjust=False).mean()
                logger.info(f"Calculated {period}-day EMA with {len(result.dropna())} valid values")
            elif indicator_type.lower() == 'rsi':
                # Relative Strength Index using pandas_ta
                rsi = ta.rsi(result['close'], length=period)
                result[f'rsi_{period}'] = rsi
                logger.info(f"Calculated {period}-day RSI with {len(result.dropna())} valid values")
            elif indicator_type.lower() == 'volatility':
                # Calculate daily returns
                result['daily_return'] = result['close'].pct_change()
                
                # Calculate historical volatility (standard deviation of returns over the period)
                result[f'volatility_{period}'] = result['daily_return'].rolling(window=period).std() * (252 ** 0.5)  # Annualized
                
                # Drop the temporary daily_return column
                result.drop('daily_return', axis=1, inplace=True)
                
                logger.info(f"Calculated {period}-day historical volatility with {len(result.dropna())} valid values")
            else:
                logger.error(f"Unsupported indicator type: {indicator_type}")
                return pd.DataFrame()
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error calculating {indicator_type}: {str(e)}")
            return pd.DataFrame()
    
    def store_technical_indicator(self, token: str, symbol: str, indicator_name: str, 
                                 period: int, data: pd.DataFrame) -> bool:
        """
        Store technical indicator values in the database.
        
        Args:
            token: Token ID
            symbol: Symbol name
            indicator_name: Name of the indicator (e.g., 'sma')
            period: Period used for calculation
            data: DataFrame with indicator values
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Column name in the dataframe (e.g., 'sma_200')
            column_name = f"{indicator_name}_{period}"
            
            if column_name not in data.columns:
                logger.error(f"❌ Column '{column_name}' not found in data for {symbol}")
                return False
                
            # Filter out rows with NaN indicator values
            valid_data = data.dropna(subset=[column_name])
            
            if valid_data.empty:
                logger.warning(f"⚠️ No valid {indicator_name} values for {symbol} ({token}) after filtering NaNs")
                return False
                
            # Create records for insertion
            records = []
            for _, row in valid_data.iterrows():
                records.append({
                    'token': token,
                    'symbol_name': symbol,
                    'indicator_name': indicator_name,
                    'timestamp': row['timestamp'],
                    'value': row[column_name],
                    'period': period
                })
                
            # Convert to dataframe for insertion
            df = pd.DataFrame(records)
            
            # Insert with conflict resolution
            self.db_manager.conn.execute("""
                INSERT INTO technical_indicators
                (token, symbol_name, indicator_name, timestamp, value, period)
                SELECT token, symbol_name, indicator_name, timestamp, value, period
                FROM df
                ON CONFLICT(token, indicator_name, period, timestamp) DO UPDATE SET
                    symbol_name = EXCLUDED.symbol_name,
                    value = EXCLUDED.value
            """)
            
            logger.info(f"✅ Successfully stored {len(records)} {indicator_name}_{period} values for {symbol} ({token})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error storing technical indicator for {symbol} ({token}): {str(e)}")
            return False
    
    def calculate_and_store_indicator(self, token: str, symbol: str, indicator_name: str = None, period: int = None) -> bool:
        """
        Calculate and store a technical indicator for a token.
        
        Args:
            token: Token ID
            symbol: Symbol name
            indicator_name: Name of the indicator (gets from config if None)
            period: Period for calculation (gets from config if None)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use defaults from config if parameters not provided
            if indicator_name is None:
                indicator_name = self.config['default_indicator']
                
            if period is None:
                period = self.config['default_period']
                
            # Check if the indicator is supported
            if indicator_name not in self.config.get('indicators', {}):
                logger.warning(f"Indicator '{indicator_name}' not found in configuration")
                # Fall back to default indicator
                indicator_name = self.config['default_indicator']
                
            # Fetch historical data
            historical_data = self.get_historical_data(token, symbol, period)
            
            if historical_data.empty:
                return False
                
            # Calculate indicator
            indicator_data = self.calculate_moving_average(
                historical_data, 
                period=period, 
                indicator_type=indicator_name
            )
            
            if indicator_data.empty:
                return False
                
            # Store indicator values
            return self.store_technical_indicator(token, symbol, indicator_name, period, indicator_data)
            
        except Exception as e:
            logger.error(f"❌ Error calculating and storing {indicator_name} for {symbol} ({token}): {str(e)}")
            return False
    
    def process_all_equity_tokens(self, limit: Optional[int] = None, period: int = None, 
                                 indicator_name: str = None) -> Dict[str, Any]:
        """
        Process all equity tokens to calculate and store technical indicators.
        
        Args:
            limit: Maximum number of tokens to process (None for all)
            period: Period for technical indicators (gets from config if None)
            indicator_name: Name of the indicator (gets from config if None)
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Use defaults from config if parameters not provided
            if indicator_name is None:
                indicator_name = self.config['default_indicator']
                
            if period is None:
                period = self.config['default_period']
                
            logger.info(f"Starting technical indicators calculation: {indicator_name}({period})")
            
            # Get all equity tokens
            query = """
                SELECT token, name
                FROM token_master
                WHERE token_type = 'EQUITY'
            """
            
            if limit:
                query += f" LIMIT {limit}"
                
            tokens = self.db_manager.conn.execute(query).fetchdf()
            
            if tokens.empty:
                logger.warning("No equity tokens found in database")
                return {"success": 0, "errors": 0, "total": 0, "message": "No equity tokens found"}
                
            results = {
                "success": 0,
                "errors": 0,
                "total": len(tokens),
                "tokens": [],
                "indicator": indicator_name,
                "period": period
            }
            
            # Get batch size from config
            batch_size = self.config.get('batch_size', 50)
            
            # Process tokens in batches
            for i in range(0, len(tokens), batch_size):
                batch = tokens.iloc[i:i+batch_size]
                
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(tokens)+batch_size-1)//batch_size}")
                
                # Process each token in the batch
                for _, row in batch.iterrows():
                    token = row['token']
                    symbol = row['name']
                    
                    logger.info(f"Processing {indicator_name}({period}) for {symbol} ({token})")
                    
                    # Calculate and store indicator
                    if self.calculate_and_store_indicator(token, symbol, indicator_name, period):
                        results["success"] += 1
                        results["tokens"].append({
                            "token": token,
                            "symbol": symbol,
                            "status": "success"
                        })
                    else:
                        results["errors"] += 1
                        results["tokens"].append({
                            "token": token,
                            "symbol": symbol,
                            "status": "error"
                        })
            
            # Log summary
            success_rate = (results["success"] / results["total"]) * 100 if results["total"] > 0 else 0
            logger.info(f"Technical indicators processing complete. "
                       f"Success: {results['success']}/{results['total']} ({success_rate:.2f}%)")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error processing technical indicators: {str(e)}")
            return {"success": 0, "errors": 0, "total": 0, "error": str(e)}
    
    def process_multiple_indicators(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Process multiple indicators and periods as specified in the configuration.
        
        Args:
            limit: Maximum number of tokens to process (None for all)
            
        Returns:
            Dictionary with processing results for all indicators
        """
        results = {
            "overall_success": 0,
            "overall_errors": 0,
            "indicators_processed": 0,
            "results": []
        }
        
        # Get all configured indicators and their periods
        indicators = self.config.get('indicators', {})
        
        for indicator_name, indicator_config in indicators.items():
            periods = indicator_config.get('periods', [])
            
            if not periods:
                logger.warning(f"No periods configured for indicator '{indicator_name}', skipping")
                continue
                
            # Process each period for this indicator
            for period in periods:
                logger.info(f"Processing {indicator_name}({period}) for all equity tokens")
                
                # Process the indicator
                indicator_result = self.process_all_equity_tokens(
                    limit=limit,
                    period=period,
                    indicator_name=indicator_name
                )
                
                # Update overall results
                results["overall_success"] += indicator_result.get("success", 0)
                results["overall_errors"] += indicator_result.get("errors", 0)
                results["indicators_processed"] += 1
                
                # Add this indicator's results to the overall results
                results["results"].append({
                    "indicator_name": indicator_name,
                    "period": period,
                    "success": indicator_result.get("success", 0),
                    "errors": indicator_result.get("errors", 0),
                    "total": indicator_result.get("total", 0)
                })
                
        return results
    
    def get_latest_indicator_value(self, token: str, indicator_name: str = None, period: int = None) -> Optional[float]:
        """
        Get the latest value of a technical indicator for a token.
        
        Args:
            token: Token ID
            indicator_name: Name of the indicator (gets from config if None)
            period: Period used for calculation (gets from config if None)
            
        Returns:
            Latest indicator value or None if not found
        """
        try:
            # Use defaults from config if parameters not provided
            if indicator_name is None:
                indicator_name = self.config['default_indicator']
                
            if period is None:
                period = self.config['default_period']
                
            query = f"""
                SELECT value
                FROM technical_indicators
                WHERE token = '{token}'
                  AND indicator_name = '{indicator_name}'
                  AND period = {period}
                ORDER BY timestamp DESC
                LIMIT 1
            """
            
            result = self.db_manager.conn.execute(query).fetchone()
            
            if result and result[0] is not None:
                return float(result[0])
                
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting latest indicator value: {str(e)}")
            return None 