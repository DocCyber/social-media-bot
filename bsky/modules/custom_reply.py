# Custom Pattern Matching Legend:
# Symbol   Meaning
# *        Matches zero or more characters
# ?        Matches exactly one character
# [abc]    Matches one character in set
# [a-z]    Matches any letter in range
# \\       Escapes the next character (literal)

import sys
import os
import csv
import random
import requests
import re
import json
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from modules import auth

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROCESSED_FILE = os.path.join(SCRIPT_DIR, "processed_notifications.json")
REPLIED_USERS_FILE = os.path.join(SCRIPT_DIR, "last_replied_users.json")
REPLY_WINDOW = 3

def wildcard_to_regex(wildcard: str) -> str:
    wildcard = re.escape(wildcard)
    wildcard = wildcard.replace(r'\*', '.*')
    wildcard = wildcard.replace(r'\?', '.')
    return '^' + wildcard + '$'

def load_processed_notifications():
    print(f"Debug: Loading processed notifications from {PROCESSED_FILE}")
    if os.path.exists(PROCESSED_FILE):
        try:
            with open(PROCESSED_FILE, "r") as file:
                return set(json.load(file))
        except Exception as e:
            print(f"Error loading processed notifications: {e}")
    else:
        print("Debug: Processed notifications file not found, starting fresh.")
    return set()

def save_processed_notifications(processed_set):
    print(f"Debug: Saving processed notifications to {PROCESSED_FILE}")
    try:
        with open(PROCESSED_FILE, "w") as file:
            json.dump(list(processed_set), file)
    except Exception as e:
        print(f"Error saving processed notifications: {e}")

def load_last_replied_users():
    print(f"Debug: Loading last replied users from {REPLIED_USERS_FILE}")
    if os.path.exists(REPLIED_USERS_FILE):
        try:
            with open(REPLIED_USERS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading last replied users: {e}")
    else:
        print("Debug: Last replied users file not found. Creating new file.")
        save_last_replied_users([])
    return []

def save_last_replied_users(user_list):
    print(f"Debug: Saving last replied users to {REPLIED_USERS_FILE}")
    try:
        with open(REPLIED_USERS_FILE, "w") as f:
            json.dump(user_list[-100:], f)
    except Exception as e:
        print(f"Error saving last replied users: {e}")

PROCESSED_NOTIFICATIONS = load_processed_notifications()
LAST_RESPONSES = {}
LAST_REPLIED_USERS = load_last_replied_users()

def run(config, session=None):
    module_name = __name__.split('.')[-1]
    print(f"{module_name} started")

    try:
        if session is None:
            print("auth started")
            session = auth.run(config)
            print("auth finished")
            if not session:
                print(f"{module_name} failed: Authentication error")
                return

        last_check_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        print("Debug: Fetching notifications since", last_check_time.isoformat())
        notifications = get_notifications(
            config["bsky"]["pds_url"],
            session,
            since_time=last_check_time
        )

        if notifications and "notifications" in notifications:
            print("Debug: Notifications received:", len(notifications["notifications"]))
            process_custom_replies(config, session, notifications["notifications"])
        else:
            print("Debug: No notifications received.")

        print(f"{module_name} finished")
    except Exception as e:
        print(f"Error in {module_name}: {e}")

def get_notifications(pds_url, session, since_time=None, limit=50):
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

def process_custom_replies(config, session, notifications):
    replies_csv_path = os.path.join(config["paths"]["data_dir"], "replies.csv")
    print(f"Debug: Loading replies from {replies_csv_path}")
    reply_patterns = load_replies_csv(replies_csv_path)
    if not reply_patterns:
        print(f"Error: No valid patterns found in {replies_csv_path}. Exiting.")
        return

    global LAST_REPLIED_USERS

    for notification in notifications:
        if notification["reason"] in ["mention", "reply"]:
            uri = notification["uri"]
            cid = notification.get("cid")
            unique_key = f"{uri}:{cid}"

            if unique_key in PROCESSED_NOTIFICATIONS:
                print(f"Debug: Skipping already processed notification: {unique_key}")
                continue

            content = notification["record"]["text"].lower()
            author_handle = notification["author"]["handle"]
            print(f"Debug: Processing notification from {author_handle}")

            if author_handle in LAST_REPLIED_USERS:
                last_index = len(LAST_REPLIED_USERS) - 1 - LAST_REPLIED_USERS[::-1].index(author_handle)
                unique_others = set(LAST_REPLIED_USERS[last_index + 1:])
                if len(unique_others) < 2:
                    print(f"Debug: Skipping {author_handle} — not enough distinct replies since last time")
                    continue

            for wildcard_pattern, responses in reply_patterns.items():
                regex_pattern = wildcard_to_regex(wildcard_pattern.lower())
                if re.search(regex_pattern, content, re.IGNORECASE):
                    reply = random_unique_response(wildcard_pattern, responses)
                    print(f"Debug: Matched pattern '{wildcard_pattern}', replying with: {reply}")

                    # Extract reply info
                    reply_info = notification["record"].get("reply", {})

                    # Proper root-finding logic
                    if "root" in reply_info:
                        root_uri = reply_info["root"].get("uri", uri)
                        root_cid = reply_info["root"].get("cid", cid)
                    elif "parent" in reply_info:
                        root_uri = reply_info["parent"].get("uri", uri)
                        root_cid = reply_info["parent"].get("cid", cid)
                    else:
                        root_uri = uri
                        root_cid = cid

                    print(f"Debug: Root URI -> {root_uri}")
                    print(f"Debug: Parent URI -> {uri}")

                    post_reply(config["bsky"]["pds_url"], session, uri, cid, reply, root_uri=root_uri, root_cid=root_cid)

                    PROCESSED_NOTIFICATIONS.add(unique_key)
                    save_processed_notifications(PROCESSED_NOTIFICATIONS)

                    LAST_REPLIED_USERS.append(author_handle)
                    if len(LAST_REPLIED_USERS) > 100:
                        LAST_REPLIED_USERS.pop(0)
                    save_last_replied_users(LAST_REPLIED_USERS)
                    break

def post_reply(pds_url, session, parent_uri, parent_cid, reply_text, root_uri=None, root_cid=None):
    if not root_uri:
        root_uri = parent_uri
    if not root_cid:
        root_cid = parent_cid
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
        print(f"Debug: Posting reply payload: {data}")
        resp = requests.post(
            f"{pds_url}/xrpc/com.atproto.repo.createRecord",
            headers=headers,
            json=data,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error posting reply: {e}")

def load_replies_csv(file_path):
    patterns = {}
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) < 2 or not row[0].strip():
                    continue
                pattern = row[0].strip()
                responses = [resp.strip() for resp in row[1:] if resp.strip()]
                if responses:
                    patterns[pattern] = responses
        return patterns
    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
        return {}
    except Exception as e:
        print(f"Error loading CSV file {file_path}: {e}")
        return {}

def random_unique_response(pattern, responses):
    global LAST_RESPONSES
    last_response = LAST_RESPONSES.get(pattern)
    available_responses = [r for r in responses if r != last_response]
    if available_responses:
        reply = random.choice(available_responses)
        LAST_RESPONSES[pattern] = reply
        return reply
    else:
        return random.choice(responses)

def main():
    """Main entry point for custom_reply module."""
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
    
    # Run the custom_reply functionality
    run(config, None)

if __name__ == "__main__":
    with open("../config.json", "r") as config_file:
        config = json.load(config_file)
    run(config)
