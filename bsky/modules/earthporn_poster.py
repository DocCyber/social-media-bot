#!/usr/bin/env python3
"""
EarthPorn Reddit to BlueSky Image Poster
Fetches hot posts from r/EarthPorn and posts them to BlueSky with native image upload.
No Reddit API key required - uses public JSON endpoints.
"""

import os
import sys
import json
import re
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from PIL import Image
import io

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import functions from existing bsky module
bsky_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if bsky_path not in sys.path:
    sys.path.append(bsky_path)

try:
    # Try different import patterns to work in various contexts
    try:
        from bsky import bsky
        BSKY_MODULE_AVAILABLE = True
    except ImportError:
        # If that fails, try importing the bsky directory as a module
        import importlib.util
        bsky_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bsky.py')
        spec = importlib.util.spec_from_file_location("bsky", bsky_file)
        bsky = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bsky)
        BSKY_MODULE_AVAILABLE = True
except Exception as e:
    print(f"Warning: bsky module not available: {e}")
    BSKY_MODULE_AVAILABLE = False

try:
    from atproto import Client, models
    ATPROTO_AVAILABLE = True
except ImportError:
    print("Warning: atproto not available. Install with: pip install atproto")
    ATPROTO_AVAILABLE = False

class EarthPornPoster:
    def __init__(self):
        """Initialize the EarthPorn poster with configuration."""
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.keys_file = os.path.join(self.base_dir, 'keys.json')
        self.tracking_file = os.path.join(self.data_dir, 'earthporn_posted.json')

        # Reddit configuration
        self.reddit_url = "https://www.reddit.com/r/earthporn/hot.json"
        self.user_agent = "EarthPornBot/1.0 (compatible; Python/requests)"

        # Posting configuration
        self.max_posts_per_day = 50  # Maximum posts per day (high limit, controlled by schedule)
        self.min_score = 100  # Minimum Reddit score to consider posting

        # BlueSky client
        self.client = None

    def load_keys(self) -> Dict:
        """Load API keys from keys.json."""
        if os.path.exists(self.keys_file):
            try:
                with open(self.keys_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading keys: {e}")
        return {}

    def load_tracking_data(self) -> Dict:
        """Load tracking data for posted content."""
        if os.path.exists(self.tracking_file):
            try:
                with open(self.tracking_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading tracking data: {e}")

        # Return default structure
        return {
            "posted_ids": [],
            "last_check": None,
            "stats": {
                "total_posted": 0,
                "last_posted": None
            }
        }

    def save_tracking_data(self, data: Dict):
        """Save tracking data to file."""
        try:
            with open(self.tracking_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving tracking data: {e}")

    def fetch_earthporn_posts(self) -> List[Dict]:
        """Fetch hot posts from r/EarthPorn using public JSON API."""
        try:
            headers = {'User-Agent': self.user_agent}
            response = requests.get(f"{self.reddit_url}?limit=10", headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            posts = []

            for post_data in data['data']['children']:
                post = post_data['data']

                # Skip if not an image post
                if not self._is_image_post(post):
                    continue

                # Extract relevant information
                post_info = {
                    'id': post['id'],
                    'title': post['title'],
                    'url': post['url'],
                    'author': post['author'],
                    'score': post['score'],
                    'created_utc': post['created_utc'],
                    'permalink': f"https://reddit.com{post['permalink']}",
                    'subreddit': post['subreddit']
                }

                # Extract location and resolution from title
                location, resolution = self._parse_title(post['title'])
                post_info['location'] = location
                post_info['resolution'] = resolution

                posts.append(post_info)

            print(f"Fetched {len(posts)} image posts from r/EarthPorn")
            return posts

        except Exception as e:
            print(f"Error fetching EarthPorn posts: {e}")
            return []

    def _is_image_post(self, post: Dict) -> bool:
        """Check if a Reddit post contains an image."""
        url = post.get('url', '').lower()

        # Direct image links
        if any(url.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            return True

        # Common image hosting sites
        if any(domain in url for domain in ['i.redd.it', 'i.imgur.com', 'imgur.com']):
            return True

        # Check if it's a Reddit gallery or has preview images
        if 'preview' in post and 'images' in post['preview']:
            return True

        return False

    def _parse_title(self, title: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse location and resolution from Reddit post title."""
        location = None
        resolution = None

        # Common patterns for location
        location_patterns = [
            r'^([^[]+?)(?:\s*\[|$)',  # Everything before first bracket
            r'([^[,]+?),\s*[A-Z]{2}',  # City, State pattern
            r'([^[,]+?),\s*[A-Za-z\s]+(?:\[|$)',  # City, Country pattern
        ]

        for pattern in location_patterns:
            match = re.search(pattern, title)
            if match:
                location = match.group(1).strip()
                break

        # Resolution pattern [1920x1080] etc.
        resolution_match = re.search(r'\[(\d+x\d+)\]', title)
        if resolution_match:
            resolution = resolution_match.group(1)

        return location, resolution

    def _get_image_url(self, post: Dict) -> Optional[str]:
        """Get the actual image URL from a Reddit post."""
        url = post['url']

        # Direct image link
        if any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            return url

        # Reddit hosted image
        if 'i.redd.it' in url:
            return url

        # Imgur handling
        if 'imgur.com' in url:
            # Convert imgur page links to direct image links
            if not url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                # Try to get direct link
                imgur_id = url.split('/')[-1].split('.')[0]
                return f"https://i.imgur.com/{imgur_id}.jpg"

        return url

    def download_image(self, url: str) -> Optional[bytes]:
        """Download image from URL and return bytes, with compression if needed."""
        try:
            headers = {'User-Agent': self.user_agent}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            # Verify it's actually an image and process it
            try:
                img = Image.open(io.BytesIO(response.content))

                # Convert to RGB if necessary (for JPEG)
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')

                # Check file size - BlueSky limit is ~976KB
                max_size = 950 * 1024  # 950KB to be safe

                if len(response.content) <= max_size:
                    # Image is small enough, return as-is
                    return response.content

                print(f"Image too large ({len(response.content)/1024/1024:.1f}MB), compressing...")

                # Compress image
                quality = 85
                while quality > 20:
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=quality, optimize=True)
                    compressed_data = buffer.getvalue()

                    if len(compressed_data) <= max_size:
                        print(f"Compressed to {len(compressed_data)/1024:.0f}KB at quality {quality}")
                        return compressed_data

                    quality -= 10

                # If still too large, resize and try again
                print("Still too large, resizing image...")
                max_dimension = 2048
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85, optimize=True)
                final_data = buffer.getvalue()

                print(f"Final size: {len(final_data)/1024:.0f}KB")
                return final_data

            except Exception as e:
                print(f"Error processing image: {e}")
                return None

        except Exception as e:
            print(f"Error downloading image from {url}: {e}")
            return None

    def format_post_text(self, post: Dict) -> str:
        """Format the post text for BlueSky."""
        text_parts = []

        # Main text with proper hashtag formatting
        text_parts.append("Enjoy #OurEarthPorn!")
        text_parts.append("(Steal This Hashtag for your own & join the community of Nature Addicts!)")
        text_parts.append("")

        # Location and details
        location_parts = []
        if post['location']:
            location_parts.append(post['location'])

        # Add [OC] if in title
        if '[OC]' in post['title'].upper():
            location_parts.append('[OC]')

        # Add resolution if available
        if post['resolution']:
            location_parts.append(f"[{post['resolution']}]")

        if location_parts:
            text_parts.append(' '.join(location_parts))

        # Photo credit
        text_parts.append(f"Photo Credit: {post['author']}")

        return '\n'.join(text_parts)

    def get_bluesky_session(self):
        """Get BlueSky session using existing bsky module functions."""
        if not BSKY_MODULE_AVAILABLE:
            print("BlueSky module not available")
            return None

        try:
            pds_url = "https://bsky.social"
            session = bsky.manage_session(pds_url, self.keys_file)
            return session
        except Exception as e:
            print(f"Error getting BlueSky session: {e}")
            return None

    def upload_image_to_bluesky(self, image_data: bytes, session: dict) -> Optional[dict]:
        """Upload image to BlueSky and return blob reference."""
        try:
            pds_url = "https://bsky.social"

            # Upload blob
            response = requests.post(
                f"{pds_url}/xrpc/com.atproto.repo.uploadBlob",
                headers={
                    "Authorization": f"Bearer {session['accessJwt']}",
                    "Content-Type": "image/jpeg"
                },
                data=image_data
            )

            # Debug image upload
            if response.status_code != 200:
                print(f"Image upload error: {response.status_code} - {response.text}")
                return None

            response.raise_for_status()

            blob_data = response.json()
            print(f"Image uploaded successfully, blob size: {len(image_data)} bytes")
            return blob_data['blob']

        except Exception as e:
            print(f"Error uploading image to BlueSky: {e}")
            return None

    def post_to_bluesky(self, post: Dict, image_data: bytes) -> bool:
        """Post image and text to BlueSky using existing session management."""
        try:
            # Get session using existing bsky module
            session = self.get_bluesky_session()
            if not session:
                print("Could not establish BlueSky session")
                return False

            # Format post text
            text = self.format_post_text(post)

            # Check text length (BlueSky limit is 300 chars)
            if len(text) > 300:
                print(f"Post text too long ({len(text)} chars), truncating...")
                text = text[:297] + "..."

            # Upload image
            blob = self.upload_image_to_bluesky(image_data, session)
            if not blob:
                print("Failed to upload image")
                return False

            # Create hashtag facets for BlueSky
            facets = []
            hashtag_pattern = r'#\w+'

            for match in re.finditer(hashtag_pattern, text):
                start_pos = match.start()
                end_pos = match.end()
                hashtag_text = match.group()[1:]  # Remove the # symbol

                facets.append({
                    "index": {
                        "byteStart": start_pos,
                        "byteEnd": end_pos
                    },
                    "features": [{
                        "$type": "app.bsky.richtext.facet#tag",
                        "tag": hashtag_text
                    }]
                })

            # Create post with image embed and hashtag facets
            pds_url = "https://bsky.social"
            post_data = {
                "$type": "app.bsky.feed.post",
                "text": text,
                "createdAt": datetime.utcnow().isoformat() + 'Z',
                "embed": {
                    "$type": "app.bsky.embed.images",
                    "images": [{
                        "image": blob,
                        "alt": f"EarthPorn: {post['location'] or 'Beautiful landscape'}"
                    }]
                }
            }

            # Add facets if any hashtags were found
            if facets:
                post_data["facets"] = facets

            response = requests.post(
                f"{pds_url}/xrpc/com.atproto.repo.createRecord",
                headers={"Authorization": f"Bearer {session['accessJwt']}"},
                json={
                    "repo": session["did"],
                    "collection": "app.bsky.feed.post",
                    "record": post_data,
                },
            )

            # Debug: Print response details on error
            if response.status_code != 200:
                print(f"BlueSky API Error Details:")
                print(f"Status Code: {response.status_code}")
                print(f"Response: {response.text}")
                print(f"Post data: {post_data}")

            response.raise_for_status()

            safe_title = post['title'][:50].encode('ascii', 'ignore').decode('ascii')
            print(f"Successfully posted to BlueSky: {safe_title}...")
            return True

        except Exception as e:
            print(f"Error posting to BlueSky: {e}")
            return False

    def should_post_content(self, post: Dict, tracking_data: Dict) -> bool:
        """Determine if we should post this content."""
        # Check if already posted
        if post['id'] in tracking_data['posted_ids']:
            return False

        # Check minimum score
        if post['score'] < self.min_score:
            return False

        # Check daily limit (simplified check)
        if len(tracking_data['posted_ids']) >= self.max_posts_per_day:
            return False

        # No time delay check - controlled by scheduler frequency only
        return True

    def main(self):
        """Main execution function."""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting EarthPorn poster...")

        # Load tracking data
        tracking_data = self.load_tracking_data()

        # Fetch new posts
        posts = self.fetch_earthporn_posts()
        if not posts:
            print("No posts fetched, exiting")
            return

        # Sort by score (highest first) to get the hottest content
        posts.sort(key=lambda x: x['score'], reverse=True)

        posted_count = 0
        for post in posts:
            if not self.should_post_content(post, tracking_data):
                continue

            # Handle potential Unicode characters in title
            safe_title = post['title'][:50].encode('ascii', 'ignore').decode('ascii')
            print(f"Processing post: {safe_title}... (Score: {post['score']})")

            # Get image URL
            image_url = self._get_image_url(post)
            if not image_url:
                print(f"Could not determine image URL for post: {post['id']}")
                continue

            # Download image
            image_data = self.download_image(image_url)
            if not image_data:
                print(f"Could not download image for post: {post['id']}")
                continue

            # Post to BlueSky
            if self.post_to_bluesky(post, image_data):
                # Update tracking data
                tracking_data['posted_ids'].append(post['id'])
                tracking_data['stats']['total_posted'] += 1
                tracking_data['stats']['last_posted'] = datetime.now().isoformat()
                posted_count += 1

                # Limit posts per run
                if posted_count >= 1:  # Only post 1 image per run
                    break

            # Small delay between attempts
            time.sleep(2)

        # Update tracking data
        tracking_data['last_check'] = datetime.now().isoformat()
        self.save_tracking_data(tracking_data)

        if posted_count > 0:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Posted {posted_count} EarthPorn image(s) to BlueSky")
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] No new EarthPorn content to post")

def main():
    """Main execution function for standalone testing."""
    poster = EarthPornPoster()
    poster.main()

if __name__ == "__main__":
    main()