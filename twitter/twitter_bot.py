"""
Twitter External Post Adapter

Exposes post_external_text(text) that reuses the existing legacy tweet module's
authenticated client, headers, and endpoint. Does not touch joke CSV logic.

Note: Per constraints and limited API access, do not invoke this until the
rest of the RSS pipeline is validated. The function itself is safe and inert
unless called.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import sys
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from utils.error_logger import ErrorLogger

logger = ErrorLogger("twitter_adapter")


def post_external_text(text: str) -> bool:
    text = (text or "").strip()
    if not text:
        logger.warning("Empty text provided to post_external_text; skipping")
        return False

    try:
        # Reuse the legacy tweet module's OAuth1 auth, headers, and URL
        from tweet import tweet as legacy_tweet
        import requests  # from runtime env
    except Exception as e:
        logger.error("Twitter adapter import failed", exception=e)
        return False

    # Ensure we respect Twitter's 280-char limit while preserving the URL
    try:
        if len(text) > 280:
            import re
            urls = list(re.finditer(r"https?://\S+", text))
            if urls:
                last = urls[-1]
                url = text[last.start(): last.end()]
                # Reserve a space before URL if needed
                max_prefix = 279 - len(url)
                prefix = text[:last.start()].rstrip()
                if len(prefix) > max_prefix:
                    prefix = prefix[:max_prefix].rstrip()
                text = f"{prefix} {url}".strip()
            else:
                text = text[:280]
    except Exception:
        # If clamping fails for any reason, fall back to hard cut
        text = text[:280]

    try:
        payload = json.dumps({"text": text})
        resp = requests.post(
            legacy_tweet.url,
            headers=legacy_tweet.headers,
            data=payload,
            auth=legacy_tweet.auth,
            timeout=20,
        )
        if resp.status_code in (200, 201):
            logger.success("Twitter post successful")
            return True
        else:
            try:
                details = resp.json()
            except Exception:
                details = {"text": resp.text[:200]}
            logger.error("Twitter post failed", details={"status": resp.status_code, "resp": details})
            return False
    except Exception as e:
        logger.error("Twitter post error", exception=e)
        return False
