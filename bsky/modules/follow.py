import sys
import os
import requests
from datetime import datetime, timedelta, timezone
import json

# Add the parent directory to the Python path for standalone execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from modules import auth

# Path to store the list of recently followed users
RECENT_FOLLOWS_FILE = "recent_follows.json"

# Load the recent follows from file or initialize an empty list
def load_recent_follows():
    if os.path.exists(RECENT_FOLLOWS_FILE):
        with open(RECENT_FOLLOWS_FILE, "r") as file:
            return json.load(file)
    return []

# Save the recent follows to file
def save_recent_follows(recent_follows):
    with open(RECENT_FOLLOWS_FILE, "w") as file:
        json.dump(recent_follows, file)

def run(config, session=None):
    print("follow started")

    try:
        # Authenticate or use the provided session
        if session is None:
            print("No session provided. Attempting to authenticate.")
            session = auth.run(config)
            if not session:
                print("follow failed: Authentication error")
                return

        # Extract access token
        access_token = session.get("accessJwt")
        if not access_token:
            print("Access token missing in follow.")
            return

        # Fetch notifications from the past 5 minutes
        since_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        notifications = get_notifications(
            config["bsky"]["pds_url"],
            access_token,
            since_time=since_time
        )

        # Load the list of recently followed users
        recent_follows = load_recent_follows()

        # Process follow notifications
        if notifications and "notifications" in notifications:
            follow_back_users(
                config["bsky"]["pds_url"],
                access_token,
                session["did"],
                notifications["notifications"],
                recent_follows
            )

        # Save the updated list of recently followed users
        save_recent_follows(recent_follows)

        print("follow finished")
    except Exception as e:
        print(f"Error in follow: {e}")

def get_notifications(pds_url, access_token, since_time=None, limit=50):
    """Fetch notifications from Bluesky."""
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"limit": limit}
        if since_time:
            params["since"] = since_time.isoformat() + "Z"  # Only fetch new notifications
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

def follow_back_users(pds_url, access_token, did, notifications, recent_follows):
    """Follow back users from follow notifications."""
    for notification in notifications:
        if notification["reason"] == "follow":
            user_did = notification["author"]["did"]

            # Check if already recently followed
            if user_did in recent_follows:
                print(f"Skipping user {user_did}: already recently followed.")
                continue

            # Check if already following
            if not is_already_following(pds_url, access_token, did, user_did):
                follow_user(pds_url, access_token, did, user_did)

                # Update the recent follows list
                recent_follows.append(user_did)

                # Keep the recent follows list to a maximum of 1000 entries
                if len(recent_follows) > 1000:
                    recent_follows.pop(0)
            else:
                print(f"Already following user: {user_did}")

def is_already_following(pds_url, access_token, did, user_did):
    """Check if the user is already being followed."""
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"actor": user_did}
        resp = requests.get(
            f"{pds_url}/xrpc/app.bsky.graph.getFollows",
            headers=headers,
            params=params
        )
        resp.raise_for_status()
        follows = resp.json().get("follows", [])
        return any(f["did"] == user_did for f in follows)
    except requests.exceptions.RequestException as e:
        print(f"Error checking follow status for {user_did}: {e}")
        return False

def follow_user(pds_url, access_token, did, user_did):
    """Send a follow request to a specific user."""
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        data = {
            "collection": "app.bsky.graph.follow",
            "repo": did,
            "record": {
                "$type": "app.bsky.graph.follow",
                "subject": user_did,
                "createdAt": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
        }
        resp = requests.post(
            f"{pds_url}/xrpc/com.atproto.repo.createRecord",
            headers=headers,
            json=data,
        )
        resp.raise_for_status()
        print(f"Followed back: {user_did}")
    except requests.exceptions.RequestException as e:
        print(f"Error following user {user_did}: {e}")

def main():
    """Main entry point for follow module."""
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
    
    # Run the follow functionality
    run(config, None)

if __name__ == "__main__":
    # Load config for testing
    with open("../config.json", "r") as config_file:
        config = json.load(config_file)

    # Run the module independently
    run(config)
