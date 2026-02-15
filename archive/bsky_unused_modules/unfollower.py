from atproto import Client
import os
from colorama import Fore, Style
import sys
sys.path.append("D:/jokes/bsky/modules")
from auth import get_valid_session

def fetch_paginated_data(client_method, actor):
    """Fetch paginated data (followers or following)."""
    data = []
    cursor = None
    while True:
        response = client_method(actor=actor, cursor=cursor)
        if hasattr(response, 'followers'):
            data.extend(response.followers)  # For followers
        elif hasattr(response, 'follows'):
            data.extend(response.follows)  # For follows
        cursor = getattr(response, 'cursor', None)
        if not cursor:
            break
    return data

def unfollow_users():
    # Configuration parameters
    config = {
        "bsky": {
            "pds_url": "https://bsky.social",  # Update if different
            "handle": "docatcdi.com",  # Your username
            "app_password": "your_password_here",  # Replace with your actual app password
        },
        "paths": {
            "keys_file": "D:/jokes/bsky/keys.json"  # Adjust path as needed
        }
    }

    # List of usernames to ignore
    ignorable_usernames = ["theonion"]

    # Use your authentication module
    session = get_valid_session(
        config["bsky"]["pds_url"],
        config["bsky"]["handle"],
        config["bsky"]["app_password"],
        config["paths"]["keys_file"],
    )

    if not session:
        print(f"{Fore.RED}Error: Unable to authenticate with BlueSky.{Style.RESET_ALL}")
        return

    client = Client()

    try:
        print(f"{Fore.YELLOW}Logging in to BlueSky...{Style.RESET_ALL}")
        client.set_session(session)
        print(f"{Fore.GREEN}Successfully authenticated with BlueSky.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Authentication failed: {e}{Style.RESET_ALL}")
        return

    try:
        user_did = client.me['did']
        print(f"{Fore.YELLOW}Fetching followers and following for user: {config['bsky']['handle']}{Style.RESET_ALL}")

        # Fetch followers and following
        followers = fetch_paginated_data(client.get_followers, user_did)
        following = fetch_paginated_data(client.get_follows, user_did)

        # Extract follower DIDs
        follower_dids = {follower.did for follower in followers}
        # Extract following DIDs and URIs
        following_map = {follow.did: follow.viewer.following for follow in following}

        # Map usernames to DIDs for ignorable accounts
        ignorable_dids = set()
        for ignorable_username in ignorable_usernames:
            try:
                profile = client.get_profile(ignorable_username)
                ignorable_dids.add(profile['did'])
                print(f"{Fore.GREEN}Resolved username {ignorable_username} to DID {profile['did']}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}Failed to resolve username {ignorable_username}: {e}{Style.RESET_ALL}")

        # Identify users to unfollow (proof-of-concept: limit output to 10 users)
        to_unfollow = [
            did for did, uri in following_map.items()
            if did not in follower_dids and did not in ignorable_dids
        ]
        print(f"{Fore.RED}Found {len(to_unfollow)} users to potentially unfollow (excluding ignorable accounts).{Style.RESET_ALL}")

        for i, did in enumerate(to_unfollow[:10], start=1):  # Limit to the first 10 users
            print(f"{Fore.YELLOW}({i}/10) Would unfollow DID: {did}{Style.RESET_ALL}")

        print(f"{Fore.GREEN}Proof of concept completed. No users were actually unfollowed.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}An unexpected error occurred: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    unfollow_users()
