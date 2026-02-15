import re
import random
import sys
import tweepy
from praise_templates import OPENING, STRUGGLE_ACK, STRUGGLE_ACK_2, REFRAME, CLOSING

SECRETS_FILE = r'd:\secrets\TwitterPayAsYouGo.txt'
MAX_CHARS = 280


def expand_template(text):
    """Replace {option1|option2|option3} patterns with a random choice."""
    return re.sub(
        r'\{([^{}]+)\}',
        lambda m: random.choice(m.group(1).split('|')),
        text
    )


def generate_post():
    """Generate a complete validation post from all template sections."""
    parts = [
        expand_template(random.choice(section))
        for section in [OPENING, STRUGGLE_ACK, STRUGGLE_ACK_2, REFRAME, CLOSING]
    ]
    return ' '.join(parts)


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


def post_to_twitter(text):
    """Authenticate and post a tweet. Returns the tweet ID on success."""
    consumer_key, consumer_secret, access_token, access_token_secret, bearer_token = load_twitter_credentials()

    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
        bearer_token=bearer_token
    )

    response = client.create_tweet(text=text)
    return response.data['id']


if __name__ == '__main__':
    post = generate_post()

    if len(post) > MAX_CHARS:
        print(f"WARNING: Post is {len(post)} chars, over {MAX_CHARS} limit. Regenerating...")
        for _ in range(20):
            post = generate_post()
            if len(post) <= MAX_CHARS:
                break
        else:
            print("Could not generate a post under the character limit after 20 attempts.")
            sys.exit(1)

    print(f"Post ({len(post)} chars):")
    print(post)
    print()

    tweet_id = post_to_twitter(post)
    print(f"Posted! Tweet ID: {tweet_id}")
