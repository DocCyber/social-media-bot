#!/usr/bin/env python3
"""
Cross-Platform Content Coordination System
Manages content distribution and prevents duplicate posts across platforms.
"""

import json
import hashlib
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import sys

sys.path.append(str(Path(__file__).parent.parent))

from utils.date_aware_logger import get_enhanced_logger
from utils.monitoring import record_metric
from utils.config_manager import ConfigManager

class ContentType(Enum):
    JOKE = "joke"
    ADVERTISEMENT = "advertisement" 
    COMIC = "comic"
    INTERACTION = "interaction"
    CUSTOM = "custom"

class PostStatus(Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class ContentItem:
    id: str
    content: str
    content_type: ContentType
    platforms: List[str]
    scheduled_times: Dict[str, datetime]
    status: Dict[str, PostStatus]
    metadata: Dict[str, Any]
    content_hash: str = ""
    created_at: datetime = None
    priority: int = 1

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.md5(self.content.encode('utf-8')).hexdigest()
        if not self.created_at:
            self.created_at = datetime.now()
        if not self.status:
            self.status = {platform: PostStatus.PENDING for platform in self.platforms}

class ContentCoordinator:
    def __init__(self):
        self.logger = get_enhanced_logger("content_coordinator", enable_background_markers=False)
        self.config_manager = ConfigManager()
        
        # Content tracking
        self.pending_content: Dict[str, ContentItem] = {}
        self.posted_content: Dict[str, ContentItem] = {}
        self.content_history: List[str] = []  # Content hashes to prevent duplicates
        
        # Platform coordination
        self.platform_queues: Dict[str, List[str]] = {
            "twitter": [],
            "mastodon": [],
            "bluesky": []
        }
        
        self.platform_cooldowns: Dict[str, datetime] = {}
        self.platform_limits: Dict[str, Dict[str, int]] = {
            "twitter": {"daily_limit": 100, "hourly_limit": 15},
            "mastodon": {"daily_limit": 200, "hourly_limit": 25},
            "bluesky": {"daily_limit": 150, "hourly_limit": 20}
        }
        
        self._load_state()
        
        self.logger.info("Content coordinator initialized")

    def _load_state(self):
        """Load coordinator state from file."""
        state_file = Path(__file__).parent / "coordinator_state.json"
        
        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                
                # Restore pending content
                for content_data in state.get('pending_content', []):
                    content_item = self._dict_to_content_item(content_data)
                    self.pending_content[content_item.id] = content_item
                
                # Restore posted content (last 1000 items)
                for content_data in state.get('posted_content', [])[-1000:]:
                    content_item = self._dict_to_content_item(content_data)
                    self.posted_content[content_item.id] = content_item
                
                # Restore content history
                self.content_history = state.get('content_history', [])[-5000:]  # Keep last 5000
                
                # Restore platform queues
                self.platform_queues = state.get('platform_queues', self.platform_queues)
                
                self.logger.info(f"Loaded coordinator state: {len(self.pending_content)} pending, {len(self.posted_content)} posted")
                
            except Exception as e:
                self.logger.error(f"Error loading coordinator state: {e}")

    def _save_state(self):
        """Save coordinator state to file."""
        state_file = Path(__file__).parent / "coordinator_state.json"
        
        try:
            state = {
                'pending_content': [self._content_item_to_dict(item) for item in self.pending_content.values()],
                'posted_content': [self._content_item_to_dict(item) for item in list(self.posted_content.values())[-1000:]],
                'content_history': self.content_history[-5000:],
                'platform_queues': self.platform_queues,
                'saved_at': datetime.now().isoformat()
            }
            
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Error saving coordinator state: {e}")

    def _dict_to_content_item(self, data: Dict) -> ContentItem:
        """Convert dictionary to ContentItem."""
        # Handle datetime fields
        scheduled_times = {}
        for platform, time_str in data.get('scheduled_times', {}).items():
            if isinstance(time_str, str):
                scheduled_times[platform] = datetime.fromisoformat(time_str)
            else:
                scheduled_times[platform] = time_str
        
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        # Handle enum fields
        content_type = ContentType(data.get('content_type', 'custom'))
        
        status = {}
        for platform, status_str in data.get('status', {}).items():
            status[platform] = PostStatus(status_str)
        
        return ContentItem(
            id=data['id'],
            content=data['content'],
            content_type=content_type,
            platforms=data['platforms'],
            scheduled_times=scheduled_times,
            status=status,
            metadata=data.get('metadata', {}),
            content_hash=data.get('content_hash', ''),
            created_at=created_at,
            priority=data.get('priority', 1)
        )

    def _content_item_to_dict(self, item: ContentItem) -> Dict:
        """Convert ContentItem to dictionary."""
        return {
            'id': item.id,
            'content': item.content,
            'content_type': item.content_type.value,
            'platforms': item.platforms,
            'scheduled_times': {k: v.isoformat() if isinstance(v, datetime) else v 
                              for k, v in item.scheduled_times.items()},
            'status': {k: v.value for k, v in item.status.items()},
            'metadata': item.metadata,
            'content_hash': item.content_hash,
            'created_at': item.created_at.isoformat() if item.created_at else None,
            'priority': item.priority
        }

    def add_content(self, content: str, content_type: ContentType, 
                   platforms: List[str], scheduled_times: Optional[Dict[str, datetime]] = None,
                   metadata: Optional[Dict[str, Any]] = None, priority: int = 1) -> str:
        """Add content for coordinated posting."""
        
        # Check for duplicate content
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        if content_hash in self.content_history:
            self.logger.warning("Duplicate content detected, skipping")
            return None
        
        # Generate unique ID
        content_id = str(uuid.uuid4())
        
        # Set default scheduled times if not provided
        if not scheduled_times:
            scheduled_times = {}
            base_time = datetime.now() + timedelta(minutes=30)
            for platform in platforms:
                scheduled_times[platform] = base_time + timedelta(minutes=platforms.index(platform) * 5)
        
        # Create content item
        content_item = ContentItem(
            id=content_id,
            content=content,
            content_type=content_type,
            platforms=platforms,
            scheduled_times=scheduled_times,
            status={platform: PostStatus.PENDING for platform in platforms},
            metadata=metadata or {},
            content_hash=content_hash,
            priority=priority
        )
        
        # Add to pending content
        self.pending_content[content_id] = content_item
        self.content_history.append(content_hash)
        
        # Add to platform queues
        for platform in platforms:
            if platform in self.platform_queues:
                self.platform_queues[platform].append(content_id)
        
        self._save_state()
        
        self.logger.info(f"Added content for {len(platforms)} platforms: {content_id}")
        record_metric("content_added", 1, "coordinator", {"platforms": len(platforms)})
        
        return content_id

    def get_next_content(self, platform: str) -> Optional[ContentItem]:
        """Get the next content item for a platform."""
        if platform not in self.platform_queues or not self.platform_queues[platform]:
            return None
        
        # Check platform cooldown
        if platform in self.platform_cooldowns:
            if datetime.now() < self.platform_cooldowns[platform]:
                return None
        
        # Check platform limits
        if self._check_platform_limits(platform):
            return None
        
        # Get next content from queue (priority sorted)
        queue = self.platform_queues[platform]
        available_content = []
        
        for content_id in queue:
            if content_id in self.pending_content:
                content_item = self.pending_content[content_id]
                if content_item.status.get(platform) == PostStatus.PENDING:
                    # Check if scheduled time has arrived
                    scheduled_time = content_item.scheduled_times.get(platform)
                    if not scheduled_time or scheduled_time <= datetime.now():
                        available_content.append((content_item.priority, content_item))
        
        if not available_content:
            return None
        
        # Sort by priority (higher priority first)
        available_content.sort(key=lambda x: x[0], reverse=True)
        
        return available_content[0][1]

    def mark_content_posted(self, content_id: str, platform: str, success: bool = True):
        """Mark content as posted for a platform."""
        if content_id not in self.pending_content:
            self.logger.warning(f"Content {content_id} not found in pending content")
            return
        
        content_item = self.pending_content[content_id]
        
        if success:
            content_item.status[platform] = PostStatus.POSTED
            self.logger.info(f"Content {content_id} posted successfully on {platform}")
            record_metric("content_posted", 1, "coordinator", {"platform": platform})
        else:
            content_item.status[platform] = PostStatus.FAILED
            self.logger.error(f"Content {content_id} failed to post on {platform}")
            record_metric("content_failed", 1, "coordinator", {"platform": platform})
        
        # Remove from platform queue
        if platform in self.platform_queues and content_id in self.platform_queues[platform]:
            self.platform_queues[platform].remove(content_id)
        
        # Check if content is complete for all platforms
        if all(status in [PostStatus.POSTED, PostStatus.FAILED, PostStatus.SKIPPED] 
               for status in content_item.status.values()):
            # Move to posted content
            self.posted_content[content_id] = content_item
            del self.pending_content[content_id]
        
        # Set platform cooldown
        self._set_platform_cooldown(platform)
        
        self._save_state()

    def _check_platform_limits(self, platform: str) -> bool:
        """Check if platform has reached posting limits."""
        if platform not in self.platform_limits:
            return False
        
        limits = self.platform_limits[platform]
        now = datetime.now()
        
        # Count posts in last hour and day
        hourly_posts = 0
        daily_posts = 0
        
        for content_item in self.posted_content.values():
            if platform in content_item.status and content_item.status[platform] == PostStatus.POSTED:
                post_time = content_item.scheduled_times.get(platform)
                if post_time:
                    if now - post_time < timedelta(hours=1):
                        hourly_posts += 1
                    if now - post_time < timedelta(days=1):
                        daily_posts += 1
        
        # Check limits
        if hourly_posts >= limits.get("hourly_limit", 100):
            self.logger.warning(f"Hourly limit reached for {platform}: {hourly_posts}")
            return True
        
        if daily_posts >= limits.get("daily_limit", 1000):
            self.logger.warning(f"Daily limit reached for {platform}: {daily_posts}")
            return True
        
        return False

    def _set_platform_cooldown(self, platform: str):
        """Set cooldown period for a platform after posting."""
        cooldown_minutes = {
            "twitter": 5,   # 5 minutes between Twitter posts
            "mastodon": 3,  # 3 minutes between Mastodon posts
            "bluesky": 4    # 4 minutes between Bluesky posts
        }
        
        minutes = cooldown_minutes.get(platform, 5)
        self.platform_cooldowns[platform] = datetime.now() + timedelta(minutes=minutes)

    def schedule_cross_platform_content(self, content: str, content_type: ContentType,
                                       platforms: List[str], stagger_minutes: int = 5,
                                       start_time: Optional[datetime] = None,
                                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """Schedule content across multiple platforms with staggered timing."""
        
        if not start_time:
            start_time = datetime.now() + timedelta(minutes=10)
        
        # Create staggered schedule
        scheduled_times = {}
        for i, platform in enumerate(platforms):
            scheduled_times[platform] = start_time + timedelta(minutes=i * stagger_minutes)
        
        content_id = self.add_content(
            content=content,
            content_type=content_type,
            platforms=platforms,
            scheduled_times=scheduled_times,
            metadata=metadata,
            priority=2  # Higher priority for cross-platform content
        )
        
        self.logger.info(f"Scheduled cross-platform content {content_id} across {len(platforms)} platforms")
        
        return content_id

    def get_platform_statistics(self, platform: str) -> Dict[str, Any]:
        """Get posting statistics for a platform."""
        now = datetime.now()
        stats = {
            "total_pending": 0,
            "total_posted": 0,
            "total_failed": 0,
            "posts_last_hour": 0,
            "posts_last_day": 0,
            "queue_length": len(self.platform_queues.get(platform, [])),
            "next_available": None
        }
        
        # Count pending content
        for content_item in self.pending_content.values():
            if platform in content_item.status:
                if content_item.status[platform] == PostStatus.PENDING:
                    stats["total_pending"] += 1
        
        # Count posted and failed content
        for content_item in self.posted_content.values():
            if platform in content_item.status:
                status = content_item.status[platform]
                post_time = content_item.scheduled_times.get(platform)
                
                if status == PostStatus.POSTED:
                    stats["total_posted"] += 1
                    if post_time and now - post_time < timedelta(hours=1):
                        stats["posts_last_hour"] += 1
                    if post_time and now - post_time < timedelta(days=1):
                        stats["posts_last_day"] += 1
                elif status == PostStatus.FAILED:
                    stats["total_failed"] += 1
        
        # Next available time
        if platform in self.platform_cooldowns:
            if self.platform_cooldowns[platform] > now:
                stats["next_available"] = self.platform_cooldowns[platform].isoformat()
        
        return stats

    def cleanup_old_content(self, days_old: int = 7):
        """Clean up old posted content."""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        # Clean posted content
        old_content_ids = []
        for content_id, content_item in self.posted_content.items():
            if content_item.created_at and content_item.created_at < cutoff_date:
                old_content_ids.append(content_id)
        
        for content_id in old_content_ids:
            del self.posted_content[content_id]
        
        # Clean content history
        if len(self.content_history) > 10000:
            self.content_history = self.content_history[-5000:]
        
        if old_content_ids:
            self.logger.info(f"Cleaned up {len(old_content_ids)} old content items")
            self._save_state()

    def get_content_preview(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get preview of pending and recent content."""
        preview = []
        
        # Recent posted content
        recent_posted = sorted(
            self.posted_content.values(),
            key=lambda x: x.created_at or datetime.min,
            reverse=True
        )[:limit//2]
        
        for content_item in recent_posted:
            preview.append({
                "id": content_item.id,
                "content": content_item.content[:100] + "..." if len(content_item.content) > 100 else content_item.content,
                "type": content_item.content_type.value,
                "platforms": content_item.platforms,
                "status": {k: v.value for k, v in content_item.status.items()},
                "created_at": content_item.created_at.isoformat() if content_item.created_at else None
            })
        
        # Pending content
        pending_sorted = sorted(
            self.pending_content.values(),
            key=lambda x: x.priority,
            reverse=True
        )[:limit//2]
        
        for content_item in pending_sorted:
            preview.append({
                "id": content_item.id,
                "content": content_item.content[:100] + "..." if len(content_item.content) > 100 else content_item.content,
                "type": content_item.content_type.value,
                "platforms": content_item.platforms,
                "status": {k: v.value for k, v in content_item.status.items()},
                "scheduled_times": {k: v.isoformat() for k, v in content_item.scheduled_times.items()},
                "priority": content_item.priority
            })
        
        return preview

def get_content_coordinator() -> ContentCoordinator:
    """Get the global content coordinator instance."""
    if not hasattr(get_content_coordinator, '_instance'):
        get_content_coordinator._instance = ContentCoordinator()
    return get_content_coordinator._instance