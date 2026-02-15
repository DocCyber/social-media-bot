#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter Auto-Reply with Claude AI
Automatically generates and posts engagement replies to users from accounts.txt (in sequential order)
Uses voice file for personality and Claude API for generation
"""

import tweepy
import requests
import os
import sys
import csv
import time
from datetime import datetime, timedelta, timezone

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Some IDEs wrap stdout in a way that doesn't support reconfigure
        pass

# ============================================================================
# CONFIGURATION
# ============================================================================

# File paths
SECRETS_FILE = r'd:\secrets\TwitterPayAsYouGo.txt'
ACCOUNTS_FILE = 'accounts.txt'
VOICE_FILE = 'DocsVoice.txt'
CLAUDE_API_FILE = r'D:\secrets\CLAUDEAPI.txt'
ACCOUNT_INDEX_FILE = 'account_index.txt'
REPLIED_TWEETS_FILE = 'replied_tweets.txt'
COUNTER_FILE = 'counter.txt'
USER_DATA_CSV = 'user_data.csv'
LAST_ADD_CHECK_FILE = 'last_add_check.txt'

# Settings
MAX_CHARS = 280
LOOKBACK_HOURS = 12
MAX_TWEETS_TO_FETCH = 5

# Loop settings - keep dedup list same size as run cycles
CYCLES = 222
DELAY_SECONDS = 20
MAX_REPLIED_TWEETS = 500 # CYCLES  # Keep dedup list size = number of cycles

# ============================================================================
# AUTHENTICATION & SETUP
# ============================================================================

def load_twitter_credentials():
    """Load Twitter API credentials from secrets file."""
    config = {}
    with open(SECRETS_FILE, 'r') as f:
        for line in f:
            stripped = line.strip()
            if ':' in stripped:
                key, value = stripped.split(':', 1)
                config[key.strip().lower().replace(' ', '_')] = value.strip()

    consumer_key = config.get('consumer_key') or config.get('api_key')
    consumer_secret = config.get('secret_key') or config.get('api_secret')
    access_token = config.get('access_token')
    access_token_secret = config.get('access_token_secret')
    bearer_token = config.get('bearer_token')

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        raise ValueError("Missing required Twitter credentials")

    return consumer_key, consumer_secret, access_token, access_token_secret, bearer_token

def load_voice_file():
    """Load the voice.txt file containing personality and style instructions."""
    try:
        if os.path.exists(VOICE_FILE):
            with open(VOICE_FILE, 'r', encoding='utf-8') as f:
                voice_content = f.read().strip()
                if voice_content:
                    return voice_content
                else:
                    print(f"Warning: Voice file {VOICE_FILE} is empty")
                    return None
        else:
            print(f"Error: Voice file not found at {VOICE_FILE}")
            return None
    except Exception as e:
        print(f"Error loading voice file: {e}")
        return None

def load_claude_api_key():
    """Load Claude API key from secrets file."""
    try:
        if not os.path.exists(CLAUDE_API_FILE):
            print(f"Error: Claude API key file not found at {CLAUDE_API_FILE}")
            return None

        with open(CLAUDE_API_FILE, 'r', encoding='utf-8') as f:
            api_key = f.read().strip()

        if not api_key:
            print("Error: Claude API key file is empty")
            return None

        return api_key
    except Exception as e:
        print(f"Error loading Claude API key: {e}")
        return None

def load_accounts():
    """
    Load target accounts from user_data.csv.
    Returns usernames in the order they appear in CSV (keep CSV sorted by engagement!).
    CSV should be pre-sorted with high-engagement accounts at the top.
    """
    if not os.path.exists(USER_DATA_CSV):
        raise FileNotFoundError(f"user_data.csv not found in script directory: {os.getcwd()}")

    user_data_dict = load_user_data_csv()

    if not user_data_dict:
        raise ValueError("No users in user_data.csv.")

    # Return usernames in the order they appear in CSV (CSV is already sorted)
    # Note: load_user_data_csv() reads CSV in order, so dict preserves insertion order (Python 3.7+)
    usernames = list(user_data_dict.keys())

    return usernames

def get_next_username(all_usernames, cycle_index=0):
    """
    Get username from sorted list based on cycle index.
    Index resets at start of each script run (no persistent file).
    Within a run, progresses through the list cycle by cycle.

    Args:
        all_usernames: List of usernames from CSV (pre-sorted by engagement)
        cycle_index: Current cycle number (0-based) within this script execution
    """
    if not all_usernames:
        return None

    # Wrap around if we exceed the list
    index = cycle_index % len(all_usernames)
    selected = all_usernames[index]

    print(f"[CSV ROTATION] Cycle {cycle_index + 1}: Selected @{selected} (position {index + 1}/{len(all_usernames)})")

    return selected

# ============================================================================
# PERSISTENT COUNTER (position tracking between runs)
# ============================================================================

def load_counter():
    """Load the current account index from counter.txt. Returns 0 if file doesn't exist."""
    if not os.path.exists(COUNTER_FILE):
        return 0
    try:
        with open(COUNTER_FILE, 'r') as f:
            return int(f.read().strip())
    except (ValueError, IOError):
        return 0

