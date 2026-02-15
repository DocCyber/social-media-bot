#!/usr/bin/env python3
"""
AI-Enhanced BlueSky Reply System
Uses Anthropic Claude API with voice.txt to generate authentic replies in your style.
Includes data validation, length limits, and testing safety controls.
"""

import sys
import os
import json
import re
import requests
import random
from datetime import datetime, timezone, timedelta

# Add the parent directory to the Python path for standalone execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from modules import auth

# Configuration
TESTING_MODE = False  # Set to False to respond to all users
TESTING_USER = "mrsdocatcdi.bsky.social"  # Only respond to this user during testing
MAX_CHARS = 280  # Character limit for responses
MAX_RETRIES = 3  # Maximum API retries for shortening
MAX_REPLIES_PER_USER_PER_6H = 1  # Maximum replies per user per 6-hour window
MAX_CONSECUTIVE_REPLIES = 1  # Maximum consecutive replies to same user

# File paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
PROCESSED_FILE = os.path.join(SCRIPT_DIR, "processed_notifications.json")
VOICE_FILE = os.path.join(DATA_DIR, "voice.txt")
BANNED_WORDS_FILE = os.path.join(DATA_DIR, "banned_words.txt")
COST_TRACKING_FILE = os.path.join(SCRIPT_DIR, "ai_cost_tracking.json")
REPLY_LOG_FILE = os.path.join(DATA_DIR, "ai_reply_log.txt")
USER_6H_COUNTS_FILE = os.path.join(SCRIPT_DIR, "user_6h_reply_counts.json")
CONSECUTIVE_REPLIES_FILE = os.path.join(SCRIPT_DIR, "consecutive_replies.json")
REPLIED_POSTS_FILE = os.path.join(SCRIPT_DIR, "replied_posts.json")

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
        else:
            print(f"Error: Voice file not found at {VOICE_FILE}")
            return None

    except Exception as e:
        print(f"Error loading voice file at {VOICE_FILE}: {e}")
        return None

def load_banned_words():
    """Load the banned words list from file."""
    try:
        if os.path.exists(BANNED_WORDS_FILE):
            with open(BANNED_WORDS_FILE, 'r', encoding='utf-8') as f:
                banned_words = [line.strip().lower() for line in f if line.strip()]
                return banned_words
        else:
            print(f"Error: Banned words file not found at {BANNED_WORDS_FILE}")
            return []
    except Exception as e:
        print(f"Error loading banned words file at {BANNED_WORDS_FILE}: {e}")
        return []

def is_emoji_only_response(text):
    """Check if the text contains only emojis, whitespace, and basic punctuation."""
    # Remove all whitespace and basic punctuation
    cleaned = re.sub(r'[\s\.,!?;:\-_]+', '', text)
    if not cleaned:
        return True

    # Check if remaining characters are only emojis
    # Basic emoji ranges in Unicode
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)

    # Remove all emojis and see if anything remains
    no_emojis = emoji_pattern.sub('', cleaned)
    return len(no_emojis) == 0

def has_meaningful_words(text):
    """Check if text has meaningful words (not just filler or emoji responses)."""
    # Remove emojis and punctuation
    cleaned = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251\s\.,!?;:\-_]+', '', text)

    # Check for actual letters
    return len(re.sub(r'[^a-zA-Z]', '', cleaned)) >= 2

def generate_random_emoji_response(user_text):
    """Generate a random emoji response based on detected emoji in user text."""
    # Simple emoji detection
    happy_emojis = [':)', ':D', '😊', '😄', '🙂']
    sad_emojis = [':(', '😢', '😞', '☹️']
    neutral_emojis = [':|', '😐', '😶']
    wink_emojis = [';)', '😉']
    confused_emojis = [':/', '😕', '🤔']

    # Check user's text for emotional indicators
    if any(emoji in user_text for emoji in ['😄', '😊', '🙂', '😁', '😆', '😃']):
        return random.choice([':)', ':D', '😊'])
    elif any(emoji in user_text for emoji in ['😢', '😞', '☹️', '😭', '😿']):
        return random.choice([':(', '😞'])
    elif any(emoji in user_text for emoji in ['😉']):
        return random.choice([';)', '😉'])
    elif any(emoji in user_text for emoji in ['😕', '🤔', '😐']):
        return random.choice([':/', ':|'])
    else:
        # Default random selection
        all_emojis = [':)', ';)', ':D']
        return random.choice(all_emojis)

