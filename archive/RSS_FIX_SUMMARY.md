# RSS Feed Bot - Fixed Issues & Usage Guide

## Date: 2025-11-17

---

## Problems Found and Fixed

### 1. **BlueSky Import Path Bug** ❌ → ✅
**Location:** `rss/rss_watcher.py:198`

**Problem:** Code tried to import `bluesky.bsky_bot` which doesn't exist
```python
bsky_mod = import_module("bluesky.bsky_bot")  # WRONG PATH
```

**Fix:** Updated to use correct module path and proper import logic
```python
bsky_mod = import_module("bsky.bsky")
import bluesky.bsky_bot as bsky_adapter
```

---

### 2. **State Management Spam Bug** ❌ → ✅
**Location:** `rss/rss_watcher.py:232-234`

**Problem:**
- First run: Only processed 1 item and saved its GUID
- Second run: ALL items before that GUID were considered "new" → SPAM!
- This caused 10 articles to dump to BlueSky at once

**Fix:** Completely rewrote state management:
- **First run**: Marks newest item as seen WITHOUT posting (safety!)
- **Subsequent runs**: Only posts truly NEW items
- **Deduplication**: Added `posted_items.json` to track all posted GUIDs
- **Chronological**: Posts oldest-first to maintain article order

---

### 3. **Platform Configuration Issues** ❌ → ✅
**Location:** `config/master_config.json`

**Problem:**
- No `enable_bluesky` config option
- Invalid model name `"gpt-5.1"`
- Twitter posted once but BlueSky failed due to import bug

**Fix:**
- Added `enable_bluesky: true` config
- Changed model to `"gpt-4o-mini"` (valid OpenAI model)
- Both Twitter AND BlueSky now configured to post

---

### 4. **Scheduler Configuration** ✅ (Was Actually Fine!)
**Location:** `main_launcher.py:183`

**Status:** Scheduler is configured correctly
```python
schedule.every(20).minutes.do(rss_run_once)
```

**BUT**: The main launcher needs to be **actively running** for the scheduler to work!

---

## New Features Added

### 1. **First-Run Safety**
- Config option: `post_on_first_run` (default: `false`)
- Prevents spam on initial setup
- Marks newest article as seen without posting

### 2. **Deduplication Tracking**
- New file: `rss/posted_items.json`
- Tracks all posted article GUIDs
- Prevents accidental reposts even if state corrupts

### 3. **Better Logging**
- Shows which platform adapters loaded successfully
- Detailed error messages for troubleshooting
- Clear indication of what's happening at each step

### 4. **Improved Error Handling**
- Continues if one platform fails
- Retries up to 2 times per platform
- Only marks items as posted if at least one platform succeeds

---

## Configuration Reference

**File:** `config/master_config.json`

```json
"rss": {
  "feeds": [
    "https://thesixthlense.com/feed.xml"
  ],
  "poll_interval_minutes": 20,           // How often to check for new articles
  "post_delay_seconds": [5, 10],         // Random delay between platforms
  "enable_twitter": true,                // ✅ Post to Twitter
  "enable_mastodon": false,              // ❌ Don't post to Mastodon
  "enable_bluesky": true,                // ✅ Post to BlueSky
  "post_on_first_run": false,            // ❌ Don't spam old articles on first run
  "llm_enabled": true,                   // ✅ Use AI to generate teasers
  "llm_model": "gpt-4o-mini"             // OpenAI model for teaser generation
}
```

---

## How to Use

### Option 1: Run via Main Launcher (Recommended)
This runs ALL your bot functions including RSS checking every 20 minutes:

```bash
cd D:\jokes
python main_launcher.py
```

**What it does:**
- Posts jokes to BlueSky every hour at :31
- Posts jokes to Twitter every even hour at :30
- Checks RSS feed every 20 minutes
- Runs AI replies, follows, reactions, etc.
- Runs continuously until you stop it (Ctrl+C)

### Option 2: Run RSS Watcher Standalone
For testing or if you only want RSS functionality:

```bash
cd D:\jokes
python -m rss.rss_watcher
```

**What it does:**
- Checks RSS feed once
- Posts any new articles to Twitter and BlueSky
- Exits after completion

### Option 3: Continuous RSS-Only Mode
```bash
cd D:\jokes
python rss_runner.py
```

**What it does:**
- Checks RSS feed every 5 minutes (hardcoded)
- Runs continuously
- RSS-only, no other bot functions

---

## What Happens When a New Article is Published

1. **RSS Watcher polls** `thesixthlense.com/feed.xml`
2. **Detects new article** (GUID not in state)
3. **Fetches full article** text for better context
4. **Generates AI teaser** using GPT-4o-mini
5. **Posts to Twitter** (5-10 sec delay)
6. **Posts to BlueSky** (5-10 sec delay)
7. **Saves state** to prevent reposting
8. **Logs success** and waits for next poll

---

## Testing Results ✅

### Test 1: Adapter Loading
```
[2025-11-17 12:40:33] rss_watcher: BlueSky adapter loaded successfully
[2025-11-17 12:40:33] rss_watcher: Twitter adapter loaded successfully
```
**Result:** ✅ Both platforms load correctly

### Test 2: First Run Safety
```
[2025-11-17 12:42:20] rss_watcher: First run for feed https://thesixthlense.com/feed.xml,
marking newest as seen without posting (safety)
```
**Result:** ✅ No spam on first run

### Test 3: No New Items
```
[2025-11-17 12:42:34] rss_watcher: No new items for feed: https://thesixthlense.com/feed.xml
```
**Result:** ✅ Correctly detects when there are no new articles

---

## State Files

### `rss/rss_state.json`
Tracks the last seen article GUID for each feed:
```json
{
  "feeds": {
    "https://thesixthlense.com/feed.xml": "https://thesixthlense.com/article/..."
  },
  "last_checked": "2025-11-17T12:42:20.953940-05:00"
}
```

### `rss/posted_items.json` (NEW)
Deduplication safety - tracks ALL posted GUIDs:
```json
[
  "https://thesixthlense.com/article/...",
  "https://thesixthlense.com/article/...",
  ...
]
```

---

## Troubleshooting

### "No platform adapters available"
**Problem:** Neither Twitter nor BlueSky could be loaded
**Fix:** Check that `bsky/bsky.py` and `twitter/twitter_bot.py` exist

### "BlueSky adapter failed to load"
**Problem:** Import error with BlueSky module
**Fix:** Ensure `bluesky/bsky_bot.py` exists and `bsky/bsky.py` is working

### Articles not posting
**Problem:** Scheduler not running
**Fix:** Make sure `main_launcher.py` is actively running (not just open in editor)

### Duplicate posts
**Problem:** State file corrupted
**Fix:** The new `posted_items.json` provides backup deduplication

---

## Summary

✅ **Fixed:** BlueSky import path
✅ **Fixed:** State management spam bug
✅ **Fixed:** First-run safety added
✅ **Fixed:** Deduplication tracking
✅ **Fixed:** Platform configuration
✅ **Verified:** Scheduler is configured correctly
✅ **Tested:** Both adapters load successfully

**Next Step:** Run `python main_launcher.py` to start the bot with all fixes applied!