def save_counter(value):
    """Save the current account index to counter.txt."""
    with open(COUNTER_FILE, 'w') as f:
        f.write(str(value))

# ============================================================================
# REPLIED TWEETS TRACKING
# ============================================================================

def load_replied_tweets():
    """Load the list of tweet IDs we've already replied to."""
    replied_tweets = set()

    if not os.path.exists(REPLIED_TWEETS_FILE):
        return replied_tweets

    try:
        with open(REPLIED_TWEETS_FILE, 'r') as f:
            for line in f:
                tweet_id = line.strip()
                if tweet_id:
                    replied_tweets.add(tweet_id)
    except Exception as e:
        print(f"Error loading replied tweets: {e}")

    return replied_tweets

def save_replied_tweets(replied_tweets_set):
    """Save the replied tweets list, capping at MAX_REPLIED_TWEETS."""
    try:
        # Convert set to list and keep only the most recent MAX_REPLIED_TWEETS
        # (In practice, we'll add new ones to the end and trim old ones from the beginning)
        tweets_list = list(replied_tweets_set)[-MAX_REPLIED_TWEETS:]

        with open(REPLIED_TWEETS_FILE, 'w') as f:
            for tweet_id in tweets_list:
                f.write(f"{tweet_id}\n")

        print(f"[DEDUP] Saved {len(tweets_list)} replied tweet IDs (max {MAX_REPLIED_TWEETS})")
    except Exception as e:
        print(f"Error saving replied tweets: {e}")

def add_replied_tweet(tweet_id):
    """Add a tweet ID to the replied tweets list."""
    replied_tweets = load_replied_tweets()
    replied_tweets.add(str(tweet_id))
    save_replied_tweets(replied_tweets)
    print(f"[DEDUP] Added tweet {tweet_id} to replied list")

def has_replied_to_tweet(tweet_id):
    """Check if we've already replied to this tweet."""
    replied_tweets = load_replied_tweets()
    return str(tweet_id) in replied_tweets

# ============================================================================
# BOOKMARK PHRASE PROCESSING - TIMESTAMP TRACKING
# ============================================================================

def load_last_add_check():
    """Load the timestamp of the last bookmark phrase check."""
    if not os.path.exists(LAST_ADD_CHECK_FILE):
        # First run - use 7 days ago (API limit)
        first_run_time = datetime.now(timezone.utc) - timedelta(days=7)
        return first_run_time.isoformat(timespec='seconds')

    try:
        with open(LAST_ADD_CHECK_FILE, 'r') as f:
            timestamp = f.read().strip()
            if timestamp:
                return timestamp
    except Exception as e:
        print(f"[BOOKMARK] Error loading last check time: {e}")

    # Fallback to 7 days ago
    fallback_time = datetime.now(timezone.utc) - timedelta(days=7)
    return fallback_time.isoformat(timespec='seconds')

def save_last_add_check():
    """Save current timestamp as last bookmark phrase check time."""
    current_time = datetime.now(timezone.utc).isoformat(timespec='seconds')

    try:
        with open(LAST_ADD_CHECK_FILE, 'w') as f:
            f.write(current_time)
        print(f"[BOOKMARK] Updated last check time: {current_time}")
    except Exception as e:
        print(f"[BOOKMARK] Error saving last check time: {e}")

def parse_add_tag_variant(tweet_text):
    """
    Parse which bookmark variant was used in the tweet.
    Returns tuple: (variant_name, should_add, friend_foe_status, priority)

    Supported variants:
    - "bookmark this" - Normal add (default)
    - "bookmark this in my friend category" - Add and mark as friend
    - "bookmark this in my foe category" - Add and mark as foe
    - "bookmark this in my jokster category" - Add as jokster (witty banter, playful, avoid politics)
    - "bookmark this in my snark category" - Add as snark (sarcastic, sharp wit)
    - "bookmark this in my priority category" - Add with high priority
    - (Future: remove functionality if needed)
    """
    text_lower = tweet_text.lower()

    # Check for category-specific bookmarks
    if 'bookmark this in my friend category' in text_lower:
        return ('FRIEND', True, 'friend', 1)

    if 'bookmark this in my foe category' in text_lower:
        return ('FOE', True, 'foe', 1)

    if 'bookmark this in my jokster category' in text_lower:
        return ('JOKSTER', True, 'jokster', 1)

    if 'bookmark this in my snark category' in text_lower:
        return ('SNARK', True, 'snark', 1)

    if 'bookmark this in my priority category' in text_lower:
        return ('PRIORITY', True, '', 2)

    # Default: "bookmark this" (without category)
    if 'bookmark this' in text_lower:
        return ('DEFAULT', True, '', 1)

    # Fallback (shouldn't happen if search query is correct)
    return ('DEFAULT', True, '', 1)

