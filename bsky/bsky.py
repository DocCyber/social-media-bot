import os
import requests
import json
import csv
from datetime import datetime

# Directory for corrupted lines file
corrupted_lines_file = r"d:\jokes\corrupted_lines.txt"

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
    print("Attempting to refresh the session...")
    try:
        resp = requests.post(
            f"{pds_url}/xrpc/com.atproto.server.refreshSession",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        resp.raise_for_status()
        print("Session refreshed successfully.")
        return resp.json()
    except requests.exceptions.RequestException as e:
        log_corrupted_line("BlueSky Refresh", "N/A", str(e))
        return None

def bsky_login_session(pds_url: str, handle: str, password: str) -> dict:
    """Authenticate with BlueSky Social using createSession."""
    print("Attempting to log in to BlueSky...")
    try:
        resp = requests.post(
            f"{pds_url}/xrpc/com.atproto.server.createSession",
            json={"identifier": handle, "password": password},
        )
        resp.raise_for_status()
        print("Login successful.")
        return resp.json()
    except requests.exceptions.RequestException as e:
        log_corrupted_line("BlueSky Login", "N/A", str(e))
        return None

def manage_session(pds_url: str, keys_file: str) -> dict:
    """
    Manage BlueSky session by attempting to refresh first,
    falling back to createSession if needed.
    """
    keys = load_keys(keys_file)
    session = None

    # Check for an existing refresh token
    if "bsky" in keys and "refreshJwt" in keys["bsky"]:
        session = refresh_session(pds_url, keys["bsky"]["refreshJwt"])

    # If refreshing fails, create a new session
    if not session:
        print("Falling back to creating a new session.")
        if "bsky" in keys and "handle" in keys["bsky"] and "app_password" in keys["bsky"]:
            session = bsky_login_session(pds_url, keys["bsky"]["handle"], keys["bsky"]["app_password"])
        else:
            print("Credentials missing in keys.json. Exiting.")
            exit(1)

    # Save the new session details
    if session:
        keys["bsky"]["accessJwt"] = session["accessJwt"]
        keys["bsky"]["refreshJwt"] = session["refreshJwt"]
        save_keys(keys_file, keys)

    return session

def create_post(pds_url: str, session: dict, text: str):
    """Create a simple text post with hashtag facets."""
    import re

    # Create hashtag and link facets for BlueSky
    facets = []
    hashtag_pattern = r'#\w+'
    url_pattern = r'https?://\S+'

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

    # Add link facets so URLs become clickable across clients
    for match in re.finditer(url_pattern, text):
        start_pos = match.start()
        end_pos = match.end()
        url_text = match.group()

        facets.append({
            "index": {
                "byteStart": start_pos,
                "byteEnd": end_pos
            },
            "features": [{
                "$type": "app.bsky.richtext.facet#link",
                "uri": url_text
            }]
        })

    post_data = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": datetime.utcnow().isoformat() + 'Z',  # UTC time with Zulu Time Zone
    }

    # Add facets if any hashtags/links were found
    if facets:
        post_data["facets"] = facets
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
        log_corrupted_line("BlueSky Post", "N/A", str(e))
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

