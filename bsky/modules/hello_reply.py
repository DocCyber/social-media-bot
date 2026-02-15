import sys
import os
import random
import requests
import re
import json
from datetime import datetime, timezone, timedelta

# Add the parent directory to the Python path for standalone execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from modules import auth

# File to persist processed notifications
PROCESSED_FILE = "processed_notifications.json"

# Load processed notifications from file
def load_processed_notifications():
    """Load processed notifications from a file."""
    if os.path.exists(PROCESSED_FILE):
        try:
            with open(PROCESSED_FILE, "r") as file:
                return set(json.load(file))
        except Exception as e:
            print(f"Error loading processed notifications: {e}")
    return set()

def save_processed_notifications(processed_set):
    """Save processed notifications to a file."""
    try:
        with open(PROCESSED_FILE, "w") as file:
            json.dump(list(processed_set), file)
    except Exception as e:
        print(f"Error saving processed notifications: {e}")

# Initialize in-memory set to track processed notifications
PROCESSED_NOTIFICATIONS = load_processed_notifications()

def run(config, session):
    module_name = __name__.split('.')[-1]
    print(f"{module_name} started")

    try:
        # Simulate session creation if not provided
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
            process_greetings(
                config,
                session,
                notifications["notifications"]
            )

        print(f"{module_name} finished")
    except Exception as e:
        print(f"Error in {module_name}: {e}")

def get_notifications(pds_url, session, since_time=None, limit=50):
    """Fetch notifications from Bluesky."""
    try:
        headers = {"Authorization": "Bearer " + session["accessJwt"]}
        params = {"limit": limit}
        if since_time:
            params["since"] = since_time.isoformat() + "Z"  # Fetch only new notifications
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

def process_greetings(config, session, notifications):
    """Check for greetings in mentions and replies, and respond."""
    greetings_path = os.path.join(config["paths"]["data_dir"], "greetings.txt")
    hellos_front_path = os.path.join(config["paths"]["data_dir"], "hellos_front.txt")
    hellos_back_path = os.path.join(config["paths"]["data_dir"], "hellos_back.txt")

    # Load greeting patterns
    greeting_patterns = load_lines(greetings_path)
    if not greeting_patterns:
        print(f"Error: No greeting patterns found in {greetings_path}. Exiting.")
        return

    for notification in notifications:
        # Filter out irrelevant notifications
        if notification["reason"] not in ["mention", "reply"]:
            continue

        # Safely extract URI and CID
        uri = notification.get("uri", "unknown")
        cid = notification.get("cid", None)  # Include CID for unique identification
        unique_key = f"{uri}:{cid}"  # Combine URI and CID for uniqueness

        if unique_key in PROCESSED_NOTIFICATIONS:
            continue  # Skip if already processed

        # Safely get author handle and content
        author_handle = notification.get("author", {}).get("handle", "unknown")
        content = notification.get("record", {}).get("text", "").lower()

        # Include mentions in the text for matching
        mentions = [
            mention.get("handle", "")
            for mention in notification.get("record", {}).get("facets", [])
        ]
        if mentions:
            content += " " + " ".join(mentions).lower()

        # Check for regex match with greeting patterns
        for pattern in greeting_patterns:
            regex = rf'\b{re.escape(pattern.lower())}\b'  # Match as a whole word
            if re.search(regex, content, re.IGNORECASE):
                # Generate a random reply
                front = random_line(hellos_front_path)
                back = random_line(hellos_back_path)
                reply = f"{front} {back}"
                
                # Send the reply
                if cid:  # Ensure CID is included for proper replies
                    post_reply(config["bsky"]["pds_url"], session, uri, cid, reply)
                    print(f"from {author_handle}: {content} \nMatch found: Pattern='{pattern}' in content='{content}' Replied")
                    PROCESSED_NOTIFICATIONS.add(unique_key)  # Mark as processed
                    save_processed_notifications(PROCESSED_NOTIFICATIONS)  # Save updated list
                return  # Exit after responding to the first match

def post_reply(pds_url, session, parent_uri, parent_cid, reply_text):
    """Post a reply to a notification."""
    try:
        headers = {"Authorization": "Bearer " + session["accessJwt"]}
        data = {
            "collection": "app.bsky.feed.post",
            "repo": session["did"],
            "record": {
                "$type": "app.bsky.feed.post",
                "text": reply_text,
                "reply": {
                    "root": {"uri": parent_uri, "cid": parent_cid},
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
    except requests.exceptions.RequestException as e:
        print(f"Error posting reply: {e}")

def load_lines(file_path):
    """Load lines from a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = [line.strip() for line in file if line.strip()]
            if not lines:
                print(f"Warning: File {file_path} is empty.")
            return lines
    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
        return []
    except Exception as e:
        print(f"Error loading file {file_path}: {e}")
        return []

def random_line(file_path):
    """Pick a random line from a file."""
    lines = load_lines(file_path)
    return random.choice(lines) if lines else "Hello!"

def main():
    """Main entry point for hello_reply module."""
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
    
    # Run the hello_reply functionality
    run(config, None)
