"""
Twitter Platform Module
Modernized version of tweet/tweet.py using the new base platform architecture.
Uses foundation utilities for consistency and eliminates code duplication.

Compatible with Python 3.10+ including 3.13.
"""

import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    requests = None

# Add platform base to path
sys.path.append(str(Path(__file__).parent))

from base import BasePlatform

try:
    from requests_oauthlib import OAuth1
    HAS_OAUTH = True
except ImportError:
    HAS_OAUTH = False
    OAuth1 = None

# Try to import image generation (optional)
try:
    sys.path.append(str(Path(__file__).parent.parent / "image"))
    from image import generate_image
    HAS_IMAGE_GEN = True
except ImportError:
    HAS_IMAGE_GEN = False
    generate_image = None


class TwitterPlatform(BasePlatform):
    """
    Twitter posting platform using the unified base architecture.
    Replaces the functionality in tweet/tweet.py with modern, maintainable code.
    """
    
    def __init__(self, **kwargs):
        """Initialize Twitter platform."""
        super().__init__('twitter', **kwargs)
        
        # Twitter-specific attributes
        self._oauth_auth = None
        self._bearer_token = None
        self._api_url = "https://api.twitter.com/2/tweets"
        self._headers = {"Content-Type": "application/json"}
        
        # Validate dependencies
        if not HAS_REQUESTS:
            raise ImportError(
                "requests library not available. Install with: pip install requests"
            )
        
        if not HAS_OAUTH:
            raise ImportError(
                "requests-oauthlib not available. Install with: pip install requests-oauthlib"
            )
        
        # Validate required configuration
        required_keys = ['consumer_key', 'consumer_secret', 'access_token', 'access_token_secret']
        if not self.validate_required_config(required_keys):
            raise ValueError(f"Missing required Twitter configuration keys: {required_keys}")
        
        # Optional bearer token check
        if not self.get_config_value('bearer_token'):
            self.logger.warning("No bearer token found - some API features may be limited")
    
    def authenticate(self) -> bool:
        """
        Authenticate with Twitter API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            if self._authenticated and self._oauth_auth:
                return True
            
            self.logger.info("Authenticating with Twitter...")
            
            # Get configuration values
            consumer_key = self.get_config_value('consumer_key')
            consumer_secret = self.get_config_value('consumer_secret')
            access_token = self.get_config_value('access_token')
            access_token_secret = self.get_config_value('access_token_secret')
            bearer_token = self.get_config_value('bearer_token')
            
            # Set up OAuth1 authentication
            self._oauth_auth = OAuth1(
                consumer_key,
                consumer_secret,
                access_token,
                access_token_secret
            )
            
            # Set up bearer token if available
            if bearer_token:
                self._bearer_token = bearer_token
                self._headers["Authorization"] = f"Bearer {bearer_token}"
            
            # Test authentication with a simple API call
            try:
                # Test with user info endpoint
                test_url = "https://api.twitter.com/2/users/me"
                test_response = requests.get(
                    test_url,
                    headers=self._headers if bearer_token else {},
                    auth=self._oauth_auth
                )
                
                if test_response.status_code == 200:
                    user_data = test_response.json()
                    username = user_data.get('data', {}).get('username', 'Unknown')
                    self.logger.success(f"Authenticated as @{username}")
                    self._authenticated = True
                    return True
                else:
                    self.logger.error(
                        f"Twitter authentication failed: {test_response.status_code} - {test_response.text}",
                        details={'status_code': test_response.status_code}
                    )
                    return False
                    
            except Exception as e:
                self.logger.error(
                    f"Twitter API request failed during authentication: {e}",
                    exception=e
                )
                return False
            
        except Exception as e:
            self.logger.error(
                "Unexpected error during Twitter authentication",
                exception=e
            )
            return False
    
    def post_content(self, content: str, **kwargs) -> bool:
        """
        Post content to Twitter.
        
        Args:
            content: Content to tweet
            **kwargs: Additional options:
                - media_ids: List of media attachment IDs
                - in_reply_to_tweet_id: ID of tweet to reply to
                - quote_tweet_id: ID of tweet to quote
                - generate_image: Whether to generate image for the tweet (default: True)
                - image_path: Custom image path to use instead of generating
                
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
            
            # Generate image if requested and available
            image_path = None
            if kwargs.get('generate_image', True) and HAS_IMAGE_GEN:
                try:
                    image_path = generate_image(content)
                    if image_path:
                        self.logger.info(f"Generated image: {image_path}")
                except Exception as e:
                    self.logger.warning(f"Image generation failed: {e}")
            
            # Prepare tweet data
            tweet_data = {"text": content}
            
            # Add optional parameters
            if kwargs.get('in_reply_to_tweet_id'):
                tweet_data["reply"] = {"in_reply_to_tweet_id": kwargs['in_reply_to_tweet_id']}
            
            if kwargs.get('quote_tweet_id'):
                tweet_data["quote_tweet_id"] = kwargs['quote_tweet_id']
            
            if kwargs.get('media_ids'):
                tweet_data["media"] = {"media_ids": kwargs['media_ids']}
            
            # Post the tweet
            self.logger.info(f"Posting tweet: {content[:100]}...")
            
            response = requests.post(
                self._api_url,
                headers=self._headers,
                data=json.dumps(tweet_data),
                auth=self._oauth_auth
            )
            
            self.logger.info(f"Twitter API response: {response.text}")
            
            # Parse response
            try:
                response_data = response.json()
                
                if response.status_code == 201 and 'data' in response_data:
                    # Success
                    tweet_id = response_data['data']['id']
                    tweet_text = response_data['data']['text']
                    
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.logger.success(
                        f"Tweet posted successfully at {timestamp}"
                    )
                    self.logger.info(f"Tweet ID: {tweet_id}")
                    self.logger.info(f"Content:\n{tweet_text}\n" + "-" * 20)
                    
                    return True
                    
                else:
                    # Error response
                    error_msg = response_data.get('detail', 'Unknown error')
                    errors = response_data.get('errors', [])
                    
                    self.logger.error(
                        f"Twitter API error: {response.status_code} - {error_msg}",
                        details={
                            'status_code': response.status_code,
                            'errors': errors,
                            'content_length': len(content)
                        }
                    )
                    return False
                    
            except json.JSONDecodeError:
                self.logger.error(
                    f"Invalid JSON response from Twitter API: {response.text}",
                    details={'status_code': response.status_code}
                )
                return False
            
        except Exception as e:
            if "requests" in str(type(e)):
                self.logger.error(
                    f"Network error during Twitter post: {e}",
                    details={'content_length': len(content)},
                    exception=e
                )
            else:
                self.logger.error(
                    "Unexpected error during Twitter post",
                    details={'content_length': len(content)},
                    exception=e
                )
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Twitter platform statistics."""
        stats = super().get_stats()
        
        if self._authenticated:
            try:
                # Get user info
                user_url = "https://api.twitter.com/2/users/me?user.fields=public_metrics"
                response = requests.get(
                    user_url,
                    headers=self._headers,
                    auth=self._oauth_auth
                )
                
                if response.status_code == 200:
                    user_data = response.json().get('data', {})
                    metrics = user_data.get('public_metrics', {})
                    
                    stats.update({
                        'username': user_data.get('username'),
                        'name': user_data.get('name'),
                        'followers_count': metrics.get('followers_count'),
                        'following_count': metrics.get('following_count'),
                        'tweet_count': metrics.get('tweet_count'),
                        'listed_count': metrics.get('listed_count')
                    })
                else:
                    stats['stats_error'] = f"API error: {response.status_code}"
                    
            except Exception as e:
                stats['stats_error'] = str(e)
        
        return stats
    
    def test_connection(self) -> bool:
        """Test Twitter connection and API access."""
        try:
            if not self.authenticate():
                return False
            
            # Try to get user info as a connection test
            test_url = "https://api.twitter.com/2/users/me"
            response = requests.get(
                test_url,
                headers=self._headers,
                auth=self._oauth_auth
            )
            
            if response.status_code == 200:
                user_data = response.json().get('data', {})
                username = user_data.get('username', 'Unknown')
                
                self.logger.success(f"Connection test successful - Connected as @{username}")
                return True
            else:
                self.logger.error(f"Connection test failed: {response.status_code} - {response.text}")
                return False
            
        except Exception as e:
            self.logger.error("Connection test failed", exception=e)
            return False
    
    def upload_media(self, media_path: str) -> Optional[str]:
        """
        Upload media to Twitter and return media ID.
        
        Args:
            media_path: Path to media file
            
        Returns:
            Media ID string if successful, None otherwise
        """
        try:
            # This would require the v1.1 media upload endpoint
            # Implementation would go here for media uploads
            self.logger.warning("Media upload not yet implemented")
            return None
            
        except Exception as e:
            self.logger.error("Media upload failed", exception=e)
            return None


# Backward compatibility function to maintain existing interface
def tweet_item(filename: str, index_key: str, add_text: Optional[str] = None) -> bool:
    """
    Backward compatibility function for existing tweet_item calls.
    This maintains the exact same interface as the original tweet.py
    
    Args:
        filename: CSV file containing tweets
        index_key: Index key for tracking position
        add_text: Additional text to append
        
    Returns:
        True if successful, False otherwise
    """
    try:
        platform = TwitterPlatform()
        return platform.post_item_from_csv(filename, index_key, add_text)
    except Exception as e:
        # Fallback to basic error logging if platform creation fails
        print(f"ERROR: Twitter posting failed: {e}")
        return False


# Example usage and testing
if __name__ == "__main__":
    print("Testing TwitterPlatform...")
    
    try:
        # Create platform instance
        twitter = TwitterPlatform()
        print(f"Platform created: {twitter}")
        
        # Test authentication
        if twitter.authenticate():
            print("Authentication successful!")
            
            # Get stats
            stats = twitter.get_stats()
            print(f"Platform stats: {stats}")
            
            # Test connection
            if twitter.test_connection():
                print("Connection test passed!")
            
            # Test posting (uncomment to actually post)
            # success = twitter.post_content("Test tweet from new TwitterPlatform! #automation")
            # print(f"Test tweet result: {success}")
            
            # Test CSV posting (uncomment to actually post)
            # success = twitter.post_item_from_csv("jokes.csv", "joke")
            # print(f"CSV tweet result: {success}")
            
        else:
            print("Authentication failed")
    
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nTesting backward compatibility function...")
    
    # Test backward compatibility (uncomment to actually post)
    # result = tweet_item("jokes.csv", "joke")
    # print(f"Backward compatibility result: {result}")
    
    print("TwitterPlatform test completed.")