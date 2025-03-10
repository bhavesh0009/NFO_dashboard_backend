"""
Equity market data manager for Angel One API.
Handles fetching and processing spot equity price data.
"""

import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from logzero import logger
import time

from src.angel_one_connector import AngelOneConnector
from src.db_manager import DBManager
from src.config_manager import config

class EquityMarketDataManager:
    """Manages fetching and processing of spot equity market data."""
    
    def __init__(self, connector: Optional[AngelOneConnector] = None, db_manager: Optional[DBManager] = None):
        """
        Initialize equity market data manager.
        
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
    
    def get_equity_tokens(self, limit: int = 5) -> pd.DataFrame:
        """
        Get equity tokens from database.
        
        Args:
            limit: Maximum number of tokens to fetch (default: 5 for testing)
            
        Returns:
            pd.DataFrame: DataFrame with equity token information
        """
        try:
            query = """
                SELECT token, name, exch_seg
                FROM token_master
                WHERE token_type = 'EQUITY'
                LIMIT ?
            """
            result = self.db_manager.conn.execute(query, [limit]).fetchdf()
            logger.info(f"✅ Retrieved {len(result)} equity tokens from database")
            return result
        except Exception as e:
            logger.error(f"❌ Error fetching equity tokens: {str(e)}")
            return pd.DataFrame()
    
    def _get_date_params(self) -> tuple:
        """
        Get fromdate and todate parameters for market data query.
        
        Returns:
            tuple: (fromdate, todate) formatted strings
        """
        # Get the start date from configuration
        from_date = config.get('equity_market_data', 'start_date')
        
        # To date is yesterday at market close
        yesterday = datetime.now() - timedelta(days=1)
        market_end = config.get('market', 'trading_hours', 'end')
        to_date = yesterday.strftime("%Y-%m-%d") + f" {market_end}"
        
        logger.info(f"Date range for equity market data: {from_date} to {to_date}")
        return from_date, to_date
    
    def fetch_equity_market_data(self, token: str, exchange: str, name: str, interval: str = "ONE_DAY") -> Optional[Dict[str, Any]]:
        """
        Fetch market data for a single equity token.
        
        Args:
            token: Symbol token
            exchange: Exchange segment (NSE)
            name: Name of the equity token (for logging)
            interval: Data interval (ONE_MINUTE, ONE_DAY, etc.) Default: ONE_DAY
            
        Returns:
            Optional[Dict[str, Any]]: Market data response or None if failed
        """
        from_date, to_date = self._get_date_params()
        
        params = {
            "exchange": exchange,
            "symboltoken": token,
            "interval": interval,
            "fromdate": from_date,
            "todate": to_date
        }
        
        try:
            logger.info(f"Fetching equity market data for {name} ({token}) with {interval} interval")
            market_data = self.connector.api.getCandleData(params)
            
            if market_data.get('status'):
                logger.info(f"✅ Successfully fetched {len(market_data.get('data', []))} records for {name}")
                return market_data
            else:
                logger.error(f"❌ Failed to fetch equity market data for {name}: {market_data.get('message', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error fetching equity market data for {name}: {str(e)}")
            return None
    
    def process_equity_market_data(self, limit: int = 5, interval: str = None) -> Dict[str, Any]:
        """
        Process market data for equity tokens.
        
        Args:
            limit: Maximum number of tokens to process (default: 5 for testing)
            interval: Data interval (ONE_MINUTE, ONE_DAY, etc.) If None, uses config default
            
        Returns:
            Dict[str, Any]: Results summary with success and error counts
        """
        # Use default interval from config if none provided
        if interval is None:
            interval = config.get('equity_market_data', 'default_interval')
        
        equity_tokens = self.get_equity_tokens(limit)
        
        if equity_tokens.empty:
            logger.error("No equity tokens found")
            return {"success": 0, "errors": 0, "message": "No equity tokens found"}
        
        results = {
            "success": 0,
            "errors": 0,
            "data": {}
        }
        
        for _, row in equity_tokens.iterrows():
            token = row['token']
            exchange = row['exch_seg']
            name = row['name']
            
            # Fetch market data for this token
            market_data = self.fetch_equity_market_data(token, exchange, name, interval=interval)
            
            if market_data and market_data.get('status'):
                data = market_data.get('data', [])
                results["success"] += 1
                results["data"][token] = {
                    "name": name,
                    "records": len(data),
                    "sample": data[:2]  # Log first 2 records as sample
                }
            else:
                results["errors"] += 1
            
            # Add a small delay to avoid API rate limits
            request_delay = config.get('equity_market_data', 'rate_limiting', 'request_delay')
            time.sleep(request_delay)
        
        logger.info(f"✅ Equity market data processing complete. Success: {results['success']}, Errors: {results['errors']}")
        return results
        
    def fetch_and_store_equity_market_data(self, limit: int = 5, interval: str = None) -> Dict[str, Any]:
        """
        Fetch and store market data for equity tokens.
        
        Args:
            limit: Maximum number of tokens to process (default: 5 for testing)
            interval: Data interval (ONE_MINUTE, ONE_DAY, etc.) If None, uses config default
            
        Returns:
            Dict[str, Any]: Results summary with success and error counts
        """
        # Use default interval from config if none provided
        if interval is None:
            interval = config.get('equity_market_data', 'default_interval')
        
        equity_tokens = self.get_equity_tokens(limit)
        
        if equity_tokens.empty:
            logger.error("No equity tokens found")
            return {"success": 0, "errors": 0, "message": "No equity tokens found"}
        
        results = {
            "success": 0,
            "errors": 0,
            "data": {}
        }
        
        for _, row in equity_tokens.iterrows():
            token = row['token']
            exchange = row['exch_seg']
            name = row['name']
            
            # Fetch market data for this token
            market_data = self.fetch_equity_market_data(token, exchange, name, interval=interval)
            
            if market_data and market_data.get('status'):
                data = market_data.get('data', [])
                
                # Store the data in the database
                if self.db_manager.store_historical_data(token, name, data):
                    results["success"] += 1
                    results["data"][token] = {
                        "name": name,
                        "records": len(data),
                        "sample": data[:2]  # Log first 2 records as sample
                    }
                else:
                    results["errors"] += 1
                    logger.error(f"Failed to store equity market data for {name} ({token})")
            else:
                results["errors"] += 1
            
            # Add a small delay to avoid API rate limits
            request_delay = config.get('equity_market_data', 'rate_limiting', 'request_delay')
            time.sleep(request_delay)
        
        logger.info(f"✅ Equity market data fetch and store complete. Success: {results['success']}, Errors: {results['errors']}")
        return results

    def fetch_and_store_equity_market_data_for_token(self, token: str, name: str, exchange: str, interval: str = None) -> Dict[str, Any]:
        """
        Fetch and store historical equity market data for a single token.
        
        Args:
            token: Equity token ID
            name: Symbol name
            exchange: Exchange segment
            interval: Data interval (e.g., ONE_DAY, ONE_MINUTE)
            
        Returns:
            Dict[str, Any]: Results summary
        """
        try:
            if interval is None:
                interval = config.get('equity_market_data', 'default_interval')
                
            logger.info(f"Fetching {interval} data for {name} ({token})...")
            
            # Fetch data
            response = self.fetch_equity_market_data(token, exchange, name, interval)
            
            if not response:
                logger.error(f"Failed to fetch data for {name} ({token})")
                return {'success': False, 'error': 'API request failed'}
                
            # Extract data
            data = response.get('data', [])
            
            if not data:
                logger.warning(f"No data returned for {name} ({token})")
                return {'success': False, 'error': 'No data returned'}
                
            # Store data
            if self.db_manager:
                success = self.db_manager.store_historical_data(token, name, data)
                if success:
                    logger.info(f"Successfully stored {len(data)} records for {name} ({token})")
                    return {
                        'success': True,
                        'records': len(data),
                        'token': token,
                        'name': name
                    }
                else:
                    logger.error(f"Failed to store data for {name} ({token})")
                    return {'success': False, 'error': 'Database storage failed'}
            else:
                logger.error(f"Database manager not available for {name} ({token})")
                return {'success': False, 'error': 'Database manager not available'}
                
        except Exception as e:
            error_msg = f"Error processing {name} ({token}): {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}

if __name__ == "__main__":
    # Test the equity market data manager
    try:
        logger.info("Testing Equity Market Data Manager")
        manager = EquityMarketDataManager()
        results = manager.process_equity_market_data(limit=5)
        
        # Log sample data
        for token, data in results.get("data", {}).items():
            logger.info(f"Sample data for {data['name']} ({token}): {data['sample']}")
            
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}") 