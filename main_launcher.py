#!/usr/bin/env python3
"""
Main Bot Platform Launcher
Centralized launcher for all social media automation
Starting with BlueSky, will expand to Twitter, Mastodon, etc.

Current version: Testing BlueSky every 5 minutes
"""

import sys
import os
import time
import random
import threading
import schedule
from datetime import datetime, timedelta
from pathlib import Path

# Add project path
BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))
# Add /tweet module path so we can import tweet.py
sys.path.append(str(BASE_DIR / "tweet"))
# Add PAYGTwitter paths for auto-reply and praise bot
sys.path.append(str(BASE_DIR / "PAYGTwitter"))
sys.path.append(str(BASE_DIR / "PAYGTwitter" / "praise_bot"))

def calculate_random_time(base_hour: int, base_minute: int = 30, window: int = 15) -> str:
    """Calculate a random time within ±window minutes of base time."""
    base_time = datetime(2000, 1, 1, base_hour, base_minute)
    offset_minutes = random.randint(-window, window)
    random_time = base_time + timedelta(minutes=offset_minutes)
    return random_time.strftime("%H:%M")

def create_randomized_tweet_wrapper(base_hour: int):
    """
    Create a wrapper function that posts a tweet and tracks last run to prevent
    multiple posts in the same day.
    """
    tag_name = f"twitter_post_h{base_hour}"
    last_run_date = {'date': None}  # Mutable dict to track last run date

    def randomized_tweet_post():
        """Post tweet only once per day for this hour."""
        now = datetime.now()
        today = now.date()

        # Check if we already posted today for this hour
        if last_run_date['date'] == today:
            print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Already posted for hour {base_hour} today, skipping")
            return

        # Execute the tweet post
        try:
            import tweet
            filename = "jokes.csv"
            index_key = "joke"
            print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Randomized tweet start: "
                  f"base_hour={base_hour}")
            tweet.tweet_item(filename, index_key)
            print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Randomized tweet completed")

            # Mark that we posted today
            last_run_date['date'] = today

        except Exception as e:
            print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Error in randomized tweet "
                  f"(base_hour={base_hour}): {e}")

    return randomized_tweet_post

def bsky_post():
    """Post to BlueSky - scheduled function."""
    current_time = datetime.now()
    try:
        from bsky import bsky
        bsky.main()
        print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] bsky.main() completed")
    except Exception as e:
        print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] Error in bsky.main(): {e}")

def run_launcher():
    """Run BlueSky interactions - follow-backs, likes, replies."""
    current_time = datetime.now()
    print(f"\n[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] Running BlueSky interactions...")
    try:
        from bsky.modules import hello_reply, custom_reply, follow, reactions
        hello_reply.main()
        custom_reply.main()
        follow.main()
        reactions.main()
    except Exception as e:
        print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] Error in BlueSky interactions: {e}")

def process_interactions_main():
    """Process BlueSky interactions - comprehensive daily processing."""
    try:
        from bsky.modules import custom_reply, follow, reactions
        custom_reply.main()
        follow.main()
        reactions.main()
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error processing BlueSky interactions: {e}")

def bsky_bestthing_main():
    """Run BlueSky best thing posting."""
    try:
        from bskyBESTTHING import main as bestthing_main
        bestthing_main()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] BlueSky best thing posting completed")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error in BlueSky best thing posting: {e}")

def bsky_taunt_main():
    """Run BlueSky taunt bot posting."""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running BlueSky taunt bot posting...")
    try:
        from bsky_taunt.bsky_taunt import main as taunt_main
        taunt_main()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] BlueSky taunt bot posting completed")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error in BlueSky taunt bot posting: {e}")

def tweet_post():
    """Post to Twitter/X from jokes.csv using index.json['joke'] every even hour at :30 (no midnight)."""
    now = datetime.now()
    try:
        import tweet  # /tweet/tweet.py
        filename = "jokes.csv"   # root
        index_key = "joke"       # from index.json
        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] tweet.tweet_item start: file={filename}, key={index_key}")
        tweet.tweet_item(filename, index_key)  # no add_text
        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] tweet.tweet_item completed")
    except Exception as e:
        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Error in tweet_post(): {e}")

