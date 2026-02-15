import csv
from collections import defaultdict
import os
from datetime import datetime, timedelta, timezone

# Define weights for different interaction types
INTERACTION_WEIGHTS = {
    "reply": 3,
    "quote": 3,
    "repost": 2,
    "mention": 2,
    "like": 1,
    "follow": 1,
}

def create_file_if_not_exists(file_path, headers):
    """Create a CSV file with headers if it doesn't exist."""
    if not os.path.exists(file_path):
        with open(file_path, "w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()

def load_interactions(file_path, days=7):
    """Load interactions from the CSV file, filtering by the past X days."""
    interactions = []
    try:
        with open(file_path, "r") as file:
            reader = csv.DictReader(file)
            # Make the cutoff date offset-aware (UTC)
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).replace(tzinfo=timezone.utc)
            for row in reader:
                # Parse ISO timestamp (handles fractional seconds)
                interaction_date = datetime.fromisoformat(row["Timestamp"].replace("Z", "+00:00"))
                if interaction_date >= cutoff_date:
                    interactions.append(row)
    except FileNotFoundError:
        print(f"{file_path} not found. Starting with an empty interaction list.")
    except Exception as e:
        print(f"Error loading interactions: {e}")
    return interactions

def calculate_user_scores(interactions):
    """Calculate scores for each user based on interaction weights."""
    user_scores = defaultdict(int)
    for interaction in interactions:
        user = interaction["User"]
        interaction_type = interaction["Type"]
        weight = INTERACTION_WEIGHTS.get(interaction_type, 1)
        user_scores[user] += weight
    return user_scores

def apply_debits(user_scores, debit_file, days=7):
    """Subtract points from user scores based on the debit file."""
    try:
        # Ensure the debit file exists and has headers
        create_file_if_not_exists(debit_file, ["User", "Points", "Timestamp"])
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).replace(tzinfo=timezone.utc)
        with open(debit_file, "r") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames is None or not any(reader):
                print(f"{debit_file} is empty. No debits applied.")
                return
            for row in reader:
                user = row["User"]
                debit_date = datetime.fromisoformat(row["Timestamp"].replace("Z", "+00:00"))
                if debit_date >= cutoff_date:
                    debit_points = int(row["Points"])
                    user_scores[user] -= debit_points
    except FileNotFoundError:
        print(f"{debit_file} not found. No debits applied.")
    except Exception as e:
        print(f"Error applying debits: {e}")

def save_user_scores(user_scores, output_file):
    """Save user scores to a CSV file."""
    try:
        with open(output_file, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["User", "Score"])
            for user, score in sorted(user_scores.items(), key=lambda x: x[1], reverse=True):
                writer.writerow([user, score])
    except Exception as e:
        print(f"Error saving user scores: {e}")

def save_usernames_to_text(user_scores, text_file):
    """Save usernames to a plain text file in order of interactivity with '@' prefix."""
    try:
        with open(text_file, "w") as file:
            for user, _ in sorted(user_scores.items(), key=lambda x: x[1], reverse=True):
                file.write(f"@{user}\n")  # Add '@' before the username
    except Exception as e:
        print(f"Error saving usernames to text file: {e}")

def main():
    # File paths
    base_dir = "d:\\jokes\\bsky\\data"
    interactions_file = os.path.join(base_dir, "interactions.csv")
    debit_file = os.path.join(base_dir, "debits.csv")  # New debit file
    user_scores_csv = os.path.join(base_dir, "user_scores.csv")
    usernames_txt = os.path.join(base_dir, "usernames.txt")

    # Ensure the base directory exists
    os.makedirs(base_dir, exist_ok=True)

    # Ensure interactions.csv and debits.csv exist
    create_file_if_not_exists(interactions_file, ["URI", "User", "Type", "Timestamp"])
    create_file_if_not_exists(debit_file, ["User", "Points", "Timestamp"])

    # Load interactions
    interactions = load_interactions(interactions_file, days=7)
    if not interactions:
        print("No interactions found.")
        return

    # Calculate user scores
    user_scores = calculate_user_scores(interactions)

    # Apply debits
    apply_debits(user_scores, debit_file, days=7)

    # Save scores to CSV
    save_user_scores(user_scores, user_scores_csv)
    print(f"User scores saved to {user_scores_csv}")

    # Save usernames to text file
    save_usernames_to_text(user_scores, usernames_txt)
    print(f"Usernames saved to {usernames_txt}")

if __name__ == "__main__":
    main()
