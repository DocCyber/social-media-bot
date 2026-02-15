import os
import requests
import json
from datetime import datetime, timezone

def bsky_login_session(pds_url: str, handle: str, password: str) -> dict:
    """ Authenticate with BlueSky Social """
    try:
        resp = requests.post(
            pds_url + "/xrpc/com.atproto.server.createSession",
            json={"identifier": handle, "password": password},
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"Error during BlueSky login: {e}")
        raise

def create_post(pds_url: str, session: dict, text: str):
    """ Create a simple text post with hashtag facets """
    import re

    # Create hashtag facets for BlueSky
    facets = []
    hashtag_pattern = r'#\w+'

    for match in re.finditer(hashtag_pattern, text):
        start_pos = match.start()
        end_pos = match.end()
        hashtag_text = match.group()[1:]  # Remove the # symbol

        facets.append({
            "index": {
                "byteStart": start_pos,
                "byteEnd": end_pos
            },
            "features": [{
                "$type": "app.bsky.richtext.facet#tag",
                "tag": hashtag_text
            }]
        })

    post_data = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),  # UTC time with Zulu Time Zone
    }

    # Add facets if any hashtags were found
    if facets:
        post_data["facets"] = facets
    try:
        resp = requests.post(
            pds_url + "/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": "Bearer " + session["accessJwt"]},
            json={
                "repo": session["did"],
                "collection": "app.bsky.feed.post",
                "record": post_data,
            },
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"Error during BlueSky post creation: {e}")
        raise

def get_current_profile(pds_url: str, session: dict):
    """Get the current user profile."""
    try:
        resp = requests.get(
            pds_url + "/xrpc/com.atproto.repo.getRecord",
            headers={"Authorization": "Bearer " + session["accessJwt"]},
            params={
                "repo": session["did"],
                "collection": "app.bsky.actor.profile",
                "rkey": "self"
            }
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting current profile: {e}")
        return None

def update_profile_with_pinned_post(pds_url: str, session: dict, post_uri: str, post_cid: str):
    """Update user profile to pin a specific post using official method."""
    try:
        # First, get current profile
        current_profile = get_current_profile(pds_url, session)
        if not current_profile:
            print("Could not retrieve current profile for pinning")
            return False
            
        profile_record = current_profile.get("value", {})
        
        # Add or update the pinnedPost field
        profile_record["pinnedPost"] = {
            "uri": post_uri,
            "cid": post_cid
        }
        
        # Update the profile record
        resp = requests.post(
            pds_url + "/xrpc/com.atproto.repo.putRecord",
            headers={"Authorization": "Bearer " + session["accessJwt"]},
            json={
                "repo": session["did"],
                "collection": "app.bsky.actor.profile",
                "rkey": "self",
                "record": profile_record
            }
        )
        resp.raise_for_status()
        print(f"Successfully pinned post: {post_uri}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error pinning post via profile update: {e}")
        return False

def find_todays_best_thing_post(pds_url: str, session: dict, target_hashtag: str = "#BestThingOfTheDay"):
    """Find today's best thing post to pin."""
    try:
        resp = requests.get(
            pds_url + "/xrpc/app.bsky.feed.getAuthorFeed",
            headers={"Authorization": "Bearer " + session["accessJwt"]},
            params={
                "actor": session["did"],
                "limit": 10
            }
        )
        resp.raise_for_status()
        feed = resp.json()
        
        today = datetime.now(timezone.utc).date()
        
        for item in feed.get("feed", []):
            post = item.get("post", {})
            record = post.get("record", {})
            post_text = record.get("text", "")
            created_at = record.get("createdAt", "")
            
            # Check if it's today's post with the right hashtag
            try:
                post_date = datetime.fromisoformat(created_at.rstrip("Z")).date()
                if post_date == today and target_hashtag.lower() in post_text.lower():
                    return post.get("uri"), post.get("cid")
            except ValueError:
                continue
                
        return None, None
    except requests.exceptions.RequestException as e:
        print(f"Error finding today's post: {e}")
        return None, None

def main():
    # Define the fixed question text to post daily at midnight
    text = "What's the best thing that happened to you today?\n\n#BestThingOfTheDay"
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Starting BlueSky best thing posting with pinning...")

    # File path for credentials
    base_dir = os.path.dirname(os.path.abspath(__file__))
    keys_file = os.path.join(base_dir, 'keys.json')

    try:
        # Read credentials from keys.json
        with open(keys_file, 'r') as file:
            credentials = json.load(file)

        # BlueSky posting using existing session management
        pds_url = "https://bsky.social"

        # Use existing session management from bsky module
        import sys
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.append(current_dir)

        try:
            from bsky import bsky
            session = bsky.manage_session(pds_url, keys_file)
            if not session:
                raise Exception("Could not establish session")
        except Exception as e:
            print(f"[{timestamp}] Error getting session: {e}")
            return
        post_response = create_post(pds_url, session, text)
        print(f"[{timestamp}] Midnight question post created:", post_response.get("uri", "No URI"))
        
        # Extract post details for pinning
        post_uri = post_response.get("uri")
        post_cid = post_response.get("cid")
        
        if post_uri and post_cid:
            print(f"[{timestamp}] Attempting to pin the new post...")
            pinning_success = update_profile_with_pinned_post(pds_url, session, post_uri, post_cid)
            if pinning_success:
                print(f"[{timestamp}] Successfully pinned today's best thing post!")
            else:
                print(f"[{timestamp}] Failed to pin post, but post was created successfully")
        else:
            print(f"[{timestamp}] Post created but missing URI/CID for pinning")
            
    except FileNotFoundError:
        print(f"[{timestamp}] Error: keys.json not found at {keys_file}")
    except KeyError as e:
        print(f"[{timestamp}] Error: Missing key in credentials: {e}")
    except Exception as e:
        print(f"[{timestamp}] Error in BlueSky best thing posting: {e}")

if __name__ == "__main__":
    main()