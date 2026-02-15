import sys
import os
import csv
import requests
from datetime import datetime, timezone, timedelta

# Add the parent directory to the Python path for standalone execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from modules import auth

# Constant for the CSV file name
INTERACTIONS_CSV = "interactions.csv"

def run(config, session=None):
    print("notifications started")

    try:
        # Ensure the data_dir is properly defined
        data_dir = config["paths"].get("data_dir")
        if not data_dir:
            raise KeyError("'data_dir' is missing in the configuration paths.")

        # Path to the CSV file for storing notifications
        csv_file_path = os.path.join(data_dir, INTERACTIONS_CSV)

        # Authenticate or use the provided session
        if session is None:
            print("No session provided. Attempting to authenticate.")
            session = auth.run(config)
            if not session:
                print("Authentication failed in notifications.")
                return

        # Extract access token from session
        access_token = session.get("accessJwt")
        if not access_token:
            print("Access token missing in notifications.")
            return

        # Load processed notification URIs
        processed_uris = load_processed_uris(csv_file_path)

        # Fetch notifications from the past 5 minutes
        last_check_time = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(minutes=5)
        notifications = get_notifications(
            config["bsky"]["pds_url"],
            access_token,
            since_time=last_check_time
        )

        if notifications and "notifications" in notifications:
            print(f"Fetched {len(notifications['notifications'])} notifications.")

            # Summarize notifications and filter new ones
            summary = {}
            new_entries = []

            for notification in notifications["notifications"]:
                uri = notification.get("uri")
                reason = notification.get("reason", "unknown")

                # Skip already processed notifications
                if uri in processed_uris:
                    continue

                # Add to summary
                summary[reason] = summary.get(reason, 0) + 1

                # Add to new entries
                user = notification.get("author", {}).get("handle", "unknown")
                timestamp = notification.get("indexedAt", "unknown")
                did = notification.get("author", {}).get("did", "unknown")
                new_entries.append({
                    "URI": uri,
                    "User": user,
                    "Type": reason,
                    "Timestamp": timestamp,
                    "DID": did,
                })

                # Mark URI as processed
                processed_uris.add(uri)

            # Save new entries to CSV
            save_to_csv(csv_file_path, new_entries)

            # Print the summary
            for reason, count in summary.items():
                print(f"  - {reason}: {count}")
        else:
            print("No new notifications.")

        print("notifications finished")
    except Exception as e:
        print(f"Error in notifications: {e}")

def get_notifications(pds_url, access_token, since_time=None, limit=50):
    """Fetch notifications from Bluesky."""
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"limit": limit}
        current_time = datetime.utcnow().replace(tzinfo=timezone.utc)

        if since_time:
            params["since"] = since_time.isoformat() + "Z"  # Fetch only new notifications
            print(f"Debug: Checking notifications between since_time and current_time")
            print(f"Debug:   since_time = {params['since']}")
            print(f"Debug: current_time = {current_time.isoformat()}")

        resp = requests.get(
            f"{pds_url}/xrpc/app.bsky.notification.listNotifications",
            headers=headers,
            params=params
        )
        resp.raise_for_status()
        notifications = resp.json()

        # Filter notifications by the actual time stamp
        if "notifications" in notifications:
            filtered_notifications = []
            for notification in notifications["notifications"]:
                # Parse notification timestamp
                notif_time = datetime.fromisoformat(notification["indexedAt"].rstrip("Z")).replace(tzinfo=timezone.utc)
                if notif_time >= since_time:
                    filtered_notifications.append(notification)

            # Return filtered results
            notifications["notifications"] = filtered_notifications

        return notifications
    except requests.exceptions.RequestException as e:
        print(f"Error fetching notifications: {e}")
        return {}

def load_processed_uris(csv_file_path):
    """Load processed URIs from the CSV file."""
    processed_uris = set()
    if os.path.exists(csv_file_path):
        try:
            with open(csv_file_path, "r") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    processed_uris.add(row["URI"])
        except Exception as e:
            print(f"Error loading processed URIs: {e}")
    return processed_uris

def save_to_csv(csv_file_path, data):
    """Save new notification entries to the CSV file."""
    try:
        # Ensure the parent directory for the CSV file exists
        os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)

        file_exists = os.path.exists(csv_file_path)
        with open(csv_file_path, "a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["URI", "User", "Type", "Timestamp", "DID"])
            if not file_exists:
                writer.writeheader()  # Write header if the file doesn't exist
            writer.writerows(data)
    except Exception as e:
        print(f"Error saving to CSV: {e}")
