import sys
import os
from datetime import datetime, timedelta, timezone
import requests
import csv

# Add the parent directory to the Python path for standalone execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from modules import auth

LIKED_POSTS_FILE = "liked_posts.csv"

def run(config, session=None):
    print("reactions started")

    try:
        # Authenticate or use the provided session
        if session is None:
            print("No session provided. Attempting to authenticate.")
            session = auth.run(config)
            if not session:
                print("reactions failed: Authentication error")
                return

        # Extract access token
        access_token = session.get("accessJwt")
        if not access_token:
            print("Access token missing in reactions.")
            return

        # Fetch recent notifications (last 5 minutes)
        since_time = datetime.now(timezone.utc).replace(tzinfo=timezone.utc) - timedelta(minutes=5)
        notifications = get_notifications(
            config["bsky"]["pds_url"],
            access_token,
            since_time=since_time
        )

        # Process notifications and like replies/quotes
        if notifications and "notifications" in notifications:
            process_notifications(
                config["bsky"]["pds_url"],
                access_token,
                session["did"],  # Use DID for record creation
                notifications["notifications"],
                LIKED_POSTS_FILE
            )

        print("reactions finished")
    except Exception as e:
        print(f"Error in reactions: {e}")

def get_notifications(pds_url, access_token, since_time=None, limit=50):
    """Fetch notifications from Bluesky."""
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
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

def process_notifications(pds_url, access_token, did, notifications, liked_posts_file):
    """Process notifications to like replies and quotes."""
    liked_posts = load_liked_posts(liked_posts_file)

    for notification in notifications:
        reason = notification["reason"]
        target_uri = notification["uri"]

        # Skip if the post has already been liked
        if target_uri in liked_posts:
            print(f"Post {target_uri} already liked. Skipping...")
            continue

        if reason in ["reply", "quote"]:  # Handle both replies and quotes
            target_cid = notification["cid"]

            # Send the like
            like_target(pds_url, access_token, did, target_uri, target_cid)

            # Save the liked post to the CSV
            save_liked_post(liked_posts_file, target_uri)

    # Trim the CSV file to avoid excessive growth
    trim_csv_file(liked_posts_file)

def like_target(pds_url, access_token, did, target_uri, target_cid):
    """Send a 'like' to a specific target (reply or quote)."""
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        data = {
            "collection": "app.bsky.feed.like",
            "repo": did,
            "record": {
                "$type": "app.bsky.feed.like",
                "subject": {
                    "uri": target_uri,
                    "cid": target_cid,
                },
                "createdAt": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
        }
        resp = requests.post(
            f"{pds_url}/xrpc/com.atproto.repo.createRecord",
            headers=headers,
            json=data,
        )
        resp.raise_for_status()  # Raises an exception only if there's an error
    except requests.exceptions.RequestException as e:
        print(f"Error liking target {target_uri}: {e}")  # Logs errors only

def load_liked_posts(filename, max_age_hours=12):
    """Load liked posts from a CSV file and remove expired entries."""
    liked_posts = {}
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

    if not os.path.exists(filename):
        return liked_posts

    with open(filename, mode="r") as file:
        reader = csv.reader(file)
        for row in reader:
            uri, timestamp_str = row
            timestamp = datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)
            if timestamp > cutoff_time:
                liked_posts[uri] = timestamp

    # Overwrite the file with only valid (non-expired) entries
    with open(filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        for uri, timestamp in liked_posts.items():
            writer.writerow([uri, timestamp.isoformat()])

    return liked_posts

def save_liked_post(filename, uri):
    """Save a liked post's URI and timestamp to the CSV file."""
    with open(filename, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([uri, datetime.now(timezone.utc).isoformat()])

def trim_csv_file(filename, max_lines=500):
    """Trim the CSV file to keep only the most recent entries."""
    if not os.path.exists(filename):
        return

    with open(filename, mode="r") as file:
        rows = list(csv.reader(file))

    if len(rows) > max_lines:
        rows = rows[-max_lines:]  # Keep only the last `max_lines` entries

    with open(filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(rows)

def main():
    """Main entry point for reactions module."""
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
    
    # Run the reactions functionality
    run(config, None)

if __name__ == "__main__":
    import json

    # Load config for testing
    with open("../config.json", "r") as config_file:
        config = json.load(config_file)

    # Run the module independently
    run(config)
