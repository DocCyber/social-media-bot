# Engagement Tracking for Account Curation

## Summary
Added engagement metrics to user_data.csv to help identify the best accounts for continued interaction. These metrics allow you to calculate an **engagement opportunity rate** for each account and curate your accounts.txt list based on real performance data.

## New CSV Fields

### Existing Field (Already Tracked):
- **times_checked** - Total number of times we've looked at this account

### Engagement Metrics:
- **times_replied** - Number of successful replies posted to this account
- **times_skipped** - Number of times Claude returned SKIP (not a good engagement opportunity)
- **times_no_tweet** - Number of times no qualifying tweet was found (no recent posts, or only replies/retweets)

### Relationship Marker (NEW):
- **friend_foe** - Optional marker to adjust reply tone
  - `'friend'` - Be warmer, more generous, supportive even if tweet is ambiguous
  - `'foe'` - Be sharper, more critical/pointed in responses
  - `''` (empty) - Neutral tone, follow normal voice rules

## Key Metric: Engagement Opportunity Rate

**Formula:**
```
Engagement Rate = times_replied / times_checked
```

This tells you what percentage of checks result in a successful engagement opportunity.

**Example:**
- Account A: 10 checked, 8 replied → **80% engagement rate** ⭐
- Account B: 10 checked, 2 replied → **20% engagement rate**

Account A is a much better target for continued engagement!

## When Metrics Are Incremented

### times_checked (Existing)
**When:** Every time we fetch user info from Twitter
**Where:** In `update_user_data()` - happens when `get_random_user_tweet()` successfully gets user object
**Code Location:** Line ~296-302

### times_no_tweet (NEW)
**When:** User exists but no qualifying tweet found in lookback window
**Reasons:**
- User hasn't posted in last 12 hours
- User only posted replies or retweets (we exclude these)
- Protected account
**Code Location:** Line ~595-597

### times_skipped (NEW)
**When:** Claude analyzes the tweet and returns "SKIP"
**Reasons:**
- Tweet isn't a good engagement opportunity
- Topic doesn't align with our voice
- Would be awkward or forced to reply
**Code Location:** Line ~619-621

### times_replied (NEW)
**When:** Successfully posted a reply to Twitter
**Code Location:** Line ~643-644

## Console Output

When metrics are incremented, you'll see:
```
[ENGAGEMENT] @username times_no_tweet: 2 → 3
[ENGAGEMENT] @username times_skipped: 1 → 2
[ENGAGEMENT] @username times_replied: 5 → 6
```

## Using Data for Curation

### Step 1: Let Bot Run
Run 200+ cycles to collect meaningful data on all accounts.

### Step 2: Analyze the CSV
Open `user_data.csv` in Excel/LibreOffice and add a calculated column:
```
engagement_rate = times_replied / times_checked
```

### Step 3: Sort by Engagement Rate
Sort descending to see best performers at top.

### Step 4: Identify Patterns

**High Engagement (>50%):**
- Keep these accounts! They consistently post content worth engaging with
- Example: Dad joke accounts, comedy writers, specific topic experts

**Medium Engagement (20-50%):**
- Review case by case
- Check if they post inconsistently or on variable topics

**Low Engagement (<20%):**
- Consider removing from accounts.txt
- Reasons might be:
  - Rarely posts (high times_no_tweet)
  - Posts content that doesn't fit our voice (high times_skipped)
  - Mostly posts replies/retweets (high times_no_tweet)

### Step 5: Curate accounts.txt
Remove low performers, add similar accounts to high performers.

## Example Analysis

### Sample CSV Data After 200 Cycles:

| username | times_checked | times_replied | times_skipped | times_no_tweet | engagement_rate |
|----------|--------------|---------------|---------------|----------------|-----------------|
| @DadJokes | 8 | 7 | 1 | 0 | **87.5%** ⭐⭐⭐ |
| @ComedyCentral | 8 | 5 | 2 | 1 | **62.5%** ⭐⭐ |
| @RandomTweeter | 8 | 1 | 3 | 4 | **12.5%** ❌ |
| @NewsBot | 8 | 0 | 1 | 7 | **0%** ❌ |

