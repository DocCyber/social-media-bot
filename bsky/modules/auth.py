import requests
import logging
import json
import os
from datetime import datetime, timedelta
import jwt  # Install with `pip install pyjwt`

def run(config):
    module_name = __name__.split('.')[-1]
    print(f"{module_name} started")

    session = get_valid_session(
        config["bsky"]["pds_url"],
        config["bsky"]["handle"],
        config["bsky"]["app_password"],
        config["paths"]["keys_file"]
    )

    if session:
        print(f"{module_name} finished")
        return session
    else:
        print(f"{module_name} failed")
        return None

def get_valid_session(pds_url, handle, password, keys_file):
    keys = load_keys(keys_file)

    # Check if accessJwt is valid
    if "accessJwt" in keys.get("bsky", {}):
        if is_token_valid(keys["bsky"]["accessJwt"]):
            logging.info("Using valid access token.")
            return keys

    # Refresh session if possible
    if "refreshJwt" in keys.get("bsky", {}):
        refreshed = refresh_session(pds_url, keys["bsky"]["refreshJwt"])
        if refreshed:
            keys["bsky"]["accessJwt"] = refreshed["accessJwt"]
            keys["bsky"]["refreshJwt"] = refreshed["refreshJwt"]
            save_keys(keys_file, keys)  # Save updated tokens
            return refreshed

    # Otherwise, create a new session
    return bsky_login_session(pds_url, handle, password, keys_file)

def is_token_valid(access_token):
    """Check if the JWT is still valid."""
    try:
        payload = jwt.decode(access_token, options={"verify_signature": False})
        expiry = datetime.fromtimestamp(payload["exp"])
        if expiry > datetime.utcnow():
            return True
    except Exception as e:
        logging.error(f"Error checking token validity: {e}")
    return False

def bsky_login_session(pds_url, handle, password, keys_file):
    """Create a new session."""
    keys = load_keys(keys_file)
    try:
        logging.info("Creating a new session.")
        resp = requests.post(
            f"{pds_url}/xrpc/com.atproto.server.createSession",
            json={"identifier": handle, "password": password},
        )
        resp.raise_for_status()
        session = resp.json()
        keys["bsky"] = {
            "accessJwt": session["accessJwt"],
            "refreshJwt": session["refreshJwt"]
        }
        save_keys(keys_file, keys)
        logging.info("New session created successfully.")
        return keys
    except requests.exceptions.RequestException as e:
        logging.error(f"Error creating session: {e}")
        return {}

def refresh_session(pds_url, refresh_token):
    """Refresh the session using the refresh token."""
    try:
        resp = requests.post(
            f"{pds_url}/xrpc/com.atproto.server.refreshSession",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        resp.raise_for_status()
        logging.info("Session refreshed successfully.")
        return resp.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error refreshing session: {e}")
        return {}

def load_keys(file_path):
    """Load keys from the JSON file."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as file:
                return json.load(file)
        except Exception as e:
            logging.error(f"Error loading keys from {file_path}: {e}")
    return {}

def save_keys(file_path, keys):
    """Save keys back to the JSON file."""
    try:
        with open(file_path, "w") as file:
            json.dump(keys, file, indent=4)
    except Exception as e:
        logging.error(f"Error saving keys to {file_path}: {e}")
