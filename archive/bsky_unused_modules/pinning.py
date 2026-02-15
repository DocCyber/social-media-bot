import sys
import os
import json
from datetime import datetime, timezone, timedelta
import requests

# Add the parent directory to the Python path for standalone execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from modules import auth

PIN_STATUS_FILE = os.path.join(os.path.dirname(__file__), "..", "pin_status.json")  # Path to store pin status

def run(config, session=None):
    print("pinning started")

    try:
        # Authenticate or use the provided session
        if session is None:
            print("No session provided. Attempting to authenticate.")
            session = auth.run(config)
            if not session:
                print("pinning failed: Authentication error")
                return

        # Extract access token
        access_token = session.get("accessJwt")
        if not access_token:
            print("Access token missing in pinning.")
            return

        # Check if already pinned today
        current_time = datetime.now(timezone.utc)
        if is_already_pinned_today(current_time):
            print("Post already pinned today. Skipping.")
            return

        # Find and pin today's post
        target_text = "What's the best thing that happened to you today?"
        post_uri = find_todays_post(
            config["bsky"]["pds_url"],
            access_token,
            session["did"],
            target_text,
            current_time
        )

        if post_uri:
            pin_post(config["bsky"]["pds_url"], access_token, post_uri)
            update_pin_status(current_time)
        else:
            print("No matching post found to pin.")

        print("pinning finished")
    except Exception as e:
        print(f"Error in pinning: {e}")

def is_text_match(post_text, target_text):
    """Check if the target hashtag exists in the post text."""
    target_hashtag = "#bestthingoftheday"  # Ensure case-insensitive match
    contains_hashtag = target_hashtag in post_text.lower()
    print(f"Debug: Checking if '{target_hashtag}' is in '{post_text.lower()}': {contains_hashtag}")
    return contains_hashtag

def is_already_pinned_today(current_time):
    """Check if the post has already been pinned today."""
    if not os.path.exists(PIN_STATUS_FILE):
        return False  # No pin status file, assume not pinned

    try:
        with open(PIN_STATUS_FILE, "r") as file:
            status = json.load(file)
            last_pinned_date = datetime.fromisoformat(status.get("last_pinned", "").rstrip("Z")).replace(tzinfo=timezone.utc)
            return last_pinned_date.date() == current_time.date()
    except (ValueError, KeyError) as e:
        print(f"Error reading or parsing pin status: {e}")
        return False  # Assume not pinned if the status is invalid

def update_pin_status(current_time):
    """Update the pin status to mark today's post as pinned."""
    try:
        with open(PIN_STATUS_FILE, "w") as file:
            json.dump({"last_pinned": current_time.isoformat()}, file, indent=4)
        print("Pin status updated.")
    except Exception as e:
        print(f"Error updating pin status: {e}")

def find_todays_post(pds_url, access_token, did, target_text, current_time, limit=50):
    """Find the most recent post with specific content created today."""
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"actor": did, "limit": limit}
        resp = requests.get(
            f"{pds_url}/xrpc/app.bsky.feed.getAuthorFeed",
            headers=headers,
            params=params,
        )
        resp.raise_for_status()
        posts = resp.json().get("feed", [])

        print("Debug: Retrieved posts:")
        for post in posts:
            post_record = post.get("post", {}).get("record", {})
            post_text = post_record.get("text", "")
            post_created_at = post_record.get("createdAt", "")

            # Debugging output for time comparison
            print(f"  Post: {post_text} (created at {post_created_at})")
            print(f"Checking post created at {post_created_at} against current time {current_time}")

            # Check for today's post by hashtag
            if is_text_match(post_text, target_text):  # Only match the hashtag
                print(f"Found matching post: {post['post']['uri']}")
                return post["post"]["uri"]

        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching posts: {e}")
        return None

def is_today(post_created_at, current_time):
    """Check if a post's timestamp is from today's UTC date."""
    try:
        post_time = datetime.fromisoformat(post_created_at.rstrip("Z")).replace(tzinfo=timezone.utc)
        is_today = post_time.date() == current_time.date()
        print(f"Debug: Comparing post time {post_time.date()} with current date {current_time.date()}: {is_today}")
        return is_today
    except ValueError as e:
        print(f"Error parsing post timestamp: {e}")
        return False

def pin_post(pds_url, access_token, post_uri):
    """Pin a post by its URI."""
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        data = {
            "$type": "app.bsky.feed.pin",
            "uri": post_uri,
        }
        resp = requests.post(
            f"{pds_url}/xrpc/app.bsky.feed.pin",
            headers=headers,
            json=data,
        )
        resp.raise_for_status()
        print(f"Successfully pinned post: {post_uri}")
    except requests.exceptions.RequestException as e:
        print(f"Error pinning post {post_uri}: {e}")

def main():
    """Main entry point for pinning module."""
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

    # Run the pinning functionality
    run(config, None)

if __name__ == "__main__":
    main()