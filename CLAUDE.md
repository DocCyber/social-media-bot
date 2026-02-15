# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-platform social media automation bot that posts humor content (jokes, images, themed posts) to BlueSky, Twitter/X, and Mastodon. The system uses simple scheduled tasks to orchestrate content posting and interactive engagement.

**Architecture:** Simple, direct-import design using Python's `schedule` library. The codebase previously had a unified platform layer and advanced automation framework (now in `archive/` directory) but currently operates with standalone modules.

## Running the Bot

**Primary launcher (only entry point):**
```bash
python main_launcher.py
```
This starts the main scheduler loop with all scheduled tasks for all platforms.

**Individual module testing:**
```bash
python bsky/bsky.py              # Manual BlueSky post from jokes.csv
python tweet/tweet.py             # Manual Twitter post from jokes.csv
python bsky/modules/ai_reply.py   # Test AI reply module
python bsky/modules/follow.py     # Test follow-back module
python rss_runner.py             # Single RSS polling cycle (if configured)
```

## Current Architecture

### Execution Flow
1. **main_launcher.py** is the ONLY entry point
2. Uses Python's `schedule` library for simple cron-like scheduling
3. Main loop polls every 1 second, executing pending tasks
4. Each scheduled task directly imports and calls legacy module functions
5. No threading (except for Twitter auto-reply which runs in background daemon thread)
6. No unified platform abstraction - each platform uses its own posting logic

### Active Modules

**BlueSky (`bsky/`):**
- `bsky/bsky.py` - Main posting module (posts from jokes.csv or DocAfterDark.csv)
  - `main()` - Post next joke using index.json["bsky"]
  - `post_docafterdark()` - Post DocAfterDark at night
- `bsky/modules/` - Interaction modules:
  - `hello_reply.py` - Reply to greetings/mentions
  - `custom_reply.py` - Custom reply templates
  - `follow.py` - Follow-back logic
  - `reactions.py` - Like posts in timeline
  - `ai_reply.py` - AI-powered replies to mentions (OpenAI/Anthropic)
  - `conservative_unfollower.py` - Unfollow non-reciprocal accounts (slow, conservative)
  - `data_collector.py` - Collect following/follower data (weekly)
  - `earthporn_poster.py` - Repost EarthPorn images
  - `auth.py` - Shared authentication helpers

**Twitter (`tweet/`, `PAYGTwitter/`):**
- `tweet/tweet.py` - Legacy Twitter posting using OAuth1
  - `tweet_item(filename, index_key)` - Post from CSV using index.json
  - `tweet_docafterdark()` - Post DocAfterDark content
- `PAYGTwitter/TwitterAutoReply.py` - Auto-reply bot (friend/foe management, AI replies)
- `PAYGTwitter/praise_bot/` - Praise/validation post generator

**Mastodon:**
- **BROKEN:** `main_launcher.py` references archived `platforms.mastodon_platform` (line 141)
- No active Mastodon posting module currently works

**RSS (optional):**
- `rss_runner.py` - Polls RSS feeds and posts via platform adapters
- `rss/rss_watcher.py` - Feed parsing and teaser generation
- `bluesky/bsky_bot.py`, `twitter/twitter_bot.py`, `masto_adapter/masto_bot.py` - Platform adapters

**Specialty Bots:**
- `bsky_taunt/bsky_taunt.py` - Taunt/roast posting bot
- Referenced but may be archived: `bskyBESTTHING.py`

### Scheduling (main_launcher.py)

All schedules defined in `main()` function using `schedule` library:

**BlueSky:**
- Every 5 minutes: Interactions (hello_reply, custom_reply, follow, reactions)
- Every hour at :00: Interactions
- Every hour at :31: Post joke
- Daily at 00:01: Best thing posting
- Daily at 00:15: Process interactions
- Daily at 19:00: Taunt bot
- Daily at 22:04: DocAfterDark
- Every 65 minutes: EarthPorn poster
- Every 12 minutes: AI reply processor
- Every 120 minutes: Conservative unfollower
- Weekly (Sunday 02:00): Data collection

**Twitter:**
- Even hours (2, 4, 6, 8, 10, 14, 16, 18, 20, 22) - Randomized between :15-:45
  - Skips midnight (0) and noon (12) to conserve API limits
  - Random times regenerated daily at 00:30
  - Per-hour deduplication prevents multiple posts same day
