"""
RSS Watcher and Fan-out Poster

Polls configured RSS feeds, generates a single teaser per new item, and posts
to platform-specific lightweight adapters via post_external_text().

Failure isolation is enforced: one retry max per platform, continue on errors.
BlueSky strictly reuses the existing session/token refresh logic (no new login).
Twitter posting is disabled by default per limited API access; enable via config.
"""

from __future__ import annotations

import json
import time
import random
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Optional dependency; handle gracefully if missing
try:
    import feedparser  # type: ignore
    HAS_FEEDPARSER = True
except Exception:
    HAS_FEEDPARSER = False

# Project utilities
import sys
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from utils.error_logger import ErrorLogger
    from utils.config_manager import ConfigManager
    from utils.llm_teaser import generate_teaser_llm
    from utils.article_fetcher import fetch_article_text
except Exception:
    # Minimal fallbacks if utils not yet importable
    class ErrorLogger:  # type: ignore
        def __init__(self, module_name: str):
            self.module_name = module_name
        def info(self, msg: str, details: Optional[Dict]=None):
            print(f"[INFO] {self.module_name}: {msg}")
        def success(self, msg: str, details: Optional[Dict]=None):
            print(f"[OK] {self.module_name}: {msg}")
        def warning(self, msg: str, details: Optional[Dict]=None, context: Optional[str]=None):
            print(f"[WARN] {self.module_name}: {msg}")
        def error(self, msg: str, details: Optional[Dict]=None, exception: Optional[Exception]=None):
            print(f"[ERROR] {self.module_name}: {msg} :: {exception}")
    class ConfigManager:  # type: ignore
        def __init__(self):
            self._config = {}
        def load_all_configs(self):
            try:
                with open(BASE_DIR / "config" / "master_config.json", "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            except Exception:
                try:
                    with open(BASE_DIR / "config.json", "r", encoding="utf-8") as f:
                        self._config = json.load(f)
                except Exception:
                    self._config = {}
        def get_global_config(self, key: str, default=None):
            return self._config.get(key, default)

    def generate_teaser_llm(title: str, summary: str, link: str, model: str = "gpt-4.1", article_text: Optional[str] = None):  # type: ignore
        return None

    def fetch_article_text(url: str, timeout: int = 15, max_chars: int = 4000):  # type: ignore
        return None


STATE_PATH = BASE_DIR / "rss" / "rss_state.json"
POSTED_ITEMS_PATH = BASE_DIR / "rss" / "posted_items.json"
LAST_PUBDATE_PATH = BASE_DIR / "rss" / "last_posted_pubdate.json"

# Thread-safe lock for file operations
_file_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def parse_pubdate(date_str: str) -> Optional[datetime]:
    """Parse RFC 2822 or ISO date string to datetime object."""
    if not date_str:
        return None
    try:
        # Try RFC 2822 format (common in RSS)
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str)
    except Exception:
        pass
    try:
        # Try ISO format
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except Exception:
        return None


def load_state(path: Path = STATE_PATH) -> Dict:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"feeds": {}, "last_checked": _now_iso()}


def save_state(state: Dict, path: Path = STATE_PATH) -> bool:
    with _file_lock:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            return True
        except Exception:
            return False


def load_posted_items(path: Path = POSTED_ITEMS_PATH) -> set:
    """Load set of GUIDs that have already been posted (deduplication safety)."""
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
    except Exception:
        pass
    return set()


def save_posted_items(posted: set, path: Path = POSTED_ITEMS_PATH) -> bool:
    """Save set of posted GUIDs for deduplication."""
    with _file_lock:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(list(posted), f, indent=2)
            return True
        except Exception:
            return False


def load_last_pubdate(path: Path = LAST_PUBDATE_PATH) -> Optional[datetime]:
    """Load the most recent pubDate we've successfully posted."""
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                date_str = data.get("last_posted_pubdate")
                if date_str:
                    return parse_pubdate(date_str)
    except Exception:
        pass
    return None


def save_last_pubdate(pub_date: datetime, path: Path = LAST_PUBDATE_PATH) -> bool:
    """Save the pubDate of the most recently posted item."""
    with _file_lock:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "last_posted_pubdate": pub_date.isoformat(),
                    "updated_at": _now_iso()
                }, f, indent=2)
            return True
        except Exception:
            return False


