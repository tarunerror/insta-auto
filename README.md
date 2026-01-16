# Instagram Comment-to-DM Automation Bot

Automatically send personalized DMs to users who follow you and comment on your Instagram Reels. Perfect for content creators who want to deliver free guides, links, or exclusive content to engaged followers.

## How It Works

```
User follows you → Comments with keyword on your reel → Receives automated DM + Comment reply
```

## Features

| Feature | Description |
|---------|-------------|
| **Multi-Reel Monitoring** | Monitor unlimited reels with different messages for each |
| **Keyword Filtering** | Only respond to comments containing specific trigger words |
| **Follower Verification** | Only DM users who actually follow you |
| **Personalized Messages** | Use `{username}` placeholder for personalization |
| **Comment Replies** | Automatically reply to comments after DMing |
| **Duplicate Prevention** | Database tracks all interactions - never spam the same user |
| **Parallel Processing** | Process 100+ reels simultaneously for speed |
| **Rate Limiting** | Built-in safety features to avoid Instagram blocks |
| **Session Caching** | Saves login session to avoid repeated authentication |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up credentials
cp .env.example .env
# Edit .env with your Instagram username/password

# 3. Configure your reels
cp config.example.json config.json
# Edit config.json with your reel URLs and messages

# 4. Run the bot
python bot.py
```

> **New to this?** See [SETUP.md](SETUP.md) for a detailed beginner-friendly guide.

## Command-Line Options

| Command | Description |
|---------|-------------|
| `python bot.py` | Run once and exit |
| `python bot.py -c` | Run continuously (checks every X minutes) |
| `python bot.py -p` | Parallel mode (fetch all reels at once) |
| `python bot.py -f` | **Full parallel** (fastest - fetch + DM simultaneously) |
| `python bot.py -c -f` | Continuous + full parallel (recommended for many reels) |

### Execution Modes Explained

| Mode | Speed | Best For |
|------|-------|----------|
| Default | Slow | 1-5 reels, safest option |
| `-p` (parallel) | Medium | 10-50 reels |
| `-f` (full-parallel) | Fast | 50+ reels, time-sensitive |

## Configuration

### config.json

```json
{
  "reels": [
    {
      "url": "https://www.instagram.com/reel/ABC123/",
      "keywords": ["free", "info", "send", "want"],
      "message": "Hey {username}, thanks for commenting! Here's your free guide: https://yourlink.com"
    },
    {
      "url": "https://www.instagram.com/reel/XYZ789/",
      "keywords": ["interested", "yes", "me"],
      "message": "Hi {username}! Check out this exclusive content: https://anotherlink.com"
    }
  ],
  "settings": {
    "check_interval_minutes": 3,
    "min_delay_seconds": 45,
    "max_delay_seconds": 90,
    "max_dms_per_session": 20,
    "max_parallel_reels": 5,
    "max_parallel_dms": 3,
    "parallel_dm_delay": 3.0,
    "comment_replies": [
      "Hey @{username}, check your DMs!",
      "@{username} just sent you something special!",
      "Sent it to your inbox @{username}!"
    ]
  }
}
```

### All Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `check_interval_minutes` | 3 | Minutes between checks in continuous mode |
| `min_delay_seconds` | 45 | Minimum delay between DMs (sequential mode) |
| `max_delay_seconds` | 90 | Maximum delay between DMs (sequential mode) |
| `max_dms_per_session` | 20 | Max DMs per run/cycle |
| `max_parallel_reels` | 5 | Concurrent reel fetches (parallel modes) |
| `max_parallel_dms` | 3 | Concurrent DM sends (full-parallel mode) |
| `parallel_dm_delay` | 3.0 | Seconds between parallel DM batches |
| `comment_replies` | [] | Random replies posted on user's comment |

### Keyword Matching

| Keywords | Matches | Doesn't Match |
|----------|---------|---------------|
| `["free", "info"]` | "I want free guide", "send info" | "hello", "nice video" |
| `["send", "want"]` | "send me", "I want it" | "great content" |
| `[]` (empty) | **All comments** | Nothing |

- **Case-insensitive**: "FREE" matches "free"
- **Partial match**: "free" matches "freebie"
- **Any match**: Comment needs ANY ONE keyword

## Example Output

```
[2026-01-17 10:30:00] [INFO] ==================================================
[2026-01-17 10:30:00] [INFO] Instagram Comment-to-DM Automation Bot
[2026-01-17 10:30:00] [INFO] Mode: FULL PARALLEL (fetching + DMs simultaneously)
[2026-01-17 10:30:00] [INFO] ==================================================
[2026-01-17 10:30:00] [INFO] Stats: 45 total DMs, 12 today
[2026-01-17 10:30:01] [INFO] Logged in as @your_username (from saved session)
[2026-01-17 10:30:01] [INFO] ==================================================
[2026-01-17 10:30:01] [INFO] [FULL PARALLEL] Processing 25 reels
[2026-01-17 10:30:01] [INFO] [FULL PARALLEL] Max 3 concurrent DMs, 3.0s delay
[2026-01-17 10:30:01] [INFO] ==================================================
[2026-01-17 10:30:01] [INFO] Phase 1: Fetching comments from all reels...
[2026-01-17 10:30:05] [INFO] Phase 1 complete: 150 comments fetched in 4.2s
[2026-01-17 10:30:05] [INFO] ----------------------------------------
[2026-01-17 10:30:05] [INFO] Phase 2: Filtering and collecting DM tasks...
[2026-01-17 10:30:10] [INFO] Phase 2 complete: 8 DMs queued
[2026-01-17 10:30:10] [INFO] ----------------------------------------
[2026-01-17 10:30:10] [INFO] Phase 3: Sending 8 DMs in parallel...
[2026-01-17 10:30:11] [INFO] [PARALLEL DM] Sending to @user1...
[2026-01-17 10:30:11] [INFO] [PARALLEL DM] Sending to @user2...
[2026-01-17 10:30:11] [INFO] [PARALLEL DM] Sending to @user3...
[2026-01-17 10:30:12] [INFO] [PARALLEL DM] ✓ DM sent to @user1 (1 total)
[2026-01-17 10:30:12] [INFO] [PARALLEL DM] ✓ DM sent to @user2 (2 total)
[2026-01-17 10:30:13] [INFO] [PARALLEL DM] ✓ DM sent to @user3 (3 total)
[2026-01-17 10:30:30] [INFO] ==================================================
[2026-01-17 10:30:30] [INFO] [FULL PARALLEL] Complete!
[2026-01-17 10:30:30] [INFO] [FULL PARALLEL] 8 DMs sent, 0 failed in 20.1s
[2026-01-17 10:30:30] [INFO] [FULL PARALLEL] Total this session: 8
```

## Project Structure

```
insta-auto/
├── bot.py              # Main automation script
├── database.py         # SQLite database for tracking users
├── config.json         # Your configuration (create from example)
├── config.example.json # Template configuration
├── .env                # Your credentials (create from example)
├── .env.example        # Template for credentials
├── requirements.txt    # Python dependencies
├── README.md           # This file
├── SETUP.md            # Beginner-friendly setup guide
├── session.json        # Auto-created: Login session cache
└── processed.db        # Auto-created: Database of processed users
```

## Safety Features

| Feature | Purpose |
|---------|---------|
| Random delays (45-90s) | Mimics human behavior |
| Session limit (20 DMs) | Prevents rate limiting |
| Parallel rate limiter | Controls concurrent DM speed |
| Session caching | Avoids repeated logins |
| Duplicate prevention | Never DMs same user twice per reel |
| Auto-stop on block | Immediately stops if Instagram restricts |
| Thread-safe operations | Prevents race conditions in parallel mode |

## Security

| Feature | Description |
|---------|-------------|
| Environment variables | Credentials in `.env`, not in code |
| .gitignore protection | Sensitive files excluded from git |
| Session file permissions | 600 (owner-only) on Unix |
| Config validation | All settings validated on startup |

## Troubleshooting

### "Instagram requires verification"
- Log into Instagram manually in your browser
- Complete any security challenges (CAPTCHA, email verification)
- Delete `session.json` and try again

### "Login failed"
- Double-check username/password
- Disable 2FA or use an app-specific password
- Wait a few hours if too many login attempts

### "Instagram blocked DM action"
- You've been rate-limited
- Wait 24-48 hours before running again
- Reduce `max_dms_per_session` to 10-15
- Increase delay settings

### Bot not finding comments
- Make sure the reel URL is correct (try opening it in browser)
- Check if the reel has any comments
- Verify your keywords match the comment text

## Reducing Risk

This bot uses unofficial Instagram automation. To minimize account risk:

| Setting | Safe Value | Description |
|---------|------------|-------------|
| `max_dms_per_session` | 10-20 | Keep low |
| `min_delay_seconds` | 45+ | Higher is safer |
| `max_parallel_dms` | 2-3 | Don't go higher |
| Run frequency | 2-3x/day | Don't run 24/7 |

## Cloud Deployment

### PythonAnywhere (Free)
1. Create account at pythonanywhere.com
2. Upload all files
3. Create scheduled task: `python bot.py`

### Railway / Render
1. Connect GitHub repo
2. Set environment variables
3. Deploy with cron job

## License

For personal use only. Use at your own risk. The developers are not responsible for any account restrictions or bans.

## Support

Having issues? Check [SETUP.md](SETUP.md) for detailed setup instructions or open an issue on GitHub.
