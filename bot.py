import json
import random
import re
import sys
import time
from pathlib import Path

from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired, FeedbackRequired, LoginRequired

from database import Database


class InstagramBot:
    def __init__(self, config_path="config.json"):
        self.config = self._load_config(config_path)
        self.client = Client()
        self.client.delay_range = [2, 5]
        self.db = Database()
        self.session_file = Path("session.json")
        self.dms_sent_this_session = 0

    def _load_config(self, config_path: str) -> dict:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _log(self, message: str, level: str = "INFO"):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def login(self):
        username = self.config["username"]
        password = self.config["password"]

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
                else:
                    user_id = str(comment.user.pk)
                    username = comment.user.username
                    comment_text = comment.text

                if not user_id or not username:
                    continue

                if self.db.is_processed(user_id, shortcode):
                    already_processed += 1
                    continue

                if not self._comment_matches_keywords(comment_text, keywords):
                    self._log(f"@{username} comment has no matching keyword - skipping")
                    skipped_no_keyword += 1
                    self.db.mark_processed(user_id, username, shortcode)
                    continue

                new_commenters += 1

                if not self._check_follows_you(int(user_id)):
                    self._log(f"@{username} does NOT follow you - skipping")
                    skipped_not_following += 1
                    self.db.mark_processed(user_id, username, shortcode)
                    continue

                self._log(f"@{username} follows you - sending DM...")
                self._random_delay()

                if self._send_dm(int(user_id), username, dm_message):
                    self._log(f"✓ DM sent to @{username}")
                    dms_sent += 1
                    self.dms_sent_this_session += 1
                    self.db.mark_processed(user_id, username, shortcode)
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

    def run(self):
        self._log("=" * 50)
        self._log("Instagram Comment-to-DM Automation Bot")
        self._log("=" * 50)

        stats = self.db.get_stats()
        self._log(
            f"Stats: {stats['total_dms_sent']} total DMs, {stats['dms_sent_today']} today"
        )

        if not self.login():
            self._log("Exiting due to login failure", "ERROR")
            sys.exit(1)

        try:
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


if __name__ == "__main__":
    bot = InstagramBot()
    bot.run()