def mastodon_post():
    """Post to Mastodon from jokes.csv using index.json['Mastodon']."""
    now = datetime.now()
    try:
        from platforms.mastodon_platform import MastodonPlatform
        platform = MastodonPlatform()
        if platform.authenticate():
            result = platform.post_item_from_csv("jokes.csv", "Mastodon")
            print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Mastodon post {'completed' if result else 'failed'}")
        else:
            print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Mastodon authentication failed")
    except Exception as e:
        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Error in mastodon_post(): {e}")

def tweet_docafterdark():
    """Post DocAfterDark to Twitter at 22:03."""
    try:
        import tweet
        tweet.tweet_docafterdark()
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error in tweet_docafterdark(): {e}")

def bsky_docafterdark():
    """Post DocAfterDark to BlueSky at 22:04."""
    try:
        from bsky import bsky
        bsky.post_docafterdark()
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error in bsky_docafterdark(): {e}")

def earthporn_poster():
    """Post EarthPorn images to BlueSky."""
    try:
        from bsky.modules import earthporn_poster
        earthporn_poster.main()
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error in earthporn_poster(): {e}")

def ai_reply_processor():
    """Process AI-powered replies to mentions and interactions."""
    try:
        from bsky.modules import ai_reply
        ai_reply.main()
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error in ai_reply_processor(): {e}")

def conservative_unfollower():
    """Run conservative unfollowing (10 accounts per pass)."""
    try:
        from bsky.modules import conservative_unfollower
        conservative_unfollower.main()
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error in conservative_unfollower(): {e}")

def refresh_follow_data():
    """Refresh following/follower data collection (weekly)."""
    try:
        from bsky.modules import data_collector
        data_collector.main()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Follow data collection completed")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error in refresh_follow_data(): {e}")

def schedule_dynamic_task(func, min_minutes, max_minutes, tag_name):
    """Schedule a task to run once after a random delay, then reschedule with a new random delay."""
    delay = random.randint(min_minutes, max_minutes)
    next_time = datetime.now() + timedelta(minutes=delay)
    time_str = next_time.strftime("%H:%M")

    def run_and_reschedule():
        try:
            func()
        except Exception as e:
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Error in {tag_name}: {e}")
        # Clear this one-shot and schedule next run with a fresh random delay
        schedule.clear(tag_name)
        schedule_dynamic_task(func, min_minutes, max_minutes, tag_name)
        return schedule.CancelJob

    schedule.clear(tag_name)
    schedule.every(delay).minutes.do(run_and_reschedule).tag(tag_name)
    print(f"  [{tag_name}] Next run in ~{delay} min (around {time_str})")

def twitter_auto_reply():
    """Run Twitter auto-reply bot in a fire-and-forget background thread."""
    def _run():
        original_dir = os.getcwd()
        try:
            os.chdir(str(BASE_DIR / "PAYGTwitter"))
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [TwitterAutoReply] Starting...")

            from TwitterAutoReply import (
                load_twitter_credentials, load_accounts, load_counter, save_counter,
                main as auto_reply_main, validate_csv_integrity, process_add_tags
            )
            import tweepy

            # Startup checks (ADD tags, CSV validation)
            consumer_key, consumer_secret, access_token, access_token_secret, bearer_token = load_twitter_credentials()
            client = tweepy.Client(
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
                bearer_token=bearer_token
            )
            validate_csv_integrity()
            process_add_tags(client)

            # Run cycles until first successful reply (same logic as standalone)
            start_index = load_counter()
            usernames = load_accounts()
            total_users = len(usernames)
            current_index = start_index

            while True:
                wrapped_index = current_index % total_users
                replied = auto_reply_main(cycle_index=wrapped_index)
                current_index += 1
                if replied:
                    save_counter(current_index % total_users)
                    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [TwitterAutoReply] Done - reply posted")
                    break
                time.sleep(20)
        except Exception as e:
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [TwitterAutoReply] Error: {e}")
        finally:
            os.chdir(original_dir)

    thread = threading.Thread(target=_run, daemon=True, name="TwitterAutoReply")
    thread.start()

def twitter_praise_bot():
    """Generate and post a praise/validation tweet."""
    original_dir = os.getcwd()
    try:
        os.chdir(str(BASE_DIR / "PAYGTwitter" / "praise_bot"))
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [PraiseBot] Generating post...")

        from generate_praise import generate_post, post_to_twitter

        post = generate_post()
        if len(post) > 280:
            for _ in range(20):
                post = generate_post()
                if len(post) <= 280:
                    break
            else:
                print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [PraiseBot] Could not generate post under 280 chars")
                return

        tweet_id = post_to_twitter(post)
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [PraiseBot] Posted! Tweet ID: {tweet_id}")
    except Exception as e:
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [PraiseBot] Error: {e}")
    finally:
        os.chdir(original_dir)

