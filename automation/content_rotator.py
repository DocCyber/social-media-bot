#!/usr/bin/env python3
"""
Automated Content Rotation System
Intelligently manages content selection, rotation, and freshness across platforms.
"""

import csv
import json
import random
import hashlib
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import sys

sys.path.append(str(Path(__file__).parent.parent))

from utils.csv_handler import CSVHandler
from utils.date_aware_logger import get_enhanced_logger
from utils.monitoring import record_metric
from utils.config_manager import ConfigManager
from automation.content_coordinator import ContentType, get_content_coordinator

class ContentSource(Enum):
    CSV_JOKES = "csv_jokes"
    CSV_REPLIES = "csv_replies"
    ADVERTISEMENTS = "advertisements"
    COMICS = "comics"
    CUSTOM = "custom"

@dataclass
class ContentPool:
    source: ContentSource
    items: List[Dict[str, Any]]
    used_recently: deque
    last_refreshed: datetime
    max_recent_history: int = 100

class ContentRotator:
    def __init__(self):
        self.logger = get_enhanced_logger("content_rotator")
        self.config_manager = ConfigManager()
        self.csv_handler = CSVHandler()
        self.coordinator = get_content_coordinator()
        
        # Content pools
        self.content_pools: Dict[ContentSource, ContentPool] = {}
        
        # Rotation tracking
        self.platform_preferences: Dict[str, Dict[str, Any]] = {
            "twitter": {
                "preferred_types": [ContentType.JOKE, ContentType.ADVERTISEMENT],
                "max_length": 280,
                "freshness_hours": 24
            },
            "mastodon": {
                "preferred_types": [ContentType.JOKE, ContentType.COMIC],
                "max_length": 500,
                "freshness_hours": 36
            },
            "bluesky": {
                "preferred_types": [ContentType.JOKE, ContentType.CUSTOM],
                "max_length": 300,
                "freshness_hours": 30
            }
        }
        
        # Content freshness tracking
        self.content_freshness: Dict[str, Dict[str, datetime]] = defaultdict(dict)
        
        # Initialize content pools
        self._initialize_content_pools()
        self._load_freshness_data()
        
        self.logger.info("Content rotator initialized")

    def _initialize_content_pools(self):
        """Initialize all content pools."""
        
        # Initialize CSV jokes pool
        jokes_file = self.config_manager.get_nested_value("paths.jokes_csv")
        if jokes_file and Path(jokes_file).exists():
            jokes_data = self.csv_handler.load_csv(jokes_file)
            self.content_pools[ContentSource.CSV_JOKES] = ContentPool(
                source=ContentSource.CSV_JOKES,
                items=jokes_data,
                used_recently=deque(maxlen=200),
                last_refreshed=datetime.now()
            )
            self.logger.info(f"Loaded {len(jokes_data)} jokes from CSV")
        
        # Initialize CSV replies pool
        replies_file = self.config_manager.get_nested_value("paths.replies_csv")
        if replies_file and Path(replies_file).exists():
            replies_data = self.csv_handler.load_csv(replies_file)
            self.content_pools[ContentSource.CSV_REPLIES] = ContentPool(
                source=ContentSource.CSV_REPLIES,
                items=replies_data,
                used_recently=deque(maxlen=100),
                last_refreshed=datetime.now()
            )
            self.logger.info(f"Loaded {len(replies_data)} replies from CSV")
        
        # Initialize advertisements pool
        ads_data = self._load_advertisements()
        self.content_pools[ContentSource.ADVERTISEMENTS] = ContentPool(
            source=ContentSource.ADVERTISEMENTS,
            items=ads_data,
            used_recently=deque(maxlen=50),
            last_refreshed=datetime.now()
        )
        
        # Initialize comics pool
        comics_data = self._load_comics()
        self.content_pools[ContentSource.COMICS] = ContentPool(
            source=ContentSource.COMICS,
            items=comics_data,
            used_recently=deque(maxlen=30),
            last_refreshed=datetime.now()
        )

    def _load_advertisements(self) -> List[Dict[str, Any]]:
        """Load advertisement content."""
        ads_file = Path(__file__).parent.parent / "data" / "advertisements.json"
        
        if ads_file.exists():
            try:
                with open(ads_file, 'r', encoding='utf-8') as f:
                    ads_data = json.load(f)
                    return ads_data.get('advertisements', [])
            except Exception as e:
                self.logger.error(f"Error loading advertisements: {e}")
        
        # Default advertisements if file doesn't exist
        return [
            {
                "content": "Check out our latest comedy content! 🎭 #Comedy #Humor",
                "priority": 2,
                "platforms": ["twitter", "mastodon", "bluesky"]
            },
            {
                "content": "Daily dose of humor coming your way! Follow for more laughs 😄",
                "priority": 1,
                "platforms": ["twitter", "bluesky"]
            }
        ]

    def _load_comics(self) -> List[Dict[str, Any]]:
        """Load comic content."""
        comics_dir = Path(__file__).parent.parent / "comics"
        comics_data = []
        
        if comics_dir.exists():
            for comic_file in comics_dir.glob("*.json"):
                try:
                    with open(comic_file, 'r', encoding='utf-8') as f:
                        comic_info = json.load(f)
                        comics_data.append(comic_info)
                except Exception as e:
                    self.logger.error(f"Error loading comic {comic_file}: {e}")
        
        return comics_data

    def _load_freshness_data(self):
        """Load content freshness tracking data."""
        freshness_file = Path(__file__).parent / "content_freshness.json"
        
        if freshness_file.exists():
            try:
                with open(freshness_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    for content_hash, platforms in data.items():
                        for platform, timestamp_str in platforms.items():
                            self.content_freshness[content_hash][platform] = datetime.fromisoformat(timestamp_str)
                            
                self.logger.debug("Loaded content freshness data")
                
            except Exception as e:
                self.logger.error(f"Error loading freshness data: {e}")

    def _save_freshness_data(self):
        """Save content freshness tracking data."""
        freshness_file = Path(__file__).parent / "content_freshness.json"
        
        try:
            data = {}
            for content_hash, platforms in self.content_freshness.items():
                data[content_hash] = {
                    platform: timestamp.isoformat()
                    for platform, timestamp in platforms.items()
                }
            
            with open(freshness_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving freshness data: {e}")

    def get_fresh_content(self, platform: str, content_type: Optional[ContentType] = None) -> Optional[Dict[str, Any]]:
        """Get fresh content for a platform."""
        
        platform_prefs = self.platform_preferences.get(platform, {})
        preferred_types = platform_prefs.get("preferred_types", [ContentType.JOKE])
        max_length = platform_prefs.get("max_length", 500)
        freshness_hours = platform_prefs.get("freshness_hours", 24)
        
        # Determine content type to use
        if content_type:
            target_types = [content_type]
        else:
            target_types = preferred_types
        
        # Try each content type in order of preference
        for target_type in target_types:
            content_source = self._map_content_type_to_source(target_type)
            if content_source in self.content_pools:
                content = self._select_content_from_pool(
                    content_source, platform, max_length, freshness_hours
                )
                if content:
                    return {**content, "content_type": target_type}
        
        # Fallback to any available fresh content
        for source, pool in self.content_pools.items():
            content = self._select_content_from_pool(
                source, platform, max_length, freshness_hours
            )
            if content:
                content_type = self._map_source_to_content_type(source)
                return {**content, "content_type": content_type}
        
        self.logger.warning(f"No fresh content available for {platform}")
        return None

    def _map_content_type_to_source(self, content_type: ContentType) -> Optional[ContentSource]:
        """Map content type to content source."""
        mapping = {
            ContentType.JOKE: ContentSource.CSV_JOKES,
            ContentType.ADVERTISEMENT: ContentSource.ADVERTISEMENTS,
            ContentType.COMIC: ContentSource.COMICS,
            ContentType.INTERACTION: ContentSource.CSV_REPLIES
        }
        return mapping.get(content_type)

    def _map_source_to_content_type(self, source: ContentSource) -> ContentType:
        """Map content source to content type."""
        mapping = {
            ContentSource.CSV_JOKES: ContentType.JOKE,
            ContentSource.ADVERTISEMENTS: ContentType.ADVERTISEMENT,
            ContentSource.COMICS: ContentType.COMIC,
            ContentSource.CSV_REPLIES: ContentType.INTERACTION
        }
        return mapping.get(source, ContentType.CUSTOM)

    def _select_content_from_pool(self, source: ContentSource, platform: str, 
                                 max_length: int, freshness_hours: int) -> Optional[Dict[str, Any]]:
        """Select content from a specific pool."""
        if source not in self.content_pools:
            return None
        
        pool = self.content_pools[source]
        freshness_cutoff = datetime.now() - timedelta(hours=freshness_hours)
        
        # Filter available content
        available_content = []
        
        for item in pool.items:
            content_text = self._extract_content_text(item)
            
            # Check length constraints
            if len(content_text) > max_length:
                continue
            
            # Check if recently used
            content_hash = hashlib.md5(content_text.encode('utf-8')).hexdigest()
            if content_hash in pool.used_recently:
                continue
            
            # Check freshness for this platform
            if content_hash in self.content_freshness:
                if platform in self.content_freshness[content_hash]:
                    last_used = self.content_freshness[content_hash][platform]
                    if last_used > freshness_cutoff:
                        continue
            
            available_content.append((item, content_hash, content_text))
        
        if not available_content:
            return None
        
        # Select content based on weighted randomization
        selected_item, content_hash, content_text = self._weighted_content_selection(available_content)
        
        # Mark as recently used
        pool.used_recently.append(content_hash)
        self.content_freshness[content_hash][platform] = datetime.now()
        self._save_freshness_data()
        
        # Record metrics
        record_metric("content_selected", 1, "rotator", {
            "source": source.value,
            "platform": platform
        })
        
        return {
            "content": content_text,
            "source": source.value,
            "metadata": selected_item
        }

    def _extract_content_text(self, item: Dict[str, Any]) -> str:
        """Extract content text from an item."""
        # Try common content field names
        for field in ['content', 'text', 'joke', 'message', 'description']:
            if field in item:
                return str(item[field])
        
        # Fallback to first string value
        for value in item.values():
            if isinstance(value, str) and len(value.strip()) > 10:
                return value.strip()
        
        return str(item)

    def _weighted_content_selection(self, available_content: List[Tuple]) -> Tuple:
        """Select content using weighted randomization."""
        if len(available_content) == 1:
            return available_content[0]
        
        # Calculate weights based on various factors
        weighted_items = []
        
        for item, content_hash, content_text in available_content:
            weight = 1.0
            
            # Boost weight for higher priority items
            if isinstance(item, dict) and 'priority' in item:
                weight *= item['priority']
            
            # Boost weight for less recently used content
            total_usage = sum(1 for platforms in self.content_freshness.values() 
                            if content_hash in self.content_freshness and platforms)
            weight *= max(0.1, 1.0 / max(1, total_usage))
            
            # Boost weight for optimal content length
            optimal_length = 150  # Sweet spot for most platforms
            length_factor = 1.0 - abs(len(content_text) - optimal_length) / 200
            weight *= max(0.5, length_factor)
            
            weighted_items.append((weight, item, content_hash, content_text))
        
        # Select using weighted random choice
        total_weight = sum(weight for weight, _, _, _ in weighted_items)
        
        if total_weight <= 0:
            return random.choice(available_content)
        
        random_value = random.uniform(0, total_weight)
        current_weight = 0
        
        for weight, item, content_hash, content_text in weighted_items:
            current_weight += weight
            if random_value <= current_weight:
                return (item, content_hash, content_text)
        
        # Fallback
        return available_content[-1]

    def schedule_automated_content(self, platform: str, num_posts: int = 1,
                                 start_time: Optional[datetime] = None,
                                 spacing_hours: int = 4) -> List[str]:
        """Schedule multiple automated content posts for a platform."""
        
        if not start_time:
            start_time = datetime.now() + timedelta(minutes=30)
        
        scheduled_content_ids = []
        
        for i in range(num_posts):
            # Get fresh content
            content_data = self.get_fresh_content(platform)
            if not content_data:
                self.logger.warning(f"No content available for post {i+1} on {platform}")
                continue
            
            # Calculate post time
            post_time = start_time + timedelta(hours=i * spacing_hours)
            
            # Schedule with coordinator
            content_id = self.coordinator.add_content(
                content=content_data["content"],
                content_type=content_data["content_type"],
                platforms=[platform],
                scheduled_times={platform: post_time},
                metadata={
                    "source": content_data["source"],
                    "automated": True,
                    "rotation_batch": datetime.now().isoformat()
                }
            )
            
            if content_id:
                scheduled_content_ids.append(content_id)
        
        self.logger.info(f"Scheduled {len(scheduled_content_ids)} automated posts for {platform}")
        
        return scheduled_content_ids

    def refresh_content_pools(self):
        """Refresh content pools from source files."""
        refreshed_count = 0
        
        for source, pool in self.content_pools.items():
            try:
                if source == ContentSource.CSV_JOKES:
                    jokes_file = self.config_manager.get_nested_value("paths.jokes_csv")
                    if jokes_file and Path(jokes_file).exists():
                        new_data = self.csv_handler.load_csv(jokes_file)
                        if len(new_data) != len(pool.items):
                            pool.items = new_data
                            pool.last_refreshed = datetime.now()
                            refreshed_count += 1
                            self.logger.info(f"Refreshed jokes pool: {len(new_data)} items")
                
                elif source == ContentSource.CSV_REPLIES:
                    replies_file = self.config_manager.get_nested_value("paths.replies_csv")
                    if replies_file and Path(replies_file).exists():
                        new_data = self.csv_handler.load_csv(replies_file)
                        if len(new_data) != len(pool.items):
                            pool.items = new_data
                            pool.last_refreshed = datetime.now()
                            refreshed_count += 1
                            self.logger.info(f"Refreshed replies pool: {len(new_data)} items")
                
                elif source == ContentSource.ADVERTISEMENTS:
                    new_ads = self._load_advertisements()
                    if new_ads != pool.items:
                        pool.items = new_ads
                        pool.last_refreshed = datetime.now()
                        refreshed_count += 1
                        self.logger.info(f"Refreshed advertisements pool: {len(new_ads)} items")
                
                elif source == ContentSource.COMICS:
                    new_comics = self._load_comics()
                    if len(new_comics) != len(pool.items):
                        pool.items = new_comics
                        pool.last_refreshed = datetime.now()
                        refreshed_count += 1
                        self.logger.info(f"Refreshed comics pool: {len(new_comics)} items")
            
            except Exception as e:
                self.logger.error(f"Error refreshing {source.value} pool: {e}")
        
        if refreshed_count > 0:
            record_metric("content_pools_refreshed", refreshed_count, "rotator")
        
        return refreshed_count

    def get_content_statistics(self) -> Dict[str, Any]:
        """Get content rotation statistics."""
        stats = {
            "content_pools": {},
            "platform_usage": defaultdict(int),
            "freshness_tracking": len(self.content_freshness),
            "total_available_content": 0
        }
        
        # Pool statistics
        for source, pool in self.content_pools.items():
            stats["content_pools"][source.value] = {
                "total_items": len(pool.items),
                "recently_used": len(pool.used_recently),
                "last_refreshed": pool.last_refreshed.isoformat() if pool.last_refreshed else None
            }
            stats["total_available_content"] += len(pool.items)
        
        # Platform usage statistics
        for content_hash, platforms in self.content_freshness.items():
            for platform in platforms:
                stats["platform_usage"][platform] += 1
        
        return stats

    def reset_content_freshness(self, platform: Optional[str] = None, 
                              hours_old: int = 168):  # 1 week default
        """Reset content freshness to allow reuse of old content."""
        cutoff_date = datetime.now() - timedelta(hours=hours_old)
        reset_count = 0
        
        if platform:
            # Reset for specific platform
            for content_hash in list(self.content_freshness.keys()):
                if platform in self.content_freshness[content_hash]:
                    if self.content_freshness[content_hash][platform] < cutoff_date:
                        del self.content_freshness[content_hash][platform]
                        reset_count += 1
                        
                        # Clean up empty entries
                        if not self.content_freshness[content_hash]:
                            del self.content_freshness[content_hash]
        else:
            # Reset for all platforms
            for content_hash in list(self.content_freshness.keys()):
                platforms_to_remove = []
                for plat, timestamp in self.content_freshness[content_hash].items():
                    if timestamp < cutoff_date:
                        platforms_to_remove.append(plat)
                        reset_count += 1
                
                for plat in platforms_to_remove:
                    del self.content_freshness[content_hash][plat]
                
                # Clean up empty entries
                if not self.content_freshness[content_hash]:
                    del self.content_freshness[content_hash]
        
        if reset_count > 0:
            self._save_freshness_data()
            self.logger.info(f"Reset freshness for {reset_count} content items")
            record_metric("content_freshness_reset", reset_count, "rotator", 
                         {"platform": platform or "all"})
        
        return reset_count

def get_content_rotator() -> ContentRotator:
    """Get the global content rotator instance."""
    if not hasattr(get_content_rotator, '_instance'):
        get_content_rotator._instance = ContentRotator()
    return get_content_rotator._instance