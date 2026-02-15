"""
Unified BlueSky Authentication Module
Consolidates the duplicate authentication logic found in 13+ BlueSky modules.
Provides centralized session management with JWT refresh capabilities.

Compatible with Python 3.10+ including 3.13.
"""

import json
import requests
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

# Add utils to path for enhanced logging
sys.path.append(str(Path(__file__).parent.parent.parent / "utils"))

try:
    from error_logger import ErrorLogger
    from config_manager import ConfigManager
    HAS_UTILS = True
except ImportError:
    HAS_UTILS = False
    ErrorLogger = None
    ConfigManager = None


class BlueSkyAuth:
    """
    Unified BlueSky authentication and session management.
    Replaces duplicate auth logic across multiple BlueSky modules.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize BlueSky authentication.
        
        Args:
            config_path: Path to config file (defaults to bsky/config.json)
        """
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), "..", "..", "bsky", "config.json")
        self.session_data = None
        self.authenticated = False
        
        # Initialize logging
        if HAS_UTILS:
            self.logger = ErrorLogger("bluesky_auth")
            self.config_manager = ConfigManager()
            self.config_manager.load_all_configs()
        else:
            self.logger = None
            self.config_manager = None
        
        # Load configuration
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load BlueSky configuration from file."""
        try:
            if self.config_manager:
                # Use unified config manager
                bluesky_config = self.config_manager.get_platform_config('bluesky')
                if bluesky_config:
                    return bluesky_config.config
            
            # Fallback to direct file loading
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    return config.get('bsky', {})
            
            # Try alternate config locations
            alt_paths = [
                os.path.join(os.path.dirname(__file__), "..", "..", "config.json"),
                os.path.join(os.path.dirname(__file__), "..", "..", "keys.json")
            ]
            
            for alt_path in alt_paths:
                if os.path.exists(alt_path):
                    with open(alt_path, 'r') as f:
                        config = json.load(f)
                        bsky_config = config.get('bsky', {})
                        if bsky_config:
                            return bsky_config
                        
            self._log("No BlueSky configuration found", "warning")
            return {}
            
        except Exception as e:
            self._log(f"Failed to load BlueSky config: {e}", "error")
            return {}
    
    def _log(self, message: str, level: str = "info") -> None:
        """Log a message using available logger."""
        if self.logger:
            if level == "info":
                self.logger.info(message)
            elif level == "warning":
                self.logger.warning(message)
            elif level == "error":
                self.logger.error(message)
            elif level == "success":
                self.logger.success(message)
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] BlueSky Auth {level.upper()}: {message}")
    
    def create_session(self) -> bool:
        """
        Create a new BlueSky session using credentials.
        
        Returns:
            True if session created successfully, False otherwise
        """
        try:
            handle = self.config.get('handle')
            app_password = self.config.get('app_password')
            pds_url = self.config.get('pds_url', 'https://bsky.social')
            
            if not handle or not app_password:
                self._log("Missing BlueSky handle or app_password in config", "error")
                return False
            
            self._log(f"Creating BlueSky session for {handle}")
            
            # Create session
            response = requests.post(
                f"{pds_url}/xrpc/com.atproto.server.createSession",
                headers={"Content-Type": "application/json"},
                json={"identifier": handle, "password": app_password}
            )
            
            if response.status_code == 200:
                self.session_data = response.json()
                self.authenticated = True
                self._log("BlueSky session created successfully", "success")
                
                # Update config with tokens (if available)
                self._update_stored_tokens()
                
                return True
            else:
                self._log(f"Failed to create BlueSky session: {response.status_code} - {response.text}", "error")
                return False
                
        except Exception as e:
            self._log(f"Exception during BlueSky session creation: {e}", "error")
            return False
    
    def refresh_session(self) -> bool:
        """
        Refresh existing BlueSky session using refresh token.
        
        Returns:
            True if session refreshed successfully, False otherwise
        """
        try:
            # Try to get refresh token from current session or config
            refresh_token = None
            
            if self.session_data and 'refreshJwt' in self.session_data:
                refresh_token = self.session_data['refreshJwt']
            elif 'refreshJwt' in self.config:
                refresh_token = self.config['refreshJwt']
            
            if not refresh_token:
                self._log("No refresh token available, creating new session", "info")
                return self.create_session()
            
            pds_url = self.config.get('pds_url', 'https://bsky.social')
            
            self._log("Refreshing BlueSky session")
            
            # Refresh session
            response = requests.post(
                f"{pds_url}/xrpc/com.atproto.server.refreshSession",
                headers={"Authorization": f"Bearer {refresh_token}"}
            )
            
            if response.status_code == 200:
                self.session_data = response.json()
                self.authenticated = True
                self._log("BlueSky session refreshed successfully", "success")
                
                # Update stored tokens
                self._update_stored_tokens()
                
                return True
            else:
                self._log(f"Failed to refresh BlueSky session: {response.status_code} - {response.text}", "warning")
                # Try creating new session as fallback
                return self.create_session()
                
        except Exception as e:
            self._log(f"Exception during BlueSky session refresh: {e}", "error")
            # Try creating new session as fallback
            return self.create_session()
    
    def authenticate(self) -> bool:
        """
        Ensure valid authentication (refresh if needed, create if none exists).
        
        Returns:
            True if authenticated, False otherwise
        """
        if self.authenticated and self.session_data and self._is_token_valid():
            return True
        
        # Try refresh first, then create new
        if self.config.get('refreshJwt') or (self.session_data and self.session_data.get('refreshJwt')):
            if self.refresh_session():
                return True
        
        # Fallback to creating new session
        return self.create_session()
    
    def _is_token_valid(self) -> bool:
        """
        Check if current access token is still valid.
        
        Returns:
            True if token appears valid, False otherwise
        """
        if not self.session_data or 'accessJwt' not in self.session_data:
            return False
        
        # Simple token expiry check (JWT tokens typically expire in 2-24 hours)
        # For now, we'll assume tokens are valid for 2 hours
        if hasattr(self, '_last_auth_time'):
            time_since_auth = datetime.now() - self._last_auth_time
            if time_since_auth > timedelta(hours=2):
                return False
        
        return True
    
    def _update_stored_tokens(self) -> None:
        """Update stored tokens in config files for persistence."""
        if not self.session_data:
            return
        
        try:
            # Update timestamp
            self._last_auth_time = datetime.now()
            
            # Try to update the keys.json file with new tokens
            keys_file = os.path.join(os.path.dirname(__file__), "..", "..", "keys.json")
            if os.path.exists(keys_file):
                with open(keys_file, 'r') as f:
                    keys_data = json.load(f)
                
                if 'bsky' not in keys_data:
                    keys_data['bsky'] = {}
                
                keys_data['bsky'].update({
                    'accessJwt': self.session_data.get('accessJwt'),
                    'refreshJwt': self.session_data.get('refreshJwt'),
                    'handle': self.session_data.get('handle', self.config.get('handle')),
                    'pds_url': self.config.get('pds_url', 'https://bsky.social')
                })
                
                with open(keys_file, 'w') as f:
                    json.dump(keys_data, f, indent=4)
                
                self._log("Updated stored BlueSky tokens", "info")
        except Exception as e:
            self._log(f"Failed to update stored tokens: {e}", "warning")
    
    def get_session(self) -> Optional[Dict[str, Any]]:
        """
        Get current session data.
        
        Returns:
            Session data dictionary or None if not authenticated
        """
        if self.authenticated and self.session_data:
            return self.session_data.copy()
        return None
    
    def get_access_token(self) -> Optional[str]:
        """
        Get current access token.
        
        Returns:
            Access token string or None if not authenticated
        """
        if self.authenticated and self.session_data:
            return self.session_data.get('accessJwt')
        return None
    
    def get_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers with authentication.
        
        Returns:
            Headers dictionary with Authorization header
        """
        headers = {"Content-Type": "application/json"}
        
        token = self.get_access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        return headers
    
    def make_authenticated_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make an authenticated HTTP request to BlueSky API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: API endpoint URL
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
        """
        if not self.authenticate():
            raise Exception("Failed to authenticate with BlueSky")
        
        # Ensure headers include authentication
        headers = kwargs.get('headers', {})
        headers.update(self.get_headers())
        kwargs['headers'] = headers
        
        return requests.request(method, url, **kwargs)
    
    def test_connection(self) -> bool:
        """
        Test the BlueSky connection and authentication.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            if not self.authenticate():
                return False
            
            # Test with a simple API call
            pds_url = self.config.get('pds_url', 'https://bsky.social')
            response = self.make_authenticated_request(
                'GET',
                f"{pds_url}/xrpc/com.atproto.server.getSession"
            )
            
            if response.status_code == 200:
                session_info = response.json()
                handle = session_info.get('handle', 'Unknown')
                self._log(f"BlueSky connection test successful - Connected as {handle}", "success")
                return True
            else:
                self._log(f"BlueSky connection test failed: {response.status_code}", "error")
                return False
                
        except Exception as e:
            self._log(f"BlueSky connection test failed: {e}", "error")
            return False


