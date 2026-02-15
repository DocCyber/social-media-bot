#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper script to manage friend/foe markers for Twitter accounts.

Usage:
    python manage_friend_foe.py list              # Show all marked accounts
    python manage_friend_foe.py set @username friend
    python manage_friend_foe.py set @username foe
    python manage_friend_foe.py clear @username   # Remove marker
"""

import sys
import csv

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

USER_DATA_CSV = 'user_data.csv'

def load_csv():
    """Load user data CSV."""
    users = {}
    try:
        with open(USER_DATA_CSV, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                users[row['username']] = row
    except FileNotFoundError:
        print(f"Error: {USER_DATA_CSV} not found")
        sys.exit(1)
    return users

def save_csv(users):
    """Save user data CSV."""
    if not users:
        return

    fieldnames = list(next(iter(users.values())).keys())

    with open(USER_DATA_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for username in sorted(users.keys()):
            writer.writerow(users[username])

    print(f"Saved changes to {USER_DATA_CSV}")

def list_marked():
    """List all accounts with friend/foe markers."""
    users = load_csv()

    friends = []
    foes = []

    for username, data in users.items():
        status = data.get('friend_foe', '')
        if status == 'friend':
            friends.append(username)
        elif status == 'foe':
            foes.append(username)

    print("\n=== FRIENDS ===")
    if friends:
        for u in sorted(friends):
            print(f"  @{u}")
    else:
        print("  (none)")

    print("\n=== FOES ===")
    if foes:
        for u in sorted(foes):
            print(f"  @{u}")
    else:
        print("  (none)")

    print(f"\nTotal: {len(friends)} friends, {len(foes)} foes\n")

def set_status(username, status):
    """Set friend/foe status for a user."""
    username = username.lstrip('@')

    if status not in ['friend', 'foe']:
        print(f"Error: Status must be 'friend' or 'foe', got '{status}'")
        sys.exit(1)

    users = load_csv()

    if username not in users:
        print(f"Error: @{username} not found in {USER_DATA_CSV}")
        print("User must be checked at least once before marking.")
        sys.exit(1)

    users[username]['friend_foe'] = status
    save_csv(users)

    print(f"[OK] Set @{username} as {status}")

def clear_status(username):
    """Clear friend/foe status for a user."""
    username = username.lstrip('@')

    users = load_csv()

    if username not in users:
        print(f"Error: @{username} not found in {USER_DATA_CSV}")
        sys.exit(1)

    users[username]['friend_foe'] = ''
    save_csv(users)

    print(f"[OK] Cleared status for @{username} (now neutral)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == 'list':
        list_marked()
    elif command == 'set':
        if len(sys.argv) != 4:
            print("Usage: manage_friend_foe.py set @username friend|foe")
            sys.exit(1)
        set_status(sys.argv[2], sys.argv[3])
    elif command == 'clear':
        if len(sys.argv) != 3:
            print("Usage: manage_friend_foe.py clear @username")
            sys.exit(1)
        clear_status(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)
