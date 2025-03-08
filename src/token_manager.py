"""
Token Manager for Angel One API.
Handles fetching and processing of token master data.
"""

import json
import requests
from datetime import datetime
from typing import Optional, Dict, List, Any
from logzero import logger
from src.db_manager import DBManager

class TokenManager:
    """Manages token data from Angel One API."""
    
    ANGEL_API_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    
    def __init__(self, db_manager: Optional[DBManager] = None):
        """Initialize TokenManager."""
        self.tokens_data: Optional[List[Dict[str, Any]]] = None
        self.db_manager = db_manager or DBManager()
    
    def fetch_tokens(self) -> bool:
        """
        Fetch token master data from Angel One API.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Fetching token master data from Angel One API...")
            response = requests.get(self.ANGEL_API_URL)
            response.raise_for_status()
            
            self.tokens_data = response.json()
            logger.info(f"✅ Successfully fetched {len(self.tokens_data)} tokens")
            
            # Log first few records to understand the structure
            logger.info("Sample token data structure:")
            for idx, token in enumerate(self.tokens_data[:3]):
                logger.info(f"Token {idx + 1}: {json.dumps(token, indent=2)}")
            
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
    
    def get_current_expiry_futures(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get F&O stocks with nearest expiry date.
        
        Returns:
            Optional[List[Dict[str, Any]]]: Filtered futures tokens
        """
        if not self.tokens_data:
            logger.error("❌ No token data available. Call fetch_tokens() first.")
            return None
            
        try:
            # Filter futures stocks
            futures_tokens = [
                token for token in self.tokens_data
                if token.get('instrumenttype') == 'FUTSTK' and token.get('exch_seg') == 'NFO'
            ]
            
            if not futures_tokens:
                logger.error("❌ No futures tokens found")
                return None
            
            # Check all distinct expiry formats
            distinct_expiry_formats = set()
            for token in futures_tokens:
                if expiry := token.get('expiry'):
                    distinct_expiry_formats.add(expiry)
            
            logger.info("All distinct expiry formats found:")
            for expiry in sorted(distinct_expiry_formats):
                logger.info(f"Expiry format: {expiry}")
            
            # Log sample of futures tokens before processing
            logger.info("\nSample futures tokens before processing:")
            for token in futures_tokens[:3]:
                logger.info(f"Symbol: {token.get('symbol')}, Expiry: {token.get('expiry')}")
            
            # Convert expiry strings to dates and find minimum expiry
            for token in futures_tokens:
                if token.get('expiry'):
                    try:
                        expiry_date = datetime.strptime(token['expiry'], '%d%b%Y').date()
                        token['expiry_date'] = expiry_date
                        # Keep the original expiry string for database
                        token['expiry'] = expiry_date.strftime('%Y-%m-%d')
                    except ValueError as e:
                        logger.error(f"❌ Error parsing expiry date for {token.get('symbol')}: {str(e)}")
                        logger.error(f"  Original expiry value: '{token.get('expiry')}'")
                        token['expiry_date'] = None
                else:
                    token['expiry_date'] = None
            
            valid_tokens = [token for token in futures_tokens if token.get('expiry_date')]
            if not valid_tokens:
                logger.error("❌ No valid expiry dates found")
                return None
                
            min_expiry = min(token['expiry_date'] for token in valid_tokens)
            
            # Filter tokens with minimum expiry date
            current_expiry_futures = [
                token for token in valid_tokens
                if token.get('expiry_date') == min_expiry
            ]
            
            # Log sample of processed futures tokens
            logger.info("\nSample processed futures tokens:")
            for token in current_expiry_futures[:3]:
                logger.info(f"Symbol: {token.get('symbol')}, Original Expiry: {token.get('expiry')}, Parsed Date: {token.get('expiry_date')}")
            
            logger.info(f"✅ Found {len(current_expiry_futures)} current expiry futures")
            return current_expiry_futures
            
        except Exception as e:
            logger.error(f"❌ Error processing futures tokens: {str(e)}")
            return None
    
    def get_equity_tokens_for_futures(self, futures_tokens: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """
        Get corresponding equity spot tokens for futures.
        
        Args:
            futures_tokens: List of futures tokens to find equity spots for
            
        Returns:
            Optional[List[Dict[str, Any]]]: Filtered equity tokens
        """
        if not self.tokens_data:
            logger.error("❌ No token data available. Call fetch_tokens() first.")
            return None
            
        try:
            # Extract names from futures tokens
            futures_names = {token['name'] for token in futures_tokens}
            logger.info(f"Base names from futures: {sorted(futures_names)[:5]}")
            
            # Create equity symbols by adding -EQ suffix
            equity_symbols = {f"{name}-EQ" for name in futures_names}
            logger.info(f"Equity symbols to search: {sorted(equity_symbols)[:5]}")
            
            # Filter equity tokens
            equity_tokens = [
                token for token in self.tokens_data
                if token.get('exch_seg') == 'NSE' and token.get('symbol') in equity_symbols
            ]
            
            # Log sample matches
            logger.info("\nSample equity matches found:")
            for token in equity_tokens[:3]:
                logger.info(f"Symbol: {token.get('symbol')}, Name: {token.get('name')}, Exchange: {token.get('exch_seg')}")
            
            # Add reference to futures token
            for eq_token in equity_tokens:
                base_name = eq_token['symbol'].replace('-EQ', '')
                matching_futures = next(
                    (ft['token'] for ft in futures_tokens if ft['name'] == base_name),
                    None
                )
                eq_token['futures_token'] = matching_futures
                
                # Log the mapping
                if matching_futures:
                    logger.info(f"Mapped equity {eq_token['symbol']} to futures token {matching_futures} (base name: {base_name})")
            
            logger.info(f"✅ Found {len(equity_tokens)} corresponding equity tokens")
            return equity_tokens if equity_tokens else None
            
        except Exception as e:
            logger.error(f"❌ Error processing equity tokens: {str(e)}")
            # Log more details about the error
            logger.error(f"Error details: {str(e)}")
            if futures_tokens:
                logger.error("Sample futures token for debugging:")
                logger.error(json.dumps(futures_tokens[0], indent=2))
            return None
    
    def process_and_store_tokens(self) -> bool:
        """
        Process and store both futures and equity tokens.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get current expiry futures
            futures_tokens = self.get_current_expiry_futures()
            if not futures_tokens:
                return False
            
            # Store futures tokens
            if not self.db_manager.store_futures_tokens(futures_tokens):
                return False
            
            # Get and store corresponding equity tokens
            equity_tokens = self.get_equity_tokens_for_futures(futures_tokens)
            if not equity_tokens:
                return False
            
            if not self.db_manager.store_equity_tokens(equity_tokens, futures_tokens):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error in token processing pipeline: {str(e)}")
            return False
    
    def get_tokens(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get the fetched token data.
        
        Returns:
            Optional[List[Dict[str, Any]]]: List of token dictionaries if available, None otherwise
        """
        return self.tokens_data 