# CSV-Based Rotation Guide

## What Changed

### Before (accounts.txt)
- Read usernames from `accounts.txt`
- Sequential rotation with `account_index.txt` tracking
- No user data, no friend/foe context
- Equal coverage of all accounts

### After (user_data.csv)
- Read usernames from `user_data.csv`
- **Always starts from the top** - no index tracking
- Full user data available (bio, followers, engagement metrics)
- Friend/foe context **automatically passed to Claude**
- Focus on **engagement over coverage**

## How It Works

### 1. Load Accounts from CSV

```python
def load_accounts():
    # Loads usernames from user_data.csv in order
    # Returns: ['user1', 'user2', 'user3', ...]
```

### 2. Always Pick First User

```python
def get_next_username(all_usernames):
    # Always returns all_usernames[0]
    # No index tracking, always starts from top
```

### 3. Friend/Foe Context Passed to Claude

**Already implemented!** Lines 952-967:

```python
# Load user data from CSV to pass context to Claude
user_data_dict = load_user_data_csv()
user_record = user_data_dict.get(username, {})
user_bio = user_record.get('description', '')
friend_foe_status = user_record.get('friend_foe', '')

# Build user context dict
user_context = {
    'username': username,
    'bio': user_bio,
    'friend_foe': friend_foe_status
}

# Pass to Claude
ai_reply, should_retweet = generate_ai_reply(voice_content, tweet_text, api_key, user_context)
```

Claude receives:
- Username
- User's bio
- Friend/foe status ('friend', 'foe', or '')

Claude's tone adjusts automatically:
- **Friend** → Supportive, generous, warm
- **Foe** → Critical, sharp, pointed
- **Neutral** → Normal engagement tone

## Sorting Your CSV for Maximum Engagement

Since the bot **always picks the first user**, you should **sort your CSV by engagement priority**.

### Recommended Sort Order

**Option 1: By Engagement Rate (Best)**
```python
# Sort by: times_replied / times_checked (highest first)
# Users who get good replies consistently
```

**Option 2: By Priority + Friend Status**
```python
# Sort by:
# 1. Friends first (friend_foe = 'friend')
# 2. Then by engagement rate
# 3. Neutral users next
# 4. Foes last (if you still want to engage)
```

**Option 3: By Recent Success**
```python
# Sort by: times_replied (most replies first)
# Users you've successfully engaged with
```

### How to Sort Your CSV

#### Using Python (Quick Script)

```python
import csv
import pandas as pd

# Load CSV
df = pd.read_csv('user_data.csv')

# Calculate engagement rate
df['engagement_rate'] = df['times_replied'] / df['times_checked'].replace(0, 1)

# Sort by engagement rate (highest first)
df_sorted = df.sort_values('engagement_rate', ascending=False)

# Save back to CSV (overwrite)
df_sorted.to_csv('user_data.csv', index=False)

print(f"Sorted {len(df)} users by engagement rate")
print("\nTop 5 users:")
print(df_sorted[['username', 'engagement_rate', 'times_replied', 'times_checked']].head())
```

#### Using Excel/LibreOffice

1. Open `user_data.csv` in Excel
2. Select all data (Ctrl+A)
3. Go to Data → Sort
4. Sort by: Calculate engagement rate column first, or use times_replied
5. Order: Largest to Smallest
6. Save as CSV

### Example Sorted CSV

```csv
username,user_id,...,times_checked,times_replied,times_skipped,friend_foe
HighEngageUser,123,    ...,50,45,5,friend        # 90% engagement rate
MediumEngageUser,456,  ...,40,25,15,friend       # 62.5% engagement rate
NewFriend,789,         ...,10,7,3,friend         # 70% engagement rate
NeutralUser,101,       ...,30,15,15,              # 50% engagement rate
LowEngageUser,102,     ...,20,5,15,               # 25% engagement rate
FoeAccount,103,        ...,15,10,5,foe            # 66% but marked as foe
```

**Bot will always pick `HighEngageUser` first** since they're at the top.

## CSV Data Fields

### Used by Bot
- ✅ **username** - Required for selection
- ✅ **description** (bio) - Passed to Claude for context
- ✅ **friend_foe** - Tone adjustment ('friend', 'foe', '')

### Used for Sorting
- ✅ **times_checked** - How many times checked
- ✅ **times_replied** - How many times bot replied
- ✅ **times_skipped** - How many times skipped
- ✅ **times_no_tweet** - How many times had no qualifying tweet

### Kept for Reference (Not Used by Bot)
- 📊 **user_id** - Twitter ID
- 📊 **name** - Display name
- 📊 **created_at** - Account creation date
- 📊 **location** - User location
- 📊 **url** - User website
- 📊 **profile_image_url** - Avatar URL
- 📊 **verified** - Verification status
- 📊 **verified_type** - Type of verification
- 📊 **protected** - Protected account flag
- 📊 **followers_count** - Follower count
- 📊 **following_count** - Following count
- 📊 **tweet_count** - Total tweets
- 📊 **listed_count** - Listed count
- 📊 **like_count** - Total likes
- 📊 **pinned_tweet_id** - Pinned tweet
- 📊 **last_updated** - Last data fetch

