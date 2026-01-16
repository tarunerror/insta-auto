import json
import os
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock, Semaphore

from dotenv import load_dotenv
from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired, FeedbackRequired, LoginRequired

from database import Database

# Load environment variables from .env file
load_dotenv()


class RateLimiter:
    """Controls rate of DM sending to avoid Instagram blocks"""

    def __init__(self, max_concurrent: int = 3, delay_between: float = 2.0):
        self.semaphore = Semaphore(max_concurrent)
        self.delay = delay_between
        self._lock = Lock()
        self._last_release = 0

    def acquire(self):
        """Acquire a slot, waiting if necessary"""
        self.semaphore.acquire()
        with self._lock:
            now = time.time()
            wait_time = self._last_release + self.delay - now
            if wait_time > 0:
                time.sleep(wait_time)

    def release(self):
        """Release a slot"""
        with self._lock:
            self._last_release = time.time()
        self.semaphore.release()


class InstagramBot:
    def __init__(self, config_path="config.json"):
        self.config = self._load_config(config_path)
        self.client = Client()
        self.client.delay_range = [2, 5]
        self.db = Database()
        self.session_file = Path("session.json")
        self.dms_sent_this_session = 0
        self._client_lock = Lock()  # Lock for thread-safe client access
        self._log_lock = Lock()  # Lock for thread-safe logging

        # Parallel processing settings
        self.max_workers = self.config.get("settings", {}).get("max_parallel_reels", 5)
        self.max_dm_workers = self.config.get("settings", {}).get("max_parallel_dms", 3)
        self.dm_delay = self.config.get("settings", {}).get("parallel_dm_delay", 3.0)

        # Rate limiter for parallel DMs
        self._rate_limiter = RateLimiter(
            max_concurrent=self.max_dm_workers, delay_between=self.dm_delay
        )
        self._dm_counter_lock = Lock()
        self._stop_flag = False

    def _load_config(self, config_path: str) -> dict:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        self._validate_config(config)
        return config

    def _validate_config(self, config: dict):
        """Validate config structure and values"""
        if "reels" not in config or not isinstance(config["reels"], list):
            raise ValueError("Config must contain 'reels' list")

        if "settings" not in config:
            raise ValueError("Config must contain 'settings'")

        settings = config["settings"]
        required_settings = [
            "check_interval_minutes",
            "min_delay_seconds",
            "max_delay_seconds",
            "max_dms_per_session",
        ]
        for setting in required_settings:
            if setting not in settings:
                raise ValueError(f"Missing required setting: {setting}")
            if not isinstance(settings[setting], (int, float)) or settings[setting] < 0:
                raise ValueError(f"Setting '{setting}' must be a positive number")

        for i, reel in enumerate(config["reels"]):
            if "url" not in reel:
                raise ValueError(f"Reel {i + 1} missing 'url'")
            if "message" not in reel:
                raise ValueError(f"Reel {i + 1} missing 'message'")

    def _log(self, message: str, level: str = "INFO"):
        with self._log_lock:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] [{level}] {message}")

    def _secure_session_file(self):
        """Set restrictive permissions on session file (Unix only)"""
        try:
            if sys.platform != "win32":
                import stat

                os.chmod(self.session_file, stat.S_IRUSR | stat.S_IWUSR)  # 600
        except Exception:
            pass  # Ignore on Windows or if permission change fails

    def login(self):
        # Prefer environment variables, fallback to config
        username = os.environ.get("INSTAGRAM_USERNAME") or self.config.get("username")
        password = os.environ.get("INSTAGRAM_PASSWORD") or self.config.get("password")

        if not username or not password:
            self._log(
                "Missing credentials. Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD environment variables or in config.json",
                "ERROR",
            )
            return False

        if self.session_file.exists():
            self._log("Found saved session, attempting to restore...")
            try:
                self.client.load_settings(self.session_file)
                self.client.login(username, password)
                self.client.get_timeline_feed()
                self._log(f"Logged in as @{username} (from saved session)")
                return True
            except Exception as e:
                self._log(f"Session restore failed: {e}", "WARN")
                self.session_file.unlink(missing_ok=True)

        self._log("Logging in with credentials...")
        try:
            time.sleep(3)
            self.client.login(username, password)
            self.client.dump_settings(self.session_file)
            self._secure_session_file()
            self._log(f"Logged in as @{username}")
            return True
        except ChallengeRequired:
            self._log(
                "Instagram requires verification (check your email/phone)", "ERROR"
            )
            return False
        except Exception as e:
            self._log(f"Login failed: {e}", "ERROR")
            return False

    def _extract_reel_id(self, url: str) -> str:
        patterns = [
            r"instagram\.com/reels?/([A-Za-z0-9_-]+)",
            r"instagram\.com/p/([A-Za-z0-9_-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        raise ValueError(f"Could not extract reel ID from URL: {url}")

    def _get_media_pk(self, shortcode: str) -> int:
        media_pk = self.client.media_pk_from_code(shortcode)
        return media_pk

    def _get_comments_raw(self, media_pk: int, amount: int = 50) -> list:
        """Get comments using raw API to avoid pydantic validation errors"""
        try:
            comments = self.client.media_comments(media_pk, amount=amount)
            return comments
        except Exception:
            # Fallback: use private API directly
            try:
                result = self.client.private_request(
                    f"media/{media_pk}/comments/",
                    params={"can_support_threading": "true"},
                )
                comments_data = result.get("comments", [])
                return comments_data
            except Exception as e:
                self._log(f"Failed to get comments: {e}", "ERROR")
                return []

    def _check_follows_you(self, user_id: int) -> bool:
        try:
            friendship = self.client.user_friendship_v1(user_id)
            return friendship.followed_by
        except Exception as e:
            self._log(f"Could not check follow status: {e}", "WARN")
            return False

    def _send_dm(self, user_id: int, username: str, message: str) -> bool:
        try:
            personalized_message = message.replace("{username}", username)
            self.client.direct_send(personalized_message, [user_id])
            return True
        except FeedbackRequired as e:
            self._log(f"Instagram blocked DM action: {e}", "ERROR")
            self._log("Stopping session to prevent further blocks", "WARN")
            raise
        except Exception as e:
            self._log(f"Failed to send DM to @{username}: {e}", "ERROR")
            return False

    def _reply_to_comment(self, media_pk: int, comment_id: str, username: str) -> bool:
        """Reply to a comment with a random personalized message"""
        try:
            comment_replies = self.config["settings"].get("comment_replies", [])
            if not comment_replies:
                self._log("No comment_replies configured, skipping reply", "WARN")
                return False

            # Pick a random reply and personalize it
            reply_template = random.choice(comment_replies)
            reply_text = reply_template.replace("{username}", username)

            # Small delay before replying
            time.sleep(random.uniform(1, 2))

            # Use private API directly to avoid Pydantic validation errors
            # on clips_metadata.original_sound_info.audio_filter_infos
            result = self.client.private_request(
                f"media/{media_pk}/comment/",
                data={
                    "comment_text": reply_text,
                    "replied_to_comment_id": comment_id,
                },
            )
            return result.get("comment") is not None
        except FeedbackRequired as e:
            self._log(f"Instagram blocked comment reply: {e}", "WARN")
            return False
        except Exception as e:
            self._log(f"Failed to reply to @{username}'s comment: {e}", "WARN")
            return False

    def _random_delay(self):
        min_delay = self.config["settings"]["min_delay_seconds"]
        max_delay = self.config["settings"]["max_delay_seconds"]
        delay = random.uniform(min_delay, max_delay)
        self._log(f"Waiting {delay:.1f} seconds...")
        time.sleep(delay)

    def _comment_matches_keywords(self, comment_text: str, keywords: list) -> bool:
        if not keywords:
            return True
        comment_lower = comment_text.lower()
        for keyword in keywords:
            if keyword.lower() in comment_lower:
                return True
        return False

    def process_reel(self, reel_url: str, dm_message: str, keywords: list = None):
        max_dms = self.config["settings"]["max_dms_per_session"]

        if self.dms_sent_this_session >= max_dms:
            self._log(f"Reached session limit of {max_dms} DMs", "WARN")
            return

        try:
            shortcode = self._extract_reel_id(reel_url)
            self._log(f"Checking reel: {reel_url}")

            media_pk = self._get_media_pk(shortcode)
            comments = self._get_comments_raw(media_pk, amount=50)

            self._log(f"Found {len(comments)} comments")
            if keywords:
                self._log(f"Filtering for keywords: {keywords}")

            new_commenters = 0
            dms_sent = 0
            skipped_not_following = 0
            skipped_no_keyword = 0
            already_processed = 0

            for comment in comments:
                if self.dms_sent_this_session >= max_dms:
                    self._log(f"Reached session limit of {max_dms} DMs", "WARN")
                    break

                # Handle both Comment object and raw dict
                if isinstance(comment, dict):
                    user_id = str(comment.get("user", {}).get("pk", ""))
                    username = comment.get("user", {}).get("username", "")
                    comment_text = comment.get("text", "")
                    comment_id = str(comment.get("pk", ""))
                else:
                    user_id = str(comment.user.pk)
                    username = comment.user.username
                    comment_text = comment.text
                    comment_id = str(comment.pk)

                if not user_id or not username:
                    continue

                if self.db.is_processed(user_id, shortcode):
                    already_processed += 1
                    continue

                if not self._comment_matches_keywords(comment_text, keywords):
                    self._log(f"@{username} comment has no matching keyword - skipping")
                    skipped_no_keyword += 1
                    self.db.mark_processed(user_id, username, shortcode, comment_id)
                    continue

                new_commenters += 1

                if not self._check_follows_you(int(user_id)):
                    self._log(f"@{username} does NOT follow you - skipping")
                    skipped_not_following += 1
                    self.db.mark_processed(user_id, username, shortcode, comment_id)
                    continue

                self._log(f"@{username} follows you - sending DM...")
                self._random_delay()

                if self._send_dm(int(user_id), username, dm_message):
                    self._log(f"✓ DM sent to @{username}")
                    dms_sent += 1
                    self.dms_sent_this_session += 1
                    self.db.mark_processed(user_id, username, shortcode, comment_id)

                    # Reply to the comment after sending DM
                    if comment_id and self._reply_to_comment(
                        media_pk, comment_id, username
                    ):
                        self._log(f"✓ Replied to @{username}'s comment")
                        self.db.mark_comment_replied(user_id, shortcode)
                else:
                    self._log(f"✗ Failed to DM @{username}", "WARN")

            self._log(
                f"Reel complete: {new_commenters} matched keywords, {dms_sent} DMs sent, "
                f"{skipped_not_following} not following, {skipped_no_keyword} no keyword, "
                f"{already_processed} already processed"
            )

        except FeedbackRequired:
            raise
        except Exception as e:
            self._log(f"Error processing reel: {e}", "ERROR")

    def process_all_reels(self):
        """Process all reels once"""
        for reel in self.config["reels"]:
            keywords = reel.get("keywords", [])
            self.process_reel(reel["url"], reel["message"], keywords)

            if (
                self.dms_sent_this_session
                >= self.config["settings"]["max_dms_per_session"]
            ):
                break

    def _fetch_reel_comments(self, reel: dict) -> dict:
        """Fetch comments for a single reel (thread-safe for parallel execution)"""
        reel_url = reel["url"]
        keywords = reel.get("keywords", [])
        dm_message = reel["message"]

        try:
            shortcode = self._extract_reel_id(reel_url)
            self._log(f"[PARALLEL] Fetching comments from: {reel_url}")

            # Thread-safe API calls with lock
            with self._client_lock:
                media_pk = self._get_media_pk(shortcode)
                comments = self._get_comments_raw(media_pk, amount=50)

            self._log(f"[PARALLEL] Found {len(comments)} comments in reel {shortcode}")

            return {
                "success": True,
                "reel_url": reel_url,
                "shortcode": shortcode,
                "media_pk": media_pk,
                "comments": comments,
                "keywords": keywords,
                "dm_message": dm_message,
            }
        except Exception as e:
            self._log(f"[PARALLEL] Error fetching {reel_url}: {e}", "ERROR")
            return {
                "success": False,
                "reel_url": reel_url,
                "error": str(e),
            }

    def _process_fetched_comments(self, reel_data: dict):
        """Process comments that were already fetched (DMs sent sequentially)"""
        if not reel_data.get("success"):
            return

        max_dms = self.config["settings"]["max_dms_per_session"]
        shortcode = reel_data["shortcode"]
        media_pk = reel_data["media_pk"]
        comments = reel_data["comments"]
        keywords = reel_data["keywords"]
        dm_message = reel_data["dm_message"]

        if keywords:
            self._log(
                f"Processing reel {shortcode} - filtering for keywords: {keywords}"
            )

        new_commenters = 0
        dms_sent = 0
        skipped_not_following = 0
        skipped_no_keyword = 0
        already_processed = 0

        for comment in comments:
            if self.dms_sent_this_session >= max_dms:
                self._log(f"Reached session limit of {max_dms} DMs", "WARN")
                break

            # Handle both Comment object and raw dict
            if isinstance(comment, dict):
                user_id = str(comment.get("user", {}).get("pk", ""))
                username = comment.get("user", {}).get("username", "")
                comment_text = comment.get("text", "")
                comment_id = str(comment.get("pk", ""))
            else:
                user_id = str(comment.user.pk)
                username = comment.user.username
                comment_text = comment.text
                comment_id = str(comment.pk)

            if not user_id or not username:
                continue

            if self.db.is_processed(user_id, shortcode):
                already_processed += 1
                continue

            if not self._comment_matches_keywords(comment_text, keywords):
                self._log(f"@{username} comment has no matching keyword - skipping")
                skipped_no_keyword += 1
                self.db.mark_processed(user_id, username, shortcode, comment_id)
                continue

            new_commenters += 1

            if not self._check_follows_you(int(user_id)):
                self._log(f"@{username} does NOT follow you - skipping")
                skipped_not_following += 1
                self.db.mark_processed(user_id, username, shortcode, comment_id)
                continue

            self._log(f"@{username} follows you - sending DM...")
            self._random_delay()

            if self._send_dm(int(user_id), username, dm_message):
                self._log(f"✓ DM sent to @{username}")
                dms_sent += 1
                self.dms_sent_this_session += 1
                self.db.mark_processed(user_id, username, shortcode, comment_id)

                # Reply to the comment after sending DM
                if comment_id and self._reply_to_comment(
                    media_pk, comment_id, username
                ):
                    self._log(f"✓ Replied to @{username}'s comment")
                    self.db.mark_comment_replied(user_id, shortcode)
            else:
                self._log(f"✗ Failed to DM @{username}", "WARN")

        self._log(
            f"Reel {shortcode} complete: {new_commenters} matched keywords, {dms_sent} DMs sent, "
            f"{skipped_not_following} not following, {skipped_no_keyword} no keyword, "
            f"{already_processed} already processed"
        )

    def process_all_reels_parallel(self):
        """
        Process all reels with parallel comment fetching.

        Phase 1: Fetch comments from ALL reels simultaneously (parallel)
        Phase 2: Process DMs sequentially to avoid rate limits
        """
        reels = self.config["reels"]
        max_dms = self.config["settings"]["max_dms_per_session"]

        if not reels:
            self._log("No reels configured", "WARN")
            return

        self._log(
            f"[PARALLEL MODE] Processing {len(reels)} reels with {self.max_workers} workers"
        )

        # Phase 1: Fetch comments from all reels in parallel
        self._log("=" * 40)
        self._log("Phase 1: Fetching comments from all reels in parallel...")

        all_reel_data = []
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all fetch tasks
            future_to_reel = {
                executor.submit(self._fetch_reel_comments, reel): reel for reel in reels
            }

            # Collect results as they complete
            for future in as_completed(future_to_reel):
                reel = future_to_reel[future]
                try:
                    reel_data = future.result()
                    all_reel_data.append(reel_data)
                except Exception as e:
                    self._log(f"Failed to fetch reel {reel['url']}: {e}", "ERROR")

        fetch_time = time.time() - start_time
        successful_fetches = sum(1 for r in all_reel_data if r.get("success"))
        total_comments = sum(
            len(r.get("comments", [])) for r in all_reel_data if r.get("success")
        )

        self._log(
            f"Phase 1 complete: Fetched {total_comments} comments from {successful_fetches}/{len(reels)} reels in {fetch_time:.1f}s"
        )

        # Phase 2: Process DMs sequentially
        self._log("=" * 40)
        self._log("Phase 2: Processing DMs sequentially...")

        for reel_data in all_reel_data:
            if self.dms_sent_this_session >= max_dms:
                self._log(f"Reached session limit of {max_dms} DMs", "WARN")
                break

            try:
                self._process_fetched_comments(reel_data)
            except FeedbackRequired:
                raise
            except Exception as e:
                self._log(f"Error processing reel: {e}", "ERROR")

        self._log("=" * 40)
        self._log(
            f"[PARALLEL MODE] Cycle complete. DMs sent this session: {self.dms_sent_this_session}"
        )

    def _send_dm_task(self, task: dict) -> dict:
        """
        Send a single DM with rate limiting (for parallel execution).
        Returns result dict with success status.
        """
        if self._stop_flag:
            return {"success": False, "reason": "stopped", **task}

        try:
            self._rate_limiter.acquire()

            # Check if we should stop
            if self._stop_flag:
                return {"success": False, "reason": "stopped", **task}

            # Check DM limit
            with self._dm_counter_lock:
                max_dms = self.config["settings"]["max_dms_per_session"]
                if self.dms_sent_this_session >= max_dms:
                    return {"success": False, "reason": "limit_reached", **task}

            user_id = task["user_id"]
            username = task["username"]
            message = task["dm_message"]
            shortcode = task["shortcode"]
            media_pk = task["media_pk"]
            comment_id = task["comment_id"]

            self._log(f"[PARALLEL DM] Sending to @{username}...")

            # Send DM with client lock
            with self._client_lock:
                success = self._send_dm(user_id, username, message)

            if success:
                with self._dm_counter_lock:
                    self.dms_sent_this_session += 1
                    current_count = self.dms_sent_this_session

                self.db.mark_processed(str(user_id), username, shortcode, comment_id)
                self._log(
                    f"[PARALLEL DM] ✓ DM sent to @{username} ({current_count} total)"
                )

                # Reply to comment
                with self._client_lock:
                    if comment_id and self._reply_to_comment(
                        media_pk, comment_id, username
                    ):
                        self._log(f"[PARALLEL DM] ✓ Replied to @{username}'s comment")
                        self.db.mark_comment_replied(str(user_id), shortcode)

                return {"success": True, **task}
            else:
                return {"success": False, "reason": "send_failed", **task}

        except FeedbackRequired:
            self._stop_flag = True
            return {"success": False, "reason": "blocked", **task}
        except Exception as e:
            self._log(
                f"[PARALLEL DM] Error sending to @{task.get('username', '?')}: {e}",
                "ERROR",
            )
            return {"success": False, "reason": str(e), **task}
        finally:
            self._rate_limiter.release()

    def _collect_dm_tasks(self, all_reel_data: list) -> list:
        """
        Collect all DM tasks from fetched reel data.
        Filters comments and checks follow status.
        """
        dm_tasks = []

        for reel_data in all_reel_data:
            if not reel_data.get("success"):
                continue

            shortcode = reel_data["shortcode"]
            media_pk = reel_data["media_pk"]
            comments = reel_data["comments"]
            keywords = reel_data["keywords"]
            dm_message = reel_data["dm_message"]

            self._log(
                f"[COLLECT] Processing reel {shortcode} ({len(comments)} comments)"
            )

            for comment in comments:
                # Handle both Comment object and raw dict
                if isinstance(comment, dict):
                    user_id = comment.get("user", {}).get("pk", "")
                    username = comment.get("user", {}).get("username", "")
                    comment_text = comment.get("text", "")
                    comment_id = str(comment.get("pk", ""))
                else:
                    user_id = comment.user.pk
                    username = comment.user.username
                    comment_text = comment.text
                    comment_id = str(comment.pk)

                if not user_id or not username:
                    continue

                # Skip already processed
                if self.db.is_processed(str(user_id), shortcode):
                    continue

                # Check keyword match
                if not self._comment_matches_keywords(comment_text, keywords):
                    self.db.mark_processed(
                        str(user_id), username, shortcode, comment_id
                    )
                    continue

                # Check follow status (with lock)
                with self._client_lock:
                    follows = self._check_follows_you(int(user_id))

                if not follows:
                    self._log(f"[COLLECT] @{username} does NOT follow - skipping")
                    self.db.mark_processed(
                        str(user_id), username, shortcode, comment_id
                    )
                    continue

                # Add to DM queue
                dm_tasks.append(
                    {
                        "user_id": int(user_id),
                        "username": username,
                        "shortcode": shortcode,
                        "media_pk": media_pk,
                        "comment_id": comment_id,
                        "dm_message": dm_message,
                    }
                )
                self._log(f"[COLLECT] @{username} queued for DM")

        return dm_tasks

    def process_all_reels_full_parallel(self):
        """
        FULLY PARALLEL processing - fetches AND sends DMs in parallel.

        Phase 1: Fetch comments from ALL reels simultaneously
        Phase 2: Collect and filter all DM tasks
        Phase 3: Send ALL DMs in parallel with rate limiting
        """
        reels = self.config["reels"]
        max_dms = self.config["settings"]["max_dms_per_session"]

        if not reels:
            self._log("No reels configured", "WARN")
            return

        self._stop_flag = False

        self._log("=" * 50)
        self._log(f"[FULL PARALLEL] Processing {len(reels)} reels")
        self._log(
            f"[FULL PARALLEL] Max {self.max_dm_workers} concurrent DMs, {self.dm_delay}s delay"
        )
        self._log("=" * 50)

        # Phase 1: Fetch comments from all reels in parallel
        self._log("Phase 1: Fetching comments from all reels...")
        start_time = time.time()

        all_reel_data = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_reel = {
                executor.submit(self._fetch_reel_comments, reel): reel for reel in reels
            }
            for future in as_completed(future_to_reel):
                try:
                    reel_data = future.result()
                    all_reel_data.append(reel_data)
                except Exception as e:
                    self._log(f"Fetch error: {e}", "ERROR")

        fetch_time = time.time() - start_time
        total_comments = sum(
            len(r.get("comments", [])) for r in all_reel_data if r.get("success")
        )
        self._log(
            f"Phase 1 complete: {total_comments} comments fetched in {fetch_time:.1f}s"
        )

        # Phase 2: Collect DM tasks
        self._log("-" * 40)
        self._log("Phase 2: Filtering and collecting DM tasks...")

        dm_tasks = self._collect_dm_tasks(all_reel_data)

        # Limit to max DMs
        if len(dm_tasks) > max_dms:
            self._log(f"Limiting from {len(dm_tasks)} to {max_dms} DMs")
            dm_tasks = dm_tasks[:max_dms]

        self._log(f"Phase 2 complete: {len(dm_tasks)} DMs queued")

        if not dm_tasks:
            self._log("No DMs to send")
            return

        # Phase 3: Send DMs in parallel
        self._log("-" * 40)
        self._log(f"Phase 3: Sending {len(dm_tasks)} DMs in parallel...")
        start_time = time.time()

        successful = 0
        failed = 0

        with ThreadPoolExecutor(max_workers=self.max_dm_workers) as executor:
            futures = [executor.submit(self._send_dm_task, task) for task in dm_tasks]

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result.get("success"):
                        successful += 1
                    else:
                        failed += 1
                        if result.get("reason") == "blocked":
                            self._log("Instagram blocked - stopping all DMs", "ERROR")
                            break
                except Exception as e:
                    failed += 1
                    self._log(f"DM task error: {e}", "ERROR")

        dm_time = time.time() - start_time

        self._log("=" * 50)
        self._log(f"[FULL PARALLEL] Complete!")
        self._log(
            f"[FULL PARALLEL] {successful} DMs sent, {failed} failed in {dm_time:.1f}s"
        )
        self._log(f"[FULL PARALLEL] Total this session: {self.dms_sent_this_session}")

    def run(self, parallel: bool = False, full_parallel: bool = False):
        self._log("=" * 50)
        self._log("Instagram Comment-to-DM Automation Bot")
        if full_parallel:
            self._log("Mode: FULL PARALLEL (fetching + DMs simultaneously)")
        elif parallel:
            self._log("Mode: PARALLEL (fetching all reels simultaneously)")
        self._log("=" * 50)

        stats = self.db.get_stats()
        self._log(
            f"Stats: {stats['total_dms_sent']} total DMs, {stats['dms_sent_today']} today"
        )

        if not self.login():
            self._log("Exiting due to login failure", "ERROR")
            sys.exit(1)

        try:
            if full_parallel:
                self.process_all_reels_full_parallel()
            elif parallel:
                self.process_all_reels_parallel()
            else:
                for reel in self.config["reels"]:
                    keywords = reel.get("keywords", [])
                    self.process_reel(reel["url"], reel["message"], keywords)

                    if (
                        self.dms_sent_this_session
                        >= self.config["settings"]["max_dms_per_session"]
                    ):
                        break

        except FeedbackRequired:
            self._log("Session stopped due to Instagram restrictions", "ERROR")
        except KeyboardInterrupt:
            self._log("Bot stopped by user")
        finally:
            self._log(f"Session complete: {self.dms_sent_this_session} DMs sent")
            stats = self.db.get_stats()
            self._log(f"Total DMs sent all time: {stats['total_dms_sent']}")

    def run_continuous(self, parallel: bool = False, full_parallel: bool = False):
        """Run continuously, checking for new comments at intervals"""
        self._log("=" * 50)
        self._log("Instagram Comment-to-DM Automation Bot (Continuous Mode)")
        if full_parallel:
            self._log("Mode: FULL PARALLEL (fetching + DMs simultaneously)")
        elif parallel:
            self._log("Mode: PARALLEL (fetching all reels simultaneously)")
        self._log("=" * 50)
        self._log("Press Ctrl+C to stop")

        stats = self.db.get_stats()
        self._log(
            f"Stats: {stats['total_dms_sent']} total DMs, {stats['dms_sent_today']} today"
        )

        if not self.login():
            self._log("Exiting due to login failure", "ERROR")
            sys.exit(1)

        check_interval = self.config["settings"].get(
            "check_interval_seconds",
            self.config["settings"].get("check_interval_minutes", 1) * 60,
        )

        try:
            while True:
                self._log("-" * 40)
                self._log("Checking for new comments...")

                self.dms_sent_this_session = 0  # Reset per cycle

                if full_parallel:
                    self.process_all_reels_full_parallel()
                elif parallel:
                    self.process_all_reels_parallel()
                else:
                    for reel in self.config["reels"]:
                        keywords = reel.get("keywords", [])
                        self.process_reel(reel["url"], reel["message"], keywords)

                stats = self.db.get_stats()
                self._log(f"Cycle complete. Total DMs sent: {stats['total_dms_sent']}")
                self._log(f"Next check in {check_interval} seconds...")

                time.sleep(check_interval)

        except FeedbackRequired:
            self._log("Bot stopped due to Instagram restrictions", "ERROR")
        except KeyboardInterrupt:
            self._log("Bot stopped by user")
        finally:
            stats = self.db.get_stats()
            self._log(f"Total DMs sent all time: {stats['total_dms_sent']}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Instagram Comment-to-DM Bot")
    parser.add_argument(
        "--continuous",
        "-c",
        action="store_true",
        help="Run continuously, checking for new comments at intervals",
    )
    parser.add_argument(
        "--parallel",
        "-p",
        action="store_true",
        help="Fetch comments from all reels in parallel (DMs still sequential)",
    )
    parser.add_argument(
        "--full-parallel",
        "-f",
        action="store_true",
        help="FULL parallel mode: fetch comments AND send DMs simultaneously (fastest, with rate limiting)",
    )
    args = parser.parse_args()

    bot = InstagramBot()

    if args.continuous:
        bot.run_continuous(parallel=args.parallel, full_parallel=args.full_parallel)
    else:
        bot.run(parallel=args.parallel, full_parallel=args.full_parallel)
