"""
Mastodon Platform Module
Modernized version of toot/toot.py using the new base platform architecture.
Uses foundation utilities for consistency and eliminates code duplication.

Compatible with Python 3.10+ including 3.13.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Add platform base to path
sys.path.append(str(Path(__file__).parent))

from base import BasePlatform

try:
    from mastodon import Mastodon, MastodonAPIError
    HAS_MASTODON = True
except ImportError:
    HAS_MASTODON = False
    Mastodon = None
    MastodonAPIError = Exception


class MastodonPlatform(BasePlatform):
    """
    Mastodon posting platform using the unified base architecture.
    Replaces the functionality in toot/toot.py with modern, maintainable code.
    """
    
    def __init__(self, **kwargs):
        """Initialize Mastodon platform."""
        super().__init__('mastodon', **kwargs)
        
        # Mastodon-specific attributes
        self._mastodon_client = None
        
        # Validate dependencies
        if not HAS_MASTODON:
            raise ImportError(
                "mastodon.py library not available. Install with: pip install Mastodon.py"
            )
        
        # Validate required configuration
        required_keys = ['client_id', 'client_secret', 'access_token', 'api_base_url']
        if not self.validate_required_config(required_keys):
            raise ValueError(f"Missing required Mastodon configuration keys: {required_keys}")
    
    def authenticate(self) -> bool:
        """
        Authenticate with Mastodon API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            if self._authenticated and self._mastodon_client:
                return True
            
            self.logger.info("Authenticating with Mastodon...")
            
            # Get configuration values
            client_id = self.get_config_value('client_id')
            client_secret = self.get_config_value('client_secret') 
            access_token = self.get_config_value('access_token')
            api_base_url = self.get_config_value('api_base_url')
            
            # Initialize Mastodon client
            self._mastodon_client = Mastodon(
                client_id=client_id,
                client_secret=client_secret,
                access_token=access_token,
                api_base_url=api_base_url
            )
            
            # Test the connection by getting account info
            try:
                account_info = self._mastodon_client.me()
                self.logger.success(f"Authenticated as @{account_info['username']}")
                self._authenticated = True
                self._client = self._mastodon_client
                return True
                
            except MastodonAPIError as e:
                self.logger.error(
                    f"Mastodon API authentication failed: {e}",
                    details={'api_base_url': api_base_url}
                )
                return False
            
        except Exception as e:
            self.logger.error(
                "Unexpected error during Mastodon authentication",
                exception=e
            )
            return False
    
    def post_content(self, content: str, **kwargs) -> bool:
        """
        Post content to Mastodon.
        
        Args:
            content: Content to post (toot text)
            **kwargs: Additional options:
                - visibility: 'public', 'unlisted', 'private', 'direct'
                - in_reply_to_id: ID of toot to reply to
                - media_ids: List of media attachment IDs
                - sensitive: Mark toot as sensitive
                - spoiler_text: Content warning text
                
        Returns:
            True if post successful, False otherwise
        """
        try:
            if not self._authenticated:
                self.logger.error("Not authenticated - cannot post")
                return False
            
            if not content.strip():
                self.logger.warning("Empty content - skipping post")
                return False
            
            # Extract Mastodon-specific options
            visibility = kwargs.get('visibility', 'public')
            in_reply_to_id = kwargs.get('in_reply_to_id')
            media_ids = kwargs.get('media_ids')
            sensitive = kwargs.get('sensitive', False)
            spoiler_text = kwargs.get('spoiler_text')
            
            # Post the toot (using status_post for newer Mastodon.py versions)
            self.logger.info(f"Posting toot: {content[:100]}...")

            toot_response = self._mastodon_client.status_post(
                content,
                visibility=visibility,
                in_reply_to_id=in_reply_to_id,
                media_ids=media_ids,
                sensitive=sensitive,
                spoiler_text=spoiler_text
            )
            
            # Log success with toot details
            toot_url = toot_response.get('url', 'N/A')
            toot_id = toot_response.get('id', 'N/A')
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.logger.success(
                f"Toot posted successfully at {timestamp}"
            )
            self.logger.info(f"Toot ID: {toot_id}, URL: {toot_url}")
            self.logger.info(f"Content:\n{content}\n" + "-" * 20)
            
            return True
            
        except MastodonAPIError as e:
            self.logger.error(
                f"Mastodon API error during post: {e}",
                details={
                    'content_length': len(content),
                    'visibility': kwargs.get('visibility', 'public')
                }
            )
            return False
            
        except Exception as e:
            self.logger.error(
                "Unexpected error during Mastodon post",
                details={'content_length': len(content)},
                exception=e
            )
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Mastodon platform statistics."""
        stats = super().get_stats()
        
        if self._authenticated and self._mastodon_client:
            try:
                # Get account info
                account = self._mastodon_client.me()
                stats.update({
                    'username': account.get('username'),
                    'display_name': account.get('display_name'),
                    'followers_count': account.get('followers_count'),
                    'following_count': account.get('following_count'),
                    'statuses_count': account.get('statuses_count'),
                    'instance': self.get_config_value('api_base_url')
                })
            except Exception as e:
                stats['stats_error'] = str(e)
        
        return stats
    
    def test_connection(self) -> bool:
        """Test Mastodon connection and API access."""
        try:
            if not self.authenticate():
                return False
            
            # Try to get instance info as a connection test
            instance_info = self._mastodon_client.instance()
            instance_name = instance_info.get('title', 'Unknown')
            
            self.logger.success(f"Connection test successful - Connected to {instance_name}")
            return True
            
        except Exception as e:
            self.logger.error("Connection test failed", exception=e)
            return False


# Backward compatibility function to maintain existing interface
def toot_item(filename: str, index_key: str, add_text: Optional[str] = None) -> bool:
    """
    Backward compatibility function for existing toot_item calls.
    This maintains the exact same interface as the original toot.py
    
    Args:
        filename: CSV file containing toots
        index_key: Index key for tracking position
        add_text: Additional text to append
        
    Returns:
        True if successful, False otherwise
    """
    try:
        platform = MastodonPlatform()
        return platform.post_item_from_csv(filename, index_key, add_text)
    except Exception as e:
        # Fallback to basic error logging if platform creation fails
        print(f"ERROR: Mastodon posting failed: {e}")
        return False


# Example usage and testing
if __name__ == "__main__":
    print("Testing MastodonPlatform...")
    
    try:
        # Create platform instance
        mastodon = MastodonPlatform()
        print(f"Platform created: {mastodon}")
        
        # Test authentication
        if mastodon.authenticate():
            print("Authentication successful!")
            
            # Get stats
            stats = mastodon.get_stats()
            print(f"Platform stats: {stats}")
            
            # Test connection
            if mastodon.test_connection():
                print("Connection test passed!")
            
            # Test posting (uncomment to actually post)
            # success = mastodon.post_content("Test post from new MastodonPlatform!")
            # print(f"Test post result: {success}")
            
            # Test CSV posting (uncomment to actually post)
            # success = mastodon.post_item_from_csv("jokes.csv", "Mastodon")
            # print(f"CSV post result: {success}")
            
        else:
            print("Authentication failed")
    
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nTesting backward compatibility function...")
    
    # Test backward compatibility (uncomment to actually post)
    # result = toot_item("jokes.csv", "Mastodon")
    # print(f"Backward compatibility result: {result}")
    
    print("MastodonPlatform test completed.")