**Analysis:**
- **@DadJokes**: Amazing! 7/8 checks resulted in replies. Keep this account!
- **@ComedyCentral**: Good performer, posts consistently engaging content
- **@RandomTweeter**: Low rate - mostly no qualifying tweets. Consider removing.
- **@NewsBot**: Zero engagement - probably posts too infrequently or wrong content type. Remove.

## Advanced Curation Queries

### Find Accounts That Post Consistently But We Skip
```
times_no_tweet = 0 AND times_skipped > 3
```
These accounts post regularly but Claude doesn't like the content fit.

### Find Accounts That Rarely Post
```
times_no_tweet / times_checked > 0.6
```
Over 60% of checks found no qualifying tweet.

### Find "Sure Thing" Accounts
```
times_replied / times_checked > 0.7
```
Over 70% success rate - these are your core accounts!

## Building the Perfect accounts.txt

### Strategy:
1. **Identify your top 5-10 performers** (highest engagement rate)
2. **Find similar accounts:**
   - Check who they follow
   - Check who follows them
   - Look for accounts with similar bios/content
3. **Add them to accounts.txt**
4. **Run another 200 cycles** to test new accounts
5. **Repeat the curation process**

### Result:
Over time, you'll build a curated list of accounts that consistently provide good engagement opportunities, maximizing the value of each cycle.

## CSV Columns Reference

Complete list of columns in user_data.csv:

**Profile Data:**
- username, user_id, name, created_at, description, location, url
- profile_image_url, verified, verified_type, protected

**Metrics:**
- followers_count, following_count, tweet_count, listed_count, like_count

**Tracking:**
- pinned_tweet_id, last_updated

**Engagement Analytics:**
- times_checked, times_replied, times_skipped, times_no_tweet

**Relationship Markers:**
- friend_foe (empty/'friend'/'foe')

## Maintenance

### Resetting Stats
To reset engagement tracking for all accounts:
1. Delete user_data.csv
2. Next run will recreate it with fresh counters

### Resetting One Account
1. Open user_data.csv
2. Find the account row
3. Set times_checked, times_replied, times_skipped, times_no_tweet to 0
4. Save

## Implementation Details

### New Function: `increment_user_metric(username, metric_name)`
**Purpose:** Atomically increment a single engagement metric for a user
**Parameters:**
- `username` - Twitter handle (without @)
- `metric_name` - One of: 'times_replied', 'times_skipped', 'times_no_tweet'

**Behavior:**
1. Loads current CSV data
2. Finds user record
3. Increments specified metric by 1
4. Saves back to CSV
5. Prints confirmation: `[ENGAGEMENT] @user metric: old → new`

### Data Preservation
When updating user data (e.g., refreshing follower counts), engagement metrics are **preserved** from the previous record. Only times_checked increments automatically - the other metrics only change when explicitly incremented.

## Example Workflow

**Cycle 1:**
```
[ROTATION] Selected account 1/25: @DadJokes
[DATA] Updated user @DadJokes (check #1)
...
[ENGAGEMENT] @DadJokes times_replied: 0 → 1
[SUCCESS] REPLY POSTED!
```

**Cycle 2:**
```
[ROTATION] Selected account 2/25: @NewsBot
[DATA] Updated user @NewsBot (check #1)
No qualifying original posts from @NewsBot in last 12h.
[ENGAGEMENT] @NewsBot times_no_tweet: 0 → 1
```

**Cycle 3:**
```
[ROTATION] Selected account 3/25: @PoliticalTweets
[DATA] Updated user @PoliticalTweets (check #1)
...
AI decided not to reply to this tweet (not a good engagement opportunity)
[ENGAGEMENT] @PoliticalTweets times_skipped: 0 → 1
```

