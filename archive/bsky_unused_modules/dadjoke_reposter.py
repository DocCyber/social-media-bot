import os
import json
import requests
from datetime import datetime, timedelta, timezone
import random

# Try to import langdetect, fallback to basic filtering if not available
try:
    from langdetect import detect, DetectorFactory
    from langdetect.lang_detect_exception import LangDetectException
    DetectorFactory.seed = 0  # Ensure consistent results across runs
    HAS_LANGDETECT = True
except ImportError:
    HAS_LANGDETECT = False
    print("langdetect not available, using basic text filtering")
PARENT_DIR = os.path.abspath(os.path.join(os.getcwd(), ".."))

# Paths for configuration and session files
CONFIG_FILE = os.path.join(PARENT_DIR, "config.json")
SESSION_FILE = os.path.join(PARENT_DIR, "session.json")
LOG_FILE = "dadjoke_log.json"

def load_file(file_path):
    """Utility function to load JSON data from a file."""
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return json.load(file)
    return {}

def save_file(file_path, data):
    """Utility function to save JSON data to a file."""
    with open(file_path, "w") as file:
        json.dump(data, file)

def refresh_session(config):
    """Use the centralized auth system."""
    try:
        import auth
        return auth.run(config)
    except ImportError as e:
        print(f"Auth module not available ({e}), using fallback session")
        return load_file(SESSION_FILE)

def find_random_dadjoke(config, session):
    """Find a random #dadjoke post and filter for English posts."""
    try:
        # Handle both session formats - direct accessJwt or nested in bsky key
        access_token = session.get('accessJwt') or session.get('bsky', {}).get('accessJwt')
        if not access_token:
            print("No access token found in session")
            return None
            
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"q": "#dadjoke", "limit": 50}
        resp = requests.get(
            f"{config['bsky']['pds_url']}/xrpc/app.bsky.feed.searchPosts",
            headers=headers,
            params=params
        )
        resp.raise_for_status()
        posts = resp.json().get("posts", [])

        # Filter posts for English content
        good_posts = []
        for post in posts:
            try:
                text = post["record"]["text"]

                # Basic quality check: must have some text content
                if len(text.strip()) < 10:
                    continue

                # Use language detection if available, otherwise basic checks
                if HAS_LANGDETECT:
                    if detect(text) == "en":
                        good_posts.append(post)
                else:
                    # Basic English detection: check for common English words/patterns
                    text_lower = text.lower()
                    if any(word in text_lower for word in ['the', 'and', 'a', 'to', 'of', 'is', 'why', 'what', 'how']):
                        good_posts.append(post)

            except Exception:
                continue

        return random.choice(good_posts) if good_posts else None
    except requests.exceptions.RequestException as e:
        print(f"Error searching for dad jokes: {e}")
        return None
    
def post_repost(pds_url, session, post_uri, post_cid):
    """Repost a notification."""
    headers = {"Authorization": f"Bearer {session.get('accessJwt') or session.get('bsky', {}).get('accessJwt')}"}
    data = {
        "collection": "app.bsky.feed.repost",
        "repo": session["did"],
        "record": {
            "$type": "app.bsky.feed.repost",
            "subject": {"uri": post_uri, "cid": post_cid},
            "createdAt": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }
    }
    try:
        resp = requests.post(
            f"{pds_url}/xrpc/com.atproto.repo.createRecord",
            headers=headers,
            json=data,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"Error creating repost: {e}")
        raise

def follow_user(pds_url, session, user_did):
    """Follow a user."""
    headers = {"Authorization": f"Bearer {session.get('accessJwt') or session.get('bsky', {}).get('accessJwt')}"}
    data = {
        "collection": "app.bsky.graph.follow",
        "repo": session["did"],
        "record": {
            "$type": "app.bsky.graph.follow",
            "subject": user_did,
            "createdAt": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }
    }
    try:
        resp = requests.post(
            f"{pds_url}/xrpc/com.atproto.repo.createRecord",
            headers=headers,
            json=data,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"Error following user: {e}")
        raise

def run(config, session):
    """Main function to find and repost #dadjoke."""
    print("dadjoke_reposter started.")
    log_data = load_file(LOG_FILE)
    reposted_posts = set(log_data.get("reposted_posts", []))
    reposted_users = log_data.get("reposted_users", {})

    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
    reposted_users = {
        user: time for user, time in reposted_users.items()
        if datetime.fromisoformat(time).replace(tzinfo=timezone.utc) > cutoff_time
    }
    print(f"{len(reposted_users)} users are still restricted from reposting.")

    post = find_random_dadjoke(config, session)
    if not post:
        print("No suitable posts found.")
        return

    post_uri = post["uri"]
    post_cid = post["cid"]
    author_did = post["author"]["did"]
    author_handle = post["author"]["handle"]

    if post_uri in reposted_posts or author_did in reposted_users:
        print(f"Skipping - already interacted with post or user {author_handle}")
        return

    try:
        # Try to repost
        post_repost(config["bsky"]["pds_url"], session, post_uri, post_cid)
        print(f"Repost successful for post by {author_handle}")
        reposted_posts.add(post_uri)

        # Try to follow
        follow_user(config["bsky"]["pds_url"], session, author_did)
        print(f"Follow successful for {author_handle}")
        reposted_users[author_did] = datetime.now(timezone.utc).isoformat()

    except Exception as e:
        print(f"Error during repost/follow for {author_handle}: {e}")
        # Still mark as attempted to avoid retries
        reposted_posts.add(post_uri)
        reposted_users[author_did] = datetime.now(timezone.utc).isoformat()

    log_data["reposted_posts"] = list(reposted_posts)
    log_data["reposted_users"] = reposted_users
    save_file(LOG_FILE, log_data)
    print("dadjoke_reposter finished.")

if __name__ == "__main__":
    config = load_file(CONFIG_FILE)
    session = refresh_session(config)
    run(config, session)