def search_add_tag_replies(client, start_time):
    """
    Search for bot's own replies containing "bookmark this" phrases (all variants) since start_time.
    Returns list of (tweet_id, tweet_text, target_username, target_user_obj) tuples.
    """
    try:
        # Get authenticated user handle
        me = client.get_me()
        auth_handle = me.data.username

        print(f"[BOOKMARK] Searching for 'bookmark this' phrases since: {start_time}")

        # Search for replies with "bookmark this" phrase
        # Note: Using 'is:reply' instead of 'filter:replies' for compatibility with pay-as-you-go tier
        query = f'from:{auth_handle} is:reply "bookmark this" -is:retweet'

        response = client.search_recent_tweets(
            query=query,
            tweet_fields=['id', 'text', 'created_at', 'in_reply_to_user_id'],
            expansions=['in_reply_to_user_id'],
            user_fields=['username', 'id', 'name', 'created_at', 'description', 'location',
                        'profile_image_url', 'protected', 'public_metrics', 'url',
                        'verified', 'verified_type'],
            max_results=100,
            start_time=start_time
        )

        if not response.data:
            print("[BOOKMARK] No new 'bookmark this' phrases found")
            return []

        # Build user ID → user object mapping from includes
        includes_users = {}
        if response.includes and 'users' in response.includes:
            for user in response.includes['users']:
                includes_users[user.id] = user

        # Extract target users from replies with tweet text
        found_tags = []
        for tweet in response.data:
            target_user_id = tweet.in_reply_to_user_id
            if target_user_id and target_user_id in includes_users:
                target_user = includes_users[target_user_id]
                found_tags.append((tweet.id, tweet.text, target_user.username, target_user))

        print(f"[BOOKMARK] Found {len(found_tags)} new bookmark phrases")
        return found_tags

    except Exception as e:
        print(f"[BOOKMARK] Error searching for bookmark phrases: {e}")
        return []

def add_user_from_tag(username, user_obj, friend_foe_status=''):
    """
    Add a user from bookmark phrase to user_data.csv, or update their friend/foe status if they exist.
    User object already fetched from search API (via expansions).
    Returns True if user was added or updated, False if no change needed.

    Args:
        username: Twitter username (without @)
        user_obj: User object from Twitter API
        friend_foe_status: 'friend', 'foe', or '' (neutral)
    """
    # Check if user already exists
    user_data_dict = load_user_data_csv()

    if username in user_data_dict:
        # User exists - check if we need to update friend/foe status
        current_status = user_data_dict[username].get('friend_foe', '')

        if friend_foe_status and friend_foe_status != current_status:
            # Status is changing - update it
            try:
                set_friend_foe_status(username, friend_foe_status)
                status_display = f"'{current_status}'" if current_status else "'neutral'"
                print(f"[BOOKMARK] Updated @{username} status: {status_display} -> '{friend_foe_status}'")
                return True
            except Exception as e:
                print(f"[BOOKMARK] Error updating status for @{username}: {e}")
                return False
        else:
            # No status change needed
            print(f"[BOOKMARK] User @{username} already in CSV (no change needed)")
            return False

    try:
        # User doesn't exist - add them
        # Add to CSV using existing function
        # user_obj already has all fields from search expansions
        update_user_data(username, user_obj)

        # If friend/foe status specified, set it
        if friend_foe_status:
            set_friend_foe_status(username, friend_foe_status)
            print(f"[BOOKMARK] Added @{username} to user_data.csv as {friend_foe_status}")
        else:
            print(f"[BOOKMARK] Added @{username} to user_data.csv")

        return True

    except Exception as e:
        print(f"[BOOKMARK] Error adding user @{username}: {e}")
        return False

def remove_user_from_rotation(username):
    """
    Remove a user from rotation by deleting them from user_data.csv.
    Used for ##ADD-REMOVE## tags.
    Returns True if user was removed, False if not found.
    """
    user_data_dict = load_user_data_csv()

    if username not in user_data_dict:
        print(f"[REMOVE TAG] User @{username} not in CSV (already removed or never added)")
        return False

    try:
        # Remove from dictionary
        del user_data_dict[username]

        # Save back to CSV
        save_user_data_to_csv(user_data_dict)

        print(f"[REMOVE TAG] Removed @{username} from user_data.csv")
        return True

    except Exception as e:
        print(f"[REMOVE TAG] Error removing user @{username}: {e}")
        return False

def validate_csv_integrity():
    """
    Validate user_data.csv integrity before adding new users.
    Checks for duplicate usernames, missing required fields, etc.
    """
    user_data_dict = load_user_data_csv()

    if not user_data_dict:
        print("[CSV CHECK] CSV is empty or missing - will be created on first add")
        return True

    # Check for duplicates (should be impossible but worth checking)
    usernames = list(user_data_dict.keys())
    if len(usernames) != len(set(usernames)):
        print("[CSV CHECK] WARNING: Duplicate usernames found in CSV!")
        return False

    # Check each record has required fields
    required_fields = ['username', 'user_id']
    missing_fields = []

    for username, data in user_data_dict.items():
        for field in required_fields:
            if field not in data or not data[field]:
                missing_fields.append((username, field))

    if missing_fields:
        print(f"[CSV CHECK] WARNING: Missing required fields: {missing_fields[:5]}...")
        return False

    print(f"[CSV CHECK] CSV validated - {len(user_data_dict)} users in rotation pool")
    return True

