# Sequential Account Rotation Change

## Summary
Changed TwitterAutoReply.py from **random account selection** to **sequential order** selection. This ensures all accounts in accounts.txt are checked in order without duplicates or skips.

## Why This Change?

### Old System (Random with Used List):
- ❌ Picked random accounts from "available" pool
- ❌ Tracked last 15 used accounts to avoid duplicates
- ❌ Could hit some accounts multiple times before checking others
- ❌ Less predictable rotation
- ❌ More complex code with used_accounts.txt management

### New System (Sequential Index):
- ✅ Goes through accounts.txt in order (line by line)
- ✅ Guarantees every account gets checked before repeating
- ✅ Simpler, more predictable behavior
- ✅ Uses simple account_index.txt to track position
- ✅ Automatically wraps to start when reaching end

## Changes Made

### 1. Replaced File Constants
**Before:**
```python
USED_ACCOUNTS_FILE = 'used_accounts.txt'
DEFAULT_USED_LIST_SIZE = 15
```

**After:**
```python
ACCOUNT_INDEX_FILE = 'account_index.txt'
# (Removed DEFAULT_USED_LIST_SIZE - no longer needed)
```

### 2. Replaced Complex Functions with Simple Index Tracking

**Removed:**
- `load_used_accounts()` - 30+ lines of code
- `save_used_accounts()` - 10+ lines of code
- `mark_account_used()` - 10+ lines of code
- `get_available_username()` - Random selection from filtered list

**Added:**
- `load_account_index()` - Simple integer read
- `save_account_index()` - Simple integer write
- `get_next_username()` - Sequential selection with auto-increment

### 3. Updated Function Calls
**Before:**
```python
selected_username = get_available_username(usernames)
# Later...
mark_account_used(username)
```

**After:**
```python
selected_username = get_next_username(usernames)
# No need to mark as used - index auto-advances
```

### 4. Removed Random Import
No longer using `random.choice()`, so removed:
```python
import random
```

## How It Works

### account_index.txt Format
Simple one-line file containing just the current index:
```
0
```
or
```
5
```

### Execution Flow

**Cycle 1:**
- Read account_index.txt → `0`
- Select accounts.txt line 0 → `@FirstAccount`
- Save account_index.txt → `1`
- Print: `[ROTATION] Selected account 1/10: @FirstAccount`

**Cycle 2:**
- Read account_index.txt → `1`
- Select accounts.txt line 1 → `@SecondAccount`
- Save account_index.txt → `2`
- Print: `[ROTATION] Selected account 2/10: @SecondAccount`

**Cycle 10:**
- Read account_index.txt → `9`
- Select accounts.txt line 9 → `@TenthAccount`
- Save account_index.txt → `10`
- Print: `[ROTATION] Selected account 10/10: @TenthAccount`

**Cycle 11 (Wrap Around):**
- Read account_index.txt → `10`
- Index >= 10 (list length), so reset to `0`
- Select accounts.txt line 0 → `@FirstAccount`
- Save account_index.txt → `1`
- Print: `[ROTATION] Wrapped back to start of account list`
- Print: `[ROTATION] Selected account 1/10: @FirstAccount`

### Index Advances Even if No Tweet
The index advances **immediately** when an account is selected, regardless of whether:
- User has recent tweets
- We get a valid tweet
- We successfully post a reply

This ensures we don't get stuck retrying the same account repeatedly.

## Example Console Output

```
[ROTATION] Selected account 1/25: @SaysDadJokes
User: Dad Jokes | Followers: 50000 | Following: 100
Bio: Daily dad jokes to make you groan...

Most recent original post by @SaysDadJokes (2026-02-07 14:30:00 UTC):
--------------------------------------------------------------------------------
I used to hate facial hair, but then it grew on me.
--------------------------------------------------------------------------------
```

Next cycle:
```
[ROTATION] Selected account 2/25: @ComedyCentral
```

When it wraps:
```
[ROTATION] Wrapped back to start of account list
[ROTATION] Selected account 1/25: @SaysDadJokes
```

## Benefits

### 1. Fair Rotation
Every account gets checked exactly once before any account is checked twice.

### 2. Predictable
You know exactly which accounts will be checked next by looking at account_index.txt.

### 3. No Gaps
With random selection, some accounts might not get checked for long periods. Sequential guarantees coverage.

### 4. Simpler Code
Reduced from ~50 lines of rotation logic to ~25 lines. Easier to understand and maintain.

### 5. Easy to Reset
Want to start over? Just delete account_index.txt or set it to 0.

### 6. Easy to Skip Accounts
Want to skip certain accounts temporarily? Just move them to bottom of accounts.txt.

## Migration

### Old Files (Can be Deleted)
- `used_accounts.txt` - No longer used

### New Files (Auto-Created)
- `account_index.txt` - Tracks current position (0-based index)

### No Action Required
The code will automatically:
- Create account_index.txt if it doesn't exist (starts at 0)
- Work with existing accounts.txt without changes
- Handle wrap-around automatically

## Testing

After this change, run a few cycles and verify:
1. First cycle selects account #1 from accounts.txt
2. Second cycle selects account #2
3. Continues in order through the list
4. When reaching end, wraps back to #1
5. Console shows: `[ROTATION] Selected account X/Y: @username`

## Compatibility

✅ **Fully compatible** with existing setup:
- Same accounts.txt format
- Same deduplication (replied_tweets.txt still works)
- Same user data CSV tracking
- Same joke detection and retweet features

The **only** change is the account selection algorithm: random → sequential.
