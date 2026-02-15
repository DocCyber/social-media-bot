import tweepy
from datetime import datetime, timedelta, timezone

SECRETS_FILE = r'd:\secrets\TwitterPayAsYouGo.txt'


def load_twitter_credentials():
    """Load Twitter API credentials from secrets file."""
    config = {}
    with open(SECRETS_FILE, 'r') as f:
        for line in f:
            stripped = line.strip()
            if ':' in stripped:
                key, value = stripped.split(':', 1)
                config[key.strip().lower().replace(' ', '_')] = value.strip()

    consumer_key = config.get('consumer_key') or config.get('api_key')
    consumer_secret = config.get('secret_key') or config.get('api_secret')
    access_token = config.get('access_token')
    access_token_secret = config.get('access_token_secret')
    bearer_token = config.get('bearer_token')

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        raise ValueError("Missing required Twitter credentials")

    return consumer_key, consumer_secret, access_token, access_token_secret, bearer_token


def search():
    consumer_key, consumer_secret, access_token, access_token_secret, bearer_token = load_twitter_credentials()

    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
        bearer_token=bearer_token
    )

    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=12)

    query = (
        '("hard time") '
        'lang:en -is:reply -is:retweet -has:mentions -has:links -bitcoin -RT'
    )

    response = client.search_recent_tweets(
        query=query,
        max_results=10,
        tweet_fields=['created_at', 'text', 'author_id'],
        sort_order='recency',
        start_time=one_hour_ago
    )

    if not response.data:
        print("No tweets found in the last hour.")
        return

    # Filter out any lingering retweets by text prefix
    original_tweets = []
    for tweet in response.data:
        if not tweet.text.startswith('RT @'):
            original_tweets.append(tweet)

    if not original_tweets:
        print("No original tweets found in the last hour (all results were retweets or none matched).")
        return

    print(f"Found {len(original_tweets)} original tweets (no RTs/replies):\n")
    for i, tweet in enumerate(original_tweets, 1):
        print(f"--- {i} ---")
        print(f"Author ID: {tweet.author_id}")
        print(f"Time:      {tweet.created_at}")
        print(f"Text:      {tweet.text}")
        print(f"Tweet ID:  {tweet.id}")
        print(f"Link:      https://x.com/i/status/{tweet.id}")
        print()


if __name__ == '__main__':
    search()
