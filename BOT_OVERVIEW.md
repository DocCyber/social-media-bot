# Social Media Automation Bot - Overview

**Last Updated:** 2025-02-15
**Status:** Production
**Platforms:** BlueSky, Twitter/X, Mastodon (via RSS)

## Table of Contents
1. [Quick Start](#quick-start)
2. [System Architecture](#system-architecture)
3. [Platforms & Features](#platforms--features)
4. [Content Sources](#content-sources)
5. [Scheduling & Automation](#scheduling--automation)
6. [Configuration](#configuration)
7. [Data & Logs](#data--logs)
8. [Common Tasks](#common-tasks)

---

## Quick Start

### Running the Bot

**Main Entry Point:**
```bash
python main_launcher.py
```

This starts the complete automation system with all scheduled tasks across all platforms.

### Platform-Specific Scripts

```bash
# BlueSky - legacy poster (used by main launcher)
python bsky/bsky.py

# Twitter - legacy poster (used by main launcher)
python tweet/tweet.py

# Twitter - Auto-reply bot with AI
python PAYGTwitter/TwitterAutoReply.py

# RSS - Process and post articles
python rss_runner.py
```

---

## System Architecture

### Directory Structure

```
jokes/
├── main_launcher.py          # Main scheduler (entry point)
├── rss_runner.py             # RSS feed processor
├── keys.json                  # Credentials (BlueSky + Twitter)
├── index.json                 # Content rotation indexes
├── jokes.csv                  # Main joke content
├── DocAfterDark.csv          # NSFW/adult humor
│
├── bsky/                      # BlueSky platform
│   ├── bsky.py               # Legacy poster (ACTIVE)
│   ├── modules/              # Interaction modules
│   │   ├── ai_reply.py       # AI-powered replies
│   │   ├── custom_reply.py   # Pattern-matched replies
│   │   ├── hello_reply.py    # Greeting responses
│   │   ├── reactions.py      # Like posts
│   │   ├── follow.py         # Follow users
│   │   ├── conservative_unfollower.py  # Unfollow logic
│   │   ├── earthporn_poster.py        # Repost scenic content
│   │   └── data_collector.py          # Follower analytics
│   └── data/                 # BlueSky data files
│       ├── voice.txt         # AI personality
│       ├── banned_words.txt  # AI safety filter
│       ├── replies.csv       # Custom reply patterns
│       └── *_log_*.txt       # Daily logs
│
├── tweet/                     # Twitter legacy
│   └── tweet.py              # Legacy poster (ACTIVE)
│
├── PAYGTwitter/              # Twitter auto-reply system
│   ├── TwitterAutoReply.py   # Main reply bot
│   ├── user_data.csv         # User tracking database
│   ├── last_add_check.txt    # Bookmark tracking
│   └── praise_bot/           # Praise generation
│
├── rss/                       # RSS system
│   └── rss_watcher.py        # Feed monitoring
│
├── bluesky/                   # RSS → BlueSky adapter
│   └── bsky_bot.py
│
├── twitter/                   # RSS → Twitter adapter
│   └── twitter_bot.py
│
├── masto_adapter/            # RSS → Mastodon adapter
│   └── masto_bot.py
│
├── bsky_taunt/               # Taunt generator
│   └── bsky_taunt.py
│
└── config/                    # Configuration files
```

### Execution Flow

1. **main_launcher.py** starts and registers all scheduled tasks
2. Main loop polls every 1 second, executing pending tasks
3. Each platform module handles its own:
   - Authentication
   - Content posting
   - Interactions (likes, follows, replies)
   - Error handling
4. Index advancement happens **after** successful posts

---

## Platforms & Features

### BlueSky (@docatcdi.com)

**Posting:**
- Hourly jokes at :31 (offset from Twitter)
- Nightly "DocAfterDark" at 22:04
- EarthPorn reposts every 65 minutes
- RSS article teasers (via adapter)

**Interactions (Every 5 minutes):**
- AI-powered replies (Claude Sonnet 4.5)
- Pattern-matched custom replies
- Greeting responses
- Like posts with reactions
- Follow users who engage
- Unfollow non-reciprocal follows (conservative)

**Features:**
- AI personality from `voice.txt`
- Banned word filtering
- Rate limiting (1 reply/user/6hr, max 1 consecutive)
- Daily interaction logs
- Follower analytics

### Twitter/X (@DocAtCDI)

**Main Bot (PAYGTwitter/TwitterAutoReply.py):**
- Sequential rotation through `user_data.csv`
- Replies with jokes to tracked users
- "Bookmark this" phrase detection for user management
- Category system (friend/foe/jokster/snark/priority)
- Engagement tracking
- Claude AI for personalized responses

**Legacy Posting (tweet/tweet.py):**
- Even hours (2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22)
- Randomized windows (±15 min, changes daily at 00:30)
- Per-hour deduplication via `last_run_date` tracking
- Uses `keys.json` for credentials

**Bookmark Phrase System:**
- "bookmark this" → Add user (neutral)
- "bookmark this in my friend category" → Add as friend
- "bookmark this in my foe category" → Add as foe
- "bookmark this in my jokster category" → Add as jokster
- "bookmark this in my snark category" → Add as snark
- "bookmark this in my priority category" → Add high priority

### Mastodon

**Status:** RSS adapter only (toot/toot.py archived)
- Posts RSS teasers via `masto_adapter/masto_bot.py`
- Uses Mastodon.py library

---

## Content Sources

### Primary CSVs

| File | Purpose | Index Key | Schedule |
|------|---------|-----------|----------|
| `jokes.csv` | Main humor content | `joke` | Hourly (BlueSky :31, Twitter even hours) |
| `DocAfterDark.csv` | Adult/NSFW humor | `docafterdark` | Nightly 22:03-22:04 |
| `bsky/data/replies.csv` | Custom reply patterns | N/A | Reactive |

### Content Rotation

- **Index tracking:** `index.json` maintains position for each content source
- **Wrapping:** Auto-resets to 0 when reaching end of CSV
- **No deduplication:** Content will repeat after full rotation
- **State:** Not persisted between restarts (freshness resets)

### CSV Format

```csv
Joke Text Column
"First joke here"
"Second joke here"
"Third joke here"
```

---

## Scheduling & Automation

### Main Scheduler (main_launcher.py)

Uses Python's `schedule` library (NOT croniter) with simple syntax:

```python
# BlueSky
schedule.every().hour.at(":31").do(bsky_post)
schedule.every(5).minutes.do(bsky_interactions)
schedule.every().day.at("22:04").do(bsky_docafterdark)

# Twitter (randomized)
# Even hours with ±15 min window, regenerated daily at 00:30
calculate_random_time()  # Creates random times for each even hour

# EarthPorn
schedule.every(65).minutes.do(earthporn_post)

# Unfollower
schedule.every(120).minutes.do(bsky_unfollower)

# AI Reply
schedule.every(12).minutes.do(bsky_ai_reply)
```

### Schedule Details

| Task | Frequency | Time | Notes |
|------|-----------|------|-------|
| BlueSky posting | Hourly | :31 | Offset from Twitter |
| BlueSky interactions | Every 5 min | N/A | Likes, follows, replies |
| BlueSky AI replies | Every 12 min | N/A | Claude-powered |
| BlueSky DocAfterDark | Daily | 22:04 | NSFW content |
| BlueSky unfollower | Every 2 hours | N/A | Conservative mode |
| BlueSky EarthPorn | Every 65 min | N/A | Scenic repost |
| Twitter posting | Even hours | Randomized window | 2,4,6,8,10,12,14,16,18,20,22 |
| Twitter DocAfterDark | Daily | 22:03 | NSFW content |

### Twitter Randomization

- **Daily regeneration:** 00:30 creates new random times
- **Window:** ±15 minutes from hour mark (e.g., 14:15-14:45)
- **Deduplication:** Per-hour tracking prevents multiple posts same day
- **Wrapper functions:** Track `last_run_date` per hour

---

## Configuration

### Credential Files

**Location:** All credentials now in `D:\secrets\` directory

| File | Purpose | Required For |
|------|---------|--------------|
| `D:\secrets\CLAUDEAPI.txt` | Claude API key | AI replies (BlueSky, Twitter) |
| `D:\secrets\GPTAPI.txt` | OpenAI API key | RSS teasers |
| `D:\secrets\TwitterPayAsYouGo.txt` | Twitter credentials (5 lines) | Twitter auto-reply bot |
| `keys.json` (root) | BlueSky + Twitter legacy | Main launcher |

**keys.json format:**
```json
{
  "bsky": {
    "handle": "docatcdi.com",
    "app_password": "xxxx-xxxx-xxxx-xxxx",
    "accessJwt": "auto-refreshed",
    "refreshJwt": "auto-refreshed"
  },
  "twitter": {
    "consumer_key": "...",
    "consumer_secret": "...",
    "access_token": "...",
    "access_token_secret": "...",
    "bearer_token": "..."
  }
}
```

### BlueSky Token Management

- **Auto-refresh:** JWT tokens refresh automatically
- **Persistence:** Refreshed tokens write back to `keys.json`
- **Rotation:** New `accessJwt` and `refreshJwt` saved on each refresh

### Rate Limits

**Platform Limits (enforced by code):**

| Platform | Daily Limit | Hourly Limit | Notes |
|----------|-------------|--------------|-------|
| Twitter | ~11 posts | 15 posts | Free tier heavily restricted |
| BlueSky | 150 posts | 20 posts | Includes replies |
| Mastodon | 200 posts | 25 posts | RSS only |

**BlueSky AI Reply Limits:**
- 1 reply per user per 6-hour window
- Max 1 consecutive reply to same user
- Tracked in `user_6h_reply_counts.json` and `consecutive_replies.json`

---

## Data & Logs

### Persistent State

| File | Purpose | Location |
|------|---------|----------|
| `index.json` | Content rotation indexes | Root |
| `keys.json` | Platform credentials | Root |
| `PAYGTwitter/user_data.csv` | Twitter user database | PAYGTwitter/ |
| `PAYGTwitter/last_add_check.txt` | Bookmark tracking timestamp | PAYGTwitter/ |
| `bsky/modules/*.json` | BlueSky state (follows, replies, etc.) | bsky/modules/ |

### Logs

**BlueSky Daily Logs:**
- `bsky/data/ai_reply_log_YYYY-MM-DD.txt` - AI conversation logs
- `bsky/data/unfollower_log_YYYY-MM-DD.txt` - Unfollow activity

**Twitter Logs:**
- `PAYGTwitter/engagement_log.txt` - User engagement tracking

**System Logs:**
- Console output (main_launcher.py)
- `corrupted_lines.txt` - CSV encoding failures

### Index.json Structure

```json
{
  "joke": 42,
  "bsky": 15,
  "Mastodon": 8,
  "docafterdark": 3
}
```

---

## Common Tasks

### Adding New Jokes

1. Open `jokes.csv` or `DocAfterDark.csv`
2. Add new rows with jokes in first column
3. Save file (UTF-8 encoding)
4. Bot will automatically include in rotation

### Adding Users to Twitter Rotation

**Via Reply:**
Reply to their tweet with "bookmark this in my friend category" (or other category)

**Via CSV:**
1. Open `PAYGTwitter/user_data.csv`
2. Add row: `username,display_name,friend_foe,priority,engagement_score,...`
3. Save file

### Updating AI Personality

1. Edit `bsky/data/voice.txt`
2. Modify personality instructions
3. Changes take effect on next AI reply

### Viewing Logs

```bash
# Today's AI replies
cat bsky/data/ai_reply_log_$(date +%Y-%m-%d).txt

# Today's unfollows
cat bsky/data/unfollower_log_$(date +%Y-%m-%d).txt

# Twitter engagement
cat PAYGTwitter/engagement_log.txt
```

### Manually Posting

```bash
# BlueSky
python bsky/bsky.py

# Twitter
python tweet/tweet.py

# RSS cycle
python rss_runner.py
```

### Resetting RSS State

```bash
python reset_rss_for_testing.py
```

---

## Security Notes

⚠️ **Never commit to Git:**
- `keys.json`
- `D:\secrets\*`
- Any files with API keys or passwords
- `bsky/modules/*.json` (state files with DIDs)
- `PAYGTwitter/user_data.csv` (user data)

✅ **Safe to commit:**
- `jokes.csv`, `DocAfterDark.csv`
- `bsky/data/voice.txt`, `banned_words.txt`, `replies.csv`
- All `.py` scripts
- Documentation (`.md` files)
- `.gitignore` configuration

---

## Architecture Decisions

### Why Simple Scheduling?

- **schedule library** over croniter avoids threading complexity
- In-process execution (not threaded) prevents hangs
- 1-second poll loop is lightweight and reliable

### Why Legacy + Modern Code?

- **Gradual migration:** Consolidated modules (platforms/, utils/) built but not active (ARCHIVED)
- **Production stability:** Legacy code (bsky/bsky.py, tweet/tweet.py) proven reliable
- **Risk mitigation:** Dual paths allow testing without breaking production

### Why Per-Hour Twitter Dedup?

- Free tier limits to ~50 tweets/month
- Randomized windows reduce predictability
- Per-hour tracking prevents multiple posts if bot restarts

### Why CSV Over Database?

- Simple, human-editable content management
- No database dependencies
- Easy backup and version control
- Fast reads for small datasets

---

## Troubleshooting

### Bot Not Posting

1. Check credentials in `keys.json` and `D:\secrets\`
2. Verify file paths (absolute vs relative)
3. Check console for authentication errors
4. Ensure CSVs exist and are readable

### BlueSky 401 Errors

- Tokens may have expired
- Delete `accessJwt` and `refreshJwt` from `keys.json`
- Bot will create new session on next run

### Twitter Rate Limits

- Free tier is severely restricted (50 tweets/month)
- Reduce posting frequency
- Upgrade to paid tier for higher limits

### CSV Encoding Errors

- Check `corrupted_lines.txt` for details
- Re-save CSV as UTF-8
- If special characters fail, try Windows-1252

---

## Future Enhancements

- [ ] Complete migration to consolidated platforms/ (currently archived)
- [ ] Database for user tracking (replace CSV)
- [ ] Web dashboard for monitoring
- [ ] Metrics and analytics
- [ ] Multi-account support
- [ ] Content approval queue

---

**For detailed technical information, see [TECHNICAL.md](TECHNICAL.md)**
**For AI assistant instructions, see [CLAUDE.md](CLAUDE.md)**