def process_add_tags(client):
    """
    Main orchestrator: Search for "bookmark this" phrases since last check and add/remove users from CSV.
    Called once at startup before normal rotation logic.
    Uses timestamp tracking to only process new replies.
    Supports variants: "bookmark this", "bookmark this in my friend category", etc.
    """
    print("\n" + "=" * 80)
    print("CHECKING FOR NEW BOOKMARK PHRASES")
    print("=" * 80 + "\n")

    try:
        # Load last check timestamp
        last_check = load_last_add_check()

        # Search for bookmark phrases since last check
        found_tags = search_add_tag_replies(client, start_time=last_check)

        if not found_tags:
            print("[BOOKMARK] No new bookmark phrases found\n")
            # Update timestamp even if no results (prevents re-checking same time range)
            save_last_add_check()
            return

        # Track successes
        added_count = 0
        skipped_count = 0
        removed_count = 0
        variant_counts = {}

        # Process each bookmarked user
        for tweet_id, tweet_text, username, user_obj in found_tags:
            # Parse which variant was used
            variant_name, should_add, friend_foe_status, priority = parse_add_tag_variant(tweet_text)

            # Track variant usage
            variant_counts[variant_name] = variant_counts.get(variant_name, 0) + 1

            print(f"[{variant_name}] Processing @{username} from tweet {tweet_id}...")

            if should_add:
                # Add user with appropriate friend/foe status
                if add_user_from_tag(username, user_obj, friend_foe_status):
                    added_count += 1
                else:
                    skipped_count += 1
            else:
                # Remove user (future functionality)
                if remove_user_from_rotation(username):
                    removed_count += 1
                else:
                    skipped_count += 1

        # Update last check timestamp
        save_last_add_check()

        # Summary
        print("\n" + "=" * 80)
        print("[BOOKMARK SUMMARY]")
        print(f"  Added: {added_count}")
        print(f"  Removed: {removed_count}")
        print(f"  Skipped: {skipped_count}")
        print("\n  Categories used:")
        for variant, count in sorted(variant_counts.items()):
            print(f"    {variant}: {count}")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"[BOOKMARK] Error during bookmark phrase processing: {e}")
        print("[BOOKMARK] Continuing with normal rotation...\n")
        # Don't crash - log and continue with normal bot flow

# ============================================================================
# USER DATA CSV MANAGEMENT
# ============================================================================

