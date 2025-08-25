import os
import sys
import requests
import json
import csv
import logging
from datetime import datetime
from requests_oauthlib import OAuth1
from image.image import generate_image

# Set up logging for errors
logging.basicConfig(level=logging.ERROR)

# Directory for corrupted lines file
corrupted_lines_file = r"d:\jokes\corrupted_lines.txt"

# Calculate the directory path of tweet.py
tweet_dir = os.path.dirname(os.path.abspath(__file__))

def log_corrupted_line(filename, line, error):
    with open(corrupted_lines_file, 'a') as f:
        f.write(f"File: {filename}, Error Line: {line}, Error: {error}\n")

def load_indices():
    index_filepath = os.path.join(tweet_dir, '..', 'index.json')
    with open(index_filepath, 'r') as f:
        return json.load(f)

def save_indices(indices):
    index_filepath = os.path.join(tweet_dir, '..', 'index.json')
    with open(index_filepath, 'w') as f:
        json.dump(indices, f)

def tweet_item(filename, index_key, add_text=None):
    indices = load_indices()

    # Adjust the path to point to the parent directory of tweet_dir
    jokes_filepath = os.path.join(tweet_dir, '..', filename)

    # Try different encodings to read the file
    encodings = ['utf-8', 'latin-1', 'cp1252']
    for encoding in encodings:
        try:
            with open(jokes_filepath, mode='r', encoding=encoding) as f:
                reader = csv.reader(f)
                jokes = list(reader)
                break  # Successfully read the file, exit the loop
        except UnicodeDecodeError as e:
            logging.error(f"UnicodeDecodeError with encoding {encoding}: {e}")
            # Log to corrupted_lines.txt with filename and error details
            log_corrupted_line(jokes_filepath, f"Encoding error: {encoding}", e)
        except Exception as e:
            logging.error(f"An error occurred with encoding {encoding}: {e}")
            log_corrupted_line(jokes_filepath, "Unknown line", e)
            return
    else:
        # If all encodings fail
        logging.error("Failed to read the jokes file with all attempted encodings.")
        return

    index = indices[index_key]
    if index >= len(jokes):
        indices[index_key] = 0
    joke = jokes[indices[index_key]][0]

    if add_text is not None:
        joke += "\n\n" + add_text

    image_path = generate_image(joke)
    print("Image saved at:", image_path)

    try:
        if joke.strip():
            data = json.dumps({"text": joke})
            resp = requests.post(url, headers=headers, data=data, auth=auth)
            logging.info("Response from Twitter: " + resp.text)  # Log Twitter's response

            response_data = json.loads(resp.text)
            if 'data' in response_data:
                tweet_id = response_data['data']['id']
                tweet_text = response_data['data']['text']
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logging.info('Successfully sent tweet at {}:\n{}\n{}Line: {}'.format(current_time, tweet_text, '-' * 20, index))
                indices[index_key] += 1
            else:
                logging.error("'data' key not found in the response")
                raise KeyError("'data' key not found in the response")
        else:
            logging.error("Joke text is blank")
            raise ValueError("Joke text is blank")
    except (KeyError, ValueError) as e:
        logging.error('Error: ' + str(e))
        indices[index_key] += 1
    except requests.exceptions.RequestException as e:
        logging.error('Network error: ' + str(e))
        indices[index_key] += 1

    save_indices(indices)

# Load keys from the JSON file
with open(os.path.join(tweet_dir, '../keys.json'), 'r') as f:
    keys = json.load(f)

# Assign Twitter keys
access_token = keys['twitter']['access_token']
access_token_secret = keys['twitter']['access_token_secret']
consumer_key = keys['twitter']['consumer_key']
consumer_secret = keys['twitter']['consumer_secret']
bearer_token = keys['twitter']['bearer_token']

# Set up OAuth1 authentication for Twitter API
auth = OAuth1(consumer_key, consumer_secret, access_token, access_token_secret)

# Twitter API URL and headers
url = "https://api.twitter.com/2/tweets"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer " + bearer_token
}