def get_rss_config(cfg: ConfigManager) -> Dict:
    cfg.load_all_configs()
    rss_cfg = cfg.get_global_config("rss", {}) or {}

    # Check if test mode is enabled
    test_mode = rss_cfg.get("test_mode", {})
    test_mode_enabled = test_mode.get("enabled", False)

    # Staggered posting configuration
    staggered = rss_cfg.get("staggered_posting", {})

    # Use test mode values if enabled, otherwise use production values
    if test_mode_enabled:
        delay_minutes = test_mode.get("delay_between_platforms_minutes", [5, 15])
    else:
        delay_minutes = staggered.get("delay_between_platforms_minutes", [40, 80])

    # Defaults
    return {
        "feeds": rss_cfg.get("feeds", []),
        "poll_interval_minutes": rss_cfg.get("poll_interval_minutes", 20),
        "post_delay_seconds": rss_cfg.get("post_delay_seconds", [5, 10]),
        "enable_twitter": rss_cfg.get("enable_twitter", False),  # default off per limited access
        "enable_mastodon": rss_cfg.get("enable_mastodon", True),
        "enable_bluesky": rss_cfg.get("enable_bluesky", True),  # BlueSky is main platform
        "post_on_first_run": rss_cfg.get("post_on_first_run", False),  # Safety: don't spam on first run
        "llm_enabled": rss_cfg.get("llm_enabled", True),
        "llm_model": rss_cfg.get("llm_model", "gpt-4.1"),  # user requested "5.1"; allow override via config
        "staggered_posting_enabled": staggered.get("enabled", True),
        "delay_between_platforms_minutes": delay_minutes,
        "randomize_platform_order": staggered.get("randomize_platform_order", True),
        "test_mode_enabled": test_mode_enabled,
    }


def parse_feed(url: str) -> List[Dict[str, str]]:
    """Return a list of items with keys: guid, title, link, summary, pubdate."""
    items: List[Dict[str, str]] = []
    if HAS_FEEDPARSER:
        feed = feedparser.parse(url)
        for e in getattr(feed, "entries", []):
            guid = getattr(e, "id", None) or getattr(e, "guid", None) or getattr(e, "link", None) or ""
            title = getattr(e, "title", "").strip()
            link = getattr(e, "link", "").strip()
            summary = getattr(e, "summary", getattr(e, "description", "")).strip()
            pubdate = getattr(e, "published", None) or getattr(e, "updated", None) or ""
            if guid and (title or summary):
                items.append({
                    "guid": guid,
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "pubdate": pubdate
                })
        return items
    # Minimal XML fallback
    try:
        import xml.etree.ElementTree as ET  # noqa: WPS433
        import requests  # type: ignore
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        # Basic RSS 2.0
        for item in root.findall(".//item"):
            guid = (item.findtext("guid") or item.findtext("link") or "").strip()
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            summary = (item.findtext("description") or "").strip()
            pubdate = (item.findtext("pubDate") or "").strip()
            if guid and (title or summary):
                items.append({
                    "guid": guid,
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "pubdate": pubdate
                })
        return items
    except Exception:
        return []


def generate_teaser(title: str, summary: str, link: str) -> str:
    """Generate a concise teaser. Deterministic fallback (no external API)."""
    max_len = 260  # leave room for link on platforms
    base = title.strip() or summary.strip()
    if len(base) > max_len:
        base = base[: max_len - 1] + "…"
    if link:
        return f"{base} {link}".strip()
    return base


def _post_with_retry(platform_name: str, post_func, text: str, logger: ErrorLogger) -> bool:
    tries = 0
    while tries < 2:
        try:
            ok = post_func(text)
            if ok:
                return True
            tries += 1
        except Exception as e:
            logger.warning(f"{platform_name}: post attempt failed", details={"try": tries + 1}, context=str(e))
            tries += 1
    logger.error(f"{platform_name}: giving up after 2 attempts")
    return False


