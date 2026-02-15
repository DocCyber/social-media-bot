"""Quick RSS feed debugger"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

try:
    import feedparser
except:
    print("ERROR: feedparser not installed")
    sys.exit(1)

feed_url = "https://thesixthlense.com/feed.xml"
print(f"Fetching: {feed_url}\n")

feed = feedparser.parse(feed_url)

print(f"Total entries found: {len(feed.entries)}\n")

if feed.entries:
    print("Recent entries (newest first):")
    print("-" * 80)
    for i, entry in enumerate(feed.entries[:10], 1):
        guid = getattr(entry, "id", None) or getattr(entry, "guid", None) or getattr(entry, "link", "NO GUID")
        title = getattr(entry, "title", "NO TITLE")
        pubdate = getattr(entry, "published", None) or getattr(entry, "updated", "NO DATE")
        link = getattr(entry, "link", "NO LINK")

        print(f"\n{i}. {title[:60]}")
        print(f"   PubDate: {pubdate}")
        print(f"   GUID: {guid}")
else:
    print("No entries found!")

# Check what the system thinks it's seen
import json
state_file = BASE_DIR / "rss" / "rss_state.json"
posted_file = BASE_DIR / "rss" / "posted_items.json"

print("\n" + "=" * 80)
print("SYSTEM STATE:")
print("=" * 80)

if state_file.exists():
    with open(state_file) as f:
        state = json.load(f)
    print(f"\nLast seen GUID: {state.get('feeds', {}).get(feed_url, 'NONE')}")
else:
    print("\nNo state file found")

if posted_file.exists():
    with open(posted_file) as f:
        posted = json.load(f)
    print(f"\nPosted items count: {len(posted)}")
    for guid in posted:
        print(f"  - {guid}")
else:
    print("\nNo posted items file found")
