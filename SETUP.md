# Setup Guide for Beginners

This guide will walk you through setting up the Instagram Comment-to-DM Bot step by step. No coding experience required!

## Table of Contents

1. [Requirements](#1-requirements)
2. [Installing Python](#2-installing-python)
3. [Downloading the Bot](#3-downloading-the-bot)
4. [Installing Dependencies](#4-installing-dependencies)
5. [Setting Up Your Credentials](#5-setting-up-your-credentials)
6. [Configuring Your Reels](#6-configuring-your-reels)
7. [Running the Bot](#7-running-the-bot)
8. [Understanding the Output](#8-understanding-the-output)
9. [Running Modes Explained](#9-running-modes-explained)
10. [Common Issues & Solutions](#10-common-issues--solutions)
11. [Tips for Best Results](#11-tips-for-best-results)

---

## 1. Requirements

Before you start, make sure you have:

- [ ] A computer (Windows, Mac, or Linux)
- [ ] Internet connection
- [ ] An Instagram account (Creator or Business account recommended)
- [ ] Python 3.8 or higher installed

---

## 2. Installing Python

### Check if Python is Already Installed

Open your terminal/command prompt and type:

```bash
python --version
```

If you see `Python 3.8.x` or higher, skip to [Step 3](#3-downloading-the-bot).

### Installing Python on Windows

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Click "Download Python 3.x.x"
3. Run the installer
4. **IMPORTANT**: Check the box that says "Add Python to PATH"
5. Click "Install Now"
6. Restart your computer

### Installing Python on Mac

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download the macOS installer
3. Run the installer and follow the prompts

### Installing Python on Linux

```bash
sudo apt update
sudo apt install python3 python3-pip
```

---

## 3. Downloading the Bot

### Option A: Download ZIP (Easiest)

1. Download the bot files as a ZIP
2. Extract to a folder (e.g., `C:\insta-auto` or `~/insta-auto`)

### Option B: Using Git

```bash
git clone https://github.com/tarunerror/insta-auto.git
cd insta-auto
```

---

## 4. Installing Dependencies

Open your terminal/command prompt and navigate to the bot folder:

### On Windows:
```bash
cd C:\insta-auto
```

### On Mac/Linux:
```bash
cd ~/insta-auto
```

Then install the required packages:

```bash
pip install -r requirements.txt
```

You should see output like:
```
Successfully installed instagrapi-2.x.x python-dotenv-1.x.x
```

---

## 5. Setting Up Your Credentials

Your Instagram login credentials need to be stored securely. We recommend using environment variables.

### Step 5.1: Create the .env File

**On Windows (Command Prompt):**
```bash
copy .env.example .env
```

**On Mac/Linux:**
```bash
cp .env.example .env
```

### Step 5.2: Edit the .env File

Open `.env` in any text editor (Notepad, VS Code, etc.) and replace the placeholder values:

```
INSTAGRAM_USERNAME=your_actual_username
INSTAGRAM_PASSWORD=your_actual_password
```

**Example:**
```
INSTAGRAM_USERNAME=john_doe_creator
INSTAGRAM_PASSWORD=MySecurePassword123
```

### Important Security Notes

- Never share your `.env` file with anyone
- The `.env` file is automatically ignored by git (won't be uploaded)
- If you have 2-Factor Authentication enabled, you may need to create an app-specific password

---

## 6. Configuring Your Reels

### Step 6.1: Create the Config File

**On Windows:**
```bash
copy config.example.json config.json
```

**On Mac/Linux:**
```bash
cp config.example.json config.json
```

### Step 6.2: Edit config.json

Open `config.json` in a text editor. Here's what each part means:

```json
{
  "reels": [
    {
      "url": "https://www.instagram.com/reel/ABC123/",
      "keywords": ["free", "info", "send", "want"],
      "message": "Hey {username}, thanks for commenting! Here's your free guide: https://yourlink.com"
    }
  ],
  "settings": {
    "check_interval_seconds": 10,
    "min_delay_seconds": 45,
    "max_delay_seconds": 90,
    "max_dms_per_session": 20,
    "max_parallel_reels": 5,
    "max_parallel_dms": 3,
    "parallel_dm_delay": 3.0,
    "comment_replies": [
      "Hey @{username}, check your DMs!",
      "@{username} just sent you something special!"
    ]
  }
}
```

### Step 6.3: Add Your Reels

Replace the example reel with your own:

1. **Find your reel URL**: Open your reel on Instagram and copy the URL from the address bar
2. **Choose your keywords**: What words should trigger a DM? (e.g., "free", "send", "want")
3. **Write your message**: What DM should users receive? Use `{username}` to personalize it

**Example with multiple reels:**

```json
{
  "reels": [
    {
      "url": "https://www.instagram.com/reel/DTiF-q9CGLD/",
      "keywords": ["free", "guide", "send", "want", "info"],
      "message": "Hey {username}! Thanks for your interest! Here's your FREE social media guide: https://example.com/guide"
    },
    {
      "url": "https://www.instagram.com/reel/DTlT68vk3Zp/",
      "keywords": ["course", "learn", "interested", "yes"],
      "message": "Hi {username}! Great to hear you're interested! Check out our course here: https://example.com/course"
    },
    {
      "url": "https://www.instagram.com/reel/XYZ789abc/",
      "keywords": [],
      "message": "Thanks for commenting {username}! Here's a special gift for you: https://example.com/gift"
    }
  ],
  "settings": {
    "check_interval_seconds": 10,
    "min_delay_seconds": 45,
    "max_delay_seconds": 90,
    "max_dms_per_session": 20,
    "max_parallel_reels": 5,
    "max_parallel_dms": 3,
    "parallel_dm_delay": 3.0,
    "comment_replies": [
      "Hey @{username}, check your DMs!",
      "@{username} just sent you something special!",
      "Sent to your inbox @{username}!",
      "@{username} check your messages!"
    ]
  }
}
```

### Understanding Keywords

| Keywords Setting | What Happens |
|------------------|--------------|
| `["free", "send"]` | Only DMs users whose comment contains "free" OR "send" |
| `["want", "me", "please"]` | DMs users with "want", "me", or "please" in comment |
| `[]` (empty array) | DMs ALL users who comment (use carefully!) |

### Understanding Settings

| Setting | What It Does | Recommended Value |
|---------|--------------|-------------------|
| `check_interval_seconds` | How often to check for new comments (continuous mode) | 10-30 seconds |
| `min_delay_seconds` | Minimum wait between DMs | 45 seconds |
| `max_delay_seconds` | Maximum wait between DMs | 90 seconds |
| `max_dms_per_session` | Stop after this many DMs | 15-20 |
| `max_parallel_reels` | How many reels to check at once | 5 |
| `max_parallel_dms` | How many DMs to send at once | 2-3 |
| `parallel_dm_delay` | Delay between parallel DMs | 3.0 seconds |
| `comment_replies` | Random replies to post on comments | Add 3-5 variations |

> **Note:** You can also use `check_interval_minutes` instead if you prefer minute-based intervals.

---

## 7. Running the Bot

Open your terminal and navigate to the bot folder:

```bash
cd C:\insta-auto   # Windows
cd ~/insta-auto    # Mac/Linux
```

### Basic Run (Process Once)

```bash
python bot.py
```

This will:
1. Log into Instagram
2. Check all your configured reels
3. Send DMs to matching commenters
4. Exit when done

### Continuous Mode (Recommended)

```bash
python bot.py --continuous
```
or
```bash
python bot.py -c
```

This will:
1. Log into Instagram
2. Check all reels for comments
3. Send DMs to matching commenters
4. Wait 10 seconds (configurable via `check_interval_seconds`)
5. Repeat until you press `Ctrl+C`

### Fast Mode for Many Reels

If you have many reels (10+), use parallel mode:

```bash
python bot.py --full-parallel
```
or
```bash
python bot.py -f
```

### Continuous + Fast Mode (Best for Many Reels)

```bash
python bot.py -c -f
```

This runs continuously with full parallel processing - the fastest option!

---

## 8. Understanding the Output

When the bot runs, you'll see logs like this:

```
[2026-01-17 10:30:00] [INFO] ==================================================
[2026-01-17 10:30:00] [INFO] Instagram Comment-to-DM Automation Bot
[2026-01-17 10:30:00] [INFO] ==================================================
[2026-01-17 10:30:00] [INFO] Stats: 45 total DMs, 12 today
```
This shows the bot starting and your stats.

```
[2026-01-17 10:30:01] [INFO] Logged in as @your_username (from saved session)
```
Successfully logged in! "from saved session" means it used a cached login.

```
[2026-01-17 10:30:02] [INFO] Checking reel: https://instagram.com/reel/ABC123/
[2026-01-17 10:30:03] [INFO] Found 15 comments
[2026-01-17 10:30:03] [INFO] Filtering for keywords: ['free', 'info']
```
The bot is checking your reel and found 15 comments.

```
[2026-01-17 10:30:04] [INFO] @john_doe follows you - sending DM...
[2026-01-17 10:30:05] [INFO] Waiting 52.3 seconds...
[2026-01-17 10:30:57] [INFO] ✓ DM sent to @john_doe
[2026-01-17 10:30:58] [INFO] ✓ Replied to @john_doe's comment
```
Found a matching user, waited for safety, sent the DM, and replied to their comment!

```
[2026-01-17 10:30:58] [INFO] @jane_smith does NOT follow you - skipping
```
This user commented but doesn't follow you, so no DM sent.

```
[2026-01-17 10:30:59] [INFO] @bob_user comment has no matching keyword - skipping
```
This user's comment didn't contain any of your keywords.

```
[2026-01-17 10:31:00] [INFO] Reel complete: 5 matched keywords, 3 DMs sent, 2 not following, 5 no keyword, 3 already processed
```
Summary: 5 comments matched, 3 DMs sent, 2 skipped (not followers), 5 skipped (no keyword), 3 already processed before.

```
[2026-01-17 10:31:00] [INFO] Next check in 10 seconds...
```
In continuous mode, the bot waits before checking again.

### Log Levels

| Level | Meaning |
|-------|---------|
| `[INFO]` | Normal operation |
| `[WARN]` | Warning (something to note but not critical) |
| `[ERROR]` | Error (something went wrong) |

---

## 9. Running Modes Explained

### Mode 1: Default (Sequential)

```bash
python bot.py
```

**How it works:**
```
Reel 1 → fetch comments → send DM → wait → send DM → wait → Reel 2 → ...
```

**Best for:** 1-5 reels, safest option

---

### Mode 2: Parallel Fetch (`-p`)

```bash
python bot.py -p
```

**How it works:**
```
Phase 1: Fetch ALL reels at once (parallel)
Phase 2: Send DMs one by one (sequential)
```

**Best for:** 10-50 reels

---

### Mode 3: Full Parallel (`-f`)

```bash
python bot.py -f
```

**How it works:**
```
Phase 1: Fetch ALL reels at once (parallel)
Phase 2: Collect all DM tasks
Phase 3: Send ALL DMs at once (parallel with rate limiting)
```

**Best for:** 50+ reels, when speed matters

---

### Mode 4: Continuous (`-c`)

Add `-c` to any mode to run continuously:

```bash
python bot.py -c        # Continuous + sequential
python bot.py -c -p     # Continuous + parallel fetch
python bot.py -c -f     # Continuous + full parallel (FASTEST)
```

**Best for:** Running the bot for extended periods

---

## 10. Common Issues & Solutions

### Issue: "Instagram requires verification"

**Cause:** Instagram detected unusual login activity.

**Solution:**
1. Open Instagram in your browser
2. Log in and complete any security challenges
3. Delete `session.json` from the bot folder
4. Run the bot again

---

### Issue: "Login failed"

**Cause:** Wrong credentials or too many login attempts.

**Solution:**
1. Double-check your username/password in `.env`
2. Try logging in manually on Instagram
3. If you have 2FA enabled, disable it or create an app password
4. Wait 1-2 hours before trying again

---

### Issue: "Instagram blocked DM action"

**Cause:** You've been rate-limited for sending too many DMs.

**Solution:**
1. Stop the bot immediately
2. Wait 24-48 hours before running again
3. Reduce settings:
   ```json
   "max_dms_per_session": 10,
   "min_delay_seconds": 60,
   "max_delay_seconds": 120
   ```

---

### Issue: "No module named 'instagrapi'"

**Cause:** Dependencies not installed.

**Solution:**
```bash
pip install -r requirements.txt
```

---

### Issue: Bot not finding any comments

**Cause:** Wrong reel URL or no matching comments.

**Solution:**
1. Make sure the reel URL is correct (open it in browser)
2. Check if the reel has comments
3. Try using `[]` for keywords to match all comments (for testing)

---

### Issue: Bot sends DMs but they don't appear

**Cause:** Instagram may be silently blocking your DMs.

**Solution:**
1. Check your Instagram DM requests
2. Some DMs go to "Message Requests" if users don't follow you back
3. Wait 24 hours and try again

---

## 11. Tips for Best Results

### Safety Tips

| Tip | Why |
|-----|-----|
| Start with 10-15 DMs per session | Build up slowly |
| Run 2-3 times per day max | Don't overdo it |
| Use delays of 45+ seconds | Mimic human behavior |
| Don't run 24/7 | Take breaks |

### Optimization Tips

| Tip | Why |
|-----|-----|
| Use specific keywords | Avoid false matches |
| Write genuine messages | Higher engagement |
| Include value in DM | Give them a reason to respond |
| Vary your comment replies | Look more natural |

### Example Workflow

**Morning (9 AM):**
```bash
python bot.py -f
# Sends up to 20 DMs
```

**Afternoon (2 PM):**
```bash
python bot.py -f
# Processes new comments since morning
```

**Evening (7 PM):**
```bash
python bot.py -f
# Catches evening commenters
```

### Or Run Continuously

```bash
python bot.py -c -f
# Leave running - checks every 10 seconds
# Press Ctrl+C to stop
```

---

## Need More Help?

1. Check the main [README.md](README.md) for more details
2. Look at the example config files
3. Make sure all files are in the same folder
4. Try running with default settings first

---

## Quick Reference Card

```bash
# Install
pip install -r requirements.txt

# Setup
copy .env.example .env          # Then edit with your credentials
copy config.example.json config.json  # Then edit with your reels

# Run
python bot.py           # Once
python bot.py -c        # Continuous (checks every 10 seconds)
python bot.py -f        # Fast (parallel)
python bot.py -c -f     # Continuous + Fast (recommended)

# Stop
Ctrl+C                  # Stop the bot
```

Happy automating!
