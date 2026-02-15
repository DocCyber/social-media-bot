import os
import json
import requests
from datetime import datetime, timedelta, timezone

# File to persist processed reposts
REPOSTS_FILE = os.path.join(os.path.dirname(__file__), "../reposted_posts.json")

# Load processed reposts from file
def load_processed_reposts():
    """Load processed reposts from a file."""
    if os.path.exists(REPOSTS_FILE):
        try:
            with open(REPOSTS_FILE, "r") as file:
                return set(json.load(file))
        except Exception as e:
            print(f"Error loading processed reposts: {e}")
    return set()

def save_processed_reposts(reposted_set):
    """Save processed reposts to a file."""
    try:
        with open(REPOSTS_FILE, "w") as file:
            json.dump(list(reposted_set), file)
    except Exception as e:
        print(f"Error saving processed reposts: {e}")

# Main module function
def run(config, session):
    module_name = __name__.split('.')[-1]  # Extract module name
    print(f"{module_name} started")

    try:
        # Simulate session creation if not provided
        if session is None:
            from modules import auth
            session = auth.run(config)
            if not session:
                print(f"{module_name} failed: Authentication error")
                return

        # Fetch notifications from the past 5 minutes
        last_check_time = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(minutes=5)
        notifications = get_notifications(
            config["bsky"]["pds_url"],
            session,
            since_time=last_check_time
        )

        if notifications and "notifications" in notifications:
            process_reposts(
                config,
                session,
                notifications["notifications"]
            )
    except Exception as e:
        print(f"Error in {module_name}: {e}")

    print(f"{module_name} finished")

def get_notifications(pds_url, session, since_time=None, limit=100):
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

def process_reposts(config, session, notifications):
    """Check for posts with #baddadjoke and repost them."""
    module_name = __name__.split('.')[-1]  # Extract module name for logging
    reposted_posts = load_processed_reposts()

    repost_limit = config.get("max_reposts_per_run", 1)
    reposted_count = 0

    for notification in notifications:
        # Process only mentions or replies
        if notification["reason"] in ["mention", "reply"]:
            uri = notification["uri"]
            cid = notification.get("cid")  # Include CID for unique identification
            unique_key = f"{uri}:{cid}"  # Combine URI and CID for uniqueness

            if unique_key in reposted_posts:
                print(f"Skipping already processed notification: {unique_key}")
                continue  # Skip if already reposted

            content = notification["record"]["text"].lower()

            # Check for hashtag #baddadjoke
            if "#baddadjoke" in content:
                try:
                    post_repost(config["bsky"]["pds_url"], session, uri, cid)
                    print(f"Successfully reposted: {uri}")
                    reposted_posts.add(unique_key)  # Mark as reposted
                    save_processed_reposts(reposted_posts)  # Save updated repost list
                    reposted_count += 1

                    if reposted_count >= repost_limit:
                        break  # Stop after reaching the limit
                except Exception as e:
                    print(f"Error reposting {uri}: {e}")

def post_repost(pds_url, session, post_uri, post_cid):
    """Repost a notification."""
    try:
        headers = {"Authorization": "Bearer " + session["accessJwt"]}
        data = {
            "collection": "app.bsky.feed.repost",
            "repo": session["did"],
            "record": {
                "$type": "app.bsky.feed.repost",
                "subject": {
                    "uri": post_uri,
                    "cid": post_cid
                },
                "createdAt": datetime.utcnow().isoformat() + "Z"
            }
        }
        resp = requests.post(
            f"{pds_url}/xrpc/com.atproto.repo.createRecord",
            headers=headers,
            json=data,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error posting repost: {e}")
