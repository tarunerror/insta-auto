# Instagram Comment-to-DM Automation Bot

Automatically send personalized DMs to users who follow you and comment on your specific reels.

## How It Works

```
User follows you → Comments with keyword on your reel → Receives automated DM
```

## Requirements

- Python 3.8 or higher
- Instagram account (Creator or Business)

## Setup

### 1. Install Python Dependencies

```bash
cd D:\insta-auto
pip install -r requirements.txt
```

### 2. Configure Your Account and Reels

Open `config.json` and edit:

```json
{
  "username": "your_instagram_username",
  "password": "your_instagram_password",
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
    "max_dms_per_session": 20
  }
}
```

#### Configuration Options

| Setting | Description |
|---------|-------------|
| `username` | Your Instagram username |
| `password` | Your Instagram password |
| `reels` | List of reels to monitor with their custom DM messages |
| `keywords` | List of trigger words - comment must contain ANY of these (case-insensitive) |
| `{username}` | Placeholder that gets replaced with commenter's username |
| `check_interval_minutes` | How often to check for new comments in continuous mode |
| `min_delay_seconds` | Minimum wait time between DMs (safety) |
| `max_delay_seconds` | Maximum wait time between DMs (safety) |
| `max_dms_per_session` | Stop after sending this many DMs per run |

#### Keyword Examples

| Keywords | Matches | Doesn't Match |
|----------|---------|---------------|
| `["free", "info"]` | "I want free guide", "send info please" | "hello", "nice video" |
| `["send", "want", "me"]` | "send me", "I want it" | "great content" |
| `[]` (empty) | All comments | Nothing |

### 3. Run the Bot

**Run once:**
```bash
python bot.py
```

**Run continuously (checks every X minutes):**
```bash
python bot.py --continuous
```
or
```bash
python bot.py -c
```

In continuous mode, the bot will:
1. Check all your reels for new comments
2. Send DMs to matching users
3. Wait for `check_interval_minutes` (default: 3 minutes)
4. Repeat until you press `Ctrl+C`

## Example Output

```
[2026-01-15 18:30:00] [INFO] ==================================================
[2026-01-15 18:30:00] [INFO] Instagram Comment-to-DM Automation Bot
[2026-01-15 18:30:00] [INFO] ==================================================
[2026-01-15 18:30:00] [INFO] Stats: 45 total DMs, 12 today
[2026-01-15 18:30:01] [INFO] Logged in as @your_username (from saved session)
[2026-01-15 18:30:02] [INFO] Checking reel: https://instagram.com/reel/ABC123/
[2026-01-15 18:30:03] [INFO] Found 15 comments
[2026-01-15 18:30:03] [INFO] Filtering for keywords: ['free', 'info']
[2026-01-15 18:30:04] [INFO] @john_doe follows you - sending DM...
[2026-01-15 18:30:05] [INFO] Waiting 52.3 seconds...
[2026-01-15 18:30:57] [INFO] ✓ DM sent to @john_doe
[2026-01-15 18:30:58] [INFO] @jane_smith does NOT follow you - skipping
[2026-01-15 18:30:59] [INFO] @bob_user comment has no matching keyword - skipping
[2026-01-15 18:31:00] [INFO] Reel complete: 5 matched keywords, 3 DMs sent, 2 not following, 5 no keyword, 3 already processed
[2026-01-15 18:31:00] [INFO] Session complete: 3 DMs sent
[2026-01-15 18:31:00] [INFO] Total DMs sent all time: 48
```

## Files Overview

```
insta-auto/
├── bot.py           # Main automation script
├── config.json      # Your settings and reel configurations
├── database.py      # Tracks processed users (prevents duplicate DMs)
├── requirements.txt # Python dependencies
├── session.json     # Auto-created: Saves login session
├── processed.db     # Auto-created: Database of processed users
└── README.md        # This file
```

## Safety Features

| Feature | Purpose |
|---------|---------|
| Random delays (45-90 sec) | Mimics human behavior |
| Session limit (20 DMs) | Prevents rate limiting |
| Session caching | Avoids repeated logins |
| Duplicate prevention | Never DMs same person twice per reel |
| Auto-pause on block | Stops if Instagram restricts actions |

## Running Multiple Times

The bot tracks who has been processed. Run it multiple times per day:

```bash
# Morning run
python bot.py

# Afternoon run (processes new comments only)
python bot.py

# Evening run
python bot.py
```

## Troubleshooting

### "Instagram requires verification"
- Log into Instagram manually on your browser
- Complete any security challenges
- Try running the bot again

### "Login failed"
- Double-check username/password in config.json
- Make sure 2FA is disabled or use an app password
- Wait a few hours if you've had too many login attempts

### "Instagram blocked DM action"
- You've been rate-limited
- Wait 24-48 hours before running again
- Reduce `max_dms_per_session` to a lower number

### Bot sends DMs to same person multiple times
- This shouldn't happen - the database prevents it
- Check if `processed.db` exists in your folder
- Don't delete `processed.db` unless you want to reset

## Risks

This bot uses unofficial Instagram automation which violates Instagram's Terms of Service.

| Risk | Likelihood |
|------|------------|
| Temporary action block | High (if overused) |
| Account suspension | Medium |
| Permanent ban | Low-Medium |

### Reducing Risk
- Keep `max_dms_per_session` at 20 or lower
- Run only 2-3 times per day
- Use delays of 45+ seconds
- Don't run 24/7

## Cloud Deployment (Optional)

To run this bot 24/7 without keeping your computer on:

### PythonAnywhere (Free Tier)
1. Create account at pythonanywhere.com
2. Upload all files
3. Set up a scheduled task to run `python bot.py` every few hours

### Railway (Free Tier)
1. Create account at railway.app
2. Connect your GitHub repo
3. Deploy and set up cron job

## License

For personal use only. Use at your own risk.
