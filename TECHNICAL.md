# Technical Overview and Developer Guide

**Last Updated:** 2025-02-15
**Status:** Production
**Audience:** Engineers modifying schedules, platform integrations, and content flows

## Table of Contents
1. [Principles](#principles)
2. [Entry Points](#entry-points)
3. [Architecture](#architecture)
4. [Directory Guide](#directory-guide)
5. [Critical Change Points](#critical-change-points)
6. [Data Flow](#data-flow)
7. [Testing](#testing)
8. [Common Issues](#common-issues)

---

## Principles

- **Simple Scheduling:** `schedule` library over croniter avoids threading complexity
- **Legacy Production Code:** Proven modules (`bsky/bsky.py`, `tweet/tweet.py`) still active
- **CSV-Driven Content:** Robust reading with encoding fallbacks and index tracking
- **Token Auto-Refresh:** BlueSky JWT refresh writes back to config files
- **Single-Threaded:** In-process execution (not threaded) prevents hangs
- **Per-Platform State:** Each platform manages its own credentials, indexes, and logs
- **Consolidated Modules Archived:** Refactor attempt (platforms/, utils/, automation/) moved to archive/

---

## Entry Points

### Production Scripts

```bash
# Main scheduler (primary entry point)
python main_launcher.py

# Twitter auto-reply bot with AI
python PAYGTwitter/TwitterAutoReply.py

# RSS feed processor
python rss_runner.py

# Manual posting
python bsky/bsky.py          # BlueSky
python tweet/tweet.py         # Twitter
```

### Testing & Utilities

```bash
# All test files moved to archive/
# RSS reset utility
python reset_rss_for_testing.py
```

### Dashboards (Archived)

```bash
# These were part of the consolidated refactor attempt
# Now in archive/
# python automation_dashboard.py
# python monitoring_dashboard.py
```

---

## Architecture

### Current Production Stack

```
main_launcher.py (scheduler)
  │
  ├─> BlueSky Posting
  │   └─> bsky/bsky.py (createRecord, JWT refresh)
  │
  ├─> BlueSky Interactions (every 5 min)
  │   ├─> bsky/modules/ai_reply.py (Claude-powered)
  │   ├─> bsky/modules/custom_reply.py (pattern matching)
  │   ├─> bsky/modules/hello_reply.py (greetings)
  │   ├─> bsky/modules/reactions.py (likes)
  │   ├─> bsky/modules/follow.py (follow back)
  │   ├─> bsky/modules/conservative_unfollower.py (unfollow)
  │   ├─> bsky/modules/earthporn_poster.py (repost scenic)
  │   └─> bsky/modules/data_collector.py (analytics)
  │
  ├─> Twitter Posting
  │   └─> tweet/tweet.py (OAuth1, v2 API)
  │
  └─> RSS System
      ├─> rss/rss_watcher.py (feed polling, LLM teasers)
      ├─> bluesky/bsky_bot.py (BlueSky adapter)
      ├─> twitter/twitter_bot.py (Twitter adapter)
      └─> masto_adapter/masto_bot.py (Mastodon adapter)
```

### Archived Components

The following were part of a consolidation attempt but are NOT used in production:

**Archive Location:** `archive/`

- `platforms/` - Consolidated platform layer (base.py, twitter_platform.py, etc.)
- `utils/` - Consolidated utilities (config_manager.py, csv_handler.py, etc.)
- `automation/` - Advanced scheduler and content coordination
- `monitoring_dashboard.py` - Metrics viewer
- `automation_dashboard.py` - Control panel
- All test files (`test_*.py`)

---

## Directory Guide

### Root Level

```
jokes/
├── main_launcher.py          ⭐ Main scheduler (entry point)
├── rss_runner.py             RSS feed processor
├── reset_rss_for_testing.py  RSS state reset utility
├── keys.json                  🔒 Credentials (BlueSky + Twitter)
├── index.json                 Content rotation indexes
├── jokes.csv                  Main joke content
├── DocAfterDark.csv          NSFW/adult humor
├── corrupted_lines.txt        CSV encoding error log
└── CLAUDE.md                  AI assistant instructions
```

### BlueSky Platform (bsky/)

```
bsky/
├── bsky.py                    ⭐ Legacy poster (ACTIVE in production)
│
├── modules/                   Interaction modules
│   ├── ai_reply.py           ⭐ AI-powered replies (Claude)
│   ├── custom_reply.py       ⭐ Pattern-matched replies
│   ├── hello_reply.py        ⭐ Greeting responses
│   ├── reactions.py          ⭐ Like posts
│   ├── follow.py             ⭐ Follow users
│   ├── conservative_unfollower.py  ⭐ Unfollow logic
│   ├── earthporn_poster.py   ⭐ Repost scenic content
│   ├── data_collector.py     ⭐ Follower analytics
│   ├── auth.py               Authentication helper
│   ├── __init__.py           Module imports
│   │
│   └── State Files (JSON):
│       ├── processed_notifications.json
│       ├── last_replied_users.json
│       ├── ai_cost_tracking.json
│       ├── user_6h_reply_counts.json
│       ├── consecutive_replies.json
│       ├── replied_posts.json
│       ├── liked_posts.csv
│       ├── reposted_posts.json
│       ├── recent_follows.json
│       └── unreciprocated_following.json
│
└── data/                      BlueSky data files
    ├── voice.txt             ⭐ AI personality instructions
    ├── banned_words.txt      ⭐ AI safety filter
    ├── replies.csv           ⭐ Custom reply patterns
    ├── greetings.txt         Greeting templates
    ├── hellos_front.txt      Hello prefix templates
    ├── hellos_back.txt       Hello suffix templates
    │
    └── Daily Logs:
        ├── ai_reply_log_YYYY-MM-DD.txt
        ├── unfollower_log_YYYY-MM-DD.txt
        └── data_collection.log
```

### Twitter Platform

```
tweet/
└── tweet.py                   ⭐ Legacy poster (ACTIVE)

PAYGTwitter/
├── TwitterAutoReply.py        ⭐ Main auto-reply bot
├── user_data.csv              User tracking database
├── last_add_check.txt         Bookmark tracking timestamp
├── engagement_log.txt         User engagement history
│
├── TestingNewTwitter.py       Testing utility
├── UserPull.py                User data fetcher
├── run_10_cycles.py           Multi-cycle tester
├── migrate_add_friend_foe.py  Migration helper
├── manage_friend_foe.py       Category manager
├── test_add_tag_feature.py    Tag testing
├── sort_csv_by_engagement.py  CSV sorter
│
├── praise_bot/                Praise generation system
│   ├── generate_praise.py
│   ├── generate_praise_Local_Only.py
│   ├── search_tweets.py
│   └── praise_templates.py
│
├── bakup folder do not touch claude/  Backup versions
│
└── Documentation:
    ├── CATEGORY_GUIDE.md
    ├── CSV_ROTATION_GUIDE.md
    ├── FINAL_TAG_FORMAT.md
    ├── API_TIER_FIX.md
    ├── TAG_VARIANTS.md
    └── (other implementation docs)
```

### RSS System

```
rss/
└── rss_watcher.py             Feed polling and teaser generation

bluesky/
└── bsky_bot.py                RSS → BlueSky adapter

twitter/
└── twitter_bot.py             RSS → Twitter adapter

masto_adapter/
└── masto_bot.py               RSS → Mastodon adapter
```

### Specialty Bots

```
bsky_taunt/
├── bsky_taunt.py              Taunt generator
└── corrupted_lines.txt        CSV errors for taunts
```

### Configuration

```
config/
└── (mostly unused - archived)
```

### Archive

```
archive/
├── ARCHIVE_MANIFEST.md        Archive documentation
├── automation/                Consolidated scheduler (unused)
├── platforms/                 Consolidated platform layer (unused)
├── utils/                     Consolidated utilities (unused)
├── monitoring_dashboard.py    Metrics viewer (unused)
├── automation_dashboard.py    Control panel (unused)
├── test_*.py                  All test files
├── bsky_unused_modules/       Archived BlueSky modules
├── config_unused/             Archived config files
├── data/                      Duplicate data files
├── toot/                      Mastodon legacy
└── (other legacy/unused files)
```

---

## Critical Change Points

### 1. Modify Posting Schedules

**File:** `main_launcher.py`

**BlueSky Posting:**
```python
# Hourly jokes
schedule.every().hour.at(":31").do(bsky_post)

# Nightly adult humor
schedule.every().day.at("22:04").do(bsky_docafterdark)
```

**Twitter Posting:**
```python
# Even hours with randomized windows
# Daily regeneration at 00:30
schedule.every().day.at("00:30").do(regenerate_twitter_times)

# Per-hour wrappers prevent duplicate posts
def tweet_post_at_2():
    if get_today_date() != last_run_dates.get('2'):
        tweet_post()
        last_run_dates['2'] = get_today_date()
```

**Interactions:**
```python
# BlueSky interactions every 5 minutes
schedule.every(5).minutes.do(run_bsky_interactions)

# AI replies every 12 minutes
schedule.every(12).minutes.do(bsky_ai_reply_task)

# Unfollower every 2 hours
schedule.every(120).minutes.do(bsky_unfollower_task)

# EarthPorn every 65 minutes
schedule.every(65).minutes.do(bsky_earthporn_task)
```

### 2. Add New Content Source

**Steps:**
1. Create CSV file in root directory (e.g., `new_content.csv`)
2. Add index key to `index.json`: `{"new_content": 0}`
3. Modify posting function to use new CSV:
   ```python
   def post_new_content():
       tweet_item("new_content.csv", "new_content")
   ```
4. Schedule in `main_launcher.py`:
   ```python
   schedule.every().hour.at(":45").do(post_new_content)
   ```

### 3. BlueSky Authentication

**Files:**
- `keys.json` - Credentials
- `bsky/bsky.py` - Auth logic

**Token Refresh:**
```python
def refreshSession(session, keys_file, pds_url):
    headers = {"Authorization": "Bearer " + session["refreshJwt"]}
    resp = requests.post(f"{pds_url}/xrpc/com.atproto.server.refreshSession", headers=headers)
    refreshed = resp.json()

    # Save new tokens back to keys.json
    keys["bsky"]["accessJwt"] = refreshed["accessJwt"]
    keys["bsky"]["refreshJwt"] = refreshed["refreshJwt"]
    with open(keys_file, "w") as f:
        json.dump(keys, f, indent=4)
```

### 4. Twitter Authentication

**Files:**
- `keys.json` - Legacy Twitter credentials
- `D:\secrets\TwitterPayAsYouGo.txt` - Auto-reply bot credentials

**Legacy Poster (tweet/tweet.py):**
```python
keys_filepath = os.path.join(tweet_dir, '../keys.json')
with open(keys_filepath, 'r') as f:
    keys = json.load(f)

auth = OAuth1(
    keys['twitter']['consumer_key'],
    keys['twitter']['consumer_secret'],
    keys['twitter']['access_token'],
    keys['twitter']['access_token_secret']
)
```

**Auto-Reply Bot (PAYGTwitter/TwitterAutoReply.py):**
```python
SECRETS_FILE = r'd:\secrets\TwitterPayAsYouGo.txt'
with open(SECRETS_FILE, 'r') as f:
    lines = f.read().strip().split('\n')
    consumer_key = lines[0]
    consumer_secret = lines[1]
    access_token = lines[2]
    access_token_secret = lines[3]
    bearer_token = lines[4]
```

### 5. AI Personality (BlueSky)

**File:** `bsky/data/voice.txt`

Contains personality instructions for Claude API. Changes take effect on next AI reply.

**Example:**
```
You are DocAtCDI, a medical professional with a sharp wit and dry humor.
You're sarcastic but never mean-spirited. You appreciate clever wordplay...
```

**Banned Words:** `bsky/data/banned_words.txt`
- One word/phrase per line
- Case-insensitive matching
- Prevents AI from using filtered content

### 6. Custom Reply Patterns (BlueSky)

**File:** `bsky/data/replies.csv`

**Format:**
```csv
pattern,response1,response2,response3
*hello*,Hi there!,Hello!,Hey!
*good morning*,Good morning!,Morning!,Top of the morning!
```

**Wildcards:**
- `*` - Zero or more characters
- `?` - Exactly one character
- Case-insensitive matching

### 7. Twitter User Management

**Bookmark Phrases (in replies):**
```
"bookmark this" → Add neutral
"bookmark this in my friend category" → Add as friend
"bookmark this in my foe category" → Add as foe
"bookmark this in my jokster category" → Add as jokster
"bookmark this in my snark category" → Add as snark
"bookmark this in my priority category" → Add high priority
```

**Manual CSV Editing:**
File: `PAYGTwitter/user_data.csv`

```csv
username,display_name,friend_foe,priority,engagement_score,total_replies,last_replied,last_reply_date,bio,follower_count,following_count,tweet_count,location,url,verified,verified_type,profile_image_url,created_at
```

### 8. RSS Configuration

**Feeds:** Edit `rss/rss_watcher.py` directly

```python
FEEDS = [
    {'url': 'https://example.com/rss', 'name': 'Example Feed'},
    # Add more feeds here
]
```

**LLM Teaser API Key:**
- Location: `D:\secrets\GPTAPI.txt`
- Fallback: Environment variable or keys.json

---

## Data Flow

### Content Posting Flow

```
1. Scheduler triggers posting function
2. Load index from index.json
3. Read CSV at current index
4. Increment index (or wrap to 0)
5. Save updated index
6. Authenticate with platform
7. Post content
8. Log success/failure
```

### BlueSky AI Reply Flow

```
1. Fetch notifications (last 5 minutes)
2. Filter for mentions/replies
3. Check if already processed (processed_notifications.json)
4. Check rate limits (user_6h_reply_counts.json, consecutive_replies.json)
5. Load voice.txt personality
6. Call Claude API with context
7. Sanitize response (remove haha, em dashes → commas)
8. Check banned words (banned_words.txt)
9. Validate length (≤280 chars)
10. Post reply with proper threading
11. Record state (processed, replied_posts.json)
12. Log to daily file (ai_reply_log_YYYY-MM-DD.txt)
```

### Twitter Auto-Reply Flow

```
1. Load user_data.csv rotation
2. Get user info from Twitter API
3. Select joke based on user category (friend/foe/etc.)
4. Check recent tweet for reply opportunity
5. Generate personalized response (Claude AI)
6. Post reply
7. Track engagement (engagement_log.txt)
8. Advance to next user
```

### Index Advancement

```python
def load_indices():
    with open('index.json', 'r') as f:
        return json.load(f)

def save_indices(indices):
    with open('index.json', 'w') as f:
        json.dump(indices, f)

def tweet_item(filename, index_key):
    indices = load_indices()
    current_index = indices[index_key]

    # Read CSV and get item at index
    jokes = read_csv(filename)
    joke = jokes[current_index][0]

    # Post joke
    post_to_platform(joke)

    # Advance index
    indices[index_key] = (current_index + 1) % len(jokes)
    save_indices(indices)
```

---

## Testing

### Production Testing

All automated tests moved to `archive/`. For production testing:

**Manual Testing:**
```bash
# Test BlueSky posting
python bsky/bsky.py

# Test Twitter posting
python tweet/tweet.py

# Test RSS system
python rss_runner.py

# Test Twitter auto-reply (startup check only)
python PAYGTwitter/TwitterAutoReply.py
# Press Ctrl+C after bookmark check completes
```

**Integration Testing:**
```bash
# Run main launcher for 10 minutes
python main_launcher.py
# Monitor console for errors
# Check logs for successful posts
```

**Credential Verification:**
See `CREDENTIAL_MIGRATION_CHECK.md` for testing protocol

---

## Common Issues

### CSV Encoding Errors

**Symptom:** UnicodeDecodeError in console

**Fix:**
1. Check `corrupted_lines.txt` for details
2. Open CSV in text editor
3. Save as UTF-8 encoding
4. If fails, try Windows-1252 or Latin-1

**Fallback Order:**
1. UTF-8
2. Latin-1
3. Windows CP1252
4. ASCII

### BlueSky Token Expiration

**Symptom:** 401 Unauthorized errors

**Fix:**
1. Open `keys.json`
2. Delete `accessJwt` and `refreshJwt` fields
3. Bot will create new session on next run

**Auto-Refresh:**
- Tokens refresh automatically before expiration
- New tokens write back to `keys.json`
- No manual intervention needed normally

### Twitter Rate Limits

**Symptom:** 429 Too Many Requests

**Fix:**
- Free tier: 50 tweets/month (~1.6/day)
- Reduce posting frequency
- Consider paid tier ($100/month for 10K tweets)

### Main Launcher Won't Start

**Check:**
1. `keys.json` exists and has valid structure
2. CSV files (`jokes.csv`, `DocAfterDark.csv`) exist
3. `index.json` exists and has valid JSON
4. Python dependencies installed

**Reset:**
```bash
# Reset indexes
echo '{"joke": 0, "bsky": 0, "docafterdark": 0}' > index.json

# Check credentials
cat keys.json  # Should have bsky and twitter sections
```

### AI Reply Not Working

**Check:**
1. `D:\secrets\CLAUDEAPI.txt` exists
2. API key is valid
3. `bsky/data/voice.txt` exists
4. `bsky/data/banned_words.txt` exists

**Debug:**
```bash
# Check today's AI log
cat bsky/data/ai_reply_log_$(date +%Y-%m-%d).txt

# Check rate limit files
cat bsky/modules/user_6h_reply_counts.json
cat bsky/modules/consecutive_replies.json
```

### RSS Not Posting

**Check:**
1. `D:\secrets\GPTAPI.txt` exists (for LLM teasers)
2. Feed URLs are valid
3. RSS state not corrupted

**Reset RSS:**
```bash
python reset_rss_for_testing.py
```

---

## Performance Notes

### Memory Usage

- **Baseline:** ~50-100MB (Python + schedule library)
- **RSS Fetch:** +20-50MB per feed (HTTP + parsing)
- **AI Reply:** +10-30MB per Claude API call
- **Total Expected:** 100-200MB under normal load

### CPU Usage

- **Idle:** <1% (schedule polling at 1Hz)
- **Posting:** 5-10% spike during CSV read + HTTP request
- **AI Reply:** 10-20% during Claude API call
- **Sustained:** <5% average

### Disk I/O

- **Read:** CSV files, index.json, keys.json on each post
- **Write:** index.json, daily logs, state JSONs
- **Log Rotation:** Daily logs kept indefinitely (manual cleanup)

---

## Security Considerations

### Credential Management

**Never Commit:**
- `keys.json`
- `D:\secrets\*`
- `bsky/modules/*.json` (contains DIDs)
- `PAYGTwitter/user_data.csv` (user data)

**Safe to Commit:**
- All `.py` scripts
- CSV content files (jokes, DocAfterDark)
- Documentation (`.md`)
- Configuration templates

### API Key Storage

**Current Setup:**
- BlueSky: `keys.json` (root)
- Twitter Legacy: `keys.json` (root)
- Twitter Auto-Reply: `D:\secrets\TwitterPayAsYouGo.txt`
- Claude API: `D:\secrets\CLAUDEAPI.txt`
- OpenAI API: `D:\secrets\GPTAPI.txt`

**Best Practice:**
- Use environment variables for production
- Separate credentials per environment
- Rotate keys regularly

### Rate Limiting

**BlueSky:**
- AI replies: 1/user/6hr, max 1 consecutive
- Tracked in JSON files

**Twitter:**
- Free tier: 50 tweets/month
- Per-hour deduplication prevents spam
- Bookmark processing rate-limited by Twitter API

---

## Future Development

### Planned Improvements

- [ ] Migrate to environment variables for credentials
- [ ] Database for user tracking (replace CSV)
- [ ] Metrics export (Prometheus/Grafana)
- [ ] Docker containerization
- [ ] CI/CD pipeline
- [ ] Automated testing suite restoration
- [ ] Content approval workflow

### Deprecated Features

- ✅ Consolidated platform layer (platforms/) - Archived
- ✅ Advanced scheduler (automation/) - Archived
- ✅ Monitoring dashboard - Archived
- ✅ Automation dashboard - Archived
- ✅ Mastodon direct posting (toot/) - Archived (RSS only now)

---

**For user-facing documentation, see [BOT_OVERVIEW.md](BOT_OVERVIEW.md)**
**For AI assistant instructions, see [CLAUDE.md](CLAUDE.md)**
