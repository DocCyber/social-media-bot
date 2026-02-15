# ##ADD Tag Variants - Quick Reference

## Overview

Use special tags in your replies to control how users are added to or removed from your rotation pool. **All variants are detected with a single search** - no extra API calls needed!

## Available Tags

### 1. ##ADD## (Default)
**Purpose:** Add user with neutral status

**Usage:**
```
@JokeAccount Great joke! ##ADD##
```

**Result:**
- User added to `user_data.csv`
- No friend/foe status set
- Standard priority

---

### 2. ##ADD-FRIEND##
**Purpose:** Add user and mark as friend

**Usage:**
```
@ComedyWriter Love your content! ##ADD-FRIEND##
```

**Result:**
- User added to `user_data.csv`
- `friend_foe` field set to `'friend'`
- When Claude generates replies, it will be more supportive and generous

**Why use it:** For accounts you want to engage with positively, allies, supporters

---

### 3. ##ADD-FOE##
**Purpose:** Add user and mark as foe

**Usage:**
```
@BadTakeAccount That's a terrible take. ##ADD-FOE##
```

**Result:**
- User added to `user_data.csv`
- `friend_foe` field set to `'foe'`
- When Claude generates replies, it can be more critical and sharp

**Why use it:** For adversarial accounts, debate opponents, accounts with bad takes

---

### 4. ##ADD-PRIORITY##
**Purpose:** Add user with high priority flag

**Usage:**
```
@ImportantAccount Great stuff! ##ADD-PRIORITY##
```

**Result:**
- User added to `user_data.csv`
- Higher priority value (for future priority-based rotation)
- Neutral friend/foe status

**Why use it:** For VIP accounts, high-engagement users, important voices

---

### 5. ##ADD-REMOVE##
**Purpose:** Remove user from rotation

**Usage:**
```
@SomeUser I don't want to engage anymore. ##ADD-REMOVE##
```

**Result:**
- User **removed** from `user_data.csv` entirely
- All their data deleted
- Won't appear in rotation

**Why use it:** To stop engaging with someone, clean up your rotation pool

---

## How It Works

