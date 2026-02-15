"""
Mastodon External Post Adapter

Exposes post_external_text(text) that reuses the consolidated Mastodon
platform adapter for authentication and posting. Does not alter existing
content generation paths; only provides an external entry point for RSS use.
"""

from __future__ import annotations

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from utils.error_logger import ErrorLogger

logger = ErrorLogger("mastodon_adapter")


def post_external_text(text: str) -> bool:
    text = (text or "").strip()
    if not text:
        logger.warning("Empty text provided to post_external_text; skipping")
        return False

    try:
        # Prefer the consolidated platform which reuses existing config and auth
        from platforms.mastodon_platform import MastodonPlatform
    except Exception as e:
        logger.error("Mastodon adapter not available (import failed)", exception=e)
        return False

    try:
        platform = MastodonPlatform()
        if not platform.authenticate():
            logger.error("Mastodon authentication failed")
            return False
        ok = platform.post_content(text)
        if ok:
            logger.success("Mastodon post successful")
        else:
            logger.error("Mastodon post failed")
        return ok
    except Exception as e:
        logger.error("Mastodon post error", exception=e)
        return False

