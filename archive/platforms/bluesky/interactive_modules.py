"""
Consolidated BlueSky Interactive Modules
Combines and consolidates all the duplicate interactive modules:
- 7 custom_reply variations
- notifications processing
- reactions handling  
- follow management
- repost functionality

Uses unified authentication and utilities for consistency.
Compatible with Python 3.10+ including 3.13.
"""

import os
import sys
import json
import csv
import random
import requests
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Add authentication and utilities
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent.parent / "utils"))

try:
    from bluesky_auth import BlueSkyAuth, get_bluesky_auth
    from error_logger import ErrorLogger
    from csv_handler import CSVHandler
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False
    BlueSkyAuth = None
    ErrorLogger = None
    CSVHandler = None


class BaseInteractiveModule:
    """Base class for all BlueSky interactive modules."""
    
    def __init__(self, module_name: str):
        """Initialize base interactive module."""
        self.module_name = module_name
        self.auth = get_bluesky_auth() if HAS_DEPS else None
        
        if HAS_DEPS:
            self.logger = ErrorLogger(f"bluesky_{module_name}")
            self.csv_handler = CSVHandler()
        else:
            self.logger = None
            self.csv_handler = None
        
        # Module-specific data files
        self.data_dir = Path(__file__).parent.parent.parent / "bsky" / "modules"
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _log(self, message: str, level: str = "info") -> None:
        """Log a message."""
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
            print(f"[{datetime.now()}] {self.module_name} {level.upper()}: {message}")
    
    def _load_json_data(self, filename: str, default=None) -> Any:
        """Load JSON data from file."""
        filepath = self.data_dir / filename
        try:
            if filepath.exists():
                with open(filepath, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self._log(f"Error loading {filename}: {e}", "warning")
        
        return default if default is not None else {}
    
    def _save_json_data(self, filename: str, data: Any) -> bool:
        """Save JSON data to file."""
        filepath = self.data_dir / filename
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            self._log(f"Error saving {filename}: {e}", "error")
            return False
    
    def _make_api_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make authenticated API request."""
        if not self.auth or not self.auth.authenticate():
            self._log("Authentication failed", "error")
            return None
        
        try:
            pds_url = self.auth.config.get('pds_url', 'https://bsky.social')
            url = f"{pds_url}/xrpc/{endpoint}"
            
            response = self.auth.make_authenticated_request(method, url, **kwargs)
            
            if response.status_code == 200:
                return response.json()
            else:
                self._log(f"API request failed: {response.status_code} - {response.text}", "warning")
                return None
                
        except Exception as e:
            self._log(f"API request error: {e}", "error")
            return None


class NotificationProcessor(BaseInteractiveModule):
    """Processes BlueSky notifications."""
    
    def __init__(self):
        super().__init__("notifications")
        self.processed_notifications = self._load_json_data("processed_notifications.json", set())
        if isinstance(self.processed_notifications, list):
            self.processed_notifications = set(self.processed_notifications)
    
    def get_notifications(self, since_minutes: int = 5) -> Optional[List[Dict]]:
        """Get recent notifications."""
        try:
            since_time = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(minutes=since_minutes)
            
            response = self._make_api_request(
                'GET',
                'app.bsky.notification.listNotifications',
                params={'since': since_time.isoformat()}
            )
            
            if response and 'notifications' in response:
                return response['notifications']
            
            return []
            
        except Exception as e:
            self._log(f"Error getting notifications: {e}", "error")
            return []
    
    def mark_notification_processed(self, notification_id: str) -> None:
        """Mark a notification as processed."""
        self.processed_notifications.add(notification_id)
        
        # Save periodically (every 10 notifications)
        if len(self.processed_notifications) % 10 == 0:
            self._save_json_data("processed_notifications.json", list(self.processed_notifications))
    
    def is_notification_processed(self, notification_id: str) -> bool:
        """Check if notification was already processed."""
        return notification_id in self.processed_notifications
    
    def run(self, config: Dict, session: Optional[Dict] = None) -> None:
        """Run notification processing."""
        self._log("Processing notifications")
        
        notifications = self.get_notifications()
        if not notifications:
            self._log("No notifications to process")
            return
        
        processed_count = 0
        for notification in notifications:
            notification_id = notification.get('cid')
            if not notification_id or self.is_notification_processed(notification_id):
                continue
            
            # Process the notification (this is where specific logic would go)
            self._process_notification(notification)
            self.mark_notification_processed(notification_id)
            processed_count += 1
        
        if processed_count > 0:
            self._log(f"Processed {processed_count} new notifications", "success")
            # Save final state
            self._save_json_data("processed_notifications.json", list(self.processed_notifications))
    
    def _process_notification(self, notification: Dict) -> None:
        """Process individual notification (override in subclasses)."""
        reason = notification.get('reason', 'unknown')
        author = notification.get('author', {}).get('handle', 'unknown')
        self._log(f"Notification: {reason} from {author}")


class ReplyProcessor(BaseInteractiveModule):
    """
    Consolidated custom reply processor.
    Combines functionality from all 7 custom_reply variations.
    """
    
    def __init__(self):
        super().__init__("custom_reply")
        
        # Reply management
        self.last_replied_users = self._load_json_data("last_replied_users.json", [])
        self.reply_window = 3  # Hours between replies to same user
        self.processed_notifications = self._load_json_data("processed_notifications.json", set())
        if isinstance(self.processed_notifications, list):
            self.processed_notifications = set(self.processed_notifications)
        
        # Pattern matching setup
        self.reply_patterns = self._load_reply_patterns()
    
    def _load_reply_patterns(self) -> List[Dict]:
        """Load reply patterns from CSV."""
        patterns = []
        
        try:
            # Try to load from bsky/data/replies.csv
            replies_file = Path(__file__).parent.parent.parent / "bsky" / "data" / "replies.csv"
            if replies_file.exists() and self.csv_handler:
                rows = self.csv_handler.read_csv_with_encodings(str(replies_file))
                if rows:
                    for row in rows[1:]:  # Skip header
                        if len(row) >= 2:
                            patterns.append({
                                'pattern': row[0].strip(),
                                'reply': row[1].strip(),
                                'type': 'wildcard'
                            })
            
            # Add default patterns if none loaded
            if not patterns:
                patterns = [
                    {'pattern': '*hello*', 'reply': 'Hello! How are you doing?', 'type': 'wildcard'},
                    {'pattern': '*joke*', 'reply': 'Here\'s one for you! 😄', 'type': 'wildcard'},
                    {'pattern': '*thanks*', 'reply': 'You\'re welcome! 😊', 'type': 'wildcard'},
                ]
            
            self._log(f"Loaded {len(patterns)} reply patterns")
            return patterns
            
        except Exception as e:
            self._log(f"Error loading reply patterns: {e}", "error")
            return []
    
    def wildcard_to_regex(self, wildcard: str) -> str:
        """Convert wildcard pattern to regex."""
        # Escape special regex characters except * and ?
        escaped = re.escape(wildcard)
        # Replace escaped wildcards with regex equivalents
        escaped = escaped.replace(r'\*', '.*')
        escaped = escaped.replace(r'\?', '.')
        return f'^{escaped}$'
    
    def matches_pattern(self, text: str, pattern: str) -> bool:
        """Check if text matches wildcard pattern."""
        try:
            regex = self.wildcard_to_regex(pattern.lower())
            return bool(re.match(regex, text.lower()))
        except Exception:
            return False
    
    def find_matching_reply(self, post_text: str) -> Optional[str]:
        """Find a matching reply for post text."""
        for pattern_data in self.reply_patterns:
            pattern = pattern_data.get('pattern', '')
            reply = pattern_data.get('reply', '')
            
            if self.matches_pattern(post_text, pattern):
                return reply
        
        return None
    
    def can_reply_to_user(self, user_handle: str) -> bool:
        """Check if we can reply to user (rate limiting)."""
        now = datetime.now()
        cutoff = now - timedelta(hours=self.reply_window)
        
        # Check recent replies
        recent_replies = [
            reply for reply in self.last_replied_users
            if reply.get('handle') == user_handle and
            datetime.fromisoformat(reply.get('timestamp', '1970-01-01')) > cutoff
        ]
        
        return len(recent_replies) == 0
    
    def record_reply(self, user_handle: str, post_uri: str) -> None:
        """Record that we replied to a user."""
        self.last_replied_users.append({
            'handle': user_handle,
            'post_uri': post_uri,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 100 replies
        self.last_replied_users = self.last_replied_users[-100:]
        self._save_json_data("last_replied_users.json", self.last_replied_users)
    
    def send_reply(self, reply_text: str, parent_post: Dict) -> bool:
        """Send reply to a post."""
        try:
            # Construct reply data
            reply_data = {
                "repo": self.auth.session_data.get('did'),
                "collection": "app.bsky.feed.post",
                "record": {
                    "text": reply_text,
                    "createdAt": datetime.utcnow().isoformat() + "Z",
                    "reply": {
                        "root": {
                            "uri": parent_post.get('uri'),
                            "cid": parent_post.get('cid')
                        },
                        "parent": {
                            "uri": parent_post.get('uri'),
                            "cid": parent_post.get('cid')
                        }
                    }
                }
            }
            
            response = self._make_api_request(
                'POST',
                'com.atproto.repo.createRecord',
                json=reply_data
            )
            
            if response:
                self._log(f"Sent reply: {reply_text[:50]}...", "success")
                return True
            else:
                self._log("Failed to send reply", "error")
                return False
                
        except Exception as e:
            self._log(f"Error sending reply: {e}", "error")
            return False
    
    def run(self, config: Dict, session: Optional[Dict] = None) -> None:
        """Run reply processing."""
        self._log("Processing replies")
        
        # Get recent notifications
        since_time = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(minutes=5)
        
        response = self._make_api_request(
            'GET',
            'app.bsky.notification.listNotifications',
            params={'since': since_time.isoformat()}
        )
        
        if not response or 'notifications' not in response:
            self._log("No notifications received")
            return
        
        reply_count = 0
        
        for notification in response['notifications']:
            # Process mentions and replies
            if notification.get('reason') not in ['mention', 'reply']:
                continue
            
            notification_id = notification.get('cid')
            if not notification_id or notification_id in self.processed_notifications:
                continue
            
            # Get post content
            record = notification.get('record', {})
            post_text = record.get('text', '')
            author = notification.get('author', {})
            author_handle = author.get('handle', '')
            
            if not post_text or not author_handle:
                continue
            
            # Check if we can reply to this user
            if not self.can_reply_to_user(author_handle):
                self._log(f"Skipping {author_handle} - recently replied")
                continue
            
            # Find matching reply
            reply_text = self.find_matching_reply(post_text)
            if not reply_text:
                self._log(f"No matching reply pattern for: {post_text[:50]}")
                continue
            
            # Send the reply
            if self.send_reply(reply_text, notification):
                self.record_reply(author_handle, notification.get('uri', ''))
                reply_count += 1
            
            # Mark notification as processed
            self.processed_notifications.add(notification_id)
        
        if reply_count > 0:
            self._log(f"Sent {reply_count} replies", "success")
        
        # Save processed notifications
        self._save_json_data("processed_notifications.json", list(self.processed_notifications))


class ReactionProcessor(BaseInteractiveModule):
    """Handles BlueSky reactions (likes)."""
    
    def __init__(self):
        super().__init__("reactions")
    
    def run(self, config: Dict, session: Optional[Dict] = None) -> None:
        """Run reaction processing."""
        self._log("Processing reactions")
        
        # Get recent notifications for mentions
        since_time = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(minutes=5)
        
        response = self._make_api_request(
            'GET',
            'app.bsky.notification.listNotifications',
            params={'since': since_time.isoformat()}
        )
        
        if not response or 'notifications' not in response:
            return
        
        like_count = 0
        
        for notification in response['notifications']:
            if notification.get('reason') == 'mention':
                # Like mentions
                if self._like_post(notification):
                    like_count += 1
        
        if like_count > 0:
            self._log(f"Liked {like_count} posts", "success")
    
    def _like_post(self, post: Dict) -> bool:
        """Like a post."""
        try:
            like_data = {
                "repo": self.auth.session_data.get('did'),
                "collection": "app.bsky.feed.like",
                "record": {
                    "subject": {
                        "uri": post.get('uri'),
                        "cid": post.get('cid')
                    },
                    "createdAt": datetime.utcnow().isoformat() + "Z"
                }
            }
            
            response = self._make_api_request(
                'POST',
                'com.atproto.repo.createRecord',
                json=like_data
            )
            
            return response is not None
            
        except Exception as e:
            self._log(f"Error liking post: {e}", "error")
            return False


class FollowProcessor(BaseInteractiveModule):
    """Handles BlueSky follow management."""
    
    def __init__(self):
        super().__init__("follow")
    
    def run(self, config: Dict, session: Optional[Dict] = None) -> None:
        """Run follow processing."""
        self._log("Processing follows")
        
        # Get recent followers
        response = self._make_api_request(
            'GET',
            'app.bsky.notification.listNotifications'
        )
        
        if not response or 'notifications' not in response:
            return
        
        follow_count = 0
        
        for notification in response['notifications']:
            if notification.get('reason') == 'follow':
                author = notification.get('author', {})
                if author.get('did') and self._should_follow_back(author):
                    if self._follow_user(author.get('did')):
                        follow_count += 1
        
        if follow_count > 0:
            self._log(f"Followed {follow_count} users back", "success")
    
    def _should_follow_back(self, author: Dict) -> bool:
        """Determine if we should follow back."""
        # Simple logic - follow back non-spam accounts
        followers = author.get('followersCount', 0)
        following = author.get('followsCount', 0)
        
        # Skip accounts with suspicious follow ratios
        if following > 0 and followers / following < 0.1:
            return False
        
        return True
    
    def _follow_user(self, did: str) -> bool:
        """Follow a user."""
        try:
            follow_data = {
                "repo": self.auth.session_data.get('did'),
                "collection": "app.bsky.graph.follow",
                "record": {
                    "subject": did,
                    "createdAt": datetime.utcnow().isoformat() + "Z"
                }
            }
            
            response = self._make_api_request(
                'POST',
                'com.atproto.repo.createRecord',
                json=follow_data
            )
            
            return response is not None
            
        except Exception as e:
            self._log(f"Error following user: {e}", "error")
            return False


class RepostProcessor(BaseInteractiveModule):
    """Handles BlueSky reposts."""
    
    def __init__(self):
        super().__init__("reposts")
        self.reposted_posts = self._load_json_data("reposted_posts.json", set())
        if isinstance(self.reposted_posts, list):
            self.reposted_posts = set(self.reposted_posts)
    
    def run(self, config: Dict, session: Optional[Dict] = None) -> None:
        """Run repost processing."""
        self._log("Processing reposts")
        
        # Get recent notifications for mentions
        response = self._make_api_request(
            'GET',
            'app.bsky.notification.listNotifications'
        )
        
        if not response or 'notifications' not in response:
            return
        
        repost_count = 0
        
        for notification in response['notifications']:
            if notification.get('reason') in ['mention', 'reply']:
                post_uri = notification.get('uri')
                if post_uri and post_uri not in self.reposted_posts:
                    # Check for #baddadjoke or #dadjokes hashtag in content
                    content = notification.get('record', {}).get('text', '').lower()
                    if '#baddadjoke' in content or '#dadjokes' in content:
                        if self._repost(notification):
                            self.reposted_posts.add(post_uri)
                            repost_count += 1
        
        if repost_count > 0:
            self._log(f"Reposted {repost_count} posts", "success")
            self._save_json_data("reposted_posts.json", list(self.reposted_posts))
    
    def _repost(self, post: Dict) -> bool:
        """Repost a post."""
        try:
            repost_data = {
                "repo": self.auth.session_data.get('did'),
                "collection": "app.bsky.feed.repost",
                "record": {
                    "subject": {
                        "uri": post.get('uri'),
                        "cid": post.get('cid')
                    },
                    "createdAt": datetime.utcnow().isoformat() + "Z"
                }
            }
            
            response = self._make_api_request(
                'POST',
                'com.atproto.repo.createRecord',
                json=repost_data
            )
            
            return response is not None
            
        except Exception as e:
            self._log(f"Error reposting: {e}", "error")
            return False


# Backward compatibility functions
def run_custom_reply(config: Dict, session: Optional[Dict] = None) -> None:
    """Backward compatibility function for custom_reply."""
    processor = ReplyProcessor()
    processor.run(config, session)

def run_notifications(config: Dict, session: Optional[Dict] = None) -> None:
    """Backward compatibility function for notifications."""
    processor = NotificationProcessor()
    processor.run(config, session)

def run_reactions(config: Dict, session: Optional[Dict] = None) -> None:
    """Backward compatibility function for reactions."""
    processor = ReactionProcessor()
    processor.run(config, session)

def run_follow(config: Dict, session: Optional[Dict] = None) -> None:
    """Backward compatibility function for follow."""
    processor = FollowProcessor()
    processor.run(config, session)

def run_custom_reposts(config: Dict, session: Optional[Dict] = None) -> None:
    """Backward compatibility function for reposts."""
    processor = RepostProcessor()
    processor.run(config, session)