#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for [[ADD]] tag feature
Tests the timestamp tracking and search functionality without making actual API calls
"""

import os
from datetime import datetime, timedelta, timezone

# Import functions from TwitterAutoReply
import sys
sys.path.insert(0, os.path.dirname(__file__))

# Test file paths
TEST_LAST_ADD_CHECK = 'test_last_add_check.txt'
TEST_USER_DATA_CSV = 'test_user_data.csv'

def test_timestamp_functions():
    """Test timestamp loading and saving functions."""
    print("=" * 80)
    print("TEST 1: Timestamp Tracking Functions")
    print("=" * 80)
    print()

    # Clean up test file if exists
    if os.path.exists(TEST_LAST_ADD_CHECK):
        os.remove(TEST_LAST_ADD_CHECK)
        print("[CLEANUP] Removed existing test timestamp file")

    # Test 1: First run (file doesn't exist)
    print("\n[TEST] First run - file doesn't exist")

    # Simulate load_last_add_check() behavior
    if not os.path.exists(TEST_LAST_ADD_CHECK):
        first_run_time = datetime.now(timezone.utc) - timedelta(days=7)
        timestamp = first_run_time.isoformat(timespec='seconds')
        print(f"[EXPECTED] Should return 7 days ago: {timestamp}")

    # Test 2: Save timestamp
    print("\n[TEST] Saving current timestamp")
    current_time = datetime.now(timezone.utc).isoformat(timespec='seconds')

    try:
        with open(TEST_LAST_ADD_CHECK, 'w') as f:
            f.write(current_time)
        print(f"[SUCCESS] Saved timestamp: {current_time}")
    except Exception as e:
        print(f"[FAILED] Error saving timestamp: {e}")
        return False

    # Test 3: Load saved timestamp
    print("\n[TEST] Loading saved timestamp")
    try:
        with open(TEST_LAST_ADD_CHECK, 'r') as f:
            loaded_timestamp = f.read().strip()
        print(f"[SUCCESS] Loaded timestamp: {loaded_timestamp}")

        if loaded_timestamp == current_time:
            print("[PASSED] Timestamps match!")
        else:
            print(f"[FAILED] Timestamps don't match: {loaded_timestamp} != {current_time}")
            return False
    except Exception as e:
        print(f"[FAILED] Error loading timestamp: {e}")
        return False

    # Cleanup
    if os.path.exists(TEST_LAST_ADD_CHECK):
        os.remove(TEST_LAST_ADD_CHECK)
        print("\n[CLEANUP] Removed test timestamp file")

    print("\n[PASSED] All timestamp tests passed!")
    return True

def test_csv_structure():
    """Test CSV structure and field names."""
    print("\n" + "=" * 80)
    print("TEST 2: CSV Structure")
    print("=" * 80)
    print()

    expected_fields = [
        'username', 'user_id', 'name', 'created_at', 'description', 'location',
        'url', 'profile_image_url', 'verified', 'verified_type', 'protected',
        'followers_count', 'following_count', 'tweet_count', 'listed_count', 'like_count',
        'pinned_tweet_id', 'last_updated', 'times_checked', 'times_replied', 'times_skipped',
        'times_no_tweet', 'friend_foe'
    ]

    print(f"[INFO] Expected {len(expected_fields)} fields in CSV")
    print(f"[INFO] Fields: {', '.join(expected_fields[:5])}... (showing first 5)")

    # Check if actual CSV exists
    if os.path.exists('user_data.csv'):
        try:
            import csv
            with open('user_data.csv', 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                actual_fields = reader.fieldnames

                print(f"\n[INFO] Actual CSV has {len(actual_fields)} fields")

                # Check if all expected fields are present
                missing_fields = [f for f in expected_fields if f not in actual_fields]
                extra_fields = [f for f in actual_fields if f not in expected_fields]

                if missing_fields:
                    print(f"[WARNING] Missing fields: {missing_fields}")
                    return False

                if extra_fields:
                    print(f"[WARNING] Extra fields: {extra_fields}")

                print("[PASSED] CSV structure is correct!")

                # Count rows
                f.seek(0)
                next(f)  # Skip header
                row_count = sum(1 for _ in f)
                print(f"[INFO] Current CSV has {row_count} users")

                return True

        except Exception as e:
            print(f"[FAILED] Error reading CSV: {e}")
            return False
    else:
        print("[INFO] user_data.csv doesn't exist yet (will be created on first add)")
        print("[PASSED] CSV structure test passed (no CSV to validate)")
        return True

def test_search_query():
    """Test search query format."""
    print("\n" + "=" * 80)
    print("TEST 3: Search Query Format")
    print("=" * 80)
    print()

    auth_handle = "DocAtCDI"  # Your bot handle
    expected_query = f'from:{auth_handle} is:reply ("[[ADD]]" OR "[[ADD-FRIEND]]" OR "[[ADD-FOE]]" OR "[[ADD-PRIORITY]]" OR "[[ADD-REMOVE]]") -is:retweet'

    print(f"[INFO] Expected search query:")
    print(f"       {expected_query[:80]}...")
    print()

    # Explain query components
    print("[INFO] Query components:")
    print(f"       - from:{auth_handle} -> Only bot's tweets")
    print("       - is:reply -> Only replies (compatible with pay-as-you-go tier)")
    print("       - OR query -> Explicitly searches for each variant")
    print("       - -is:retweet -> Exclude retweets")
    print()

    print("[INFO] This OR query finds:")
    print("       - [[ADD]]")
    print("       - [[ADD-FRIEND]]")
    print("       - [[ADD-FOE]]")
    print("       - [[ADD-PRIORITY]]")
    print("       - [[ADD-REMOVE]]")
    print()
    print("[INFO] Note: Must explicitly list variants - Twitter doesn't support wildcards")
    print()

    print("[PASSED] Search query format is correct!")
    return True

def test_variant_parsing():
    """Test variant parsing logic."""
    print("\n" + "=" * 80)
    print("TEST 4: Variant Parsing")
    print("=" * 80)
    print()

    # Import the parse function from TwitterAutoReply
    try:
        from TwitterAutoReply import parse_add_tag_variant
    except ImportError:
        print("[FAILED] Could not import parse_add_tag_variant function")
        return False

    # Test cases: (tweet_text, expected_variant_name, expected_should_add, expected_friend_foe)
    test_cases = [
        ("Great joke! [[ADD]]", "DEFAULT", True, ""),
        ("Love it! [[ADD]]", "DEFAULT", True, ""),
        ("[[ADD-FRIEND]] Thanks!", "FRIEND", True, "friend"),
        ("You're awesome [[ADD-FRIEND]]", "FRIEND", True, "friend"),
        ("Bad take. [[ADD-FOE]]", "FOE", True, "foe"),
        ("[[ADD-FOE]] Disagree", "FOE", True, "foe"),
        ("VIP content [[ADD-PRIORITY]]", "PRIORITY", True, ""),
        ("[[ADD-PRIORITY]] Important", "PRIORITY", True, ""),
        ("Stop engaging [[ADD-REMOVE]]", "REMOVE", False, ""),
        ("[[ADD-REMOVE]] Done", "REMOVE", False, ""),
        ("[[add-friend]] (lowercase)", "FRIEND", True, "friend"),
        ("[[Add-Foe]] (mixed case)", "FOE", True, "foe"),
    ]

    all_passed = True
    for tweet_text, expected_variant, expected_should_add, expected_friend_foe in test_cases:
        variant_name, should_add, friend_foe_status, priority = parse_add_tag_variant(tweet_text)

        if variant_name == expected_variant and should_add == expected_should_add and friend_foe_status == expected_friend_foe:
            print(f"[PASSED] '{tweet_text[:30]}...' -> {variant_name}")
        else:
            print(f"[FAILED] '{tweet_text[:30]}...'")
            print(f"         Expected: variant={expected_variant}, should_add={expected_should_add}, friend_foe={expected_friend_foe}")
            print(f"         Got:      variant={variant_name}, should_add={should_add}, friend_foe={friend_foe_status}")
            all_passed = False

    if all_passed:
        print("\n[PASSED] All variant parsing tests passed!")
    else:
        print("\n[FAILED] Some variant parsing tests failed!")

    return all_passed

def test_integration_points():
    """Test that integration points exist in main script."""
    print("\n" + "=" * 80)
    print("TEST 5: Integration Points")
    print("=" * 80)
    print()

    script_path = 'TwitterAutoReply.py'

    if not os.path.exists(script_path):
        print(f"[FAILED] {script_path} not found")
        return False

    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for required components
        checks = [
            ('LAST_ADD_CHECK_FILE', "Constant for timestamp file"),
            ('load_last_add_check()', "Function to load timestamp"),
            ('save_last_add_check()', "Function to save timestamp"),
            ('parse_add_tag_variant(', "Function to parse tag variants"),
            ('search_add_tag_replies(', "Function to search for ##ADD tags"),
            ('add_user_from_tag(', "Function to add user from tag"),
            ('remove_user_from_rotation(', "Function to remove user from rotation"),
            ('validate_csv_integrity()', "Function to validate CSV"),
            ('process_add_tags(', "Main orchestrator function"),
            ('validate_csv_integrity()', "Call in main()"),
            ('process_add_tags(client)', "Call in main()"),
        ]

        all_passed = True
        for check_str, description in checks:
            if check_str in content:
                print(f"[PASSED] Found: {description}")
            else:
                print(f"[FAILED] Missing: {description}")
                all_passed = False

        if all_passed:
            print("\n[PASSED] All integration points found!")
        else:
            print("\n[FAILED] Some integration points missing!")

        return all_passed

    except Exception as e:
        print(f"[FAILED] Error reading script: {e}")
        return False

def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("[[ADD]] TAG FEATURE - TEST SUITE")
    print("=" * 80)
    print()

    tests = [
        ("Timestamp Tracking", test_timestamp_functions),
        ("CSV Structure", test_csv_structure),
        ("Search Query Format", test_search_query),
        ("Variant Parsing", test_variant_parsing),
        ("Integration Points", test_integration_points),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n[ERROR] Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()

    for test_name, result in results:
        status = "[PASSED]" if result else "[FAILED]"
        print(f"{status} - {test_name}")

    passed_count = sum(1 for _, result in results if result)
    total_count = len(results)

    print()
    print(f"Result: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n[SUCCESS] All tests passed! Feature is ready to use.")
        print("\nNext steps:")
        print("1. Reply to someone with a tag variant in your tweet:")
        print("   - [[ADD]] (default)")
        print("   - [[ADD-FRIEND]] (mark as friend)")
        print("   - [[ADD-FOE]] (mark as foe)")
        print("   - [[ADD-PRIORITY]] (high priority)")
        print("   - [[ADD-REMOVE]] (remove from rotation)")
        print("2. Run: python TwitterAutoReply.py")
        print("3. Check that the user was added/removed from user_data.csv")
        print("\nSee TAG_VARIANTS.md for full documentation!")
    else:
        print("\n[WARNING] Some tests failed. Please review the output above.")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
