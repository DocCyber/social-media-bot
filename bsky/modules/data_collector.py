import sys
import os
import json
import logging
import requests
from datetime import datetime, timezone
from atproto import Client
from colorama import Fore, Style
import jwt

class FollowDataCollector:
    def __init__(self, config):
        self.config = config
        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        self.unreciprocated_file = os.path.join(self.data_dir, "unreciprocated_following.json")
        self.collection_log = os.path.join(self.data_dir, "data_collection.log")
        self.keys_file = config["paths"]["keys_file"]

    def log_message(self, message, level="INFO"):
        """Log messages with timestamps"""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)

        with open(self.collection_log, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")

    def load_keys(self):
        """Load keys from the JSON file."""
        if os.path.exists(self.keys_file):
            try:
                with open(self.keys_file, "r") as file:
                    return json.load(file)
            except Exception as e:
                self.log_message(f"Error loading keys from {self.keys_file}: {e}", "ERROR")
        return {}

    def save_keys(self, keys):
        """Save keys back to the JSON file."""
        try:
            with open(self.keys_file, "w") as file:
                json.dump(keys, file, indent=4)
        except Exception as e:
            self.log_message(f"Error saving keys to {self.keys_file}: {e}", "ERROR")

    def is_token_valid(self, access_token):
        """Check if the JWT is still valid."""
        try:
            payload = jwt.decode(access_token, options={"verify_signature": False})
            expiry = datetime.fromtimestamp(payload["exp"])
            if expiry > datetime.utcnow():
                return True
        except Exception as e:
            self.log_message(f"Error checking token validity: {e}", "ERROR")
        return False

    def get_authenticated_client(self):
        """Get an authenticated atproto Client, reusing tokens if valid."""
        keys = self.load_keys()
        client = Client()

        # Try to use existing valid access token
        if "bsky" in keys and "accessJwt" in keys.get("bsky", {}):
            if self.is_token_valid(keys["bsky"]["accessJwt"]):
                self.log_message("Using valid access token")
                # Create a session dict for the client
                client.login(
                    login=self.config["bsky"]["handle"],
                    password=self.config["bsky"]["app_password"]
                )
                return client

        # Try to refresh using refresh token
        if "bsky" in keys and "refreshJwt" in keys.get("bsky", {}):
            try:
                self.log_message("Attempting to refresh session")
                resp = requests.post(
                    f"{self.config['bsky']['pds_url']}/xrpc/com.atproto.server.refreshSession",
                    headers={"Authorization": f"Bearer {keys['bsky']['refreshJwt']}"},
                )
                resp.raise_for_status()
                refreshed = resp.json()

                # Save new tokens
                keys["bsky"]["accessJwt"] = refreshed["accessJwt"]
                keys["bsky"]["refreshJwt"] = refreshed["refreshJwt"]
                self.save_keys(keys)

                self.log_message("Session refreshed successfully")
                # Login with credentials (atproto Client doesn't support direct token injection easily)
                client.login(
                    login=self.config["bsky"]["handle"],
                    password=self.config["bsky"]["app_password"]
                )
                return client
            except Exception as e:
                self.log_message(f"Token refresh failed: {e}", "ERROR")

        # Create new session by logging in
        self.log_message("Creating new session via login")
        try:
            client.login(
                login=self.config["bsky"]["handle"],
                password=self.config["bsky"]["app_password"]
            )

            # Save the tokens for future use
            if hasattr(client, '_session'):
                keys["bsky"] = {
                    "accessJwt": client._session.access_jwt,
                    "refreshJwt": client._session.refresh_jwt
                }
                self.save_keys(keys)

            self.log_message("Login successful")
            return client
        except Exception as e:
            self.log_message(f"Login failed: {e}", "ERROR")
            return None

    def fetch_paginated_data(self, client, method_name, actor):
        """Fetch all paginated data (followers or following)"""
        data = []
        cursor = None
        page_count = 0

        while True:
            try:
                page_count += 1
                if method_name == "followers":
                    response = client.get_followers(actor=actor, cursor=cursor)
                    page_data = response.followers if hasattr(response, 'followers') else []
                elif method_name == "follows":
                    response = client.get_follows(actor=actor, cursor=cursor)
                    page_data = response.follows if hasattr(response, 'follows') else []
                else:
                    self.log_message(f"Unknown method: {method_name}", "ERROR")
                    break

                data.extend(page_data)
                cursor = getattr(response, 'cursor', None)

                self.log_message(f"Fetched page {page_count} of {method_name}: {len(page_data)} entries, total: {len(data)}")

                if not cursor:
                    break

            except Exception as e:
                self.log_message(f"Error fetching {method_name} page {page_count}: {e}", "ERROR")
                break

        self.log_message(f"Completed {method_name} fetch: {len(data)} total entries")
        return data

    def collect_fresh_data(self):
        """Collect fresh following and follower data from BlueSky"""
        self.log_message("Starting fresh data collection")

        # Get authenticated client
        client = self.get_authenticated_client()

        if not client:
            self.log_message("Authentication failed", "ERROR")
            return False

        try:
            user_did = client.me.did
            self.log_message(f"Authenticated as {self.config['bsky']['handle']} ({user_did})")

            # Fetch followers
            self.log_message("Fetching followers...")
            followers = self.fetch_paginated_data(client, "followers", user_did)

            # Fetch following
            self.log_message("Fetching following...")
            following = self.fetch_paginated_data(client, "follows", user_did)

            # Create sets for comparison
            follower_dids = {follower.did for follower in followers}
            following_data = {follow.did: follow for follow in following}

            self.log_message(f"Data collected - Followers: {len(follower_dids)}, Following: {len(following_data)}")

            # Find unreciprocated follows
            unreciprocated = []
            for did, follow_data in following_data.items():
                if did not in follower_dids:
                    # Get the follow creation date from the follow record
                    followed_at = getattr(follow_data, 'createdAt', '')
                    if not followed_at:
                        # If no creation date, use current time as fallback
                        followed_at = datetime.now(timezone.utc).isoformat()

                    unreciprocated.append({
                        "did": did,
                        "handle": getattr(follow_data, 'handle', ''),
                        "displayName": getattr(follow_data, 'displayName', ''),
                        "followedAt": followed_at,
                        "notFollowingSince": datetime.now(timezone.utc).isoformat(),
                        "avatar": getattr(follow_data, 'avatar', ''),
                        "description": getattr(follow_data, 'description', ''),
                        "daysNotFollowingBack": 0  # Will be calculated in unfollower
                    })

            self.log_message(f"Found {len(unreciprocated)} unreciprocated follows")

            # Save the data
            with open(self.unreciprocated_file, "w", encoding="utf-8") as f:
                json.dump({
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "stats": {
                        "total_followers": len(follower_dids),
                        "total_following": len(following_data),
                        "unreciprocated_count": len(unreciprocated),
                        "reciprocal_count": len(follower_dids.intersection(following_data.keys()))
                    },
                    "unreciprocated": unreciprocated
                }, f, indent=2, ensure_ascii=False)

            self.log_message(f"Saved {len(unreciprocated)} unreciprocated follows to {self.unreciprocated_file}")
            self.log_message("Fresh data collection completed successfully")

            return True

        except Exception as e:
            self.log_message(f"Error during data collection: {e}", "ERROR")
            return False

def main():
    """Main entry point for data collection"""
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

    collector = FollowDataCollector(config)
    success = collector.collect_fresh_data()

    if success:
        print(f"{Fore.GREEN}Data collection completed successfully{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}Data collection failed{Style.RESET_ALL}")

if __name__ == "__main__":
    main()