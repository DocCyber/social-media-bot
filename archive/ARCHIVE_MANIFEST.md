# Archive Manifest
**Created:** 2025-02-15
**Purpose:** Pre-GitHub cleanup - moved legacy, test, and unused files out of production directory

## Files Archived

### Testing Files
- test_automation_comprehensive.py
- test_bluesky_consolidated.py
- test_monitoring_comprehensive.py
- test_platforms.py
- integration_test_simple.py
- test_rss_feed.py
- test_twitter_randomization.py
- bsky/data/testreplies.py

### Legacy/Duplicate Files
- newcore.py (replaced by main_launcher.py)
- main_launcher - Copy.py (backup copy)
- bskyBESTTHING.py (legacy code)
- bsky/process_interactions.py (legacy)

### Documentation Files (Implementation Notes)
- RSS_FIX_SUMMARY.md
- MASTODON_FIX_SUMMARY.md
- RSS_RUNNER_CHANGES.md
- overview.md (replaced by BOT_OVERVIEW.md)

### Temporary/Test Data
- tmp/ directory (all joke text files)
- automation_log.txt (old log format)

### Incomplete Refactor Directories
**Note:** These were part of a consolidation effort but are not used by main_launcher.py

- automation/ (entire directory)
- automation_dashboard.py
- monitoring_dashboard.py
- platforms/ (entire directory - consolidated modules)
- utils/ (entire directory - consolidated utilities)

### Unused BlueSky Modules
- bsky/modules/baddadjokes_reposter.py
- bsky/modules/custom_reposts.py
- bsky/modules/dadjoke_reposter.py
- bsky/modules/logging_utils.py
- bsky/modules/notifications.py
- bsky/modules/pinning.py
- bsky/modules/shout_out.py
- bsky/modules/unfollower.py (replaced by conservative_unfollower.py)
- bsky/modules/csv_utils.py
- bsky/launcher.py (legacy launcher)

### Unused Mastodon
- toot/toot.py (Mastodon posting - not used)

### Duplicate Data Files
- data/csv/ (entire directory - duplicates of root CSVs)
- data/json/ (entire directory - duplicates of root index.json)
- Root level duplicates:
  - liked_posts.csv
  - processed_notifications.json
  - recent_follows.json
  - bsky/reposted_posts.json

### Unused Config Files
- config/blacklist.txt
- config/comments.txt
- config/followed.txt
- config/friends.txt
- config/skipped.txt
- config/unfollowed.txt
- config/whitelist.txt
- config/master_config.json (consolidated config attempt)
- config/docatcdi_uuid_and_cookie.json
- bsky/config.json (keys.json used instead)
- bsky/modules/config.json

### Unused Data Files
- bsky/data/__init__.py
- bsky/data/debits.csv
- bsky/data/interactions.csv
- bsky/data/keywords.csv
- bsky/data/kimmel.txt
- bsky/data/user_scores.csv
- bsky/data/usernames.txt
- bsky/data/voicebrief.txt
- bsky/data/ai_reply_log_old.txt
- bsky/modules/data/unreciprocated_following_2024-12-18.json

## Files Kept in Production

### Active Scripts
- main_launcher.py (main entry point)
- rss_runner.py (RSS feed processor)
- reset_rss_for_testing.py (RSS testing utility)

### Active BlueSky Modules
- bsky/bsky.py (legacy poster, still active)
- bsky/modules/ai_reply.py
- bsky/modules/custom_reply.py
- bsky/modules/hello_reply.py
- bsky/modules/reactions.py
- bsky/modules/follow.py
- bsky/modules/conservative_unfollower.py
- bsky/modules/earthporn_poster.py
- bsky/modules/data_collector.py
- bsky/modules/auth.py

### Active Twitter/X
- tweet/tweet.py (legacy Twitter poster)
- twitter/ (RSS adapter)
- PAYGTwitter/ (entire directory - active Twitter bot)

### RSS System
- rss/rss_watcher.py
- bluesky/bsky_bot.py (RSS adapter)
- masto_adapter/masto_bot.py (RSS adapter)
- utils/article_fetcher.py (still used by RSS)
- utils/llm_teaser.py (still used by RSS)

### Active Data Files
- jokes.csv
- DocAfterDark.csv
- index.json
- keys.json (BlueSky credentials)
- bsky/data/voice.txt (AI personality)
- bsky/data/banned_words.txt (AI safety)
- bsky/data/replies.csv (custom replies)
- bsky/data/greetings.txt, hellos_back.txt, hellos_front.txt
- bsky/data/*_log_*.txt (daily logs - kept)

### Documentation (Keep)
- CLAUDE.md (AI assistant instructions)
- BOT_OVERVIEW.md (updated)
- TECHNICAL.md (updated)
- README.md (if exists)
- PAYGTwitter/*.md (Twitter bot documentation)

## Notes

- All archived files are SAFE TO DELETE if space is needed
- The incomplete refactor directories (automation/, platforms/, utils/) were a consolidation attempt that was never finished
- Daily log files (ai_reply_log_*, unfollower_log_*) are kept in bsky/data/ for historical tracking
- Backup folders in PAYGTwitter are preserved for safety
