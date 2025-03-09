"""
Configuration manager for the application.
Handles loading and accessing configuration values.
"""

import os
import yaml
from typing import Any, Dict
from logzero import logger

class ConfigManager:
    """Manages application configuration from YAML file."""
    
    _instance = None
    
    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize configuration manager."""
        if self._initialized:
            return
            
        self.config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config',
            'config.yaml'
        )
        self.config: Dict[str, Any] = {}
        self._load_config()
        self._initialized = True
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            logger.info("✅ Configuration loaded successfully")
        except Exception as e:
            logger.error(f"❌ Error loading configuration: {str(e)}")
            raise
    
    def get(self, *keys: str) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            *keys: Sequence of keys to traverse the configuration
            
        Returns:
            Any: Configuration value
            
        Example:
            config.get('api', 'angel_one', 'token_master_url')
        """
        value = self.config
        for key in keys:
            value = value.get(key, {})
        return value if value != {} else None
    
    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()
        
config = ConfigManager()  # Create singleton instance 