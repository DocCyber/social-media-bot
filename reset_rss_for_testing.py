"""Reset RSS state for testing - allows reposting recent articles"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Set the threshold to Nov 1, 2025 so recent articles will be posted again
last_pubdate_file = BASE_DIR / "rss" / "last_posted_pubdate.json"
posted_items_file = BASE_DIR / "rss" / "posted_items.json"

print("Resetting RSS state for testing...")

# Set an old pubdate threshold
with open(last_pubdate_file, "w") as f:
    json.dump({
        "last_posted_pubdate": "2025-11-01T00:00:00+00:00",
        "updated_at": "2025-11-19T18:00:00-05:00"
    }, f, indent=2)
print(f"✓ Reset last_posted_pubdate to Nov 1, 2025")

# Clear posted items
with open(posted_items_file, "w") as f:
    json.dump([], f, indent=2)
print(f"✓ Cleared posted_items.json")

print("\nNow run: python -c \"from rss import rss_watcher; rss_watcher.run_once()\"")
print("Or just restart rss_runner.py and it will post on launch")