def _staggered_posting_thread(
    teaser: str,
    post_funcs: List[Tuple[str, any]],
    delay_minutes: Tuple[int, int],
    randomize_order: bool,
    guid: str,
    feed_url: str,
    item_pubdate: datetime,
    logger: ErrorLogger,
) -> None:
    """
    Background thread that posts to platforms with staggered timing.
    Each article gets its own thread with randomized platform order and delays.
    """
    thread_id = threading.current_thread().name
    logger.info(f"[Thread {thread_id}] Starting staggered posting cycle for item: {guid[:50]}")

    # Make a copy of post_funcs to shuffle
    platforms = list(post_funcs)

    # Randomize platform order if enabled
    if randomize_order:
        random.shuffle(platforms)
        platform_order = " -> ".join([p[0] for p in platforms])
        logger.info(f"[Thread {thread_id}] Platform order: {platform_order}")

    # Post to each platform with delays
    posted_to_any = False
    for i, (platform_name, func) in enumerate(platforms):
        # Post to this platform
        logger.info(f"[Thread {thread_id}] Posting to {platform_name} ({i+1}/{len(platforms)})")
        success = _post_with_retry(platform_name, func, teaser, logger)

        if success:
            posted_to_any = True
            logger.success(f"[Thread {thread_id}] Posted to {platform_name}")
        else:
            logger.warning(f"[Thread {thread_id}] Failed to post to {platform_name}")

        # Sleep before next platform (except after the last one)
        if i < len(platforms) - 1:
            delay_min = random.randint(delay_minutes[0], delay_minutes[1])
            delay_seconds = delay_min * 60
            next_platform = platforms[i + 1][0]
            logger.info(f"[Thread {thread_id}] Waiting {delay_min} minutes before posting to {next_platform}...")
            time.sleep(delay_seconds)

    # Log results (state was already marked as processed before thread launch)
    if posted_to_any:
        logger.success(f"[Thread {thread_id}] Completed posting cycle for item {guid[:50]}")
    else:
        logger.error(f"[Thread {thread_id}] Failed to post to any platform for item: {guid[:50]}")
        # Note: Even on failure, we already marked this as processed to prevent re-posting
        # This is intentional to avoid spam loops on persistent failures

    logger.info(f"[Thread {thread_id}] Thread exiting")