def setup_twitter_schedules():
    """Setup/refresh Twitter posting schedules with new random times."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Setting up Twitter schedules with new random times...")

    # Clear all existing Twitter schedules
    for h in range(2, 24, 2):
        if h == 0:  # Skip midnight
            continue
        # Optionally skip noon (uncomment if needed)
        # if h == 12:
        #     continue
        tag_name = f"twitter_post_h{h}"
        schedule.clear(tag_name)

    # Create new schedules with fresh random times
    for h in range(2, 24, 2):
        if h == 0:  # Skip midnight
            continue
        if h == 12:  # Skip noon to save API calls
            continue

        wrapper_func = create_randomized_tweet_wrapper(h)
        initial_time = calculate_random_time(h, 30, 15)
        tag_name = f"twitter_post_h{h}"

        schedule.every().day.at(initial_time).do(wrapper_func).tag(tag_name)
        print(f"  Hour {h:02d}: Scheduled at {initial_time} (target {h:02d}:15-{h:02d}:45)")

    print("Twitter schedules updated successfully")

def main():
    """Main launcher using schedule library."""
    print("Starting Main Bot Platform Launcher...")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Using schedule library for timing")
    print("Press Ctrl+C to stop")
    print("-" * 50)

    # BlueSky schedules (existing)
    schedule.every(5).minutes.do(run_launcher)
    schedule.every().hour.at(":00").do(run_launcher)
    schedule.every().day.at("00:15").do(process_interactions_main)
    schedule.every().hour.at(":31").do(bsky_post)
    schedule.every().day.at("00:01").do(bsky_bestthing_main)
    schedule.every().day.at("19:00").do(bsky_taunt_main)

    # Twitter/X schedule: Setup initial schedules
    # 10 posts total: 02:30, 04:30, 06:30, 08:30, 10:30, 14:30, 16:30, 18:30, 20:30, 22:30
    # (Skipping midnight and noon to conserve API limits)
    # Random time between :15 and :45 for each hour, changes daily at 00:30
    setup_twitter_schedules()

    # Refresh Twitter schedules daily at 00:30 with new random times
    schedule.every().day.at("00:30").do(setup_twitter_schedules)

    # Mastodon schedule: every hour at :37 (no API limits like Twitter!)
    schedule.every().hour.at(":37").do(mastodon_post)

    # DocAfterDark schedule: Twitter at 22:03, BlueSky at 22:04
    schedule.every().day.at("22:03").do(tweet_docafterdark)
    schedule.every().day.at("22:04").do(bsky_docafterdark)

    # EarthPorn schedule: Check for new posts every 5 minutes (TESTING - change back to 3 hours later)
    schedule.every(65).minutes.do(earthporn_poster)

    # AI Reply schedule: Process AI replies every 3 minutes (TESTING with mrsdocatcdi only)
    schedule.every(12).minutes.do(ai_reply_processor)

    # Conservative Unfollower: Unfollow 1 account every 2 minutes (TESTING - change back to 10 minutes later)
    schedule.every(120).minutes.do(conservative_unfollower)

    # Data Collection: Refresh following/follower data every Sunday at 2 AM
    schedule.every().sunday.at("02:00").do(refresh_follow_data)

    # Twitter Auto-Reply: every 10-20 minutes (target ~15 ±5), dynamic reschedule after each run
    schedule_dynamic_task(twitter_auto_reply, 10, 20, "twitter_auto_reply")

    # Praise Bot: every 360-480 minutes (6-8 hours), dynamic reschedule after each run
    schedule_dynamic_task(twitter_praise_bot, 360, 480, "twitter_praise_bot")

    print("Scheduled times:")
    for job in schedule.jobs:
        print(f"  - {job}")

    print("\nScheduler running...")
    retry_count = 0
    max_retries = 5
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
            retry_count = 0
        except KeyboardInterrupt:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Launcher stopped by user")
            break
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error in main loop: {e}")
            retry_count += 1
            if retry_count > max_retries:
                print("Exceeded maximum retry limit. Skipping this cycle.")
                retry_count = 0
                time.sleep(60)

if __name__ == "__main__":
    main()
