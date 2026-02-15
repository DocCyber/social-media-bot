# User Category Guide

## All Available Categories

### 1. **Neutral** (Default)
**Tag:** `[[ADD]]`
**Status:** `` (empty)
**Tone:** Normal engagement, balanced

### 2. **Friend**
**Tag:** `[[ADD-FRIEND]]`
**Status:** `friend`
**Tone:** Supportive, warm, generous
**Use for:** Allies, supporters, positive accounts

### 3. **Foe**
**Tag:** `[[ADD-FOE]]`
**Status:** `foe`
**Tone:** Critical, sharp, pointed
**Use for:** Adversaries, accounts with bad takes

### 4. **Jokster** ⭐ NEW
**Tag:** `[[ADD-JOKSTER]]`
**Status:** `jokster`
**Tone:** Witty banter, playful, comedian-to-comedian
**Special:** **AVOIDS politics** - focuses on pure comedy
**Use for:** Comedians, joke accounts, people who make you laugh

**Example jokster:**
- mariana Z: "Mixed up my pizza app and my dating app... Now there's a 16 inch vegetarian at my door."
- Should get playful wordplay, NOT political commentary

### 5. **Snark** ⭐ NEW
**Tag:** `[[ADD-SNARK]]`
**Status:** `snark`
**Tone:** Sarcastic, dry humor, clever burns
**Use for:** Sarcastic accounts, people who appreciate sharp wit

## How It Works

### Tagging Example

**Jokster:**
```
@mariana057 Your jokes kill me! [[ADD-JOKSTER]]
```

**Snark:**
```
@SarcasticUser Love the snark [[ADD-SNARK]]
```

### What Claude Sees

When replying to a **jokster**:
```
⚠️ TONE NOTE: This is a JOKSTER - they make jokes and enjoy witty banter.
Match their playful energy with clever wordplay and humor. Keep it light
and FUN. AVOID political commentary or hot-button issues - focus on pure
comedy and playful teasing. Think comedian-to-comedian banter, not
pundit-to-pundit debate.
```

When replying to **snark**:
```
⚠️ TONE NOTE: This is a SNARK account - they use sarcasm and sharp wit.
You can be sarcastic back, use dry humor, and employ clever burns. Snarky
energy is welcome here.
```

## Comparison Table

| Category | Tone | Politics OK? | Use Case |
|----------|------|--------------|----------|
| Neutral | Balanced | Yes | Unknown accounts |
| Friend | Supportive | Yes | Allies, supporters |
| Foe | Critical | Yes | Adversaries |
| **Jokster** | Playful | **NO** | Comedians, jokers |
| **Snark** | Sarcastic | Yes | Snarky accounts |

## Real Example: Jokster vs Neutral

### Original Tweet (mariana Z)
"Mixed up my pizza app and my dating app... Now there's a 16 inch vegetarian at my door."

### Neutral Reply (What happened)
"Could be worse. Could've been a 16 inch libertarian. At least the vegetarian won't lecture you about age of consent laws while you're trying to eat."

**Problem:** Too political (libertarian, age of consent laws)

### Jokster Reply (What should happen)
"At least the vegetarian won't try to convince you pineapple belongs on pizza. That's the real relationship dealbreaker."

**Better:** Playful, stays on topic (pizza/relationships), no politics!

## Usage

### Mark mariana Z as jokster:
```
@mariana057 Your jokes are always gold! [[ADD-JOKSTER]]
```

Then run:
```bash
python TwitterAutoReply.py
```

Next time the bot replies to her, it will:
- ✅ Focus on comedy and wordplay
- ✅ Match her playful energy
- ❌ Avoid political commentary
- ❌ Skip hot-button issues

## Manual CSV Editing

You can also edit `user_data.csv` directly:

```csv
username,user_id,...,friend_foe
mariana057,123,...,jokster
SnarkyAccount,456,...,snark
FriendAccount,789,...,friend
FoeAccount,101,...,foe
```

## All Tags Reference

```
[[ADD]]           - Neutral
[[ADD-FRIEND]]    - Friend
[[ADD-FOE]]       - Foe
[[ADD-JOKSTER]]   - Jokster (avoid politics, pure comedy)
[[ADD-SNARK]]     - Snark (sarcasm welcome)
[[ADD-PRIORITY]]  - High priority (any category)
[[ADD-REMOVE]]    - Remove from rotation
```

## Summary

**Jokster** = Comedian energy, playful banter, NO politics
**Snark** = Sarcastic wit, dry humor, clever burns

Use `[[ADD-JOKSTER]]` for accounts like mariana Z who make jokes and want witty, non-political replies!
