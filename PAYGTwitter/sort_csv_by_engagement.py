#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sort user_data.csv by engagement rate
Run this before running TwitterAutoReply.py to prioritize high-engagement users
"""

import csv
import sys

USER_DATA_CSV = 'user_data.csv'

def sort_csv_by_engagement():
    """Sort user_data.csv by engagement rate (times_replied / times_checked)."""

    print("=" * 80)
    print("SORTING USER_DATA.CSV BY ENGAGEMENT RATE")
    print("=" * 80)
    print()

    # Load CSV
    try:
        with open(USER_DATA_CSV, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)
    except FileNotFoundError:
        print(f"[ERROR] {USER_DATA_CSV} not found!")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to load CSV: {e}")
        return False

    if not rows:
        print("[ERROR] CSV is empty!")
        return False

    print(f"[INFO] Loaded {len(rows)} users from CSV")
    print()

    # Calculate engagement rate for each user
    for row in rows:
        times_checked = int(row.get('times_checked', 0) or 0)
        times_replied = int(row.get('times_replied', 0) or 0)

        if times_checked > 0:
            engagement_rate = times_replied / times_checked
        else:
            engagement_rate = 0

        row['_engagement_rate'] = engagement_rate  # Temporary field for sorting

    # Sort by engagement rate (highest first), then by friend status
    def sort_key(row):
        engagement_rate = row['_engagement_rate']
        friend_foe = row.get('friend_foe', '')

        # Priority: friends first, then by engagement rate
        if friend_foe == 'friend':
            priority = 3
        elif friend_foe == '':
            priority = 2
        else:  # foe
            priority = 1

        return (-priority, -engagement_rate)  # Negative for descending order

    rows.sort(key=sort_key)

    # Remove temporary field
    for row in rows:
        del row['_engagement_rate']

    # Save back to CSV
    try:
        with open(USER_DATA_CSV, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"[SUCCESS] Sorted {len(rows)} users and saved to {USER_DATA_CSV}")
        print()

    except Exception as e:
        print(f"[ERROR] Failed to save CSV: {e}")
        return False

    # Show top 10 users
    print("=" * 80)
    print("TOP 10 USERS (will be prioritized)")
    print("=" * 80)
    print()
    print(f"{'Rank':<6} {'Username':<20} {'Status':<10} {'Eng Rate':<10} {'Replied':<8} {'Checked':<8}")
    print("-" * 80)

    for i, row in enumerate(rows[:10], 1):
        username = row['username']
        friend_foe = row.get('friend_foe', '') or 'neutral'
        times_checked = int(row.get('times_checked', 0) or 0)
        times_replied = int(row.get('times_replied', 0) or 0)

        if times_checked > 0:
            engagement_rate = times_replied / times_checked
        else:
            engagement_rate = 0

        print(f"{i:<6} {username:<20} {friend_foe:<10} {engagement_rate:<10.1%} {times_replied:<8} {times_checked:<8}")

    print()

    # Statistics
    friend_count = sum(1 for row in rows if row.get('friend_foe') == 'friend')
    foe_count = sum(1 for row in rows if row.get('friend_foe') == 'foe')
    neutral_count = len(rows) - friend_count - foe_count

    print("=" * 80)
    print("STATISTICS")
    print("=" * 80)
    print(f"Total users:    {len(rows)}")
    print(f"Friends:        {friend_count}")
    print(f"Foes:           {foe_count}")
    print(f"Neutral:        {neutral_count}")
    print()

    avg_engagement = sum(
        (int(row.get('times_replied', 0) or 0) / int(row.get('times_checked', 1) or 1))
        for row in rows if int(row.get('times_checked', 0) or 0) > 0
    ) / len([r for r in rows if int(r.get('times_checked', 0) or 0) > 0])

    print(f"Average engagement rate: {avg_engagement:.1%}")
    print()

    print("=" * 80)
    print("CSV SORTED! Bot will always start with the top user.")
    print("Re-run this script after each bot cycle to re-sort based on new metrics.")
    print("=" * 80)

    return True

if __name__ == "__main__":
    success = sort_csv_by_engagement()
    sys.exit(0 if success else 1)
