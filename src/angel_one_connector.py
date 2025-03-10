import os
from dotenv import load_dotenv
from SmartApi import SmartConnect
import pyotp
from logzero import logger
from typing import Optional, Dict, Any, List

load_dotenv()

class AngelOneConnector:
    def __init__(self):
        """Initialize the Angel One connector with credentials from environment variables."""
        self.api_key = os.getenv('ANGEL_ONE_APP_KEY')
        self.client_id = os.getenv('ANGEL_ONE_CLIENT_ID')
        self.totp_secret = os.getenv('ANGEL_ONE_TOTP_SECRET')
        self.pin = os.getenv('ANGEL_ONE_PIN')
        
        # Validate required environment variables
        self._validate_credentials()
        
        self.api = None
        self.auth_token = None
        self.feed_token = None

    def _validate_credentials(self) -> None:
        """Validate that all required credentials are present."""
        required_vars = {
            'ANGEL_ONE_APP_KEY': self.api_key,
            'ANGEL_ONE_CLIENT_ID': self.client_id,
            'ANGEL_ONE_TOTP_SECRET': self.totp_secret,
            'ANGEL_ONE_PIN': self.pin
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    def connect(self) -> bool:
        """
        Connect to Angel One API using credentials.
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            self.api = SmartConnect(api_key=self.api_key)
            totp = pyotp.TOTP(self.totp_secret)
            data = self.api.generateSession(self.client_id, self.pin, totp.now())
            
            if data.get('status') and data['data']:
                self.auth_token = data['data']['jwtToken']
                self.feed_token = data['data']['feedToken']
                logger.info("Successfully connected to Angel One API")
                return True
            else:
                logger.error(f"Failed to connect: {data.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to Angel One API: {str(e)}")
            return False
    
    def get_profile(self) -> Optional[Dict[str, Any]]:
        """
        Get user profile information.
        Returns:
            Optional[Dict[str, Any]]: User profile data if successful, None otherwise
        """
        try:
            if not self.api:
                logger.error("Not connected to Angel One API")
                return None
                
            # Pass the auth_token as refreshToken parameter
            profile = self.api.getProfile(refreshToken=self.auth_token)
            if profile.get('status'):
                return profile['data']
            else:
                logger.error(f"Failed to get profile: {profile.get('message', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting profile: {str(e)}")
            return None
    
    def get_market_data(self, mode: str, exchange_tokens: Dict[str, List[str]]) -> Optional[Dict[str, Any]]:
        """
        Get real-time market data for specified tokens.
        
        Args:
            mode: Data mode ("FULL", "OHLC", or "LTP")
            exchange_tokens: Dictionary with exchange segments as keys and token lists as values
                             Example: {"NSE": ["3045", "881"], "NFO": ["58662"]}
        
        Returns:
            Optional[Dict[str, Any]]: Market data response if successful, None otherwise
        """
        try:
            if not self.api:
                logger.error("Not connected to Angel One API")
                return None
            
            # Validate input
            if not isinstance(exchange_tokens, dict) or not exchange_tokens:
                logger.error("Invalid exchange_tokens format")
                return None
            
            # Check if mode is valid
            valid_modes = ["FULL", "OHLC", "LTP"]
            if mode not in valid_modes:
                logger.error(f"Invalid mode: {mode}. Must be one of {valid_modes}")
                return None
            
            # Count total tokens
            total_tokens = sum(len(tokens) for tokens in exchange_tokens.values())
            if total_tokens > 50:
                logger.warning(f"Requesting data for {total_tokens} tokens, which exceeds the recommended limit of 50")
            
            # Make the API call
            logger.info(f"Fetching market data in {mode} mode for {total_tokens} tokens")
            response = self.api.getMarketData(mode, exchange_tokens)
            
            # Check response
            if response.get('status'):
                fetched = len(response.get('data', {}).get('fetched', []))
                unfetched = len(response.get('data', {}).get('unfetched', []))
                logger.info(f"Successfully fetched market data: {fetched} fetched, {unfetched} unfetched")
                return response
            else:
                logger.error(f"Failed to fetch market data: {response.get('message', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching market data: {str(e)}")
            return None

if __name__ == "__main__":
    # Test the connection
    try:
        connector = AngelOneConnector()
        if connector.connect():
            logger.info("Connection test successful")
        else:
            logger.error("Connection test failed")
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")