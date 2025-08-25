"""
Configuration Manager Utility
Unifies configuration loading across all modules that currently load:
- keys.json (root)
- data/json/keys.json  
- config.json (root)
- bsky/keys.json
- bsky/config.json

Provides centralized, validated configuration management.
Compatible with Python 3.10+ including 3.13.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass


@dataclass
class PlatformConfig:
    """Configuration for a single platform."""
    name: str
    enabled: bool
    config: Dict[str, Any]
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with optional default."""
        return self.config.get(key, default)


class ConfigManager:
    """
    Centralized configuration manager that loads and validates all bot configurations.
    Merges multiple JSON files into a unified configuration structure.
    """
    
    def __init__(self, base_path: Optional[Union[str, Path]] = None):
        """
        Initialize configuration manager.
        
        Args:
            base_path: Base directory containing config files. Defaults to jokes root.
        """
        if base_path is None:
            self.base_path = Path(__file__).parent.parent
        else:
            self.base_path = Path(base_path)
        
        self._config: Dict[str, Any] = {}
        self._platforms: Dict[str, PlatformConfig] = {}
        self._loaded = False
        self.unified_config: Dict[str, Any] = {}
        
        # Define expected config file locations (priority order)
        self.unified_config_file = self.base_path / "config" / "master_config.json"
        self.config_files = [
            self.base_path / "keys.json",              # Main API keys
            self.base_path / "data" / "json" / "keys.json",  # Alternative keys location
            self.base_path / "config.json",            # General configuration
            self.base_path / "bsky" / "keys.json",     # BlueSky specific keys
            self.base_path / "bsky" / "config.json",   # BlueSky specific config
        ]
    
    def load_all_configs(self) -> None:
        """Load configuration - prioritizes unified config over legacy files."""
        if self._loaded:
            return
        
        # Check for unified config first
        if self.unified_config_file.exists():
            self._load_unified_config()
            print(f"Using unified configuration: {self.unified_config_file}")
        else:
            # Fallback to legacy config loading
            self._load_legacy_configs()
            print("Using legacy configuration files")
        
        self._create_platform_configs()
        self._loaded = True
        
        print(f"Configuration loaded. Platforms available: {list(self._platforms.keys())}")
    
    def _load_unified_config(self) -> None:
        """Load the new unified configuration format."""
        try:
            with open(self.unified_config_file, 'r', encoding='utf-8') as f:
                self.unified_config = json.load(f)
            
            # Convert unified format to internal format
            self._config = {
                'meta': self.unified_config.get('meta', {}),
                'paths': self.unified_config.get('paths', {}),
                'logging': self.unified_config.get('logging', {}),
                'scheduling': self.unified_config.get('scheduling', {}),
                'content': self.unified_config.get('content', {}),
                'interactive': self.unified_config.get('interactive', {}),
                'security': self.unified_config.get('security', {})
            }
            
            # Convert platforms to legacy format for backward compatibility
            platforms = self.unified_config.get('platforms', {})
            for platform_name, platform_config in platforms.items():
                if platform_name == 'twitter':
                    self._config['twitter'] = platform_config
                elif platform_name == 'mastodon': 
                    self._config['mastodon'] = platform_config
                elif platform_name == 'bluesky':
                    self._config['bsky'] = platform_config  # Keep legacy 'bsky' key
                elif platform_name == 'counter':
                    self._config['counter'] = platform_config
                elif platform_name == 'imgur':
                    self._config['imgur'] = platform_config
            
            print(f"Loaded unified config from: {self.unified_config_file}")
                    
        except Exception as e:
            print(f"ERROR: Could not load unified config {self.unified_config_file}: {e}")
            # Fallback to legacy
            self._load_legacy_configs()
    
    def _load_legacy_configs(self) -> None:
        """Load legacy configuration files and merge them."""
        merged_config = {}
        
        for config_file in self.config_files:
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        file_config = json.load(f)
                    
                    # Merge configurations (later files override earlier ones for conflicts)
                    self._deep_merge(merged_config, file_config)
                    print(f"Loaded config from: {config_file}")
                    
                except json.JSONDecodeError as e:
                    print(f"ERROR: Invalid JSON in {config_file}: {e}")
                except Exception as e:
                    print(f"ERROR: Could not load {config_file}: {e}")
            else:
                print(f"Config file not found (skipping): {config_file}")
        
        self._config = merged_config
    
    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Deep merge source dict into target dict."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
    
    def _create_platform_configs(self) -> None:
        """Create platform-specific configuration objects."""
        # Map of config keys to platform names
        platform_mapping = {
            'twitter': 'twitter',
            'mastodon': 'mastodon', 
            'bsky': 'bluesky',
            'counter': 'counter',
            'imgur': 'imgur'
        }
        
        for config_key, platform_name in platform_mapping.items():
            if config_key in self._config:
                platform_config = PlatformConfig(
                    name=platform_name,
                    enabled=True,  # Assume enabled if config exists
                    config=self._config[config_key]
                )
                self._platforms[platform_name] = platform_config
        
        # Handle paths configuration specially
        if 'paths' in self._config:
            self._config['_paths'] = self._config['paths']
    
    def get_platform_config(self, platform: str) -> Optional[PlatformConfig]:
        """
        Get configuration for a specific platform.
        
        Args:
            platform: Platform name ('twitter', 'bluesky', 'mastodon', etc.)
            
        Returns:
            PlatformConfig object or None if platform not configured
        """
        if not self._loaded:
            self.load_all_configs()
        
        return self._platforms.get(platform.lower())
    
    def get_platform_value(self, platform: str, key: str, default: Any = None) -> Any:
        """
        Get a specific configuration value for a platform.
        
        Args:
            platform: Platform name
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        platform_config = self.get_platform_config(platform)
        if platform_config:
            return platform_config.get(key, default)
        return default
    
    def get_global_config(self, key: str, default: Any = None) -> Any:
        """
        Get a global configuration value.
        
        Args:
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        if not self._loaded:
            self.load_all_configs()
        
        return self._config.get(key, default)
    
    def get_paths_config(self) -> Dict[str, Any]:
        """Get paths configuration."""
        return self.get_global_config('_paths', {})
    
    def list_platforms(self) -> List[str]:
        """Get list of configured platforms."""
        if not self._loaded:
            self.load_all_configs()
        
        return list(self._platforms.keys())
    
    def validate_platform_config(self, platform: str, required_keys: List[str]) -> bool:
        """
        Validate that a platform has all required configuration keys.
        
        Args:
            platform: Platform name
            required_keys: List of required configuration keys
            
        Returns:
            True if all required keys are present, False otherwise
        """
        platform_config = self.get_platform_config(platform)
        if not platform_config:
            print(f"ERROR: No configuration found for platform '{platform}'")
            return False
        
        missing_keys = []
        for key in required_keys:
            if platform_config.get(key) is None:
                missing_keys.append(key)
        
        if missing_keys:
            print(f"ERROR: Platform '{platform}' missing required keys: {missing_keys}")
            return False
        
        return True
    
    def get_paths(self) -> Dict[str, str]:
        """Get paths configuration from unified config."""
        return self.get_global_config('paths', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration from unified config."""
        return self.get_global_config('logging', {
            'level': 'INFO',
            'console_output': True,
            'file_output': True
        })
    
    def get_scheduling_config(self) -> Dict[str, Any]:
        """Get scheduling configuration from unified config."""
        return self.get_global_config('scheduling', {})
    
    def get_content_config(self) -> Dict[str, Any]:
        """Get content configuration from unified config."""
        return self.get_global_config('content', {})
    
    def get_interactive_config(self) -> Dict[str, Any]:
        """Get interactive configuration from unified config."""
        return self.get_global_config('interactive', {})
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration from unified config."""
        return self.get_global_config('security', {})
    
    def is_platform_enabled(self, platform: str) -> bool:
        """Check if a platform is enabled in unified config."""
        platform_config = self.get_platform_config(platform)
        if platform_config:
            return platform_config.get('enabled', True)  # Default to enabled for legacy configs
        return False
    
    def get_nested_value(self, key_path: str, default: Any = None) -> Any:
        """
        Get a nested configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to the value (e.g., 'scheduling.timezone')
            default: Default value if path not found
            
        Returns:
            Configuration value or default
        """
        if not self._loaded:
            self.load_all_configs()
        
        # Handle unified config access
        if hasattr(self, 'unified_config') and self.unified_config:
            config = self.unified_config
        else:
            config = self._config
        
        keys = key_path.split('.')
        current = config
        
        try:
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return default
            return current
        except (KeyError, TypeError):
            return default

    def get_meta_info(self) -> Dict[str, Any]:
        """Get meta information from unified config."""
        return self.get_global_config('meta', {})
    
    def get_raw_config(self) -> Dict[str, Any]:
        """Get the entire raw configuration dict (for debugging)."""
        if not self._loaded:
            self.load_all_configs()
        
        return self._config.copy()
    
    def reload_configs(self) -> None:
        """Force reload of all configuration files."""
        self._loaded = False
        self._config.clear()
        self._platforms.clear()
        self.load_all_configs()


# Global configuration manager instance
_global_config_manager: Optional[ConfigManager] = None


def get_config_manager(base_path: Optional[str] = None) -> ConfigManager:
    """
    Get the global configuration manager instance.
    
    Args:
        base_path: Base directory for config files (only used on first call)
        
    Returns:
        ConfigManager instance
    """
    global _global_config_manager
    
    if _global_config_manager is None:
        _global_config_manager = ConfigManager(base_path)
        _global_config_manager.load_all_configs()
    
    return _global_config_manager


# Convenience functions for easy access
def get_platform_config(platform: str) -> Optional[PlatformConfig]:
    """Get platform configuration."""
    return get_config_manager().get_platform_config(platform)


def get_platform_value(platform: str, key: str, default: Any = None) -> Any:
    """Get platform configuration value."""
    return get_config_manager().get_platform_value(platform, key, default)


def validate_platform(platform: str, required_keys: List[str]) -> bool:
    """Validate platform configuration."""
    return get_config_manager().validate_platform_config(platform, required_keys)


# Example usage and testing
if __name__ == "__main__":
    print("Testing ConfigManager...")
    
    # Create config manager
    config_manager = ConfigManager()
    config_manager.load_all_configs()
    
    # Test platform access
    platforms = config_manager.list_platforms()
    print(f"\nConfigured platforms: {platforms}")
    
    # Test Twitter configuration
    twitter_config = config_manager.get_platform_config('twitter')
    if twitter_config:
        print(f"\nTwitter config available: {twitter_config.name}")
        print(f"Twitter consumer_key: {twitter_config.get('consumer_key', 'NOT_FOUND')}")
    
    # Test BlueSky configuration  
    bsky_config = config_manager.get_platform_config('bluesky')
    if bsky_config:
        print(f"\nBlueSky config available: {bsky_config.name}")
        print(f"BlueSky handle: {bsky_config.get('handle', 'NOT_FOUND')}")
    
    # Test validation
    if twitter_config:
        valid = config_manager.validate_platform_config('twitter', 
            ['consumer_key', 'consumer_secret', 'access_token', 'access_token_secret'])
        print(f"\nTwitter config valid: {valid}")
    
    # Test global config access
    paths = config_manager.get_paths_config()
    print(f"\nPaths config: {paths}")
    
    print("\nConfiguration manager test completed.")