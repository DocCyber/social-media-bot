import os
import requests
import json
import csv
from datetime import datetime, timezone

# Directory for corrupted lines file
corrupted_lines_file = r"d:\jokes\bsky_taunt\corrupted_lines.txt"

def log_corrupted_line(filename, line, error):
    """Log corrupted lines and errors to a file."""
    with open(corrupted_lines_file, 'a') as f:
        f.write(f"File: {filename}, Error Line: {line}, Error: {error}\n")

def load_keys(file_path):
    """Load keys from the JSON file."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as file:
                return json.load(file)
        except Exception as e:
            log_corrupted_line("Keys File", "N/A", str(e))
    return {}

def save_keys(file_path, keys):
    """Save keys back to the JSON file."""
    try:
        with open(file_path, "w") as file:
            json.dump(keys, file, indent=4)
    except Exception as e:
        log_corrupted_line("Keys File", "N/A", str(e))

def refresh_session(pds_url: str, refresh_token: str) -> dict:
    """Attempt to refresh the BlueSky session."""
    print("Attempting to refresh the taunt bot session...")
    try:
        resp = requests.post(
            f"{pds_url}/xrpc/com.atproto.server.refreshSession",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        resp.raise_for_status()
        print("Taunt bot session refreshed successfully.")
        return resp.json()
    except requests.exceptions.RequestException as e:
        log_corrupted_line("BlueSky Taunt Refresh", "N/A", str(e))
        return None

def bsky_login_session(pds_url: str, handle: str, password: str) -> dict:
    """Authenticate with BlueSky Social using createSession."""
    print("Attempting to log in to BlueSky for taunt bot...")
    try:
        resp = requests.post(
            f"{pds_url}/xrpc/com.atproto.server.createSession",
            json={"identifier": handle, "password": password},
        )
        resp.raise_for_status()
        print("Taunt bot login successful.")
        return resp.json()
    except requests.exceptions.RequestException as e:
        log_corrupted_line("BlueSky Taunt Login", "N/A", str(e))
        return None

def manage_session(pds_url: str, keys_file: str) -> dict:
    """
    Manage BlueSky taunt bot session by attempting to refresh first,
    falling back to createSession if needed.
    """
    keys = load_keys(keys_file)
    session = None

    # Check for an existing refresh token
    if "bsky_taunt" in keys and "refreshJwt" in keys["bsky_taunt"]:
        session = refresh_session(pds_url, keys["bsky_taunt"]["refreshJwt"])

    # If refreshing fails, create a new session
    if not session:
        print("Falling back to creating a new taunt bot session.")
        if "bsky_taunt" in keys and "handle" in keys["bsky_taunt"] and "app_password" in keys["bsky_taunt"]:
            session = bsky_login_session(pds_url, keys["bsky_taunt"]["handle"], keys["bsky_taunt"]["app_password"])
        else:
            print("Taunt bot credentials missing in taunt_keys.json. Exiting.")
            exit(1)

    # Save the new session details
    if session:
        keys["bsky_taunt"]["accessJwt"] = session["accessJwt"]
        keys["bsky_taunt"]["refreshJwt"] = session["refreshJwt"]
        save_keys(keys_file, keys)

    return session

def create_post(pds_url: str, session: dict, text: str):
    """Create a simple text post."""
    post_data = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),  # UTC time with Zulu Time Zone
    }
    try:
        resp = requests.post(
            f"{pds_url}/xrpc/com.atproto.repo.createRecord",
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
        log_corrupted_line("BlueSky Taunt Post", "N/A", str(e))
        raise

def update_index(json_file, index_key, max_value):
    """Update the index in the JSON file."""
    with open(json_file, 'r+') as file:
        data = json.load(file)
        data[index_key] = (data[index_key] + 1) % max_value
        file.seek(0)
        json.dump(data, file, indent=4)
        file.truncate()
    return data[index_key]

def read_taunt(taunt_file, taunt_index):
    """Read a taunt from a quoted CSV file."""
    encodings = ['utf-8', 'latin-1', 'windows-1252']
    for encoding in encodings:
        try:
            with open(taunt_file, 'r', encoding=encoding, newline='') as file:
                reader = csv.reader(file, delimiter=',', quotechar='"')
                for i, taunt in enumerate(reader):
                    if i == taunt_index:
                        return taunt[0]
        except UnicodeDecodeError as e:
            log_corrupted_line(taunt_file, f"Encoding error: {encoding}", str(e))
        except Exception as e:
            log_corrupted_line(taunt_file, "Unknown line", str(e))
            return None
    return None

def write_taunts(taunt_file, taunts):
    """Write taunts back to a quoted CSV file."""
    try:
        with open(taunt_file, 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
            for taunt in taunts:
                writer.writerow([taunt])
    except Exception as e:
        log_corrupted_line(taunt_file, "Write error", str(e))

def main():
    # Calculate the taunt bot directory
    taunt_dir = os.path.dirname(os.path.abspath(__file__))

    # Update file paths for taunt bot
    keys_file = os.path.join(taunt_dir, 'taunt_keys.json')
    index_file = os.path.join(taunt_dir, 'taunt_index.json')
    taunt_file = os.path.join(taunt_dir, 'taunt.csv')

    # Read credentials and manage session
    pds_url = "https://bsky.social"
    session = manage_session(pds_url, keys_file)
    if not session:
        print("Unable to establish a taunt bot session. Exiting.")
        return

    # Read the current index from taunt_index.json
    with open(index_file, 'r') as file:
        index_data = json.load(file)
    taunt_index = index_data['bsky_taunt']

    # Load the taunt from taunt.csv with quotes
    text = read_taunt(taunt_file, taunt_index)

    if text is None:
        print("Failed to load the taunt with all attempted encodings.")
        return

    # Create the post on BlueSky
    try:
        post_response = create_post(pds_url, session, text)
        print("Taunt post created:", post_response)
    except Exception as e:
        print(f"Failed to create taunt post: {e}")
        return

    # Update the taunt index in taunt_index.json
    total_taunts = 1000  # Update with the total number of taunts in the csv
    update_index(index_file, 'bsky_taunt', total_taunts)

if __name__ == "__main__":
    main()