def load_user_data_csv():
    """Load existing user data CSV into a dictionary keyed by username."""
    user_data = {}

    if not os.path.exists(USER_DATA_CSV):
        return user_data

    try:
        with open(USER_DATA_CSV, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                username = row.get('username', '').strip()
                if username:
                    user_data[username] = row
    except Exception as e:
        print(f"Error loading user data CSV: {e}")

    return user_data

def save_user_data_to_csv(user_data_dict):
    """Save user data dictionary to CSV."""
    # Define all the fields we're tracking
    fieldnames = [
        'username', 'user_id', 'name', 'created_at', 'description', 'location',
        'url', 'profile_image_url', 'verified', 'verified_type', 'protected',
        'followers_count', 'following_count', 'tweet_count', 'listed_count', 'like_count',
        'pinned_tweet_id', 'last_updated', 'times_checked', 'times_replied', 'times_skipped',
        'times_no_tweet', 'friend_foe'
    ]

    try:
        with open(USER_DATA_CSV, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            # Preserve original order (don't sort - user controls order for rotation)
            for username in user_data_dict.keys():
                writer.writerow(user_data_dict[username])

        print(f"[DATA] Saved {len(user_data_dict)} user records to {USER_DATA_CSV}")
    except Exception as e:
        print(f"Error saving user data CSV: {e}")

def update_user_data(username, user_obj):
    """Update or create user data entry in the CSV."""
    # Load existing data
    user_data_dict = load_user_data_csv()

    # Extract public metrics
    metrics = user_obj.public_metrics if hasattr(user_obj, 'public_metrics') and user_obj.public_metrics else {}

    # Build the user record
    user_record = {
        'username': username,
        'user_id': str(user_obj.id) if hasattr(user_obj, 'id') else '',
        'name': user_obj.name if hasattr(user_obj, 'name') else '',
        'created_at': str(user_obj.created_at) if hasattr(user_obj, 'created_at') else '',
        'description': (user_obj.description or '').replace('\n', ' ').replace('\r', ' ') if hasattr(user_obj, 'description') else '',
        'location': user_obj.location if hasattr(user_obj, 'location') else '',
        'url': user_obj.url if hasattr(user_obj, 'url') else '',
        'profile_image_url': user_obj.profile_image_url if hasattr(user_obj, 'profile_image_url') else '',
        'verified': str(user_obj.verified) if hasattr(user_obj, 'verified') else 'False',
        'verified_type': user_obj.verified_type if hasattr(user_obj, 'verified_type') else '',
        'protected': str(user_obj.protected) if hasattr(user_obj, 'protected') else 'False',
        'followers_count': str(metrics.get('followers_count', 0)),
        'following_count': str(metrics.get('following_count', 0)),
        'tweet_count': str(metrics.get('tweet_count', 0)),
        'listed_count': str(metrics.get('listed_count', 0)),
        'like_count': str(metrics.get('like_count', 0)),
        'pinned_tweet_id': str(user_obj.pinned_tweet_id) if hasattr(user_obj, 'pinned_tweet_id') and user_obj.pinned_tweet_id else '',
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'times_checked': '1',  # Will increment if already exists
        'times_replied': '0',
        'times_skipped': '0',
        'times_no_tweet': '0',
        'friend_foe': ''
    }

    # If user already exists, preserve engagement metrics and increment times_checked
    if username in user_data_dict:
        old_data = user_data_dict[username]
        old_count = int(old_data.get('times_checked', 0))
        user_record['times_checked'] = str(old_count + 1)
        # Preserve existing engagement metrics
        user_record['times_replied'] = old_data.get('times_replied', '0')
        user_record['times_skipped'] = old_data.get('times_skipped', '0')
        user_record['times_no_tweet'] = old_data.get('times_no_tweet', '0')
        user_record['friend_foe'] = old_data.get('friend_foe', '')
        print(f"[DATA] Updated user @{username} (check #{user_record['times_checked']})")
    else:
        print(f"[DATA] Added new user @{username}")

    # Update the dictionary
    user_data_dict[username] = user_record

    # Save back to CSV
    save_user_data_to_csv(user_data_dict)

    return user_record

def increment_user_metric(username, metric_name):
    """Increment a specific engagement metric for a user."""
    user_data_dict = load_user_data_csv()

    if username not in user_data_dict:
        print(f"[WARNING] Cannot increment {metric_name} - user @{username} not in CSV")
        return

    # Handle both missing keys and empty string values
    current_value_str = user_data_dict[username].get(metric_name) or '0'
    current_value = int(current_value_str) if current_value_str.strip() else 0
    user_data_dict[username][metric_name] = str(current_value + 1)

    save_user_data_to_csv(user_data_dict)
    print(f"[ENGAGEMENT] @{username} {metric_name}: {current_value} → {current_value + 1}")

def set_friend_foe_status(username, status):
    """Set friend/foe status for a user. Status can be 'friend', 'foe', 'jokster', 'snark', or '' (neutral)."""
    valid_statuses = ['friend', 'foe', 'jokster', 'snark', '']

    if status not in valid_statuses:
        print(f"[ERROR] Invalid status '{status}'. Must be 'friend', 'foe', 'jokster', 'snark', or empty string.")
        return False

    user_data_dict = load_user_data_csv()

    if username not in user_data_dict:
        print(f"[WARNING] Cannot set friend/foe - user @{username} not in CSV")
        return False

    user_data_dict[username]['friend_foe'] = status
    save_user_data_to_csv(user_data_dict)

    status_display = status if status else 'neutral'
    print(f"[FRIEND/FOE] Set @{username} as: {status_display}")
    return True

# ============================================================================
# CLAUDE API INTEGRATION
# ============================================================================

def generate_ai_reply(voice_content, original_tweet, api_key, user_context=None):
    """
    Generate an AI reply using Anthropic Claude API.

    Args:
        voice_content: Personality/style guide from DocsVoice.txt
        original_tweet: Tweet text being replied to
        api_key: Claude API key
        user_context: Optional dict with user info:
            - username: Twitter handle (without @)
            - bio: User's description/bio
            - friend_foe: 'friend', 'foe', or '' (neutral)
    """
    try:
        # Build user context section if available
        user_context_section = ""
        mention_instruction = ""
        if user_context:
            username = user_context.get('username', '')
            bio = user_context.get('bio', '')
            friend_foe = user_context.get('friend_foe', '')
            is_verified = user_context.get('verified', False)

            # Build the context text
            if username or bio:
                user_context_section = f"\nUSER CONTEXT:\n"
                if username:
                    user_context_section += f"Replying to: @{username}\n"
                if bio:
                    user_context_section += f"Their bio: {bio}\n"

                # Add tone guidance based on friend/foe marker
                if friend_foe == 'friend':
                    user_context_section += "\n⚠️ TONE NOTE: This is a friendly account. Be generous, supportive, and warm even if their tweet is ambiguous or you might disagree. Give them the benefit of the doubt.\n"
                elif friend_foe == 'foe':
                    user_context_section += "\n⚠️ TONE NOTE: This is an adversarial account. You can be more critical, sharp, or pointed in your response. Don't hold back if their take is bad.\n"
                elif friend_foe == 'jokster':
                    user_context_section += "\n⚠️ TONE NOTE: This is a JOKSTER - they make jokes and enjoy witty banter. Match their playful energy with clever wordplay and humor. Keep it light and FUN. AVOID political commentary or hot-button issues - focus on pure comedy and playful teasing. Think comedian-to-comedian banter, not pundit-to-pundit debate.\n"
                elif friend_foe == 'snark':
                    user_context_section += "\n⚠️ TONE NOTE: This is a SNARK account - they use sarcasm and sharp wit. You can be sarcastic back, use dry humor, and employ clever burns. Snarky energy is welcome here.\n"

            # Build @mention instruction based on verified status
            if is_verified and username:
                mention_instruction = f"""
@MENTION REQUIREMENT:
This user is verified. You MUST include @{username} somewhere INSIDE your reply in a place that reads naturally.
- DO NOT put @{username} at the very beginning of your reply.
- Weave it into the middle of a sentence where it makes grammatical sense.
- Example: "The hard part @{username} is remembering that..." or "Not gonna lie @{username}, that hit different"
- The @{username} must appear exactly once, naturally embedded in the text."""
            else:
                mention_instruction = """
@MENTION REQUIREMENT:
Do NOT include any @username in your reply. No @mentions at all."""

        # Build the prompt for engagement farming
        prompt = f"""You are generating a reply to engage with this tweet. Use the voice and personality described below.

VOICE/PERSONALITY:
{voice_content}
{user_context_section}
TWEET YOU'RE REPLYING TO:
"{original_tweet}"

Generate an engaging reply that follows the voice guidelines above. This is for building relationships and engagement, not arguing. Be witty, supportive, or add value to the conversation.
{mention_instruction}

CRITICAL REQUIREMENTS:
- Keep it UNDER {MAX_CHARS} characters total
- Follow all style rules from the voice file
- Make it quotable and shareable
- If the tweet doesn't warrant a good reply, return ONLY: SKIP

JOKE DETECTION:
If the tweet you're replying to is primarily a joke, pun, or humorous observation
(not just sarcasm or political commentary, but an actual joke/dad joke/pun),
prefix your response with [RETWEET] on its own line.

Example format if it's a joke:
[RETWEET]
Your witty reply here

If it's NOT primarily a joke, just return your reply normally.

Your reply (text only, no quotes around it):"""

        # Make API call to Anthropic
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        data = {
            "model": "claude-sonnet-4-5-20250929",
            "max_tokens": 150,
            "temperature": 0.8,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            ai_reply = result["content"][0]["text"].strip()

            # Check for joke detection marker
            should_retweet = False
            if ai_reply.startswith('[RETWEET]'):
                should_retweet = True
                ai_reply = ai_reply.replace('[RETWEET]', '').strip()
                print(f"[JOKE DETECTED] Claude flagged this as a joke - will retweet after reply")

            # Remove any quotation marks that might wrap the response
            if ai_reply.startswith('"') and ai_reply.endswith('"'):
                ai_reply = ai_reply[1:-1]

            return ai_reply, should_retweet
        else:
            print(f"Claude API error: {response.status_code} - {response.text}")
            return None, False

    except Exception as e:
        print(f"Error generating AI reply: {e}")
        return None, False

# ============================================================================
# TWITTER OPERATIONS
# ============================================================================

def get_random_user_tweet(client, usernames, cycle_index=0):
    """
    Select next user based on cycle index and get their most recent original tweet.

    Args:
        client: Twitter API client
        usernames: List of usernames (pre-sorted by engagement)
        cycle_index: Current cycle number (0-based) within this script execution
    """
    selected_username = get_next_username(usernames, cycle_index)
    if not selected_username:
        return None, None, None

    # Calculate lookback time
    now_utc = datetime.now(timezone.utc)
    start_time_dt = now_utc - timedelta(hours=LOOKBACK_HOURS)
    start_time = start_time_dt.isoformat(timespec='seconds')

    print(f"Looking for tweets since: {start_time}\n")

    try:
        # Get user info with all possible fields
        user_response = client.get_user(
            username=selected_username,
            user_fields=[
                'created_at', 'description', 'entities', 'location', 'pinned_tweet_id',
                'profile_image_url', 'protected', 'public_metrics', 'url', 'verified',
                'verified_type', 'withheld'
            ],
            expansions=['pinned_tweet_id']
        )

        if not user_response.data:
            print(f"User @{selected_username} not found.")
            return selected_username, None, None  # Return username so it can be marked as used

        user = user_response.data
        user_id = user.id

        # Update user data in CSV
        update_user_data(selected_username, user)

        # Print some interesting info
        metrics = user.public_metrics if hasattr(user, 'public_metrics') and user.public_metrics else {}
        print(f"User: {user.name} | Followers: {metrics.get('followers_count', '?')} | Following: {metrics.get('following_count', '?')}")
        if hasattr(user, 'description') and user.description:
            bio_preview = user.description[:80].replace('\n', ' ')
            print(f"Bio: {bio_preview}{'...' if len(user.description) > 80 else ''}")
        print()

        # Get user's recent tweets (excluding replies and retweets)
        tweets_response = client.get_users_tweets(
            id=user_id,
            max_results=MAX_TWEETS_TO_FETCH,
            start_time=start_time,
            exclude=['replies', 'retweets'],
            tweet_fields=['created_at', 'text', 'id']
        )

        if tweets_response.data:
            latest = tweets_response.data[0]
            created_at = latest.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if latest.created_at else 'N/A'

            print(f"\nMost recent original post by @{selected_username} ({created_at}):")
            print("-" * 80)
            print(latest.text)
            print("-" * 80)
            print(f"Tweet ID: {latest.id}")
            print(f"Link: https://x.com/{selected_username}/status/{latest.id}\n")

            return selected_username, latest.id, latest.text
        else:
            print(f"No qualifying original posts from @{selected_username} in last {LOOKBACK_HOURS}h.")
            return selected_username, None, None  # Return username so it can be marked as used

    except tweepy.TweepyException as e:
        print(f"Error fetching tweet: {e}")
        return selected_username, None, None  # Return username so it can be marked as used

def post_reply(client, username, tweet_id, reply_text):
    """Post a reply to the specified tweet. Reply text is posted as-is (Claude handles @mentions)."""
    try:
        # Ensure it's under character limit
        if len(reply_text) > MAX_CHARS:
            print(f"WARNING: Reply is {len(reply_text)} chars, truncating to {MAX_CHARS}")
            reply_text = reply_text[:MAX_CHARS]

        # Post the reply (in_reply_to_tweet_id handles threading, no need to prepend @)
        reply_response = client.create_tweet(
            text=reply_text,
            in_reply_to_tweet_id=tweet_id
        )

        reply_id = reply_response.data['id']
        return reply_id

    except tweepy.TweepyException as e:
        print(f"Failed to post reply: {e}")
        return None

def retweet_original_post(client, tweet_id, auth_user_id, username):
    """Retweet the original post to amplify good content."""
    if not auth_user_id:
        print("[RETWEET] Skipping - no auth user ID available")
        return False

    try:
        client.retweet(tweet_id=tweet_id, user_auth=True)
        print(f"[RETWEET] ✓ Retweeted @{username}'s joke!")
        return True
    except tweepy.TweepyException as e:
        print(f"[RETWEET] Failed to retweet: {e}")
        return False

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main(cycle_index=0):
    """
    Main execution flow for a single cycle.

    Args:
        cycle_index: Current cycle number (0-based) within this script execution
    """
    print("=" * 80)
    print("Twitter Auto-Reply with Claude AI")
    print("=" * 80)
    print()

    # Load all necessary components
    print("Loading voice file...")
    voice_content = load_voice_file()
    if not voice_content:
        print("ERROR: Cannot proceed without voice file")
        return False
    print("[OK] Voice file loaded\n")

    print("Loading Claude API key...")
    api_key = load_claude_api_key()
    if not api_key:
        print("ERROR: Cannot proceed without Claude API key")
        return False
    print("[OK] Claude API key loaded\n")

    print("Loading Twitter credentials...")
    consumer_key, consumer_secret, access_token, access_token_secret, bearer_token = load_twitter_credentials()
    print("[OK] Twitter credentials loaded\n")

    print("Initializing Twitter client...")
    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
        bearer_token=bearer_token
    )
    print("[OK] Twitter client initialized\n")

    # Get authenticated user ID for retweeting
    auth_user_id = None
    try:
        me = client.get_me()
        auth_user_id = me.data.id
        print(f"[AUTH] Authenticated as user ID: {auth_user_id}\n")
    except Exception as e:
        print(f"[WARNING] Could not get user ID: {e}")
        print("[WARNING] Retweeting will be disabled\n")

    print("Loading target accounts...")
    usernames = load_accounts()
    print(f"[OK] Loaded {len(usernames)} accounts\n")

    # Get next user's tweet based on cycle index
    print("Fetching next user's tweet...")
    username, tweet_id, tweet_text = get_random_user_tweet(client, usernames, cycle_index)

    if not username or not tweet_id or not tweet_text:
        print("Could not get a valid tweet. Exiting.")
        # Track if user exists but has no qualifying tweet
        if username:
            increment_user_metric(username, 'times_no_tweet')
        return False

    # Load user data from CSV to pass context to Claude
    user_data_dict = load_user_data_csv()
    user_record = user_data_dict.get(username, {})
    user_bio = user_record.get('description', '')
    friend_foe_status = user_record.get('friend_foe', '')
    is_verified = str(user_record.get('verified', '')).strip().lower() == 'true'

    # Build user context dict
    user_context = {
        'username': username,
        'bio': user_bio,
        'friend_foe': friend_foe_status,
        'verified': is_verified
    }

    print(f"[CONTEXT] Bio: {user_bio[:80]}..." if len(user_bio) > 80 else f"[CONTEXT] Bio: {user_bio}")
    print(f"[CONTEXT] Verified: {is_verified}")
    if friend_foe_status:
        print(f"[CONTEXT] Relationship: {friend_foe_status}")

    # Check if we've already replied to this specific tweet (deduplication)
    if has_replied_to_tweet(tweet_id):
        print(f"\n[DEDUP] We've already replied to this tweet before (ID: {tweet_id})")
        print("Exiting without calling Claude or posting.\n")
        return False

    # Generate AI reply
    print("Generating AI reply with Claude...")
    ai_reply, should_retweet = generate_ai_reply(voice_content, tweet_text, api_key, user_context)

    if not ai_reply:
        print("Failed to generate AI reply.")
        # Still add to replied tweets so we don't check it again
        add_replied_tweet(tweet_id)
        print("Exiting.\n")
        return False

    # Check if AI decided to skip
    if "SKIP" in ai_reply.upper().strip():
        print("\nAI decided not to reply to this tweet (not a good engagement opportunity)")
        increment_user_metric(username, 'times_skipped')
        # Still add to replied tweets so we don't check it again
        add_replied_tweet(tweet_id)
        print("Exiting without posting.\n")
        return False

    print("\n" + "=" * 80)
    print("GENERATED REPLY:")
    print("=" * 80)
    print(ai_reply)
    print("=" * 80)
    print(f"Character count: {len(ai_reply)}")
    print()

    # Post the reply
    print("Posting reply to Twitter...")
    reply_id = post_reply(client, username, tweet_id, ai_reply)

    if reply_id:
        # Add to replied tweets list (deduplication tracking)
        add_replied_tweet(tweet_id)

        # Track successful reply
        increment_user_metric(username, 'times_replied')

        # Retweet if Claude detected a joke
        if should_retweet:
            print()
            retweet_original_post(client, tweet_id, auth_user_id, username)

        print("\n" + "=" * 80)
        print("[SUCCESS] REPLY POSTED!")
        print("=" * 80)
        print(f"Reply ID: {reply_id}")
        print(f"Reply link: https://x.com/DocAtCDI/status/{reply_id}")
        print(f"Original tweet: https://x.com/{username}/status/{tweet_id}")
        print("=" * 80)
        print()
        return True
    else:
        print("\n[FAILED] Failed to post reply")
        return False

if __name__ == "__main__":
    # ========== ONE-TIME SETUP: Check for bookmark phrases at script startup ==========
    print("\n" + "=" * 80)
    print("STARTUP: Checking for bookmark phrases and validating CSV")
    print("=" * 80 + "\n")

    try:
        # Load credentials and create client for bookmark check
        consumer_key, consumer_secret, access_token, access_token_secret, bearer_token = load_twitter_credentials()
        client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
            bearer_token=bearer_token
        )

        # Validate CSV and process bookmark phrases (runs ONCE)
        validate_csv_integrity()
        process_add_tags(client)

        print("=" * 80)
        print("STARTUP COMPLETE - Starting cycle loop")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"[ERROR] Startup failed: {e}")
        import traceback
        traceback.print_exc()
        print("\nContinuing with cycles anyway...\n")
    # ===============================================================================

    # Load starting position and account list
    start_index = load_counter()
    usernames = load_accounts()
    total_users = len(usernames)

    print("=" * 80)
    print(f"RUNNING UNTIL FIRST REPLY (starting at position {start_index} of {total_users} accounts)")
    print(f"Delay between cycles: {DELAY_SECONDS} seconds")
    print("=" * 80 + "\n")

    current_index = start_index
    cycles_run = 0

    try:
        while True:
            wrapped_index = current_index % total_users

            print("\n" + "=" * 80)
            print(f"CYCLE {cycles_run + 1} - Position {wrapped_index + 1}/{total_users} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 80 + "\n")

            try:
                replied = main(cycle_index=wrapped_index)
            except Exception as e:
                print(f"\nError in cycle {cycles_run + 1}: {e}")
                import traceback
                traceback.print_exc()
                replied = False

            current_index += 1
            cycles_run += 1

            if replied:
                # Save position for next run and exit
                next_pos = current_index % total_users
                save_counter(next_pos)
                print("\n" + "=" * 80)
                print(f"Reply posted! Saved position {next_pos} to counter.txt for next run.")
                print(f"Ran {cycles_run} cycle(s) this session.")
                print("=" * 80 + "\n")
                break

            # Delay before next cycle
            print(f"\nNo reply posted, moving to next account...")
            print(f"Waiting {DELAY_SECONDS} seconds before next cycle...")
            time.sleep(DELAY_SECONDS)

    except KeyboardInterrupt:
        next_pos = current_index % total_users
        save_counter(next_pos)
        print(f"\n\nInterrupted after {cycles_run} cycle(s). Saved position {next_pos} to counter.txt.")
    except Exception as e:
        next_pos = current_index % total_users
        save_counter(next_pos)
        print(f"\nUnexpected error: {e}")
        print(f"Saved position {next_pos} to counter.txt.")
        import traceback
        traceback.print_exc()
