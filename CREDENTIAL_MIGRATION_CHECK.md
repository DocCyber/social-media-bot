# Credential Migration Verification Checklist

**Created:** 2025-02-15
**Purpose:** Track which files reference credential paths to ensure all point to `D:\secrets\`

## ✅ Files Confirmed Using D:\secrets\

### BlueSky Modules
- ✅ `bsky/modules/ai_reply.py` - Uses `D:\secrets\CLAUDEAPI.txt`
- ✅ `bsky/data/testreplies.py` - Uses `D:\secrets\GPTAPI.txt` (archived)

### Twitter/X Modules
- ✅ `PAYGTwitter/TwitterAutoReply.py` - Uses `D:\secrets\TwitterPayAsYouGo.txt` and `D:\secrets\CLAUDEAPI.txt`
- ✅ `PAYGTwitter/TestingNewTwitter.py` - Uses `D:\secrets\TwitterPayAsYouGo.txt`
- ✅ `PAYGTwitter/UserPull.py` - Uses `D:\secrets\TwitterPayAsYouGo.txt`
- ✅ `PAYGTwitter/praise_bot/generate_praise.py` - Uses `D:\secrets\TwitterPayAsYouGo.txt`
- ✅ `PAYGTwitter/praise_bot/generate_praise_Local_Only.py` - Uses `D:\secrets\TwitterPayAsYouGo.txt`
- ✅ `PAYGTwitter/praise_bot/search_tweets.py` - Uses `D:\secrets\TwitterPayAsYouGo.txt`

### Backup Files (Also Confirmed)
- ✅ `PAYGTwitter/bakup folder do not touch claude/TwitterAutoReply.py`
- ✅ `PAYGTwitter/bakup folder do not touch claude/TestingNewTwitter.py`
- ✅ `PAYGTwitter/bakup folder do not touch claude/UserPull.py`
- ✅ `PAYGTwitter/bakup folder do not touch claude/double backup hidden/*` (all files)

### RSS/LLM Modules
- ✅ `utils/llm_teaser.py` - Uses fallback paths including `D:\secrets\GPTAPI.txt`

## ⚠️ Files to Test for Runtime Errors

Run these files/modules and watch for credential-related errors:

### Critical Path - Main Launcher
1. **Test:** `python main_launcher.py`
   - **Watches:** BlueSky posting (bsky.py)
   - **Credential Files:** `keys.json` (BlueSky handle/app_password)
   - **Expected Behavior:** Should authenticate and schedule posts

### BlueSky Modules (via main_launcher schedules)
2. **Test:** BlueSky AI Reply Module
   - **File:** `bsky/modules/ai_reply.py`
   - **Credential:** `D:\secrets\CLAUDEAPI.txt`
   - **Trigger:** Wait for mentions/replies or test manually
   - **Expected Behavior:** Should load Claude API key and respond

3. **Test:** BlueSky Custom Reply Module
   - **File:** `bsky/modules/custom_reply.py`
   - **Credential:** `keys.json` (BlueSky auth)
   - **Expected Behavior:** Should pattern-match and reply

4. **Test:** BlueSky Hello Reply Module
   - **File:** `bsky/modules/hello_reply.py`
   - **Credential:** `keys.json`
   - **Expected Behavior:** Should respond to greetings

5. **Test:** BlueSky Reactions Module
   - **File:** `bsky/modules/reactions.py`
   - **Credential:** `keys.json`
   - **Expected Behavior:** Should like posts

6. **Test:** BlueSky Follow Module
   - **File:** `bsky/modules/follow.py`
   - **Credential:** `keys.json`
   - **Expected Behavior:** Should follow users

7. **Test:** BlueSky Conservative Unfollower
   - **File:** `bsky/modules/conservative_unfollower.py`
   - **Credential:** `keys.json`
   - **Expected Behavior:** Should unfollow non-reciprocal users

8. **Test:** BlueSky EarthPorn Poster
   - **File:** `bsky/modules/earthporn_poster.py`
   - **Credential:** `keys.json`
   - **Expected Behavior:** Should repost earth porn content

9. **Test:** BlueSky Data Collector
   - **File:** `bsky/modules/data_collector.py`
   - **Credential:** `keys.json`
   - **Expected Behavior:** Should collect follower/following data

### Twitter/X Modules
10. **Test:** Legacy Twitter Poster
    - **File:** `tweet/tweet.py`
    - **Credential:** Unknown - CHECK THIS FILE
    - **Trigger:** Main launcher Twitter schedule
    - **Expected Behavior:** Should post jokes

11. **Test:** Twitter Auto Reply Bot
    - **File:** `PAYGTwitter/TwitterAutoReply.py`
    - **Credentials:** `D:\secrets\TwitterPayAsYouGo.txt`, `D:\secrets\CLAUDEAPI.txt`
    - **Trigger:** Run directly: `python PAYGTwitter/TwitterAutoReply.py`
    - **Expected Behavior:** Should search for bookmarks, reply to users

### RSS System
12. **Test:** RSS Runner
    - **File:** `rss_runner.py`
    - **Credential:** May call LLM teaser which needs `D:\secrets\GPTAPI.txt`
    - **Trigger:** `python rss_runner.py`
    - **Expected Behavior:** Should fetch RSS feeds and post

13. **Test:** RSS Watcher
    - **File:** `rss/rss_watcher.py`
    - **Credential:** Calls LLM teaser internally
    - **Expected Behavior:** Should generate teasers

14. **Test:** BlueSky RSS Adapter
    - **File:** `bluesky/bsky_bot.py`
    - **Credential:** `keys.json`
    - **Expected Behavior:** Should post RSS items to BlueSky

15. **Test:** Twitter RSS Adapter
    - **File:** `twitter/twitter_bot.py`
    - **Credential:** CHECK THIS FILE
    - **Expected Behavior:** Should post RSS items to Twitter

16. **Test:** Mastodon RSS Adapter
    - **File:** `masto_adapter/masto_bot.py`
    - **Credential:** CHECK THIS FILE
    - **Expected Behavior:** Should post RSS items to Mastodon

## 🔍 Files That Need Manual Inspection

These files might reference credentials but haven't been fully verified:

### High Priority
- ✅ `tweet/tweet.py` - Uses `../keys.json` for Twitter credentials (relative path)
- ❓ `twitter/twitter_bot.py` - **CHECK WHERE IT LOADS TWITTER CREDENTIALS**
- ❓ `masto_adapter/masto_bot.py` - **CHECK WHERE IT LOADS MASTODON CREDENTIALS**
- ✅ `keys.json` (root) - Contains both BlueSky AND Twitter credentials

### Medium Priority
- ❓ `bsky/bsky.py` - Should use `keys.json` but verify
- ❓ `bluesky/bsky_bot.py` - Should use `keys.json` but verify

## 📝 Testing Protocol

1. **Backup Current State:**
   ```bash
   git add -A
   git commit -m "Pre-cleanup backup"
   ```

2. **Run Main Launcher (Monitor for 10 minutes):**
   ```bash
   python main_launcher.py
   ```
   - Watch for any file-not-found errors
   - Check if BlueSky posts succeed
   - Check if Twitter posts succeed (if scheduled)

3. **Test RSS System:**
   ```bash
   python rss_runner.py
   ```
   - Watch for LLM API key errors
   - Check if RSS adapters authenticate

4. **Test Twitter Bot Directly:**
   ```bash
   cd PAYGTwitter
   python TwitterAutoReply.py
   ```
   - Should load credentials from `D:\secrets\TwitterPayAsYouGo.txt`
   - Should load Claude API from `D:\secrets\CLAUDEAPI.txt`

5. **Check Logs for Errors:**
   - Look in `bsky/data/ai_reply_log_YYYY-MM-DD.txt`
   - Look in console output for "file not found" errors

## 🚨 Error Signatures to Watch For

If you see these errors, a file is looking in the wrong place for credentials:

```
FileNotFoundError: [Errno 2] No such file or directory: 'GPTAPI.txt'
FileNotFoundError: [Errno 2] No such file or directory: 'CLAUDEAPI.txt'
FileNotFoundError: [Errno 2] No such file or directory: './keys.json'
FileNotFoundError: [Errno 2] No such file or directory: 'TwitterPayAsYouGo.txt'
Error loading Twitter credentials
Error loading API key
Authentication failed
```

## ✏️ How to Fix If Found

If a file is loading credentials from wrong location:

1. Open the file
2. Search for credential loading code
3. Update path to `D:\secrets\<credential_file>`
4. Test again

Example fix:
```python
# ❌ Wrong
with open('GPTAPI.txt', 'r') as f:

# ✅ Correct
with open(r'D:\secrets\GPTAPI.txt', 'r') as f:
```

## 📋 Required Credential Files in D:\secrets\

Ensure these files exist:
- ✅ `D:\secrets\GPTAPI.txt` (OpenAI API key for RSS teasers)
- ✅ `D:\secrets\CLAUDEAPI.txt` (Claude API key for AI replies)
- ✅ `D:\secrets\TwitterPayAsYouGo.txt` (Twitter API credentials - 5 lines)

And in jokes root:
- ✅ `keys.json` (BlueSky credentials)
