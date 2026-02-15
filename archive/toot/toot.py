import os
import csv
import json
import logging
from datetime import datetime
from mastodon import Mastodon, MastodonAPIError

# Set up logging for errors
logging.basicConfig(level=logging.ERROR)

# Directory for corrupted lines file
corrupted_lines_file = r"d:\jokes\corrupted_lines.txt"

def log_corrupted_line(filename, line, error):
    with open(corrupted_lines_file, 'a') as f:
        f.write(f"File: {filename}, Error Line: {line}, Error: {error}\n")

# Load keys from the JSON file
with open('keys.json', 'r') as f:
    keys = json.load(f)

# Assign Mastodon keys
mastodon_client_id = keys['mastodon']['client_id']
mastodon_client_secret = keys['mastodon']['client_secret']
mastodon_access_token = keys['mastodon']['access_token']
mastodon_api_base_url = keys['mastodon']['api_base_url']

# Initialize Mastodon API
mastodon = Mastodon(
    client_id=mastodon_client_id,
    client_secret=mastodon_client_secret,
    access_token=mastodon_access_token,
    api_base_url=mastodon_api_base_url,
)

def toot_item(filename, index_key, add_text=None):
    # Calculate the base directory (jokes directory)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Load indices
    indices = load_indices()

    # Path for the CSV file
    jokes_file = os.path.join(base_dir, filename)

    # Load the joke with error handling for multiple encodings
    encodings = ['utf-8', 'latin-1', 'windows-1252']
    text = None
    for encoding in encodings:
        try:
            with open(jokes_file, 'r', encoding=encoding) as f:
                reader = csv.reader(f)
                jokes = list(reader)
                break  # Successfully read the file, exit the loop
        except UnicodeDecodeError as e:
            log_corrupted_line(jokes_file, f"Encoding error: {encoding}", e)
        except Exception as e:
            log_corrupted_line(jokes_file, "Unknown line", e)
            return

    if not jokes:
        print("Failed to load jokes with all attempted encodings.")
        return

    # Get the joke at the current index
    index = indices.get(index_key, 0)
    if index >= len(jokes):
        index = 0  # Reset the index if it exceeds the list
    joke = jokes[index][0]

    # Add additional text if provided
    if add_text:
        joke += "\n\n" + add_text 

    # Post the joke
    try:
        if joke.strip():  # Ensure the joke is not empty or just whitespace
            mastodon.status_post(joke)
            print("Successfully sent toot at {}:\n{}\n--------------------".format(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), joke))
        else:
            raise ValueError("Joke text is blank")
    except (MastodonAPIError, ValueError) as e:
        log_corrupted_line(jokes_file, index, str(e))
        print('Error:', e)
    finally:
        # Update the index and save it
        indices[index_key] = index + 1
        save_indices(indices)

# Load indices from a JSON file
def load_indices():
    with open('index.json', 'r') as f:
        return json.load(f)

# Save indices to a JSON file
def save_indices(indices):
    with open('index.json', 'w') as f:
        json.dump(indices, f, indent=4)

if __name__ == "__main__":
    toot_item('jokes.csv', 'mastodon')