After 200 cycles, check user_data.csv to see which accounts performed best!

## Friend/Foe Relationship Markers

### Purpose
The `friend_foe` field allows you to influence Claude's tone when replying to specific accounts. This is useful for:
- **Friends**: Accounts you want to support and build relationships with
- **Foes**: Adversarial accounts where you want sharper, more critical responses

### How It Works

**When generating replies, Claude receives user context including:**
1. The user's Twitter bio
2. The friend/foe marker (if set)
3. Tone guidance based on the marker

**Friend marker adds this to Claude's prompt:**
> ⚠️ TONE NOTE: This is a friendly account. Be generous, supportive, and warm even if their tweet is ambiguous or you might disagree. Give them the benefit of the doubt.

**Foe marker adds this to Claude's prompt:**
> ⚠️ TONE NOTE: This is an adversarial account. You can be more critical, sharp, or pointed in your response. Don't hold back if their take is bad.

**No marker (neutral):**
Claude still receives the user's bio for context but follows normal voice rules without specific tone guidance.

### Managing Friend/Foe Markers

**Using the helper script (recommended):**

```bash
# List all marked accounts
python manage_friend_foe.py list

# Mark an account as friend
python manage_friend_foe.py set @DadJokes friend

# Mark an account as foe
python manage_friend_foe.py set @HardRightTakes foe

# Remove marker (back to neutral)
python manage_friend_foe.py clear @DadJokes
```

**Manual editing:**
You can also edit `user_data.csv` directly and set the `friend_foe` column to:
- `friend`
- `foe`
- Empty (neutral)

### Console Output

When a marked account is selected, you'll see:

```
[ROTATION] Selected account 5/25: @DadJokes
[CONTEXT] Bio: Posting dad jokes daily to make you groan
[CONTEXT] Relationship: friend
Generating AI reply with Claude...
```

For neutral accounts (no marker):
```
[ROTATION] Selected account 8/25: @RandomUser
[CONTEXT] Bio: I post random thoughts about tech
Generating AI reply with Claude...
```

### Best Practices

**Mark as Friend:**
- Accounts you genuinely like and want to support
- Accounts in your "community" or niche
- Comedy accounts where you want to be encouraging
- Small accounts you're trying to help grow

**Mark as Foe:**
- Hard-right or hard-left political accounts you disagree with
- Engagement bait accounts with bad takes
- Accounts where critical/pointed replies get better engagement
- Use sparingly - too many foes can hurt your account reputation

**Leave Neutral (most accounts):**
- Most accounts should be neutral
- Let Claude judge each tweet on its merits
- Saves friend/foe markers for accounts where relationship really matters

### Curation Strategy

1. **Run 50-100 cycles with all accounts neutral**
2. **Review which accounts you naturally vibe with**
3. **Mark 3-5 accounts as friends** (your core community)
4. **Mark 1-2 accounts as foes** (if you do adversarial engagement)
5. **Keep most accounts neutral**

### Future Enhancements

Planned features for friend_foe:
- **Auto-detection**: High engagement rate → auto-suggest friend
- **Bio scanning**: Keywords (MAGA, liberal, etc.) → suggest foe
- **Gradations**: close_friend, friend, neutral, foe, enemy
- **Context expansion**: Follower count, verified status in prompts

### Implementation Notes

**When markers are used:**
- Every reply generation receives user bio (from CSV)
- Friend/foe marker influences tone if set
- Marker is preserved across CSV updates
- Must be in CSV before marking (user must be checked at least once)

**Data flow:**
```
get_random_user_tweet()
  → Updates user_data.csv with fresh bio
    ↓
main() loads user from CSV
  → Extracts bio + friend_foe
    ↓
generate_ai_reply(user_context)
  → Claude receives bio + tone guidance
```
