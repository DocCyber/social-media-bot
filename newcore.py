import sys
import os
import schedule
import time
import subprocess
import random
from datetime import datetime

# Add the parent directory and subdirectories to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "comics"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bsky"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "advertisment"))

# Import modules
import tweet
import tweetad
from insta import insta
from toot import toot_item
from comicupload import main as upload_comic
from bsky import bsky
from bskyBESTTHING import main as bsky_bestthing_main
from bsky.process_interactions import main as process_interactions_main

# Define the path to launcher.py
LAUNCHER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bsky", "launcher.py")

def run_launcher():
    try:
        result = subprocess.run(
            [sys.executable, LAUNCHER_SCRIPT],
            cwd=os.path.dirname(LAUNCHER_SCRIPT),
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"launcher.py exited with code {result.returncode}")
            print("Error output:")
            print(result.stderr)
        else:
            print("launcher.py ran successfully:")
            print(result.stdout)
    except Exception as e:
        print(f"Error running launcher.py: {e}")

def tweet_random_ad():
    print(f"Running randomized ad tweet at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    tweetad.tweet_item('jokebot.csv', 'jokebot')

def reschedule_daily_randoms():
    # Remove previous tweet_random_ad jobs
    schedule.clear('tweet_random_ad')

    am_hour = random.randint(1, 11)
    pm_hour = random.randint(13, 22)
    am_minute = random.randint(0, 59)
    pm_minute = random.randint(0, 59)

    am_time = f"{am_hour:02d}:{am_minute:02d}"
    pm_time = f"{pm_hour:02d}:{pm_minute:02d}"

    print(f"[DAILY RESET] Scheduling tweetad.tweet_item at {am_time} and {pm_time}")
    schedule.every().day.at(am_time).do(tweet_random_ad).tag('tweet_random_ad')
    schedule.every().day.at(pm_time).do(tweet_random_ad).tag('tweet_random_ad')


# Schedule each task
schedule.every(5).minutes.do(run_launcher)
schedule.every().hour.at(":00").do(run_launcher)
schedule.every().day.at("02:30").do(tweet.tweet_item, 'jokes.csv', 'joke')
schedule.every().day.at("04:30").do(tweet.tweet_item, 'jokes.csv', 'joke')
schedule.every().day.at("06:30").do(tweet.tweet_item, 'jokes.csv', 'joke')
schedule.every().day.at("08:30").do(tweet.tweet_item, 'jokes.csv', 'joke')
schedule.every().day.at("10:30").do(tweet.tweet_item, 'jokes.csv', 'joke')
schedule.every().day.at("12:30").do(tweet.tweet_item, 'jokes.csv', 'joke')
schedule.every().day.at("14:30").do(tweet.tweet_item, 'jokes.csv', 'joke')
schedule.every().day.at("16:30").do(tweet.tweet_item, 'jokes.csv', 'joke')
schedule.every().day.at("18:30").do(tweet.tweet_item, 'jokes.csv', 'joke')
schedule.every().day.at("20:30").do(tweet.tweet_item, 'jokes.csv', 'joke')
schedule.every().day.at("22:30").do(tweet.tweet_item, 'jokes.csv', 'joke')
schedule.every().day.at("00:15").do(process_interactions_main)
schedule.every().hour.at(":31").do(bsky.main)
schedule.every().hour.at(":32").do(toot_item, 'jokes.csv', 'Mastodon')
schedule.every().day.at("22:03").do(tweet.tweet_item, 'DocAfterDark.csv', 'docafterdark', '\n#DocAfterDark')
schedule.every().day.at("00:01").do(bsky_bestthing_main)
schedule.every().monday.at("12:00").do(upload_comic)
schedule.every().wednesday.at("12:00").do(upload_comic)
schedule.every().friday.at("12:00").do(upload_comic)

# Schedule the daily rescheduler
schedule.every().day.at("00:10").do(reschedule_daily_randoms)
reschedule_daily_randoms()  # Initial call on startup

# Main loop with retry mechanism
retry_count = 0
max_retries = 5

while True:
    try:
        schedule.run_pending()
        time.sleep(1)
        retry_count = 0
    except Exception as e:
        print(f"Error in main loop: {e}")
        retry_count += 1
        if retry_count > max_retries:
            print("Exceeded maximum retry limit. Skipping this cycle.")
            retry_count = 0
            time.sleep(60)
