"""
Consolidated BlueSky Platform Module
Combines posting functionality with interactive features.
Replaces bsky/bsky.py with enhanced, unified architecture.

Compatible with Python 3.10+ including 3.13.
"""

import sys
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Add platform base and utilities
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent))

try:
    from base import BasePlatform
    from bluesky_auth import BlueSkyAuth, get_bluesky_auth
    from interactive_modules import (
        NotificationProcessor,
        ReplyProcessor, 
        ReactionProcessor,
        FollowProcessor,
        RepostProcessor
    )
    HAS_PLATFORM_DEPS = True
except ImportError:
    HAS_PLATFORM_DEPS = False
    BasePlatform = object
    BlueSkyAuth = None


class BlueSkyPlatform(BasePlatform if HAS_PLATFORM_DEPS else object):
    """
    Unified BlueSky platform combining posting and interactive features.
    Replaces bsky/bsky.py with modern, maintainable architecture.
    """
    
    def __init__(self, **kwargs):
        """Initialize BlueSky platform."""
        if HAS_PLATFORM_DEPS:
            super().__init__('bluesky', **kwargs)
        else:
            self.platform_name = 'bluesky'
            self.logger = None
        
        # BlueSky-specific authentication
        self.bluesky_auth = get_bluesky_auth() if BlueSkyAuth else None
        
        # Interactive modules
        if HAS_PLATFORM_DEPS:
            self.notifications = NotificationProcessor()
            self.replies = ReplyProcessor()
            self.reactions = ReactionProcessor() 
            self.follows = FollowProcessor()
            self.reposts = RepostProcessor()
        
        # BlueSky-specific settings
        self.pds_url = "https://bsky.social"
        
    def authenticate(self) -> bool:
        """
        Authenticate with BlueSky API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        if not self.bluesky_auth:
            if self.logger:
                self.logger.error("BlueSky authentication not available")
            return False
        
        try:
            success = self.bluesky_auth.authenticate()
            if success:
                self._authenticated = True
                self._client = self.bluesky_auth
                if self.logger:
                    self.logger.success("BlueSky authentication successful")
            else:
                if self.logger:
                    self.logger.error("BlueSky authentication failed")
                    
            return success
            
        except Exception as e:
            if self.logger:
                self.logger.error("BlueSky authentication error", exception=e)
            return False
    
    def post_content(self, content: str, **kwargs) -> bool:
        """
        Post content to BlueSky.
        
        Args:
            content: Content to post
            **kwargs: Additional options:
                - reply_to: Post URI to reply to
                - images: List of image data to attach
                - embed_url: URL to embed in post
                
        Returns:
            True if post successful, False otherwise
        """
        try:
            if not self._authenticated:
                if self.logger:
                    self.logger.error("Not authenticated - cannot post")
                return False
            
            if not content.strip():
                if self.logger:
                    self.logger.warning("Empty content - skipping post")
                return False
            
            # Prepare post record
            post_record = {
                "text": content,
                "createdAt": datetime.utcnow().isoformat() + "Z"
            }
            
            # Handle reply
            reply_to = kwargs.get('reply_to')
            if reply_to:
                post_record["reply"] = {
                    "root": {"uri": reply_to, "cid": reply_to},
                    "parent": {"uri": reply_to, "cid": reply_to}
                }
            
            # Handle embeds (images, URLs, etc.)
            embed_url = kwargs.get('embed_url')
            if embed_url:
                post_record["embed"] = {
                    "$type": "app.bsky.embed.external",
                    "external": {
                        "uri": embed_url,
                        "title": "Link",
                        "description": ""
                    }
                }
            
            # Create the post
            post_data = {
                "repo": self.bluesky_auth.session_data.get('did'),
                "collection": "app.bsky.feed.post",
                "record": post_record
            }
            
            if self.logger:
                self.logger.info(f"Posting to BlueSky: {content[:100]}...")
            
            response = self.bluesky_auth.make_authenticated_request(
                'POST',
                f"{self.pds_url}/xrpc/com.atproto.repo.createRecord",
                json=post_data
            )
            
            if response.status_code == 200:
                response_data = response.json()
                post_uri = response_data.get('uri', 'unknown')
                
                if self.logger:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.logger.success(f"BlueSky post successful at {timestamp}")
                    self.logger.info(f"Post URI: {post_uri}")
                    self.logger.info(f"Content:\n{content}\n" + "-" * 20)
                
                return True
            else:
                if self.logger:
                    self.logger.error(f"BlueSky post failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            if self.logger:
                self.logger.error("BlueSky post error", exception=e)
            return False
    
    def run_interactive_modules(self, config: Dict) -> Dict[str, bool]:
        """
        Run all interactive modules (notifications, replies, etc.).
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Dictionary with results of each module
        """
        if not HAS_PLATFORM_DEPS:
            return {}
        
        results = {}
        modules = [
            ('notifications', self.notifications),
            ('replies', self.replies), 
            ('reactions', self.reactions),
            ('follows', self.follows),
            ('reposts', self.reposts)
        ]
        
        for module_name, module in modules:
            try:
                if self.logger:
                    self.logger.info(f"Running {module_name} module")
                
                module.run(config, self.bluesky_auth.get_session())
                results[module_name] = True
                
                if self.logger:
                    self.logger.success(f"{module_name} module completed")
                    
            except Exception as e:
                if self.logger:
                    self.logger.error(f"{module_name} module failed", exception=e)
                results[module_name] = False
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get BlueSky platform statistics."""
        stats = {}
        if HAS_PLATFORM_DEPS:
            stats = super().get_stats()
        else:
            stats = {'platform': self.platform_name, 'authenticated': False}
        
        if self.bluesky_auth and self.bluesky_auth.authenticated:
            try:
                session = self.bluesky_auth.get_session()
                if session:
                    stats.update({
                        'handle': session.get('handle'),
                        'did': session.get('did'),
                        'pds_url': self.pds_url
                    })
                    
                # Try to get profile info
                response = self.bluesky_auth.make_authenticated_request(
                    'GET',
                    f"{self.pds_url}/xrpc/app.bsky.actor.getProfile",
                    params={'actor': session.get('handle')}
                )
                
                if response.status_code == 200:
                    profile = response.json()
                    stats.update({
                        'followers_count': profile.get('followersCount'),
                        'follows_count': profile.get('followsCount'),
                        'posts_count': profile.get('postsCount')
                    })
                    
            except Exception as e:
                stats['stats_error'] = str(e)
        
        return stats
    
    def test_connection(self) -> bool:
        """Test BlueSky connection and API access."""
        if not self.bluesky_auth:
            return False
            
        return self.bluesky_auth.test_connection()