**All data is preserved!** Just not actively used for rotation logic.

## Console Output Examples

### Starting Bot

```
Loading target accounts...
[CSV ROTATION] Loaded 222 accounts from user_data.csv
[CSV ROTATION] Always starting from top - ensure CSV is sorted by engagement!
[OK] Loaded 222 accounts

Fetching next user's tweet...
[CSV ROTATION] Selected top account: @HighEngageUser
[CSV ROTATION] Total accounts in pool: 222
```

### With Friend Context

```
[CONTEXT] Bio: Comedy writer | Dad jokes enthusiast | Follow for daily laughs
[CONTEXT] Relationship: friend

Generating AI reply with Claude...
(Claude uses supportive tone because friend_foe = 'friend')
```

### With Foe Context

```
[CONTEXT] Bio: Political pundit | Hot takes daily
[CONTEXT] Relationship: foe

Generating AI reply with Claude...
(Claude uses critical/sharp tone because friend_foe = 'foe')
```

## Best Practices

### 1. Sort CSV Before Each Run

Since the bot always picks from top, keep your CSV freshly sorted:

```bash
# Create a quick sort script
python sort_csv_by_engagement.py
python TwitterAutoReply.py
```

### 2. Use [[ADD]] Tags to Build Your List

```
@NewUser Great content! [[ADD-FRIEND]]
```

Automatically adds to CSV with friend status.

### 3. Mark Low Performers as Foe or Remove

If someone consistently has no good tweets:

```
@LowEngager Not working out. [[ADD-REMOVE]]
```

Or mark as foe to use critical tone.

### 4. Monitor Engagement Metrics

Check your CSV regularly:

```bash
# See top performers
head -20 user_data.csv

# Count by status
grep ",friend$" user_data.csv | wc -l
grep ",foe$" user_data.csv | wc -l
```

### 5. Re-sort After Each Cycle

After running 2-3 cycles (which updates metrics), re-sort:

```python
# Quick re-sort script
import pandas as pd
df = pd.read_csv('user_data.csv')
df['engagement_rate'] = df['times_replied'] / df['times_checked'].replace(0, 1)
df.sort_values('engagement_rate', ascending=False).to_csv('user_data.csv', index=False)
```

## Migration from accounts.txt

### What Happens to accounts.txt?

**It's no longer used.** The bot now reads from `user_data.csv`.

### Are Those Users in CSV?

Check which accounts.txt users are already in CSV:

```python
# Check migration status
with open('accounts.txt') as f:
    txt_users = [line.strip() for line in f if line.strip()]

import csv
with open('user_data.csv') as f:
    csv_users = [row['username'] for row in csv.DictReader(f)]

missing = set(txt_users) - set(csv_users)
print(f"Users in accounts.txt but not in CSV: {len(missing)}")
for user in missing:
    print(f"  - {user}")
```

### Add Missing Users

For any users in accounts.txt but not in CSV:

1. Reply to them with `[[ADD]]` tag
2. Run the script once
3. They'll be auto-added

Or manually add via the API fetch (one-time):

```python
# Quick add script
import tweepy
from TwitterAutoReply import load_twitter_credentials, update_user_data

consumer_key, consumer_secret, access_token, access_token_secret, bearer_token = load_twitter_credentials()
client = tweepy.Client(
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    access_token=access_token,
    access_token_secret=access_token_secret,
    bearer_token=bearer_token
)

missing_users = ['user1', 'user2', 'user3']  # From check above

for username in missing_users:
    try:
        user_response = client.get_user(username=username, user_fields=['created_at', 'description', 'public_metrics'])
        if user_response.data:
            update_user_data(username, user_response.data)
            print(f"Added {username}")
    except Exception as e:
        print(f"Error adding {username}: {e}")
```

## Advantages of CSV Rotation

### 1. Focus on Engagement
- Always engage with your best-performing accounts first
- No time wasted on low-engagement users

### 2. Smart Tone Adjustment
- Friend/foe context automatically adjusts Claude's tone
- Build positive relationships with friends
- Use critical tone with adversaries

### 3. Rich User Data
- Bio context helps Claude craft better replies
- Engagement metrics inform who to prioritize
- Full Twitter profile data for reference

### 4. Easy Management
- Sort CSV to change priorities instantly
- Use [[ADD]] tags to grow your list
- Use [[ADD-REMOVE]] to clean up

### 5. No Coverage Anxiety
- Don't need to reply to everyone
- Focus on high-value accounts
- Better engagement = better growth

## Summary

**Old way (accounts.txt):**
- Sequential rotation
- Equal coverage
- No context
- No prioritization

**New way (user_data.csv):**
- Always start from top
- Focus on best accounts
- Friend/foe context
- Sort by engagement

**Result:** Better replies, better engagement, better growth! 🚀