# Global auth instance for shared use
_global_bluesky_auth = None

def get_bluesky_auth(config_path: Optional[str] = None) -> BlueSkyAuth:
    """
    Get global BlueSky authentication instance.
    
    Args:
        config_path: Optional config path (only used on first call)
        
    Returns:
        BlueSkyAuth instance
    """
    global _global_bluesky_auth
    
    if _global_bluesky_auth is None:
        _global_bluesky_auth = BlueSkyAuth(config_path)
    
    return _global_bluesky_auth


# Example usage and testing
if __name__ == "__main__":
    print("Testing BlueSky Authentication...")
    
    auth = BlueSkyAuth()
    
    print("Configuration loaded:")
    print(f"  Handle: {auth.config.get('handle', 'Not found')}")
    print(f"  PDS URL: {auth.config.get('pds_url', 'Not found')}")
    
    print("\nTesting authentication...")
    if auth.authenticate():
        print("Authentication successful!")
        
        session = auth.get_session()
        if session:
            print(f"  Handle: {session.get('handle')}")
            print(f"  Access token: {auth.get_access_token()[:20]}..." if auth.get_access_token() else "No token")
        
        print("\nTesting connection...")
        if auth.test_connection():
            print("Connection test passed!")
        else:
            print("Connection test failed!")
    else:
        print("Authentication failed!")
    
    print("\nBlueSky Authentication test completed.")