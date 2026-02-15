# ##ADD Tag Feature - Quick Start Guide

## What It Does

Automatically adds or removes users from `user_data.csv` when you reply to them with ##ADD tag variants in your tweet. This prepares for switching from `accounts.txt` to CSV-based rotation.

**5 variants available:**
- `##ADD##` - Default add
- `##ADD-FRIEND##` - Add as friend (supportive tone)
- `##ADD-FOE##` - Add as foe (critical tone)
- `##ADD-PRIORITY##` - Add with high priority
- `##ADD-REMOVE##` - Remove from rotation

**All variants detected with a single search** - zero extra API calls!

## How to Use

### Step 1: Tag Someone

Reply to any user with ##ADD## anywhere in your tweet:

```
@JokeAccount Great joke! ##ADD##
```

or

```
@ComedyWriter ##ADD## Love your content!
```

The ##ADD## tag can be anywhere in your tweet - beginning, middle, or end.

### Step 2: Run the Script

```bash
python TwitterAutoReply.py
```

### Step 3: Check the Output

You'll see output like this:

```
================================================================================
CHECKING FOR NEW ##ADD## TAGS
================================================================================

[CSV CHECK] CSV validated - 222 users in rotation pool
[ADD TAG] Searching for ##ADD## tags since: 2026-02-09T14:30:00+00:00
[ADD TAG] Found 1 new ##ADD## tags
[ADD TAG] Processing @JokeAccount from tweet 1234567890...
[DATA] Added new user @JokeAccount
[ADD TAG] Added @JokeAccount to user_data.csv
[ADD TAG] Updated last check time: 2026-02-10T01:45:00+00:00

================================================================================
[ADD TAG] SUMMARY: 1 added, 0 skipped (already in CSV)
================================================================================
```

### Step 4: Verify

Check that the user was added:

```bash
grep "JokeAccount" user_data.csv
```

## First Run vs. Subsequent Runs

### First Run
- Searches last 7 days for ##ADD## tags
- Creates `last_add_check.txt` with current timestamp
- May find multiple old tags if you used ##ADD## before

### Subsequent Runs
- Only searches since last timestamp
- Much faster and cheaper
- Only finds NEW tags since last run

## How It Works

1. **Searches Twitter** - Uses search API to find your replies with ##ADD##
2. **Extracts Username** - Gets the username you replied to
3. **Fetches User Data** - Gets their full profile info (bio, followers, etc.)
4. **Adds to CSV** - Saves them to `user_data.csv` with all their data
5. **Updates Timestamp** - Saves current time so next run only checks new replies

## Cost

**Zero cost if no ##ADD## tags found!**

- Uses pay-as-you-go Twitter API (same as rest of script)
- Only pays for actual results returned
- Timestamp tracking keeps searches small (only new replies)
- No extra API calls for user data (fetched with search)

## Deduplication

The feature prevents duplicates automatically:

1. **Already in CSV?** - Skips user with message: "User @username already in CSV (skipping)"
2. **Already checked?** - Timestamp tracking means old replies never searched again

## Files Created

### last_add_check.txt
- Contains timestamp of last ##ADD## check
- Auto-created on first run
- Example: `2026-02-10T01:45:00+00:00`

## Troubleshooting

### "No new ##ADD## tags found"

This is normal if:
- You haven't used ##ADD## since last run
- First run and you haven't used ##ADD## in last 7 days

### "Error searching for ##ADD## tags"

Check:
1. Bearer token is in your credentials file
2. Twitter API access is working
3. You're authenticated as the correct account

### User not added even though I tagged them

Check:
1. Tag was in YOUR reply (not someone else's)
2. Tag is exactly "##ADD##" (case-sensitive)
3. Reply wasn't deleted
4. User already exists in CSV (check with grep)

## Testing

Run the test suite to verify everything is working:

```bash
python test_add_tag_feature.py
```

Should show:

```
Result: 4/4 tests passed
[SUCCESS] All tests passed! Feature is ready to use.
```

## Integration with Normal Bot Flow

The ##ADD## tag check happens:
1. **Once at startup** - Before normal rotation begins
2. **Silently** - Doesn't interfere with reply logic
3. **Safely** - If it fails, script continues normally

Normal rotation flow:
```
Start Script
  ↓
Check CSV integrity
  ↓
Search for ##ADD## tags  ← NEW FEATURE
  ↓
Process normal rotation (223 cycles)
  ↓
End Script
```

## Next Steps (Coming Soon)

### Switch to CSV-Based Rotation

Currently the script uses `accounts.txt` for rotation. Soon it will switch to using `user_data.csv`, which means:

1. All ##ADD## users automatically in rotation
2. No manual `accounts.txt` updates needed
3. Engagement metrics tracked automatically
4. Easy to enable/disable users without deleting

### Migration is Simple

Just replace the `load_accounts()` function to read from CSV instead of accounts.txt. All rotation logic stays the same!

## Tips

### Tag Multiple People

You can tag multiple people in one session:

```
@User1 Great joke! ##ADD##
@User2 Love this! ##ADD##
@User3 So funny! ##ADD##
```

Then run the script once - it finds all three!

### Tag While Engaging

Use ##ADD## naturally while building relationships:

```
@ComedyWriter Your dad jokes are top-tier! Would love to engage more. ##ADD##
```

The bot handles the rest automatically.

### Check Your CSV Regularly

See how many users you've added:

```bash
wc -l user_data.csv
# or on Windows:
find /c /v "" user_data.csv
```

Subtract 1 for header row to get actual user count.

## Advanced Usage

### View Timestamp

Check when you last ran the script:

```bash
cat last_add_check.txt
```

Shows: `2026-02-10T01:45:00+00:00`

### View CSV Users

List all users in CSV:

```bash
cut -d',' -f1 user_data.csv | tail -n +2
```

### Search for Specific User

```bash
grep "username" user_data.csv
```

### Count Users by Status

```bash
# Count friends
grep ",friend$" user_data.csv | wc -l

# Count foes
grep ",foe$" user_data.csv | wc -l

# Count neutral (empty friend_foe)
grep ",$" user_data.csv | wc -l
```

## Summary

**The ##ADD## tag feature makes user management automatic:**

✅ Reply with ##ADD## → User added to CSV
✅ Run script → Checks for new tags
✅ Zero cost if no tags found
✅ No duplicates (automatic dedup)
✅ Full user data captured
✅ Ready for CSV-based rotation

**Just tag and forget - the bot handles the rest!**
