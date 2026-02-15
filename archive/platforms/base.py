"""
Base Platform Class
Provides common functionality for all social media posting platforms.
Uses the foundation utilities for consistency and DRY principles.

Compatible with Python 3.10+ including 3.13.
"""

import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Union

# Add utils to path
sys.path.append(str(Path(__file__).parent.parent / "utils"))

from csv_handler import CSVHandler
from error_logger import ErrorLogger
from config_manager import ConfigManager
from index_manager import IndexManager


class BasePlatform(ABC):
    """
    Abstract base class for all social media platforms.
    Provides common functionality while requiring platform-specific implementation.
    """
    
    def __init__(
        self, 
        platform_name: str,
        config_manager: Optional[ConfigManager] = None,
        csv_handler: Optional[CSVHandler] = None,
        index_manager: Optional[IndexManager] = None
    ):
        """
        Initialize base platform.
        
        Args:
            platform_name: Name of the platform (e.g., 'twitter', 'mastodon')
            config_manager: Configuration manager instance (created if None)
            csv_handler: CSV handler instance (created if None)  
            index_manager: Index manager instance (created if None)
        """
        self.platform_name = platform_name.lower()
        
        # Initialize utilities
        self.config_manager = config_manager or ConfigManager()
        self.csv_handler = csv_handler or CSVHandler()
        self.index_manager = index_manager or IndexManager()
        
        # Initialize logger for this platform
        self.logger = ErrorLogger(self.platform_name)
        
        # Load platform configuration
        self.platform_config = self.config_manager.get_platform_config(self.platform_name)
        if not self.platform_config:
            raise ValueError(f"No configuration found for platform: {self.platform_name}")
        
        # Initialize platform-specific settings
        self._authenticated = False
        self._client = None
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the platform's API.
        Must be implemented by each platform.
        
        Returns:
            True if authentication successful, False otherwise
        """
        pass
    
    @abstractmethod
    def post_content(self, content: str, **kwargs) -> bool:
        """
        Post content to the platform.
        Must be implemented by each platform.
        
        Args:
            content: Content to post
            **kwargs: Platform-specific options
            
        Returns:
            True if post successful, False otherwise
        """
        pass
    
    def post_item_from_csv(
        self, 
        filename: str, 
        index_key: str, 
        add_text: Optional[str] = None,
        reset_on_end: bool = True
    ) -> bool:
        """
        Post an item from CSV file using index tracking.
        This is the main method that replaces tweet_item, toot_item, etc.
        
        Args:
            filename: CSV filename (e.g., 'jokes.csv')
            index_key: Index key for tracking position (e.g., 'joke', 'Mastodon')
            add_text: Additional text to append to content
            reset_on_end: Whether to reset index when reaching end of file
            
        Returns:
            True if post successful, False otherwise
        """
        try:
            # Ensure authentication
            if not self._authenticated and not self.authenticate():
                self.logger.error(f"Authentication failed for {self.platform_name}")
                return False
            
            # Get current index
            current_index = self.index_manager.get_index(index_key, 0)
            
            # Get content from CSV
            content = self.csv_handler.get_item_by_index(
                filename, 
                current_index,
                error_callback=self.logger.log_corrupted_line
            )
            
            if content is None:
                # Check if we've reached the end of the file
                total_rows = self.csv_handler.count_rows(filename)
                if current_index >= total_rows:
                    if reset_on_end:
                        self.logger.info(f"Reached end of {filename}, resetting index")
                        self.index_manager.reset_index(index_key, 0)
                        current_index = 0
                        content = self.csv_handler.get_item_by_index(filename, current_index)
                    else:
                        self.logger.warning(f"Reached end of {filename}, no more content")
                        return False
                
                if content is None:
                    self.logger.error(f"Could not get content from {filename} at index {current_index}")
                    return False
            
            # Add additional text if provided
            if add_text:
                content = f"{content}\n\n{add_text}"
            
            # Validate content
            if not content.strip():
                self.logger.warning(f"Empty content at index {current_index} in {filename}")
                # Increment index anyway to avoid getting stuck
                self.index_manager.increment_index(index_key)
                return False
            
            # Post the content
            success = self.post_content(content)
            
            if success:
                # Increment index only on successful post
                new_index = self.index_manager.increment_index(index_key)
                self.logger.success(
                    f"Posted content from {filename}[{current_index}], next index: {new_index}"
                )
                self.logger.info(f"Content: {content[:100]}...")
            else:
                self.logger.error(f"Failed to post content from {filename}[{current_index}]")
            
            return success
            
        except Exception as e:
            self.logger.error(
                f"Unexpected error in post_item_from_csv", 
                details={'filename': filename, 'index_key': index_key},
                exception=e
            )
            return False
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value for this platform."""
        return self.platform_config.get(key, default)
    
    def validate_required_config(self, required_keys: list) -> bool:
        """
        Validate that all required configuration keys are present.
        
        Args:
            required_keys: List of required configuration keys
            
        Returns:
            True if all required keys present, False otherwise
        """
        return self.config_manager.validate_platform_config(self.platform_name, required_keys)
    
    def is_authenticated(self) -> bool:
        """Check if platform is authenticated."""
        return self._authenticated
    
    def get_platform_name(self) -> str:
        """Get the platform name."""
        return self.platform_name
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get platform statistics (can be overridden by platforms).
        
        Returns:
            Dictionary with platform statistics
        """
        return {
            'platform': self.platform_name,
            'authenticated': self._authenticated,
            'config_valid': self.platform_config is not None
        }
    
    def test_connection(self) -> bool:
        """
        Test platform connection (can be overridden by platforms).
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            return self.authenticate()
        except Exception as e:
            self.logger.error(f"Connection test failed", exception=e)
            return False
    
    def __str__(self) -> str:
        """String representation of platform."""
        return f"{self.__class__.__name__}({self.platform_name})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"{self.__class__.__name__}(platform='{self.platform_name}', authenticated={self._authenticated})"


# Utility functions for backward compatibility

def create_platform(platform_name: str, platform_class) -> BasePlatform:
    """
    Factory function to create a platform instance.
    
    Args:
        platform_name: Name of the platform
        platform_class: Class that inherits from BasePlatform
        
    Returns:
        Platform instance
    """
    return platform_class(platform_name)


def validate_platform_class(platform_class) -> bool:
    """
    Validate that a class properly inherits from BasePlatform.
    
    Args:
        platform_class: Class to validate
        
    Returns:
        True if valid platform class, False otherwise
    """
    return (
        hasattr(platform_class, 'authenticate') and
        hasattr(platform_class, 'post_content') and
        issubclass(platform_class, BasePlatform)
    )