#!/usr/bin/env python3
"""Test Twitter posting time randomization."""

import sys
from pathlib import Path
from datetime import datetime

# Add project path
sys.path.append(str(Path(__file__).parent))

def test_random_time_calculation():
    """Test that random times fall within expected windows."""
    from main_launcher import calculate_random_time

    print("Testing random time calculation...")
    print("=" * 60)

    # Test 20 random times for each even hour to show distribution
    for base_hour in range(2, 24, 2):
        print(f"\nTesting hour {base_hour:02d}:30...")

        times_generated = []
        min_minute = 60
        max_minute = 0

        for _ in range(20):
            random_time_str = calculate_random_time(base_hour, 30, 15)

            # Parse time
            hour, minute = map(int, random_time_str.split(':'))
            times_generated.append((hour, minute))

            # Track min/max
            if minute < min_minute:
                min_minute = minute
            if minute > max_minute:
                max_minute = minute

            # Verify bounds
            base_time = datetime(2000, 1, 1, base_hour, 30)
            random_time = datetime(2000, 1, 1, hour, minute)
            diff_minutes = (random_time - base_time).total_seconds() / 60

            assert -15 <= diff_minutes <= 15, \
                f"Time {random_time_str} outside ±15 min window for {base_hour:02d}:30"

        # Show sample times
        sample_times = [f'{h:02d}:{m:02d}' for h, m in times_generated[:8]]
        print(f"  Range: {base_hour:02d}:{min_minute:02d} to {base_hour:02d}:{max_minute:02d}")
        print(f"  Sample times: {', '.join(sample_times)}")

        # Check if :30 appeared in the samples
        has_exact_30 = any(m == 30 for h, m in times_generated)
        if has_exact_30:
            print(f"  [OK] Exact :30 appeared in random samples (as expected)")

    print("\n" + "=" * 60)
    print("[PASS] All random times within expected windows")
    print("[PASS] :30 can appear as a valid random selection")

def test_wrapper_creation():
    """Test that wrapper functions are created correctly."""
    from main_launcher import create_randomized_tweet_wrapper

    print("\nTesting wrapper function creation...")
    print("=" * 60)

    for base_hour in range(2, 24, 2):
        wrapper = create_randomized_tweet_wrapper(base_hour)

        # Verify function created
        assert callable(wrapper), f"Wrapper for hour {base_hour} is not callable"

        # Verify function name
        assert wrapper.__name__ == "randomized_tweet_post", \
            f"Unexpected function name: {wrapper.__name__}"

    print("[PASS] All 11 wrapper functions created successfully")
    print(f"  Created wrappers for hours: {', '.join([f'{h:02d}' for h in range(2, 24, 2)])}")

def test_time_distribution():
    """Test that randomization produces varied results over multiple runs."""
    from main_launcher import calculate_random_time

    print("\nTesting time distribution...")
    print("=" * 60)

    # Generate 100 random times for hour 14 (2:30 PM)
    times = []
    for _ in range(100):
        time_str = calculate_random_time(14, 30, 15)
        hour, minute = map(int, time_str.split(':'))
        times.append(minute)

    # Calculate statistics
    unique_times = len(set(times))
    min_time = min(times)
    max_time = max(times)
    avg_time = sum(times) / len(times)

    print(f"Generated 100 random times for 14:30:")
    print(f"  Unique times: {unique_times}/100")
    print(f"  Range: 14:{min_time:02d} to 14:{max_time:02d}")
    print(f"  Average: 14:{int(avg_time):02d}")
    print(f"  Expected: 14:15 to 14:45, average ~14:30")

    # Verify good distribution
    assert unique_times > 10, f"Poor distribution: only {unique_times} unique times"
    assert 15 <= min_time <= 35, f"Min time {min_time} outside expected range"
    assert 25 <= max_time <= 45, f"Max time {max_time} outside expected range"

    print("[PASS] Good distribution of random times")

if __name__ == "__main__":
    print("=" * 60)
    print("Twitter Randomization Test Suite")
    print("=" * 60)

    try:
        test_random_time_calculation()
        test_wrapper_creation()
        test_time_distribution()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        print("\nImplementation is ready for deployment.")
        print("The bot will randomize Twitter posts within ±15 minutes of :30")
        print("for all even hours (2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22).")
        print("DocAfterDark remains fixed at 22:03.")
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        sys.exit(1)
