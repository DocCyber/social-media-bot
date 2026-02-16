# Social Media Bot

Multi-platform social media automation bot with AI-powered interactions for BlueSky, Twitter/X, and Mastodon.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platforms](https://img.shields.io/badge/platforms-BlueSky%20%7C%20Twitter%20%7C%20Mastodon-orange.svg)

## 🌟 Features

### BlueSky (@docatcdi.com)
- 🤖 **AI-Powered Replies** - Claude Sonnet 4.5 for authentic, personality-driven responses
- 📝 **Automated Posting** - Hourly joke rotation with hashtag support
- 💬 **Smart Interactions** - Pattern-matched replies, greetings, reactions, and follows
- 🔄 **Conservative Unfollower** - Intelligent follower management
- 🌅 **EarthPorn Reposter** - Scenic content curation
- 📊 **Analytics** - Follower/following data collection and tracking

### Twitter/X (@DocAtCDI)
- 🎯 **Smart Reply Bot** - Sequential user rotation with personalized jokes
- 🏷️ **Natural Language Management** - "Bookmark this in my [category] category" for user tagging
- 👥 **Category System** - Friend/foe/jokster/snark/priority classifications
- 📈 **Engagement Tracking** - Monitor user interactions and reply patterns
- 🤖 **AI Integration** - Claude API for context-aware responses
- ⏰ **Randomized Scheduling** - Avoid predictability with dynamic posting times

### RSS Integration
- 📰 **Multi-Feed Support** - Monitor and post from multiple RSS feeds
- 🧠 **LLM Teasers** - AI-generated article previews
- 🔀 **Cross-Platform** - Simultaneous posting to BlueSky, Twitter, and Mastodon

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.10 or higher
python --version

# Install dependencies
pip install requests requests-oauthlib schedule atproto tweepy feedparser openai anthropic
```

### Configuration

1. **Create credential files:**
   ```bash
   # Create secrets directory
   mkdir D:\secrets

   # Add your API keys
   echo "your-claude-api-key" > D:\secrets\CLAUDEAPI.txt
   echo "your-openai-api-key" > D:\secrets\GPTAPI.txt

   # Twitter credentials (5 lines: consumer_key, consumer_secret, access_token, access_token_secret, bearer_token)
   notepad D:\secrets\TwitterPayAsYouGo.txt
   ```

2. **Create keys.json in project root:**
   ```json
   {
     "bsky": {
       "handle": "your-handle.bsky.social",
       "app_password": "xxxx-xxxx-xxxx-xxxx"
     },
     "twitter": {
       "consumer_key": "...",
       "consumer_secret": "...",
       "access_token": "...",
       "access_token_secret": "...",
       "bearer_token": "..."
     }
   }
   ```

3. **Create index.json:**
   ```json
   {
     "joke": 0,
     "bsky": 0,
     "docafterdark": 0
   }
   ```

### Running the Bot

```bash
# Main scheduler (recommended)
python main_launcher.py

# Twitter auto-reply bot (separate process)
python PAYGTwitter/TwitterAutoReply.py

# RSS processor (optional)
python rss_runner.py
```

## 📖 Documentation

- **[BOT_OVERVIEW.md](BOT_OVERVIEW.md)** - User guide with features, schedules, and common tasks
- **[TECHNICAL.md](TECHNICAL.md)** - Developer guide with architecture and code flows
- **[CREDENTIAL_MIGRATION_CHECK.md](CREDENTIAL_MIGRATION_CHECK.md)** - Security testing checklist

## 🏗️ Architecture

```
main_launcher.py (scheduler)
  │
  ├─> BlueSky
  │   ├─ Post jokes hourly (:31)
  │   ├─ AI replies (Claude)
  │   ├─ Custom/greeting replies
  │   ├─ Reactions & follows
  │   └─ Conservative unfollower
  │
  ├─> Twitter/X
  │   ├─ Post jokes (even hours, randomized)
  │   ├─ Auto-reply bot (user rotation)
  │   └─ Bookmark-based user management
  │
  └─> RSS
      ├─ Feed monitoring
      ├─ LLM teaser generation
      └─ Cross-platform posting
```

## 🛡️ Security

**Never commit these files:**
- `keys.json` - Platform credentials
- `D:\secrets\*` - API keys
- `PAYGTwitter/user_data.csv` - User database
- `bsky/modules/*.json` - State files with DIDs

The `.gitignore` is configured to protect all sensitive data automatically.

## 📝 Content Management

### Adding Jokes

1. Open `jokes.csv` or `DocAfterDark.csv`
2. Add new rows with joke text in first column
3. Save as UTF-8
4. Bot automatically includes in rotation

### Twitter User Management

Reply to a tweet with natural language:
```
"bookmark this in my friend category"
"bookmark this in my jokster category"
"bookmark this in my priority category"
```

Or edit `PAYGTwitter/user_data.csv` directly.

### Customizing AI Personality

Edit `bsky/data/voice.txt` to change AI reply style and personality.

## ⚙️ Scheduling

| Task | Frequency | Platform |
|------|-----------|----------|
| Post jokes | Hourly @ :31 | BlueSky |
| Post jokes | Even hours (randomized) | Twitter |
| AI replies | Every 12 min | BlueSky |
| Interactions | Every 5 min | BlueSky |
| Unfollower | Every 2 hours | BlueSky |
| DocAfterDark | Daily @ 22:04 | BlueSky |
| EarthPorn | Every 65 min | BlueSky |

## 🔧 Common Tasks

### View Logs
```bash
# Today's AI replies
cat bsky/data/ai_reply_log_$(date +%Y-%m-%d).txt

# Twitter engagement
cat PAYGTwitter/engagement_log.txt
```

### Manual Posting
```bash
# BlueSky
python bsky/bsky.py

# Twitter
python tweet/tweet.py
```

### Reset RSS State
```bash
python reset_rss_for_testing.py
```

## 🐛 Troubleshooting

### BlueSky 401 Errors
Delete `accessJwt` and `refreshJwt` from `keys.json`. Bot will create new session.

### Twitter Rate Limits
Free tier: 50 tweets/month (~1.6/day). Reduce posting frequency or upgrade.

### CSV Encoding Errors
Check `corrupted_lines.txt`, re-save CSV as UTF-8.

## 📊 Statistics

- **3 Platforms** - BlueSky, Twitter/X, Mastodon
- **10+ Active Modules** - Posting, AI replies, interactions, analytics
- **Rate Limited** - 1 reply/user/6hr on BlueSky
- **Smart Rotation** - CSV-based content with automatic index management
- **Safe & Secure** - Comprehensive .gitignore, credential isolation

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Test thoroughly
4. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- **Claude Sonnet 4.5** - AI reply generation
- **BlueSky API** - Social platform integration
- **Twitter API** - Social platform integration
- **Python Schedule** - Simple, reliable task scheduling

## 📞 Support

- **Documentation:** See [BOT_OVERVIEW.md](BOT_OVERVIEW.md) and [TECHNICAL.md](TECHNICAL.md)
- **Issues:** Use GitHub Issues for bug reports
- **Security:** Report security issues privately

## 🗺️ Roadmap

- [ ] Database migration (replace CSV)
- [ ] Web dashboard for monitoring
- [ ] Multi-account support
- [ ] Content approval queue
- [ ] Metrics/analytics export
- [ ] Docker containerization

---

**Built with ❤️ for automated social media engagement**

**Repository:** https://github.com/DocCyber/social-media-bot
