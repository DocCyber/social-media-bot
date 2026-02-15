import sys
import os
import json
import requests
from datetime import datetime, timezone, timedelta
from colorama import Fore, Style

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from modules.auth import get_valid_session

class ConservativeUnfollower:
    def __init__(self, config):
        self.config = config
        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        self.unreciprocated_file = os.path.join(self.data_dir, "unreciprocated_following.json")
        self.unfollower_log = os.path.join(self.data_dir, f"unfollower_log_{datetime.now().strftime('%Y-%m-%d')}.txt")
        self.whitelist_file = os.path.join(self.data_dir, "unfollow_whitelist.json")
        self.stats_file = os.path.join(self.data_dir, "unfollower_stats.json")
        self.config_file = os.path.join(self.data_dir, "unfollower_config.json")
        self.max_unfollows_per_pass = 10

        # Default settings
        self.grace_period_days = 7  # Default 7 days grace period

        # Load configuration
        self.load_config()

        # Default whitelist
        self.default_whitelist = [
            "theonion",
            "docafterdark.com",
            "did:plc:lzi56klkaehwzqut72b2hxs6"  # User's own DID
        ]

    def log_message(self, message, level="INFO"):
        """Log messages with timestamps to daily log file"""
        # Detroit time is GMT-5 (EST)
        detroit_tz = timezone(timedelta(hours=-5))
        timestamp = datetime.now(detroit_tz).strftime("%Y-%m-%d %H:%M:%S EST")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)

        # Ensure log file exists and append
        with open(self.unfollower_log, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")

    def load_config(self):
        """Load unfollower configuration"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    self.grace_period_days = config_data.get("grace_period_days", 7)
                    self.max_unfollows_per_pass = config_data.get("max_unfollows_per_pass", 10)
                return
            except Exception as e:
                self.log_message(f"Error loading config: {e}", "ERROR")

        # Create default config file
        default_config = {
            "grace_period_days": 7,
            "max_unfollows_per_pass": 10,
            "description": "Configuration for conservative unfollower. grace_period_days: how many days to wait before unfollowing someone who doesn't follow back."
        }

        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log_message(f"Error creating config file: {e}", "ERROR")

    def is_past_grace_period(self, user_data):
        """Check if a user is past the grace period for unfollowing"""
        try:
            followed_at_str = user_data.get("followedAt", "")

            # Handle legacy data that might not have followedAt field
            if not followed_at_str:
                # Check if this is old legacy data using notFollowingSince
                not_following_since = user_data.get("notFollowingSince", "")
                if not_following_since:
                    # For legacy data, use notFollowingSince as a proxy
                    # If it's from December 18, 2024, it's definitely past grace period
                    if "2024-12-18" in not_following_since:
                        self.log_message(f"Legacy data from 2024-12-18, past grace period")
                        return True

                # If no date info at all, assume it's old enough
                self.log_message(f"No date info for {user_data.get('did', 'unknown')}, assuming past grace period")
                return True

            # Parse the follow date
            followed_at = datetime.fromisoformat(followed_at_str.replace('Z', '+00:00'))
            if followed_at.tzinfo is None:
                followed_at = followed_at.replace(tzinfo=timezone.utc)

            # Calculate days since follow
            now = datetime.now(timezone.utc)
            days_since_follow = (now - followed_at).days

            return days_since_follow >= self.grace_period_days

        except Exception as e:
            self.log_message(f"Error checking grace period for {user_data.get('did', 'unknown')}: {e}", "ERROR")
            # If we can't parse the date, assume it's old enough to unfollow
            return True

    def load_whitelist(self):
        """Load whitelist of accounts to never unfollow"""
        if os.path.exists(self.whitelist_file):
            try:
                with open(self.whitelist_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return set(data.get("handles", []) + data.get("dids", []) + self.default_whitelist)
            except Exception as e:
                self.log_message(f"Error loading whitelist: {e}", "ERROR")

        # Create default whitelist file
        default_data = {
            "handles": ["theonion", "docafterdark.com"],
            "dids": ["did:plc:lzi56klkaehwzqut72b2hxs6"],
            "description": "Accounts to never unfollow. Add handles to 'handles' array or DIDs to 'dids' array."
        }

        with open(self.whitelist_file, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=2, ensure_ascii=False)

        return set(self.default_whitelist)

    def load_unreciprocated_data(self):
        """Load unreciprocated following data (handles both old and new formats)"""
        if not os.path.exists(self.unreciprocated_file):
            self.log_message("No unreciprocated following data found", "ERROR")
            return None

        try:
            with open(self.unreciprocated_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            # Handle old format (direct list) vs new format (dictionary with metadata)
            if isinstance(raw_data, list):
                self.log_message("Loading old format unreciprocated following data")
                # Convert old format to new format
                return {
                    "unreciprocated": raw_data,
                    "stats": {
                        "unreciprocated_count": len(raw_data),
                        "format": "legacy"
                    },
                    "generated_at": "unknown (legacy data)"
                }
            elif isinstance(raw_data, dict) and "unreciprocated" in raw_data:
                self.log_message("Loading new format unreciprocated following data")
                return raw_data
            else:
                self.log_message("Unrecognized data format in unreciprocated following file", "ERROR")
                return None

        except Exception as e:
            self.log_message(f"Error loading unreciprocated data: {e}", "ERROR")
            return None

    def save_stats(self, stats):
        """Save unfollower statistics"""
        try:
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log_message(f"Error saving stats: {e}", "ERROR")

    def load_stats(self):
        """Load existing stats or create new ones"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.log_message(f"Error loading stats: {e}", "ERROR")

        # Default stats
        return {
            "total_unfollowed": 0,
            "unfollows_today": 0,
            "last_unfollow_date": None,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "daily_history": {}
        }

    def update_unreciprocated_file(self, remaining_unreciprocated):
        """Update the unreciprocated following file after unfollowing"""
        try:
            data = self.load_unreciprocated_data()
            if data:
                data["unreciprocated"] = remaining_unreciprocated
                data["stats"]["unreciprocated_count"] = len(remaining_unreciprocated)
                data["last_updated"] = datetime.now(timezone.utc).isoformat()

                with open(self.unreciprocated_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                self.log_message(f"Updated unreciprocated file with {len(remaining_unreciprocated)} remaining entries")
        except Exception as e:
            self.log_message(f"Error updating unreciprocated file: {e}", "ERROR")

    def verify_relationship_status(self, session, user_did):
        """Verify the current relationship status with a specific user"""
        headers = {"Authorization": f"Bearer {session['accessJwt']}"}

        try:
            # Get the user's profile to check relationship status
            resp = requests.get(
                f"{self.config['bsky']['pds_url']}/xrpc/app.bsky.actor.getProfile",
                headers=headers,
                params={"actor": user_did}
            )
            resp.raise_for_status()
            profile = resp.json()

            viewer = profile.get("viewer", {})
            following = viewer.get("following")  # URI if we follow them, None if not
            followed_by = viewer.get("followedBy")  # URI if they follow us, None if not

            return {
                "profile": profile,
                "we_follow_them": following is not None,
                "they_follow_us": followed_by is not None,
                "follow_uri": following  # URI we need to delete the follow
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                self.log_message(f"Account deleted/suspended for {user_did}: {e}", "ERROR")
                return "deleted_account"
            else:
                self.log_message(f"HTTP error verifying relationship with {user_did}: {e}", "ERROR")
                return None
        except Exception as e:
            self.log_message(f"Error verifying relationship with {user_did}: {e}", "ERROR")
            return None

    def process_single_user(self, session, user_info):
        """Process a single user - verify relationship and take appropriate action"""
        user_did = user_info.get("did")
        handle = user_info.get("handle", "unknown")
        display_name = user_info.get("displayName", "no name")

        self.log_message(f"Processing user: {handle} ({display_name})")

        # Verify current relationship status
        relationship = self.verify_relationship_status(session, user_did)
        if relationship == "deleted_account":
            self.log_message(f"DELETED ACCOUNT: {handle} no longer exists, removing from list", "INFO")
            return "deleted_account"
        if not relationship:
            self.log_message(f"Failed to verify relationship with {handle}", "ERROR")
            return "error"

        profile = relationship["profile"]
        we_follow_them = relationship["we_follow_them"]
        they_follow_us = relationship["they_follow_us"]
        follow_uri = relationship["follow_uri"]

        # Log current relationship status
        status_msg = f"Relationship: We follow them: {we_follow_them}, They follow us: {they_follow_us}"
        self.log_message(status_msg)

        if not we_follow_them:
            self.log_message(f"STALE DATA: We don't follow {handle} anymore, removing from list", "INFO")
            return "stale_data"

        if they_follow_us:
            self.log_message(f"RELATIONSHIP CHANGED: {handle} now follows us back, removing from list", "INFO")
            return "now_following_back"

        # Confirmed unreciprocated follow - proceed with unfollow
        if not follow_uri:
            self.log_message(f"No follow URI found for {handle}", "ERROR")
            return "error"

        try:
            # Extract the record key (rkey) from the URI
            rkey = follow_uri.split('/')[-1]
            headers = {"Authorization": f"Bearer {session['accessJwt']}"}

            # Delete the follow record
            delete_resp = requests.post(
                f"{self.config['bsky']['pds_url']}/xrpc/com.atproto.repo.deleteRecord",
                headers=headers,
                json={
                    "repo": session["did"],
                    "collection": "app.bsky.graph.follow",
                    "rkey": rkey
                }
            )
            delete_resp.raise_for_status()

            self.log_message(f"UNFOLLOWED: {handle} ({display_name}) - Confirmed unreciprocated follow", "SUCCESS")
            return "unfollowed"

        except Exception as e:
            self.log_message(f"Error unfollowing {handle}: {e}", "ERROR")
            return "error"

    def run_unfollow_pass(self):
        """Run a batch pass processing multiple users up to max_unfollows_per_pass"""
        self.log_message(f"Starting conservative unfollow pass (batch mode, max: {self.max_unfollows_per_pass})")

        # Load whitelist (no logging)
        whitelist = self.load_whitelist()

        # Load unreciprocated data
        data = self.load_unreciprocated_data()
        if not data or not data.get("unreciprocated"):
            self.log_message("No unreciprocated following data available")
            return

        self.log_message(f"Total accounts in list: {len(data['unreciprocated'])}")

        # Get authenticated session
        session = get_valid_session(
            self.config["bsky"]["pds_url"],
            self.config["bsky"]["handle"],
            self.config["bsky"]["app_password"],
            self.config["paths"]["keys_file"]
        )

        if not session:
            self.log_message("Authentication failed", "ERROR")
            return

        # Find all candidates that are not whitelisted and past grace period
        candidates = []
        for user in data["unreciprocated"]:
            # Skip whitelisted accounts
            if (user["did"] in whitelist or
                user.get("handle", "") in whitelist or
                user.get("displayName", "") in whitelist):
                continue

            # Check grace period
            if self.is_past_grace_period(user):
                candidates.append(user)

                # Stop collecting once we have enough candidates
                if len(candidates) >= self.max_unfollows_per_pass:
                    break

        if not candidates:
            self.log_message("No candidates available for processing")
            return

        self.log_message(f"Found {len(candidates)} candidates for processing")

        # Process all candidates
        results = {
            "unfollowed": [],
            "stale_data": [],
            "now_following_back": [],
            "deleted_account": [],
            "error": []
        }

        for candidate in candidates:
            result = self.process_single_user(session, candidate)
            if result in results:
                results[result].append(candidate["did"])

        # Update stats
        stats = self.load_stats()
        today = datetime.now().strftime('%Y-%m-%d')

        if stats.get("last_unfollow_date") != today:
            stats["unfollows_today"] = 0

        # Initialize daily history for today if needed
        if today not in stats["daily_history"]:
            stats["daily_history"][today] = {"unfollowed": 0, "stale_cleaned": 0, "now_following_back": 0, "deleted_accounts": 0}
        else:
            # Ensure all keys exist (for compatibility with old stats)
            if "stale_cleaned" not in stats["daily_history"][today]:
                stats["daily_history"][today]["stale_cleaned"] = 0
            if "now_following_back" not in stats["daily_history"][today]:
                stats["daily_history"][today]["now_following_back"] = 0
            if "deleted_accounts" not in stats["daily_history"][today]:
                stats["daily_history"][today]["deleted_accounts"] = 0
            # Handle old "relationship_changed" key
            if "relationship_changed" in stats["daily_history"][today]:
                stats["daily_history"][today]["now_following_back"] = stats["daily_history"][today].pop("relationship_changed", 0)

        # Track all results from batch processing
        unfollowed_count = len(results["unfollowed"])
        stats["total_unfollowed"] += unfollowed_count
        stats["unfollows_today"] += unfollowed_count
        stats["last_unfollow_date"] = today
        stats["grace_period_days"] = self.grace_period_days

        # Update daily history with batch results
        stats["daily_history"][today]["unfollowed"] += len(results["unfollowed"])
        stats["daily_history"][today]["stale_cleaned"] += len(results["stale_data"])
        stats["daily_history"][today]["now_following_back"] += len(results["now_following_back"])
        stats["daily_history"][today]["deleted_accounts"] += len(results["deleted_account"])

        self.save_stats(stats)

        # Remove all processed users from list
        processed_dids = set()
        for result_list in results.values():
            processed_dids.update(result_list)

        if processed_dids:
            remaining = [user for user in data["unreciprocated"] if user["did"] not in processed_dids]
            self.update_unreciprocated_file(remaining)
            self.log_message(f"Remaining accounts: {len(remaining)}")

        # Final summary
        self.log_message(f"Pass completed: Processed {len(candidates)} accounts")
        self.log_message(f"  - Unfollowed: {len(results['unfollowed'])}")
        self.log_message(f"  - Stale data removed: {len(results['stale_data'])}")
        self.log_message(f"  - Now following back: {len(results['now_following_back'])}")
        self.log_message(f"  - Deleted accounts: {len(results['deleted_account'])}")
        self.log_message(f"  - Errors: {len(results['error'])}")
        self.log_message(f"Total unfollowed today: {stats['unfollows_today']}, All time: {stats['total_unfollowed']}")

def main():
    """Main entry point for conservative unfollower"""
    # Calculate the base directory (jokes directory)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Build configuration
    config = {
        "bsky": {
            "pds_url": "https://bsky.social",
            "handle": "docatcdi.com",
            "app_password": "hftk-zbuc-pl3k-xawr"
        },
        "paths": {
            "keys_file": os.path.join(base_dir, "keys.json"),
            "data_dir": os.path.join(base_dir, "bsky", "data")
        }
    }

    unfollower = ConservativeUnfollower(config)
    unfollower.run_unfollow_pass()

if __name__ == "__main__":
    main()