- Daily at 22:03: DocAfterDark
- Every 10-20 minutes (dynamic): Auto-reply bot (background thread)
- Every 6-8 hours (dynamic): Praise bot

**Mastodon:**
- Every hour at :37 (BROKEN - imports archived module)

### Data Files & Persistence

**Content Sources (root CSVs):**
- `jokes.csv` - Main joke content pool
- `DocAfterDark.csv` - Adult humor for nightly posts
- `questions.csv` - Question-format content
- `school.csv` - School/education themed content

**Index Tracking (`index.json`):**
- Tracks current position for each content flow
- Keys: "joke", "bsky", "Mastodon", "docafterdark", etc.
- Auto-wraps when reaching CSV end
- **Location:** Root directory or `data/json/index.json`
- **Format:** `{"joke": 42, "bsky": 15, "Mastodon": 8}`

**BlueSky State (`bsky/data/`):**
- Daily logs: `ai_reply_log_YYYY-MM-DD.txt`, `unfollower_log_YYYY-MM-DD.txt`
- User tracking: `user_scores.csv`, `interactions.csv`, `unreciprocated_following.json`
- Rate limiting: `user_6h_reply_counts.json`, `user_daily_reply_counts.json`
- Caches: `replied_posts.json`, `reposted_posts.json`, `recent_follows.json`
- Whitelists: `unfollow_whitelist.json`
- Reply data: `replies.csv`
- Templates: `greetings.txt`, `hellos_back.txt`, `hellos_front.txt`, `voice.txt`, `banned_words.txt`

**Twitter State (`PAYGTwitter/`):**
- `TwitterAccounts.csv` - Accounts for auto-reply rotation
- `counter.txt` - Current account index
- `TwitterAutoReplyLog.csv` - Reply history
- Friend/foe tracking via tags in CSV

**Configuration:**
- `keys.json` - API credentials (root or `data/json/keys.json` or `bsky/keys.json`)
- `bsky/config.json` - BlueSky-specific config
- **No unified config manager** - each module loads credentials independently

## Configuration & Credentials

**BlueSky Authentication:**
Each BlueSky module loads credentials from JSON files in priority order:
1. `bsky/keys.json`
2. `data/json/keys.json`
3. Root `keys.json`

Expected structure:
```json
{
  "bsky_handle": "yourbot.bsky.social",
  "bsky_app_password": "xxxx-xxxx-xxxx-xxxx",
  "access_jwt": "auto-refreshed-access-token",
  "refresh_jwt": "auto-refreshed-refresh-token"
}
```

BlueSky modules use `bsky/modules/auth.py` helpers:
- `refresh_session()` - Refresh expired JWT tokens
- `bsky_login_session()` - Create new session with handle/password
- Tokens auto-refresh and persist back to `keys.json`

**Twitter Authentication:**
OAuth1 credentials in `keys.json`:
```json
{
  "twitter_api_key": "...",
  "twitter_api_secret": "...",
  "twitter_access_token": "...",
  "twitter_access_token_secret": "...",
  "twitter_bearer_token": "..."
}
```

**LLM API Keys (for AI replies):**
- Environment variable or files: `secrets/GPTAPI.txt`, `D:\secrets\GPTAPI.txt`, or `keys.json`

## Common Code Patterns

**Posting to BlueSky:**
```python
from bsky import bsky
bsky.main()  # Posts next joke from jokes.csv using index.json["bsky"]
```

**Posting to Twitter:**
```python
import tweet
tweet.tweet_item("jokes.csv", "joke")  # Posts using index.json["joke"]
```

**BlueSky Interactions:**
```python
from bsky.modules import hello_reply, custom_reply, follow, reactions
hello_reply.main()
custom_reply.main()
follow.main()
reactions.main()
```

**Index Management (manual):**
```python
import json
with open("index.json", "r") as f:
    index = json.load(f)
current = index.get("bsky", 0)
# ... do something ...
index["bsky"] = current + 1
with open("index.json", "w") as f:
    json.dump(index, f, indent=4)
```

**CSV Reading:**
```python
import csv
with open("jokes.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    content = rows[index]["text"]  # Assuming "text" column
```

## Modifying Schedules

**To change posting times:**
Edit `main_launcher.py` `main()` function. Examples:

