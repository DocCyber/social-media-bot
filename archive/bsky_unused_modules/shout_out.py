import os
import json
import requests
import csv
import sys
from datetime import datetime, timedelta, timezone

# Add the parent directory to the Python path for standalone execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from modules import auth

# File paths
CONFIG_FILE = r"d:\jokes\bsky\config.json"
SESSION_FILE = r"d:\jokes\bsky\session.json"
USERNAMES_FILE = r"d:\jokes\bsky\data\usernames.txt"
DEBITS_FILE = r"d:\jokes\bsky\data\debits.csv"

# Function to load JSON
def load_json(file_path):
    """Load JSON from a file."""
    with open(file_path, "r") as file:
        return json.load(file)

# Function to save JSON
def save_json(file_path, data):
    """Save JSON to a file."""
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)

# Function to read usernames from file
def read_usernames(file_path):
    """Read usernames from a text file."""
    with open(file_path, "r") as file:
        return [line.strip() for line in file if line.strip()]

# Determine the part of the day
def get_part_of_day():
    """Return the part of the day based on the current time."""
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        return "morning"
    elif 12 <= current_hour < 17:
        return "afternoon"
    elif 17 <= current_hour < 22:
        return "evening"
    else:
        return "night"

# Check if data hasn't changed
def is_data_unchanged(debits_file, usernames):
    """Check if the same usernames were used in the last run."""
    if not os.path.exists(debits_file):
        return False  # No debits file means data hasn't been recorded yet

    with open(debits_file, "r") as file:
        reader = csv.DictReader(file)
        recent_users = [row["User"] for row in reader]

    # Compare the top 5 usernames to the recent debits
    return set(usernames) <= set(recent_users)

# Check if it's too soon to run again
def is_too_soon(debits_file, usernames):
    """Check if the script ran within the last 3 hours with the same users."""
    if not os.path.exists(debits_file):
        return False  # If no debits file exists, it's not too soon

    with open(debits_file, "r") as file:
        reader = csv.DictReader(file)
        recent_entries = [row for row in reader if row["User"] in usernames]

    # Find the most recent timestamp for the given usernames
    if not recent_entries:
        return False  # No matching entries, it's not too soon

    recent_timestamps = [
        datetime.fromisoformat(row["Timestamp"].replace("Z", "")) for row in recent_entries
    ]
    most_recent = max(recent_timestamps)

    # Check if the most recent timestamp is within the last 3 hours
    return datetime.utcnow() - most_recent < timedelta(hours=3)

# Function to log debits
def log_debits(debits_file, usernames):
    """Log debits to the debits file."""
    debits = []
    if os.path.exists(debits_file):
        with open(debits_file, "r") as file:
            reader = csv.reader(file)
            next(reader, None)  # Skip header
            debits = list(reader)
    timestamp = datetime.utcnow().isoformat() + "Z"
    debits += [[username, 25, timestamp] for username in usernames]
    with open(debits_file, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["User", "Points", "Timestamp"])  # Ensure header is written
        writer.writerows(debits)

# Function to create the shoutout text
def create_shoutout_text(usernames):
    """Create the text for the shoutout post."""
    day_of_week = datetime.now().strftime("%A")
    part_of_day = get_part_of_day()
    return (
        f"Hey everybody, it's {day_of_week} {part_of_day} I just wanted to give a big thanks to:\n\n"
        + "\n".join(usernames[:5])
        + "\n\nfor hanging out with me for the silliness, you are all what keeps me here, and I Love You All!"
    )

# Function to create a BlueSky post
def create_post(pds_url, session, text):
    """Create a simple text post on BlueSky."""
    try:
        headers = {"Authorization": f"Bearer {session['accessJwt']}"}
        data = {
            "collection": "app.bsky.feed.post",
            "repo": session["did"],
            "record": {
                "$type": "app.bsky.feed.post",
                "text": text,
                "createdAt": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
        }
        resp = requests.post(
            f"{pds_url}/xrpc/com.atproto.repo.createRecord",
            headers=headers,
            json=data,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"Error creating post: {e}")
        raise

# Main run function for module integration
def run(config, session):
    """Main function to create shoutout posts."""
    module_name = __name__.split('.')[-1]
    print(f"{module_name} started")

    try:
        # Authenticate or use the provided session
        if session is None:
            session = auth.run(config)
            if not session:
                print(f"{module_name} failed: Authentication error")
                return

        # Read usernames and prepare the post
        usernames_file = os.path.join(config["paths"]["data_dir"], "usernames.txt")
        debits_file = os.path.join(config["paths"]["data_dir"], "debits.csv")

        usernames = read_usernames(usernames_file)
        if len(usernames) < 5:
            print("Error: Less than 5 usernames found in usernames.txt.")
            print(f"{module_name} finished")
            return

        # Check if data hasn't changed
        if is_data_unchanged(debits_file, usernames[:5]):
            shoutout_text = create_shoutout_text(usernames[:5])
            print("***********DATA DIDN'T CHANGE STOP****************")
            print("Output would have been:\n")
            print(shoutout_text)
            print("\nDebits for the top 5 users would have been made.")
            print("***********DID NOT EXECUTE THIS RUN****************")
            print(f"{module_name} finished")
            return

        # Check if it's too soon to run again
        if is_too_soon(debits_file, usernames[:5]):
            shoutout_text = create_shoutout_text(usernames[:5])
            print("***********TOO SOON TO RUN AGAIN****************")
            print("Output would have been:\n")
            print(shoutout_text)
            print("\nDebits for the top 5 users would have been made.")
            print("***********DID NOT EXECUTE THIS RUN****************")
            print(f"{module_name} finished")
            return

        # Create the post
        shoutout_text = create_shoutout_text(usernames[:5])
        try:
            response = create_post(config["bsky"]["pds_url"], session, shoutout_text)
            print("Shoutout post created:", response)
        except Exception as e:
            print("Error creating shoutout post:", e)
            print(f"{module_name} finished")
            return

        # Log debits
        log_debits(debits_file, usernames[:5])
        print("Shoutout text:\n")
        print(shoutout_text)
        print("\nDebits logged for the top 5 users.")

    except Exception as e:
        print(f"Error in {module_name}: {e}")

    print(f"{module_name} finished")

def main():
    """Main entry point for shout_out module."""
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

    # Run the shout_out functionality
    run(config, None)

if __name__ == "__main__":
    main()