### Single Search Query
The bot searches for **"##ADD"** (without trailing ##) which catches ALL variants:
- ##ADD##
- ##ADD-FRIEND##
- ##ADD-FOE##
- ##ADD-PRIORITY##
- ##ADD-REMOVE##

**Cost:** Zero extra API calls! Single search finds all variants.

### Post-Processing
After finding matches, the bot:
1. Reads the tweet text
2. Detects which variant was used
3. Takes appropriate action

## Console Output Examples

### Example 1: Multiple Variants

```
================================================================================
CHECKING FOR NEW ##ADD TAGS
================================================================================

[ADD TAG] Searching for ##ADD tags (all variants) since: 2026-02-09T14:30:00+00:00
[ADD TAG] Found 4 new ##ADD tags
[FRIEND] Processing @ComedyWriter from tweet 1234567890...
[DATA] Added new user @ComedyWriter
[ADD TAG] Added @ComedyWriter to user_data.csv as friend
[DEFAULT] Processing @JokeAccount from tweet 1234567891...
[DATA] Added new user @JokeAccount
[ADD TAG] Added @JokeAccount to user_data.csv
[FOE] Processing @BadTakes from tweet 1234567892...
[DATA] Added new user @BadTakes
[ADD TAG] Added @BadTakes to user_data.csv as foe
[REMOVE] Processing @ExUser from tweet 1234567893...
[REMOVE TAG] Removed @ExUser from user_data.csv
[ADD TAG] Updated last check time: 2026-02-10T02:00:00+00:00

================================================================================
[TAG SUMMARY]
  Added: 3
  Removed: 1
  Skipped: 0

  Variants used:
    DEFAULT: 1
    FOE: 1
    FRIEND: 1
    REMOVE: 1
================================================================================
```

### Example 2: All Friends

```
================================================================================
CHECKING FOR NEW ##ADD TAGS
================================================================================

[ADD TAG] Searching for ##ADD tags (all variants) since: 2026-02-10T02:00:00+00:00
[ADD TAG] Found 2 new ##ADD tags
[FRIEND] Processing @User1 from tweet 1234567900...
[DATA] Added new user @User1
[ADD TAG] Added @User1 to user_data.csv as friend
[FRIEND] Processing @User2 from tweet 1234567901...
[DATA] Added new user @User2
[ADD TAG] Added @User2 to user_data.csv as friend
[ADD TAG] Updated last check time: 2026-02-10T02:15:00+00:00

================================================================================
[TAG SUMMARY]
  Added: 2
  Removed: 0
  Skipped: 0

  Variants used:
    FRIEND: 2
================================================================================
```

## Tag Format Notes

### Flexible Formatting
Both formats work:
- `##ADD-FRIEND##` (with trailing ##)
- `##ADD-FRIEND` (without trailing ##)

The bot detects both automatically!

### Case Insensitive
All of these work:
- `##ADD-FRIEND##`
- `##add-friend##`
- `##Add-Friend##`

### Position Doesn't Matter
Tag can be anywhere in your tweet:
- Beginning: `##ADD-FRIEND## @User Great content!`
- Middle: `@User Great content! ##ADD-FRIEND## Love it!`
- End: `@User Great content! ##ADD-FRIEND##`

## Verification

### Check User Was Added
```bash
grep "username" user_data.csv
```

### Check Friend/Foe Status
```bash
grep "username" user_data.csv | cut -d',' -f23
# Shows the friend_foe field value
```

### Count Friends vs Foes
```bash
# Count friends
grep ",friend$" user_data.csv | wc -l

# Count foes
grep ",foe$" user_data.csv | wc -l

# Count neutral (no status)
grep ",$" user_data.csv | wc -l
```

## Tips

### Building a Friend Network
Tag supportive accounts as friends to build positive relationships:
```
@SupportiveAccount Thanks for the RT! ##ADD-FRIEND##
```

### Engaging with Critics
Tag adversaries as foes to enable sharper responses:
```
@CriticAccount Your criticism is noted. ##ADD-FOE##
```

### Prioritizing VIPs
Tag high-value accounts for future priority rotation:
```
@InfluencerAccount Great insight! ##ADD-PRIORITY##
```

### Cleaning Up
Remove users you no longer want to engage with:
```
@OldAccount Moving on. ##ADD-REMOVE##
```

### Mixing Variants
Use different tags for different users in the same session:
```
# Add three users with different statuses
@Friend Thanks! ##ADD-FRIEND##
@Neutral Good point. ##ADD##
@Adversary Disagree. ##ADD-FOE##
```

Then run the script once - all three get processed!

## Current Limitations

### Priority Not Yet Implemented
The `##ADD-PRIORITY##` tag sets a priority flag, but **CSV-based rotation doesn't use it yet**. This is for future enhancement when you implement priority-based or weighted rotation.

**Current behavior:**
- Tag still works
- User gets added normally
- Priority value stored (for future use)
- No effect on rotation order yet

### Friend/Foe Tone Adjustment
The friend/foe status **already works** in Claude reply generation! Check lines 392-395 in `TwitterAutoReply.py`:

```python
if friend_foe == 'friend':
    user_context_section += "\n⚠️ TONE NOTE: This is a friendly account..."
elif friend_foe == 'foe':
    user_context_section += "\n⚠️ TONE NOTE: This is an adversarial account..."
```

So marking someone as friend/foe **immediately affects** how the bot replies to them!

## Technical Details

### Search Query
```python
query = f'from:{auth_handle} is:reply "##ADD" -is:retweet'
```

This single query finds all variants because they all start with "##ADD".

**Note:** Uses `is:reply` instead of `filter:replies` for compatibility with pay-as-you-go API tier.

### Parsing Logic
After finding matches, the bot checks the tweet text for specific variants:
1. First checks for ##ADD-REMOVE## (special case - removes instead of adds)
2. Then checks for ##ADD-FRIEND##
3. Then checks for ##ADD-FOE##
4. Then checks for ##ADD-PRIORITY##
5. Falls back to default ##ADD## if none of the above

### Performance
- **Single API call** for all variants
- **Zero extra cost** compared to basic ##ADD##
- **Same speed** regardless of how many variants you use

## Summary Table

| Tag | Adds User | Sets Status | Priority | Effect |
|-----|-----------|-------------|----------|--------|
| ##ADD## | ✅ | None | Standard | Normal add |
| ##ADD-FRIEND## | ✅ | friend | Standard | Supportive tone |
| ##ADD-FOE## | ✅ | foe | Standard | Critical tone |
| ##ADD-PRIORITY## | ✅ | None | High | Future priority rotation |
| ##ADD-REMOVE## | ❌ | N/A | N/A | Removes from CSV |

---

**Remember:** All tags work with a **single search** - no extra API calls, no extra cost!
