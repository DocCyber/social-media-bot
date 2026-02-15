import tweepy
import random
from datetime import datetime, timedelta, timezone
import os

# Secrets file
secrets_file = r'd:\secrets\TwitterPayAsYouGo.txt'

# Accounts file - same folder as this script
accounts_file = 'accounts.txt'

# Parse all credentials from the text file
config = {}
with open(secrets_file, 'r') as f:
    for line in f:
        stripped = line.strip()
        if ':' in stripped:
            key, value = stripped.split(':', 1)
            config[key.strip().lower().replace(' ', '_')] = value.strip()

# Required for write (posting replies)
consumer_key = config.get('consumer_key') or config.get('api_key')
consumer_secret = config.get('secret_key') or config.get('api_secret')
access_token = config.get('access_token')
access_token_secret = config.get('access_token_secret')
bearer_token = config.get('bearer_token')

if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
    raise ValueError("Missing required credentials for posting (need consumer_key, secret, access_token, secret). Add them to the file.")

# Initialize client with full user auth (for posting replies)
client = tweepy.Client(
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    access_token=access_token,
    access_token_secret=access_token_secret,
    bearer_token=bearer_token  # optional but harmless
)

# Load usernames
if not os.path.exists(accounts_file):
    raise FileNotFoundError(f"accounts.txt not found in script directory: {os.getcwd()}")

with open(accounts_file, 'r') as f:
    usernames = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

if not usernames:
    raise ValueError("No usernames in accounts.txt.")

# Pick random
selected_username = random.choice(usernames)
print(f"Selected random user: @{selected_username}\n")

# 12 hours ago, RFC3339
now_utc = datetime.now(timezone.utc)
start_time_dt = now_utc - timedelta(hours=12)
start_time = start_time_dt.isoformat(timespec='seconds')

print(f"Looking since: {start_time}\n")

try:
    user_response = client.get_user(username=selected_username)
    if not user_response.data:
        print(f"User @{selected_username} not found.")
    else:
        user_id = user_response.data.id

        tweets_response = client.get_users_tweets(
            id=user_id,
            max_results=5,
            start_time=start_time,
            exclude=['replies', 'retweets'],
            tweet_fields=['created_at', 'text', 'id']
        )

        if tweets_response.data:
            latest = tweets_response.data[0]
            created_at = latest.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if latest.created_at else 'N/A'
            print(f"Most recent original post by @{selected_username} ({created_at}):")
            print(latest.text)
            print(f"\nTweet ID: {latest.id} | Link: https://x.com/{selected_username}/status/{latest.id}")
            
            # Reply prompt
            reply_text = input("\nEnter your reply text (or press Enter to skip): ").strip()
            if reply_text:
                full_reply = f"@{selected_username} {reply_text}"
                try:
                    reply_response = client.create_tweet(
                        text=full_reply,
                        in_reply_to_tweet_id=latest.id
                    )
                    reply_id = reply_response.data['id']
                    print(f"\nReply posted successfully!")
                    print(f"Reply link: https://x.com/{selected_username}/status/{reply_id}")
                except tweepy.TweepyException as e:
                    print(f"Failed to post reply: {e}")
            else:
                print("Skipped replying.")
        else:
            print(f"No qualifying original posts from @{selected_username} in last 12h.")

except tweepy.TweepyException as e:
    print(f"Error: {e}")
except Exception as e:
    print(f"Unexpected: {e}")