def strip_haha_prefix(text):
    """Remove 'haha' and variants from the beginning of responses and capitalize the next word."""
    # Single comprehensive pattern to match all laughter at start
    laugh_pattern = r'^(ha+h?a*|he+h?e*|lol|lmao|rofl)[,\s]*'

    original_text = text
    text = re.sub(laugh_pattern, '', text, flags=re.IGNORECASE)

    # If we stripped something, capitalize the first letter of remaining text
    if text != original_text and text:
        text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
        print(f"Stripped haha prefix: '{original_text}' -> '{text}'")

    return text.strip()

def sanitize_response(text):
    """Replace em dashes with properly placed commas and clean up formatting."""
    # First strip any haha prefixes
    text = strip_haha_prefix(text)

    # Replace em dashes (—) with commas
    text = text.replace('—', ',')

    # Clean up any double commas that might result
    text = re.sub(r',\s*,', ',', text)

    # Clean up comma spacing
    text = re.sub(r',\s+', ', ', text)
    text = re.sub(r'\s+,', ',', text)

    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def validate_response_length(text):
    """Check if response is within character limit."""
    return len(text) <= MAX_CHARS

def contains_banned_words(text, banned_words):
    """Check if response contains any banned words or phrases."""
    text_lower = text.lower()
    for banned_phrase in banned_words:
        banned_lower = banned_phrase.lower().strip()
        if not banned_lower:  # Skip empty lines
            continue

        # For multi-word phrases, check for whole phrase
        if ' ' in banned_lower:
            if banned_lower in text_lower:
                print(f"BANNED PHRASE DETECTED: '{banned_phrase}' found in response: '{text}'")
                return True
        else:
            # For single words, check as whole word (word boundary)
            import re
            pattern = r'\b' + re.escape(banned_lower) + r'\b'
            if re.search(pattern, text_lower):
                print(f"BANNED WORD DETECTED: '{banned_phrase}' found in response: '{text}'")
                return True
    return False

def is_question_post(text):
    """Detect if original post is asking a question."""
    if not text:
        return False

    question_patterns = [
        "how do you", "how would you", "what do you", "what would you",
        "your response", "how do you respond", "what's your",
        "how should", "what should", "how would", "what would"
    ]
    text_lower = text.lower()

    # Check for question patterns
    has_question_pattern = any(pattern in text_lower for pattern in question_patterns)

    # Check for question mark
    has_question_mark = "?" in text

    return has_question_pattern or has_question_mark

