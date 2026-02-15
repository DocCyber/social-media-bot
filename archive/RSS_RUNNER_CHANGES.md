# RSS Runner Changes - Summary

## What Changed

The RSS runner system has been updated to prevent mass-posting and implement smart scheduling with timestamp tracking.

## Key Features

### 1. **Scheduled Runs**
- Runs automatically at **:15** and **:45** past each hour
- No more continuous polling - you'll know exactly when to expect posts
- Example: 12:15 PM, 12:45 PM, 1:15 PM, 1:45 PM, etc.

### 2. **One Post Per Run**
- System now posts **ONLY ONE** item per execution
- If there are 10 items in the queue, it will take 5 hours to catch up (30-minute intervals)
- Posts the **oldest** unposted item first to maintain chronological order

### 3. **PubDate Tracking**
- New file created: `rss/last_posted_pubdate.json`
- Stores the publication date of the last successfully posted item
- **Prevents reposting**: Any item with a pubDate older than or equal to the last posted item is automatically skipped
- Even if the system restarts, it won't repost old content

### 4. **Smart Filtering**
The system now:
1. Collects all eligible items from all RSS feeds
2. Filters out items already posted (GUID tracking)
3. Filters out items with pubDates older than the last posted item
4. Sorts remaining items by pubDate (oldest first)
5. Posts ONLY the oldest item
6. Updates the pubDate threshold for next run

## Files Modified

### `rss_runner.py`
- Added `wait_until_next_run_time()` function for scheduled execution
- Runs at :15 and :45 past each hour
- Improved logging and error handling

### `rss/rss_watcher.py`
- Added `parse_pubdate()` function to handle RFC 2822 and ISO date formats
- Added `load_last_pubdate()` and `save_last_pubdate()` functions
- Updated `parse_feed()` to extract pubDate from RSS entries
- Completely rewrote `run_once()` posting logic:
  - Collects all eligible items before posting
  - Filters by pubDate threshold
  - Posts only one item per run
  - Updates pubDate threshold after successful post

## New State Files

### `rss/last_posted_pubdate.json`
```json
{
  "last_posted_pubdate": "2025-11-18T09:57:41+00:00",
  "updated_at": "2025-11-18T12:15:30-05:00"
}
```

This file ensures that:
- The system remembers where it left off
- No duplicate posting of old content
- Graceful handling of system restarts

## How It Works - Example Scenario

**12:15 PM Run:**
- RSS feed has 5 new items:
  - Item A: Nov 18, 9:00 AM
  - Item B: Nov 18, 9:30 AM
  - Item C: Nov 18, 10:00 AM
  - Item D: Nov 18, 10:30 AM
  - Item E: Nov 18, 11:00 AM
- Posts Item A (oldest)
- Saves pubDate: Nov 18, 9:00 AM

**12:45 PM Run:**
- Same 5 items in feed
- Item A is skipped (pubDate <= last posted)
- Posts Item B (next oldest)
- Saves pubDate: Nov 18, 9:30 AM

**1:15 PM Run:**
- Items A & B skipped (too old)
- Posts Item C
- And so on...

## Usage

Simply run:
```bash
python rss_runner.py
```

The script will:
1. Run immediately on first execution
2. Wait until the next :15 or :45 time slot
3. Continue running indefinitely
4. Post one item every 30 minutes (if items are available)

Press `Ctrl+C` to stop.

## Benefits

✅ **No more spam** - One post every 30 minutes maximum
✅ **Predictable timing** - Know when posts will appear
✅ **No reposting** - Smart pubDate tracking prevents duplicates
✅ **Graceful catch-up** - Handles backlogs without flooding
✅ **Restart safe** - Remembers last posted item across restarts
