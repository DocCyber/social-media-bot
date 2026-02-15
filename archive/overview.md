# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Bot
- **Main launcher**: `python main_launcher.py` - Simple launcher that runs BlueSky and Twitter posting on scheduled intervals
- **Legacy core**: `python newcore.py` - Original comprehensive launcher (references many modules)
- **Direct BlueSky posting**: `python bsky/bsky.py` - Post individual jokes to BlueSky
- **Direct Twitter posting**: `python tweet/tweet.py` - Post individual jokes to Twitter/X
- **BlueSky interactions**: `python bsky/launcher.py` - Run BlueSky social interactions

### Testing
- No formal test framework is configured (pytest not available)
- Use individual test files: `test_platforms.py`, `test_bluesky_consolidated.py`, `test_automation_comprehensive.py`, `test_monitoring_comprehensive.py`
- Run tests with: `python test_[name].py`

### Monitoring & Dashboards
- **Automation dashboard**: `python automation_dashboard.py`
- **Monitoring dashboard**: `python monitoring_dashboard.py`

## High-Level Architecture

### Current Working Structure

**Main Launcher (`main_launcher.py`)**
- Simple scheduler using the `schedule` library
- Coordinates BlueSky and Twitter posting
- BlueSky interactions every 5 minutes and hourly
- Twitter/X posting on even hours at :30 (02:30, 04:30, etc.)
- Calls additional bots: `bskyBESTTHING.py` and `bsky_taunt/`

**Legacy Core (`newcore.py`)**
- Original comprehensive launcher with Instagram, Mastodon, comics
- References modules that may not all be present in current structure
- Uses subprocess calls to `bsky/launcher.py`

**Platform Implementation**
- **BlueSky**: `bsky/` directory with core posting and interaction modules
- **Twitter/X**: `tweet/` directory with simple OAuth1 posting
- **Mastodon**: `toot/` directory (legacy, may be incomplete)

### Key Working Files

**BlueSky (`bsky/`)**
- `bsky.py`: Core joke posting with session management
- `launcher.py`: Social interaction coordinator
- `process_interactions.py`: Process notifications and interactions
- `modules/`: Individual interaction modules (follow, reply, reactions, etc.)
- `config.json`, `keys.json`: BlueSky-specific configuration

**Twitter/X (`tweet/`)**
- `tweet.py`: Simple Twitter posting with OAuth1 authentication

**Special Bots**
- `bskyBESTTHING.py`: "Best thing" posting bot
- `bsky_taunt/`: Taunt bot directory

**Data & Configuration**
- `jokes.csv`: Main content database (~5400 jokes)
- `index.json`: Tracks current position for each platform
- `keys.json`: API credentials for all platforms
- `corrupted_lines.txt`: Error logging for encoding issues

### Partial Refactor Status

The repository contains a **partially completed refactor** with these directories:
- `automation/`: Advanced scheduling system (incomplete)
- `platforms/`: Platform abstraction layer (incomplete)
- `utils/`: Shared utilities (incomplete)
- `monitoring/`: System monitoring (incomplete)

**Note**: The `old/` directory contains the original working code for reference when updating the refactored version.

### Data Flow (Current Working Version)

1. **Content Management**: Jokes stored in `jokes.csv`, accessed sequentially via `index.json` counters
2. **Authentication**: Platform credentials in `keys.json`, BlueSky uses JWT with refresh
3. **Scheduling**: `main_launcher.py` coordinates posting, `bsky/launcher.py` handles interactions
4. **Error Handling**: Encoding errors logged to `corrupted_lines.txt`

### Platform Details

**BlueSky**
- Uses ATProtocol with JWT authentication and refresh tokens
- Session management in `bsky.py` handles token refresh automatically
- Modular interaction system in `bsky/modules/`
- Supports posting, following, liking, replying

**Twitter/X**
- OAuth1 authentication with requests_oauthlib
- Simple posting function with encoding fallback handling
- Uses Twitter API v2 for posting

### File Organization (Current Working)

```
├── main_launcher.py          # Simple scheduler coordinator
├── newcore.py               # Legacy comprehensive launcher
├── bsky/                    # BlueSky implementation
│   ├── bsky.py             # Core posting with session mgmt
│   ├── launcher.py         # Interaction coordinator
│   └── modules/            # Individual interaction modules
├── tweet/                   # Twitter/X posting
│   └── tweet.py            # Simple OAuth1 posting
├── bskyBESTTHING.py        # "Best thing" bot
├── bsky_taunt/             # Taunt bot
├── jokes.csv              # Main content (~5400 jokes)
├── keys.json              # API credentials
├── index.json             # Platform position tracking
└── old/                   # Original code for reference
```

**Refactor directories (incomplete)**: `automation/`, `platforms/`, `utils/`, `monitoring/`