def generate_ai_reply(voice_content, original_post, user_reply, banned_words, config, attempt=1):
    """Generate an AI reply using Anthropic Claude API."""
    try:
        # Load Anthropic API key from secrets file
        secrets_file = r"D:\secrets\CLAUDEAPI.txt"
        if not os.path.exists(secrets_file):
            print(f"Error: Anthropic API key file not found at {secrets_file}")
            return None

        with open(secrets_file, 'r', encoding='utf-8') as f:
            api_key = f.read().strip()

        if not api_key:
            print("Error: Anthropic API key file is empty")
            return None

        # Build the prompt
        if attempt == 1:
            banned_words_section = "\n".join(f"- {word}" for word in banned_words)

            # Detect if original post is a question
            is_question = is_question_post(original_post)

            if is_question:
                prompt = f"""CRITICAL - NEVER USE THESE WORDS/PHRASES:
{banned_words_section}

VOICE/PERSONALITY:
{voice_content}

CONVERSATION CONTEXT:
You (DocAtCDI) posted a question: "{original_post}"

Someone answered your question with: "{user_reply}"

Respond to their answer - you can acknowledge their perspective, add commentary about their approach, or share a different viewpoint. They're answering YOUR question, not talking TO you directly. Their reply is their response to the scenario/question you posed.

Write your reply as DocAtCDI responding to their answer. Keep it under {MAX_CHARS} characters, conversational, and in your voice. No quotation marks around your response.

IMPORTANT: If you decide not to respond (based on your personality or if the situation doesn't warrant a response), return ONLY the exact text: NO_RESPONSE

Do not add anything else. Do not explain. Just return those exact characters and nothing more."""
            else:
                prompt = f"""CRITICAL - NEVER USE THESE WORDS/PHRASES:
{banned_words_section}

VOICE/PERSONALITY:
{voice_content}

CONVERSATION CONTEXT:
You (DocAtCDI) originally posted: "{original_post}"

Then someone replied to YOUR post saying: "{user_reply}"

Now you need to respond to THEIR reply to YOUR original post. They are commenting on what YOU said, not talking about themselves.

Write your reply as DocAtCDI responding to their comment about your original post. Keep it under {MAX_CHARS} characters, conversational, and in your voice. No quotation marks around your response.

IMPORTANT: If you decide not to respond (based on your personality or if the situation doesn't warrant a response), return ONLY the exact text: NO_RESPONSE

Do not add anything else. Do not explain. Just return those exact characters and nothing more."""
        else:
            prompt = f"""The previous response was too long. Please shorten this reply to under {MAX_CHARS} characters while maintaining the same tone and meaning:

{user_reply}

Make it more concise but keep the personality and authenticity."""

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

            # Track costs
            track_api_usage(result.get("usage", {}))

            return ai_reply
        else:
            print(f"Anthropic API error: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print(f"Error generating AI reply: {e}")
        return None

def log_ai_interaction(user_handle, user_reply, ai_response, original_post=""):
    """Log AI interactions to a daily text file for analysis."""
    try:
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        date_str = now.strftime("%Y-%m-%d")

        # Create daily log file name
        daily_log_file = os.path.join(DATA_DIR, f"ai_reply_log_{date_str}.txt")

        log_entry = f"""
{'='*80}
Date: {timestamp}
User: {user_handle}
Original Post: {original_post}
User Reply: {user_reply}
AI Response: {ai_response}
{'='*80}

"""
        with open(daily_log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Error logging AI interaction: {e}")

def get_current_6h_window():
    """Get current 6-hour window identifier (YYYY-MM-DD-HH where HH is 00, 06, 12, or 18)."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    # Determine 6-hour window: 00-05, 06-11, 12-17, 18-23
    hour = now.hour
    if hour < 6:
        window_start = "00"
    elif hour < 12:
        window_start = "06"
    elif hour < 18:
        window_start = "12"
    else:
        window_start = "18"

    return f"{date_str}-{window_start}"

def load_user_6h_counts():
    """Load 6-hour window reply counts per user."""
    try:
        if os.path.exists(USER_6H_COUNTS_FILE):
            with open(USER_6H_COUNTS_FILE, 'r') as f:
                data = json.load(f)
                # Clean old windows (keep only current window)
                current_window = get_current_6h_window()
                if current_window in data:
                    return {current_window: data[current_window]}
                else:
                    return {current_window: {}}
        else:
            current_window = get_current_6h_window()
            return {current_window: {}}
    except Exception as e:
        print(f"Error loading user 6h counts: {e}")
        current_window = get_current_6h_window()
        return {current_window: {}}

def save_user_6h_counts(counts_data):
    """Save 6-hour window reply counts per user."""
    try:
        with open(USER_6H_COUNTS_FILE, 'w') as f:
            json.dump(counts_data, f, indent=2)
    except Exception as e:
        print(f"Error saving user 6h counts: {e}")

def load_consecutive_replies():
    """Load consecutive reply tracking."""
    try:
        if os.path.exists(CONSECUTIVE_REPLIES_FILE):
            with open(CONSECUTIVE_REPLIES_FILE, 'r') as f:
                return json.load(f)
        else:
            return []
    except Exception as e:
        print(f"Error loading consecutive replies: {e}")
        return []

def save_consecutive_replies(replies_list):
    """Save consecutive reply tracking."""
    try:
        # Keep only last 20 entries to prevent file from growing too large
        with open(CONSECUTIVE_REPLIES_FILE, 'w') as f:
            json.dump(replies_list[-20:], f, indent=2)
    except Exception as e:
        print(f"Error saving consecutive replies: {e}")

def can_reply_to_user(user_handle):
    """Check if we can reply to this user based on 6-hour window limits and consecutive reply rules."""
    # Check 6-hour window limit
    window_counts = load_user_6h_counts()
    current_window = get_current_6h_window()

    if current_window in window_counts and user_handle in window_counts[current_window]:
        if window_counts[current_window][user_handle] >= MAX_REPLIES_PER_USER_PER_6H:
            print(f"6-hour window limit reached for {user_handle} ({window_counts[current_window][user_handle]}/{MAX_REPLIES_PER_USER_PER_6H})")
            return False

    # Check consecutive replies
    consecutive_replies = load_consecutive_replies()
    if len(consecutive_replies) >= MAX_CONSECUTIVE_REPLIES:
        # Check if the last N replies were all to the same user
        recent_replies = consecutive_replies[-MAX_CONSECUTIVE_REPLIES:]
        if all(reply == user_handle for reply in recent_replies):
            print(f"Consecutive reply limit reached for {user_handle} (last {MAX_CONSECUTIVE_REPLIES} replies)")
            return False

    return True

def load_replied_posts():
    """Load list of posts we've already replied to."""
    try:
        if os.path.exists(REPLIED_POSTS_FILE):
            with open(REPLIED_POSTS_FILE, 'r') as f:
                return json.load(f)
        else:
            return []
    except Exception as e:
        print(f"Error loading replied posts: {e}")
        return []

def save_replied_posts(replied_list):
    """Save list of replied posts, keeping only last 50."""
    try:
        # Keep only last 50 entries to prevent file from growing too large
        with open(REPLIED_POSTS_FILE, 'w') as f:
            json.dump(replied_list[-50:], f, indent=2)
    except Exception as e:
        print(f"Error saving replied posts: {e}")

def has_already_replied_to_post(post_uri):
    """Check if we've already replied to this specific post."""
    replied_posts = load_replied_posts()
    if post_uri in replied_posts:
        print(f"Post {post_uri} already replied to. Skipping...")
        return True
    return False

def record_replied_post(post_uri):
    """Record that we replied to this specific post."""
    replied_posts = load_replied_posts()
    replied_posts.append(post_uri)
    save_replied_posts(replied_posts)

def record_reply_to_user(user_handle):
    """Record that we replied to this user for tracking purposes."""
    # Update 6-hour window count
    window_counts = load_user_6h_counts()
    current_window = get_current_6h_window()

    if current_window not in window_counts:
        window_counts[current_window] = {}

    if user_handle not in window_counts[current_window]:
        window_counts[current_window][user_handle] = 0

    window_counts[current_window][user_handle] += 1
    save_user_6h_counts(window_counts)

    # Update consecutive replies
    consecutive_replies = load_consecutive_replies()
    consecutive_replies.append(user_handle)
    save_consecutive_replies(consecutive_replies)

    print(f"Recorded reply to {user_handle} (6h window {current_window}: {window_counts[current_window][user_handle]}/{MAX_REPLIES_PER_USER_PER_6H})")

def track_api_usage(usage_data):
    """Track API usage and costs for monitoring."""
    try:
        # Load existing tracking data
        tracking_data = {"total_requests": 0, "total_tokens": 0, "estimated_cost": 0.0, "daily_usage": {}}
        if os.path.exists(COST_TRACKING_FILE):
            with open(COST_TRACKING_FILE, 'r') as f:
                tracking_data = json.load(f)

        # Add current usage
        tracking_data["total_requests"] += 1

        # Claude API returns input_tokens and output_tokens separately
        input_tokens = usage_data.get("input_tokens", 0)
        output_tokens = usage_data.get("output_tokens", 0)
        total_tokens = input_tokens + output_tokens

        if total_tokens > 0:
            tracking_data["total_tokens"] += total_tokens
            # Claude Sonnet 4.5 pricing: $3.00 per 1M input tokens, $15.00 per 1M output tokens
            input_cost = input_tokens * 0.000003
            output_cost = output_tokens * 0.000015
            tracking_data["estimated_cost"] += (input_cost + output_cost)

        # Track daily usage
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in tracking_data["daily_usage"]:
            tracking_data["daily_usage"][today] = {"requests": 0, "tokens": 0}

        tracking_data["daily_usage"][today]["requests"] += 1
        if total_tokens > 0:
            tracking_data["daily_usage"][today]["tokens"] += total_tokens

        # Save updated tracking
        with open(COST_TRACKING_FILE, 'w') as f:
            json.dump(tracking_data, f, indent=2)

    except Exception as e:
        print(f"Error tracking API usage: {e}")

def get_original_post_context(session, post_uri, config):
    """Fetch the original post that the user is replying to for context."""
    try:
        # Extract the post reference from the URI
        # BlueSky URIs look like: at://did:plc:xxx/app.bsky.feed.post/xxx
        if "app.bsky.feed.post" in post_uri:
            # Split the URI to get the repo (DID) and record key (rkey)
            parts = post_uri.split("/")
            if len(parts) >= 4:
                repo = parts[2]  # The DID
                rkey = parts[4]  # The record key

                # Fetch the post using getRecord
                headers = {"Authorization": f"Bearer {session['accessJwt']}"}
                params = {
                    "repo": repo,
                    "collection": "app.bsky.feed.post",
                    "rkey": rkey
                }

                response = requests.get(
                    f"{config['bsky']['pds_url']}/xrpc/com.atproto.repo.getRecord",
                    headers=headers,
                    params=params
                )

                if response.status_code == 200:
                    record = response.json()
                    return record.get("value", {}).get("text", "")
                else:
                    print(f"Error fetching original post: {response.status_code}")

        return ""
    except Exception as e:
        print(f"Error getting original post context: {e}")
        return ""

def load_processed_notifications():
    """Load processed notifications from file."""
    if os.path.exists(PROCESSED_FILE):
        try:
            with open(PROCESSED_FILE, "r") as file:
                return set(json.load(file))
        except Exception as e:
            print(f"Error loading processed notifications: {e}")
    return set()

def save_processed_notifications(processed_set):
    """Save processed notifications to file."""
    try:
        with open(PROCESSED_FILE, "w") as file:
            json.dump(list(processed_set), file)
    except Exception as e:
        print(f"Error saving processed notifications: {e}")

def load_keys(file_path):
    """Load keys from the JSON file."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as file:
                return json.load(file)
        except Exception as e:
            print(f"Error loading keys: {e}")
    return {}

def get_notifications(pds_url, session, since_time=None, limit=50):
    """Fetch notifications from BlueSky."""
    try:
        headers = {"Authorization": "Bearer " + session["accessJwt"]}
        params = {"limit": limit}
        if since_time:
            params["since"] = since_time.isoformat() + "Z"
        resp = requests.get(
            f"{pds_url}/xrpc/app.bsky.notification.listNotifications",
            headers=headers,
            params=params
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching notifications: {e}")
        return {}

def post_reply(pds_url, session, parent_uri, parent_cid, reply_text, root_uri=None, root_cid=None):
    """Post a reply to a notification with proper threading."""
    try:
        # If no root provided, the parent IS the root (direct reply to original post)
        if not root_uri:
            root_uri = parent_uri
        if not root_cid:
            root_cid = parent_cid

        headers = {"Authorization": "Bearer " + session["accessJwt"]}
        data = {
            "collection": "app.bsky.feed.post",
            "repo": session["did"],
            "record": {
                "$type": "app.bsky.feed.post",
                "text": reply_text,
                "reply": {
                    "root": {"uri": root_uri, "cid": root_cid},
                    "parent": {"uri": parent_uri, "cid": parent_cid}
                },
                "createdAt": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
        }
        resp = requests.post(
            f"{pds_url}/xrpc/com.atproto.repo.createRecord",
            headers=headers,
            json=data,
        )
        resp.raise_for_status()
        print(f"AI reply posted successfully: {reply_text[:50]}...")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error posting AI reply: {e}")
        return False

def process_ai_replies(config, session, notifications):
    """Process notifications and generate AI replies where appropriate."""
    voice_content = load_voice_file()
    if voice_content is None:
        print("Cannot process AI replies without voice file. Exiting.")
        return

    banned_words = load_banned_words()
    if not banned_words:
        print("Warning: No banned words loaded, continuing without banned words list.")

    processed_notifications = load_processed_notifications()

    for notification in notifications:
        # Filter for mentions and replies only
        if notification["reason"] not in ["mention", "reply"]:
            continue

        # Get notification details
        uri = notification.get("uri", "unknown")
        cid = notification.get("cid", None)
        unique_key = f"{uri}:{cid}"

        # Skip if already processed
        if unique_key in processed_notifications:
            continue

        # Get author info
        author_handle = notification.get("author", {}).get("handle", "unknown")

        # TESTING MODE: Only respond to specific user
        if TESTING_MODE and author_handle != TESTING_USER:
            print(f"Skipping {author_handle} (testing mode - only responding to {TESTING_USER})")
            continue

        # Check guardrails: daily limits and consecutive reply rules
        if not can_reply_to_user(author_handle):
            continue

        # Check if we've already replied to this specific post
        if has_already_replied_to_post(uri):
            continue

        # Get user's reply text
        user_reply = notification.get("record", {}).get("text", "")
        if not user_reply:
            continue

        # Get original post context and determine proper threading FIRST
        original_post = ""
        reply_info = notification.get("record", {}).get("reply", {})

        # Determine root and parent for proper threading
        root_uri = None
        root_cid = None

        if reply_info:
            # This is a reply to a reply - need to find the root
            if "root" in reply_info:
                root_uri = reply_info["root"].get("uri", "")
                root_cid = reply_info["root"].get("cid", "")
            elif "parent" in reply_info:
                # If no root, the parent was the original post
                root_uri = reply_info["parent"].get("uri", "")
                root_cid = reply_info["parent"].get("cid", "")

            # Get original post context from root or parent
            context_uri = root_uri if root_uri else uri
            if context_uri:
                original_post = get_original_post_context(session, context_uri, config)
        else:
            # Direct reply to original post - the notification URI is both root and parent
            root_uri = uri
            root_cid = cid

        # PRE-FILTER: Check if response is emoji-only or lacks meaningful content
        if is_emoji_only_response(user_reply) or not has_meaningful_words(user_reply):
            print(f"Pre-filter: {author_handle} sent emoji-only or minimal content, responding with random emoji")

            # Generate random emoji response with 1/3 probability (rnd(3) == 0)
            if random.randint(0, 2) == 0:
                emoji_response = generate_random_emoji_response(user_reply)
                print(f"Sending emoji response: {emoji_response}")

                # Post the emoji reply (root_uri and root_cid are now defined)
                if post_reply(config["bsky"]["pds_url"], session, uri, cid, emoji_response, root_uri, root_cid):
                    # Mark as processed and track
                    processed_notifications.add(unique_key)
                    save_processed_notifications(processed_notifications)
                    record_reply_to_user(author_handle)
                    record_replied_post(uri)
                    log_ai_interaction(author_handle, user_reply, f"[EMOJI RESPONSE] {emoji_response}", "")
                    print(f"Emoji reply posted for {author_handle}")
            else:
                print(f"Random skip: Not responding to {author_handle} this time")
                # Still mark as processed to avoid trying again
                processed_notifications.add(unique_key)
                save_processed_notifications(processed_notifications)

            continue

        print(f"Processing AI reply for {author_handle}")
        print(f"User reply: {user_reply}")
        print(f"Original post context: {original_post[:100]}..." if original_post else "No original post context")

        # Generate AI reply with validation loop
        final_reply = None
        rejected_responses = []
        for attempt in range(1, MAX_RETRIES + 1):
            print(f"AI generation attempt {attempt}")

            if attempt == 1:
                ai_reply = generate_ai_reply(voice_content, original_post, user_reply, banned_words, config, attempt)
            else:
                # For retry attempts, pass the previous response to shorten
                ai_reply = generate_ai_reply(voice_content, original_post, final_reply, banned_words, config, attempt)

            if not ai_reply:
                print("Failed to generate AI reply")
                break

            # Check for intentional non-response (more robust parsing)
            ai_reply_cleaned = ai_reply.strip()
            if "NO_RESPONSE" in ai_reply_cleaned:
                print(f"AI chose not to respond to {author_handle} based on voice instructions")
                print(f"Debug: AI returned: {repr(ai_reply_cleaned)}")
                # Format the mixed response logging
                if rejected_responses:
                    unsent_responses = " ".join(f"[mixed response {i+1}]" for i in range(len(rejected_responses)))
                    log_message = f"[AI chose not to respond]\nUnsent responses: {unsent_responses}"
                else:
                    log_message = "[AI chose not to respond]"
                log_ai_interaction(author_handle, user_reply, log_message, original_post)
                # Mark as processed so we don't try again
                processed_notifications.add(unique_key)
                save_processed_notifications(processed_notifications)
                break

            # Sanitize the response
            sanitized_reply = sanitize_response(ai_reply)

            # Check for banned words
            if contains_banned_words(sanitized_reply, banned_words):
                print(f"Reply contains banned words, retrying...")
                rejected_responses.append(f"BANNED: {sanitized_reply}")
                continue  # Skip this response and try again

            # Check length
            if validate_response_length(sanitized_reply):
                final_reply = sanitized_reply
                print(f"AI reply validated: {final_reply}")
                break
            else:
                print(f"Reply too long ({len(sanitized_reply)} chars), retrying...")
                rejected_responses.append(f"TOO_LONG: {sanitized_reply}")
                final_reply = sanitized_reply  # Keep for next attempt

        # Post the reply if we have a valid one
        if final_reply and cid:
            if post_reply(config["bsky"]["pds_url"], session, uri, cid, final_reply, root_uri, root_cid):
                # Mark as processed
                processed_notifications.add(unique_key)
                save_processed_notifications(processed_notifications)

                # Record the reply for tracking and logging
                record_reply_to_user(author_handle)
                record_replied_post(uri)  # Track this specific post to prevent duplicate replies
                log_ai_interaction(author_handle, user_reply, final_reply, original_post)

                print(f"Threading: root={root_uri}, parent={uri}")
                print(f"AI reply posted and logged for {author_handle}")
            else:
                print("Failed to post AI reply")
        else:
            print("No valid AI reply generated or missing CID")

def run(config, session=None):
    """Main entry point for AI reply module."""
    module_name = __name__.split('.')[-1]
    print(f"{module_name} started")

    try:
        if session is None:
            session = auth.run(config)
            if not session:
                print(f"{module_name} failed: Authentication error")
                return

        # Fetch notifications from the past 5 minutes
        last_check_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        notifications = get_notifications(
            config["bsky"]["pds_url"],
            session,
            since_time=last_check_time
        )

        if notifications and "notifications" in notifications:
            process_ai_replies(config, session, notifications["notifications"])

        print(f"{module_name} finished")
    except Exception as e:
        print(f"Error in {module_name}: {e}")

def main():
    """Main entry point for standalone testing."""
    # Calculate the base directory (jokes directory)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Build configuration
    config = {
        "bsky": {
            "pds_url": "https://bsky.social",
            "handle": "docatcdi.com",
            "app_password": "hftk-zbuc-pl3k-xawr"
        },
        "paths": {
            "keys_file": os.path.join(base_dir, "keys.json"),
            "data_dir": os.path.join(base_dir, "bsky", "data")
        }
    }

    # Run the AI reply functionality
    run(config, None)

if __name__ == "__main__":
    main()