```python
# BlueSky joke posting (currently every hour at :31)
schedule.every().hour.at(":31").do(bsky_post)

# Twitter randomized posting (even hours, ±15 min window)
# Modify setup_twitter_schedules() function

# Mastodon posting (currently every hour at :37)
schedule.every().hour.at(":37").do(mastodon_post)
```

**Twitter randomization:**
- `calculate_random_time(base_hour, base_minute, window)` generates random time
- `create_randomized_tweet_wrapper(base_hour)` creates per-hour dedup wrapper
- `setup_twitter_schedules()` regenerates all random times (runs daily at 00:30)

**Dynamic schedules (random intervals):**
```python
schedule_dynamic_task(func, min_minutes, max_minutes, tag_name)
# Example: schedule_dynamic_task(twitter_auto_reply, 10, 20, "twitter_auto_reply")
```

## Twitter Rate Limits

Free tier severely restricted:
- ~50 tweets/month total limit
- Current schedule: 10 posts/day (even hours except 0 and 12) = ~300/month WITHOUT DocAfterDark/praise/auto-reply
- **Recommendation:** Reduce posting frequency or upgrade to paid tier

## Critical Issues to Fix

1. **Mastodon posting broken:** `main_launcher.py` line 141-149 imports archived `platforms.mastodon_platform`
   - **Fix:** Either restore Mastodon module or remove from schedule

2. **Missing unified config:** No centralized credential management
   - Each module independently searches for keys.json
   - Risk of inconsistent credential sources

3. **No error recovery:** Failed posts don't advance index, causing retry loops

4. **Hardcoded paths:** Windows-specific paths like `d:\jokes\` in `bsky/bsky.py`

## Archived Components

The `archive/` directory contains a previously developed unified platform architecture:
- **platforms/** - BasePlatform abstraction with Twitter/BlueSky/Mastodon implementations
- **automation/** - Advanced scheduler with cron syntax, content rotation, cross-platform coordination
- **utils/** - Shared services (config_manager, csv_handler, index_manager, monitoring, health_checks)
- **Dashboards:** automation_dashboard.py, monitoring_dashboard.py

These were removed from active use but may contain useful patterns for future development.

## Development Notes

- Python 3.10+ required
- Windows development environment (MSYS_NT) with some hardcoded Windows paths
- `schedule` library for timing (simple cron-like syntax)
- Single-threaded by default (except Twitter auto-reply daemon thread)
- No automated testing currently active (test files archived)

### Key Dependencies
- `schedule` - Simple task scheduling
- `requests` - HTTP client for API calls
- `requests-oauthlib` - OAuth1 for Twitter
- `tweepy` - Twitter API wrapper (used in PAYGTwitter modules)
- `feedparser` - RSS feed parsing (optional)
- `openai` or `anthropic` - AI reply generation (optional)

## Security

- Never commit `keys.json`, `config.json` with real credentials
- BlueSky JWTs auto-refresh and persist to `keys.json` - ensure file is gitignored
- LLM API keys loaded from files in `secrets/` or `D:\secrets\` (outside repo)
- Twitter OAuth tokens in `keys.json`

## Adding New Scheduled Tasks

1. Define task function in `main_launcher.py`
2. Add schedule entry in `main()` using `schedule` library syntax:
   ```python
   schedule.every().hour.at(":15").do(your_task_function)
   schedule.every(30).minutes.do(your_task_function)
   schedule.every().day.at("14:30").do(your_task_function)
   ```
3. Use `.tag("task_name")` for clearable schedules
4. Add error handling within task function

## Troubleshooting

**"Module not found" errors:**
- Check if module is in `archive/` (was moved out of active codebase)
- Verify `sys.path.append()` statements in `main_launcher.py`

**BlueSky 401 Unauthorized:**
- Tokens expired: Delete `access_jwt` and `refresh_jwt` from `keys.json`, will auto-regenerate
- Invalid app password: Generate new one at bsky.app settings

**Twitter API errors:**
- Rate limit exceeded: Reduce posting frequency in `main_launcher.py`
- Free tier limits: Consider upgrading or reducing schedule

**Index not advancing:**
- Check `index.json` exists and is valid JSON
- Verify posting function completed successfully (check console output)

**CSV encoding errors:**
- Check `corrupted_lines.txt` for logged errors
- BlueSky modules try UTF-8, then fallback encodings
- Re-save CSV as UTF-8 without BOM