def main():
    # Calculate the base directory (jokes directory)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Update file paths
    keys_file = os.path.join(base_dir, 'keys.json')
    index_file = os.path.join(base_dir, 'index.json')
    jokes_file = os.path.join(base_dir, 'jokes.csv')

    # Read credentials and manage session
    pds_url = "https://bsky.social"
    session = manage_session(pds_url, keys_file)
    if not session:
        print("Unable to establish a session. Exiting.")
        return

    # Read the current index from index.json
    with open(index_file, 'r') as file:
        index_data = json.load(file)
    joke_index = index_data['bsky']

    # Load the joke from jokes.csv with error handling
    encodings = ['utf-8', 'latin-1', 'windows-1252']
    text = None
    for encoding in encodings:
        try:
            with open(jokes_file, 'r', encoding=encoding) as file:
                reader = csv.reader(file)
                for i, joke in enumerate(reader):
                    if i == joke_index:
                        # Check if row is empty or has no content
                        if len(joke) == 0 or not joke[0].strip():
                            print(f"Empty row at index {joke_index}, skipping...")
                            text = ""  # Mark as empty to skip
                        else:
                            text = joke[0]
                        break
            if text is not None:
                break  # Successfully read the joke (or found empty), exit the loop
        except UnicodeDecodeError as e:
            log_corrupted_line(jokes_file, f"Encoding error: {encoding}", str(e))
        except Exception as e:
            log_corrupted_line(jokes_file, "Unknown line", str(e))
            return

    if text is None:
        print("Failed to load the joke with all attempted encodings.")
        # Update index to skip this joke
        total_jokes = 5400
        update_index(index_file, 'bsky', total_jokes)
        return

    # If text is empty, skip this joke
    if not text or not text.strip():
        print(f"Skipping empty joke at index {joke_index}")
        total_jokes = 5400
        update_index(index_file, 'bsky', total_jokes)
        return

    # Create the post on BlueSky
    try:
        print(f"Attempting to post joke #{joke_index}: {repr(text)}")
        print(f"Text length: {len(text) if text else 0}")
        
        # Check text length before posting (BlueSky limit is 300 chars)
        if len(text) > 300:
            print(f"Text too long ({len(text)} chars). Skipping joke #{joke_index}")
            # Update index to skip this joke
            total_jokes = 5400
            update_index(index_file, 'bsky', total_jokes)
            return
        
        post_response = create_post(pds_url, session, text)
        print("Post created:", post_response)
    except Exception as e:
        print(f"Failed to create post: {e}")
        # If posting fails, skip this joke by updating the index
        print(f"Skipping joke #{joke_index} due to error")
        total_jokes = 5400
        update_index(index_file, 'bsky', total_jokes)
        return

    # Update the joke index in index.json
    total_jokes = 5400  # Update with the total number of jokes in the csv
    update_index(index_file, 'bsky', total_jokes)

def post_docafterdark():
    """Post DocAfterDark content to BlueSky at 22:04 with #DocAfterDark hashtag."""
    current_time = datetime.now()
    try:
        print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] Posting DocAfterDark to BlueSky...")

        # Calculate the base directory (jokes directory)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Update file paths
        keys_file = os.path.join(base_dir, 'keys.json')
        index_file = os.path.join(base_dir, 'index.json')
        docafterdark_file = os.path.join(base_dir, 'DocAfterDark.csv')

        # Read credentials and manage session
        pds_url = "https://bsky.social"
        session = manage_session(pds_url, keys_file)
        if not session:
            print("Unable to establish a session. Exiting.")
            return

        # Read the current index from index.json
        with open(index_file, 'r') as file:
            index_data = json.load(file)

        # Use separate counter for bsky docafterdark
        if 'bsky_docafterdark' not in index_data:
            index_data['bsky_docafterdark'] = 0

        docafterdark_index = index_data['bsky_docafterdark']

        # Load the content from DocAfterDark.csv with error handling
        encodings = ['utf-8', 'latin-1', 'windows-1252']
        text = None
        total_lines = 0

        for encoding in encodings:
            try:
                with open(docafterdark_file, 'r', encoding=encoding) as file:
                    reader = csv.reader(file)
                    jokes = list(reader)
                    total_lines = len(jokes)

                    if docafterdark_index < len(jokes) and len(jokes[docafterdark_index]) > 0:
                        text = jokes[docafterdark_index][0]
                        break
            except UnicodeDecodeError as e:
                log_corrupted_line(docafterdark_file, f"Encoding error: {encoding}", str(e))
            except Exception as e:
                log_corrupted_line(docafterdark_file, "Unknown line", str(e))
                return

        if text is None:
            print("Failed to load the DocAfterDark content with all attempted encodings.")
            return

        # Add #DocAfterDark hashtag
        text_with_hashtag = text + "\n\n#DocAfterDark"

        # Check text length before posting (BlueSky limit is 300 chars)
        if len(text_with_hashtag) > 300:
            print(f"Text too long ({len(text_with_hashtag)} chars). Skipping DocAfterDark #{docafterdark_index}")
            # Update index to skip this content
            index_data['bsky_docafterdark'] = (docafterdark_index + 1) % total_lines
            with open(index_file, 'w') as file:
                json.dump(index_data, file, indent=4)
            return

        post_response = create_post(pds_url, session, text_with_hashtag)
        print("DocAfterDark post created:", post_response)

        # Update the DocAfterDark index in index.json
        index_data['bsky_docafterdark'] = (docafterdark_index + 1) % total_lines
        with open(index_file, 'w') as file:
            json.dump(index_data, file, indent=4)

        print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] DocAfterDark BlueSky post completed")

    except Exception as e:
        print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] Error in DocAfterDark BlueSky post: {e}")

if __name__ == "__main__":
    main()