def run_once() -> None:
    logger = ErrorLogger("rss_watcher")
    cfg = ConfigManager()
    conf = get_rss_config(cfg)
    feeds: List[str] = conf.get("feeds", [])
    enable_twitter: bool = conf.get("enable_twitter", False)
    enable_mastodon: bool = conf.get("enable_mastodon", True)
    enable_bluesky: bool = conf.get("enable_bluesky", True)
    post_on_first_run: bool = conf.get("post_on_first_run", False)
    delay_bounds: Tuple[int, int] = tuple(conf.get("post_delay_seconds", [5, 10]))  # type: ignore

    # Staggered posting configuration
    staggered_enabled: bool = conf.get("staggered_posting_enabled", True)
    delay_minutes: Tuple[int, int] = tuple(conf.get("delay_between_platforms_minutes", [40, 80]))  # type: ignore
    randomize_order: bool = conf.get("randomize_platform_order", True)

    if not feeds:
        logger.warning("No RSS feeds configured; skipping run")
        return

    state = load_state()
    state.setdefault("feeds", {})
    posted_guids = load_posted_items()
    last_posted_pubdate = load_last_pubdate()

    # Late imports for adapters to avoid import costs when unused
    from importlib import import_module

    # Platform adapters (import defensively; continue if a platform is unavailable)
    post_funcs = []

    # BlueSky - main platform
    if enable_bluesky:
        try:
            bsky_mod = import_module("bsky.bsky")
            # Import the adapter module that has post_external_text
            bsky_adapter = sys.modules.get("bluesky.bsky_bot")
            if not bsky_adapter:
                import importlib
                import bluesky.bsky_bot as bsky_adapter
            post_funcs.append(("BlueSky", getattr(bsky_adapter, "post_external_text")))
            logger.info("BlueSky adapter loaded successfully")
        except Exception as e:
            logger.error("BlueSky adapter failed to load", exception=e)

    # Mastodon
    if enable_mastodon:
        try:
            masto_mod = import_module("masto_adapter.masto_bot")
            post_funcs.append(("Mastodon", getattr(masto_mod, "post_external_text")))
            logger.info("Mastodon adapter loaded successfully")
        except Exception as e:
            logger.warning("Mastodon adapter not available; continuing without it", context=str(e))

    # Twitter
    if enable_twitter:
        try:
            tw_mod = import_module("twitter.twitter_bot")
            post_funcs.append(("Twitter", getattr(tw_mod, "post_external_text")))
            logger.info("Twitter adapter loaded successfully")
        except Exception as e:
            logger.warning("Twitter adapter not available; continuing without it", context=str(e))

    if not post_funcs:
        logger.error("No platform adapters available; cannot post")
        return

    # Collect ALL eligible items from all feeds first
    all_eligible_items: List[Tuple[str, Dict[str, str], datetime]] = []

    for feed_url in feeds:
        try:
            items = parse_feed(feed_url)
            if not items:
                logger.warning(f"No items parsed for feed: {feed_url}")
                continue

            last_guid = state["feeds"].get(feed_url)
            is_first_run = last_guid is None

            # Filter new items; maintain feed order (newest first in feed)
            unseen: List[Dict[str, str]] = []
            for it in items:
                if last_guid and it["guid"] == last_guid:
                    # Found the last item we saw, stop here
                    break
                # Also check if we've already posted this (deduplication safety)
                if it["guid"] not in posted_guids:
                    unseen.append(it)

            # First run handling: mark newest as seen WITHOUT posting (unless configured otherwise)
            if is_first_run and unseen:
                if post_on_first_run:
                    logger.info(f"First run for feed {feed_url}, will post newest item only")
                    unseen = unseen[:1]  # Only post the newest
                else:
                    logger.info(f"First run for feed {feed_url}, marking newest as seen without posting (safety)")
                    # Just mark the newest item as seen and skip posting
                    state["feeds"][feed_url] = unseen[0]["guid"]
                    save_state(state)
                    continue

            if not unseen:
                logger.info(f"No new items for feed: {feed_url}")
                continue

            # Filter by pubDate - skip items older than last posted
            for it in unseen:
                item_pubdate = parse_pubdate(it.get("pubdate", ""))

                # Skip items without valid pubDate
                if not item_pubdate:
                    logger.warning(f"Item {it['guid'][:50]} has no valid pubDate, skipping")
                    continue

                # Skip items older than or equal to last posted pubDate
                if last_posted_pubdate and item_pubdate <= last_posted_pubdate:
                    logger.info(f"Skipping item from {item_pubdate.isoformat()} (older than last posted {last_posted_pubdate.isoformat()})")
                    continue

                # Add to eligible items with feed URL and parsed pubdate
                all_eligible_items.append((feed_url, it, item_pubdate))

        except Exception as e:
            logger.error("Feed processing error", details={"feed": feed_url}, exception=e)

    # Sort all eligible items by pubDate (oldest first)
    all_eligible_items.sort(key=lambda x: x[2])

    # Post ONLY the oldest eligible item (if any)
    if all_eligible_items:
        feed_url, item_to_post, item_pubdate = all_eligible_items[0]

        logger.info(f"Found {len(all_eligible_items)} eligible items, posting oldest from {item_pubdate.isoformat()}")

        guid = item_to_post["guid"]

        # Try LLM first if enabled; fallback to deterministic teaser
        teaser = None
        if conf.get("llm_enabled", True):
            model = conf.get("llm_model", "gpt-4.1")
            article_text = None
            # Fetch full article to improve teaser specificity
            link = item_to_post.get("link", "")
            if link:
                article_text = fetch_article_text(link)
            teaser = generate_teaser_llm(
                item_to_post.get("title", ""),
                item_to_post.get("summary", ""),
                link,
                model=model,
                article_text=article_text,
            )
        if not teaser:
            teaser = generate_teaser(
                item_to_post.get("title", ""),
                item_to_post.get("summary", ""),
                item_to_post.get("link", "")
            )

        logger.info(f"Posting item: {item_to_post.get('title', 'No title')[:50]}")

        # Choose posting strategy based on configuration
        if staggered_enabled:
            # Mark as queued IMMEDIATELY before launching thread
            # This prevents the article from being picked up again on next cycle
            state["feeds"][feed_url] = guid
            posted_guids.add(guid)
            save_state(state)
            save_posted_items(posted_guids)
            save_last_pubdate(item_pubdate)

            # Launch background thread for staggered posting
            thread_name = f"RSS-Post-{guid[:8]}"
            thread = threading.Thread(
                target=_staggered_posting_thread,
                args=(
                    teaser,
                    post_funcs,
                    delay_minutes,
                    randomize_order,
                    guid,
                    feed_url,
                    item_pubdate,
                    logger,
                ),
                name=thread_name,
                daemon=True,
            )
            thread.start()
            logger.success(f"Launched posting thread {thread_name} for item, {len(all_eligible_items)-1} remaining in queue")
        else:
            # Original immediate posting logic
            posted_to_any = False
            for platform_name, func in post_funcs:
                success = _post_with_retry(platform_name, func, teaser, logger)
                if success:
                    posted_to_any = True
                sleep_s = random.randint(delay_bounds[0], delay_bounds[1]) if delay_bounds else 6
                time.sleep(sleep_s)

            # Only mark as processed if we posted to at least one platform
            if posted_to_any:
                state["feeds"][feed_url] = guid
                posted_guids.add(guid)
                save_state(state)
                save_posted_items(posted_guids)
                # Save the pubDate as our new threshold
                save_last_pubdate(item_pubdate)
                logger.success(f"Posted 1 item from {item_pubdate.isoformat()}, {len(all_eligible_items)-1} remaining in queue")
            else:
                logger.warning(f"Failed to post to any platform for item: {guid}")
    else:
        logger.info("No eligible items to post (queue empty or all items too old)")

    state["last_checked"] = _now_iso()
    save_state(state)


if __name__ == "__main__":
    run_once()
