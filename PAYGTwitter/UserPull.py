import tweepy
import csv
import os

# Secrets file (same as before)
secrets_file = r'd:\secrets\TwitterPayAsYouGo.txt'

# Parse credentials
config = {}
with open(secrets_file, 'r') as f:
    for line in f:
        stripped = line.strip()
        if ':' in stripped:
            key_part, value = stripped.split(':', 1)
            key = key_part.strip().lower().replace(' ', '_').replace('key', 'key').replace('token', 'token')
            config[key] = value.strip()

consumer_key = config.get('consumer_key') or config.get('api_key')
consumer_secret = config.get('secret_key') or config.get('api_secret') or config.get('consumer_secret')
access_token = config.get('access_token')
access_token_secret = config.get('access_token_secret')
bearer_token = config.get('bearer_token')

if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
    raise ValueError("Missing required credentials (consumer_key, consumer_secret, access_token, access_token_secret).")

# Initialize client
client = tweepy.Client(
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    access_token=access_token,
    access_token_secret=access_token_secret,
    bearer_token=bearer_token
)

# Get your own user ID
me = client.get_me(user_fields=['id'])
if not me.data:
    raise ValueError("Could not fetch your user ID. Check auth/permissions.")
user_id = me.data.id
print(f"Fetching followers for @{me.data.username} (ID: {user_id})\n")

# Output CSV path (same dir as script)
csv_file = 'followers.csv'
print(f"Results will be saved to: {os.path.abspath(csv_file)}\n")

# Fetch one batch of followers
print("Fetching one batch of up to 1000 followers...")
followers_response = client.get_users_followers(
    id=user_id,
    max_results=1000,
    user_fields=['verified', 'public_metrics', 'username', 'name'],
    pagination_token=None
)

qualified = []
if followers_response.data:
    for user in followers_response.data:
        is_verified = user.verified
        follower_count = user.public_metrics.get('followers_count', 0)
        
        if is_verified and follower_count > 20000:
            qualified.append({
                'username': user.username,
                'name': user.name or '',
                'followers_count': follower_count,
                'user_id': user.id  # optional extra field
            })

# Save to CSV
if qualified:
    fieldnames = ['username', 'name', 'followers_count', 'user_id']
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(qualified)
    
    print(f"Done! Found {len(qualified)} matching followers.")
    print(f"Saved to {csv_file} in the script's directory.")
else:
    print("No followers in this batch match: verified + >20,000 followers.")
    # Still create empty CSV with header
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['username', 'name', 'followers_count', 'user_id'])
        writer.writeheader()
    print(f"Empty results saved to {csv_file} (header only).")

# Optional: show next page hint
if 'next_token' in followers_response.meta:
    print(f"\nMore followers available (next pagination_token: {followers_response.meta['next_token']})")
