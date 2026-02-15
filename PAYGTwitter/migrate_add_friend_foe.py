#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-time migration script to add friend_foe column to existing user_data.csv
"""

import csv
import shutil
import sys
from datetime import datetime

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

USER_DATA_CSV = 'user_data.csv'
BACKUP_CSV = f'user_data_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

def migrate():
    """Add friend_foe column to existing CSV."""

    # Create backup first
    try:
        shutil.copy2(USER_DATA_CSV, BACKUP_CSV)
        print(f"[OK] Created backup: {BACKUP_CSV}")
    except Exception as e:
        print(f"Error creating backup: {e}")
        return False

    # Read existing data
    users = []
    try:
        with open(USER_DATA_CSV, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            old_fieldnames = reader.fieldnames

            print(f"Found {len(old_fieldnames)} columns in existing CSV")

            # Check if friend_foe already exists
            if 'friend_foe' in old_fieldnames:
                print("friend_foe column already exists - no migration needed!")
                return True

            for row in reader:
                # Add the new field with empty value
                row['friend_foe'] = ''
                users.append(row)

        print(f"[OK] Loaded {len(users)} user records")
    except FileNotFoundError:
        print(f"Error: {USER_DATA_CSV} not found")
        return False
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return False

    # Define new fieldnames (same order as in TwitterAutoReply.py)
    new_fieldnames = [
        'username', 'user_id', 'name', 'created_at', 'description', 'location',
        'url', 'profile_image_url', 'verified', 'verified_type', 'protected',
        'followers_count', 'following_count', 'tweet_count', 'listed_count', 'like_count',
        'pinned_tweet_id', 'last_updated', 'times_checked', 'times_replied', 'times_skipped',
        'times_no_tweet', 'friend_foe'
    ]

    # Write updated CSV
    try:
        with open(USER_DATA_CSV, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=new_fieldnames)
            writer.writeheader()

            for user in users:
                # Ensure all fields exist (fill with empty string if missing)
                row_data = {field: user.get(field, '') for field in new_fieldnames}
                writer.writerow(row_data)

        print(f"[OK] Updated {USER_DATA_CSV} with friend_foe column")
        print(f"[OK] All {len(users)} records migrated successfully")
        return True
    except Exception as e:
        print(f"Error writing CSV: {e}")
        print(f"Your data is safe in: {BACKUP_CSV}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Migrating user_data.csv to add friend_foe column")
    print("=" * 60)
    print()

    success = migrate()

    print()
    if success:
        print("=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Verify user_data.csv has friend_foe column")
        print("2. Use: python manage_friend_foe.py list")
        print("3. Mark accounts: python manage_friend_foe.py set @username friend")
    else:
        print("=" * 60)
        print("Migration failed - see errors above")
        print("=" * 60)