# Backward compatibility functions for existing bsky.py interface
def main() -> None:
    """Backward compatibility function for bsky.main()."""
    try:
        platform = BlueSkyPlatform()
        if platform.authenticate():
            success = platform.post_item_from_csv('jokes.csv', 'bsky')
            if success:
                print("BlueSky posting successful")
            else:
                print("BlueSky posting failed")
        else:
            print("BlueSky authentication failed")
    except Exception as e:
        print(f"BlueSky main() error: {e}")


def post_to_bluesky(content: str) -> bool:
    """
    Simple posting function for backward compatibility.
    
    Args:
        content: Content to post
        
    Returns:
        True if successful, False otherwise
    """
    try:
        platform = BlueSkyPlatform()
        if platform.authenticate():
            return platform.post_content(content)
        return False
    except Exception as e:
        print(f"BlueSky posting error: {e}")
        return False


# Example usage and testing
if __name__ == "__main__":
    print("Testing consolidated BlueSky platform...")
    
    try:
        # Create platform instance
        bluesky = BlueSkyPlatform()
        print(f"Platform created: {bluesky}")
        
        # Test authentication
        if bluesky.authenticate():
            print("Authentication successful!")
            
            # Get stats
            stats = bluesky.get_stats()
            print(f"Platform stats: {stats}")
            
            # Test connection
            if bluesky.test_connection():
                print("Connection test passed!")
            
            # Test posting (uncomment to actually post)
            # success = bluesky.post_content("Test post from consolidated BlueSky platform!")
            # print(f"Test post result: {success}")
            
            # Test CSV posting (uncomment to actually post)
            # success = bluesky.post_item_from_csv("jokes.csv", "bsky")
            # print(f"CSV post result: {success}")
            
            # Test interactive modules
            print("Testing interactive modules...")
            config = {"bsky": {"pds_url": "https://bsky.social"}}
            module_results = bluesky.run_interactive_modules(config)
            print(f"Interactive module results: {module_results}")
            
        else:
            print("Authentication failed")
    
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nTesting backward compatibility...")
    
    # Test main function
    try:
        main()
    except Exception as e:
        print(f"main() test result: {e}")
    
    print("Consolidated BlueSky platform test completed.")