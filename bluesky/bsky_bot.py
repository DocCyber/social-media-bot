"""
BlueSky External Post Adapter

Exposes post_external_text(text) that strictly reuses the existing session
and token refresh flow from the legacy BlueSky module (bsky/bsky.py).

Rules:
- NEVER create a new BlueSky session here.
- Use saved access token; on 401 only, try refresh with refreshJwt once.
- Do not call createSession or add new login logic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Dict

import sys
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from utils.error_logger import ErrorLogger

# Reuse legacy BlueSky functions
from bsky import bsky as legacy_bsky
import requests


logger = ErrorLogger("bluesky_adapter")


def _load_keys(keys_path: Path) -> Dict:
    try:
        with open(keys_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to load keys.json", exception=e)
        return {}


def _save_keys(keys_path: Path, data: Dict) -> None:
    try:
        with open(keys_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.warning("Failed to persist updated tokens", exception=e)


def _make_post(session: Dict, text: str, pds_url: str) -> bool:
    """Issue the createRecord POST using the access token in session."""
    try:
        # Reuse the legacy helper to ensure identical payload and facets behavior
        legacy_bsky.create_post(pds_url, session, text)
        return True
    except requests.exceptions.RequestException as e:  # includes HTTPError
        # Detect auth expiration
        status = getattr(getattr(e, "response", None), "status_code", None)
        if status:
            logger.warning("BlueSky post failed", details={"status": status}, context=str(e))
        else:
            logger.warning("BlueSky post failed (no status)", context=str(e))
        raise


def post_external_text(text: str) -> bool:
    """
    Post a prebuilt text to BlueSky using cached session.

    Never creates a new session. If token is invalid, tries refresh once using
    the existing refreshJwt, then retries the post a single time.
    """
    text = (text or "").strip()
    if not text:
        logger.warning("Empty text provided to post_external_text; skipping")
        return False

    keys_path = BASE_DIR / "keys.json"
    keys = _load_keys(keys_path)
    bsky_keys = keys.get("bsky", {}) if isinstance(keys, dict) else {}

    pds_url = bsky_keys.get("pds_url", "https://bsky.social")
    access = bsky_keys.get("accessJwt")
    refresh = bsky_keys.get("refreshJwt")

    if not access or not refresh:
        logger.error("Missing BlueSky tokens in keys.json (accessJwt/refreshJwt)")
        return False

    # We need a session dict with did + tokens for the legacy helper
    session: Optional[Dict] = None

    # Try to get a fresh session via refresh first to ensure 'did' is present,
    # without ever creating a new login session.
    try:
        refreshed = legacy_bsky.refresh_session(pds_url, refresh)
    except Exception as e:
        logger.warning("Refresh attempt raised", context=str(e))
        refreshed = None

    if refreshed and isinstance(refreshed, dict) and refreshed.get("accessJwt") and refreshed.get("did"):
        # Persist updated tokens (avoiding unrelated fields)
        bsky_keys["accessJwt"] = refreshed.get("accessJwt")
        bsky_keys["refreshJwt"] = refreshed.get("refreshJwt", refresh)
        keys["bsky"] = bsky_keys
        _save_keys(keys_path, keys)
        session = refreshed
    else:
        # Build a minimal session from stored tokens (may lack 'did')
        # If did is missing, the post will likely fail -> we'll try a refresh on 401 in the exception path
        session = {
            "accessJwt": access,
            "refreshJwt": refresh,
            "did": bsky_keys.get("did", ""),
            "handle": bsky_keys.get("handle", ""),
        }

    # First attempt
    try:
        if not session.get("did"):
            # Attempt a lightweight getSession to retrieve did if possible
            try:
                r = requests.get(
                    f"{pds_url}/xrpc/com.atproto.server.getSession",
                    headers={"Authorization": f"Bearer {session['accessJwt']}"},
                    timeout=15,
                )
                if r.status_code == 200:
                    data = r.json()
                    if data.get("did"):
                        session["did"] = data["did"]
            except Exception:
                # Non-fatal; proceed to post and rely on refresh fallback
                pass
        if not session.get("did"):
            # As a final pre-flight, attempt refresh (once) to fill did; still no createSession
            try:
                refreshed2 = legacy_bsky.refresh_session(pds_url, refresh)
                if refreshed2 and refreshed2.get("did") and refreshed2.get("accessJwt"):
                    session = refreshed2
            except Exception:
                pass

        _make_post(session, text, pds_url)
        logger.success("BlueSky post successful")
        return True
    except requests.exceptions.RequestException as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        if status == 401 and refresh:
            # Try exactly one refresh + retry
            try:
                refreshed = legacy_bsky.refresh_session(pds_url, refresh)
                if refreshed and refreshed.get("accessJwt") and refreshed.get("did"):
                    # Persist updated tokens
                    bsky_keys["accessJwt"] = refreshed.get("accessJwt")
                    bsky_keys["refreshJwt"] = refreshed.get("refreshJwt", refresh)
                    keys["bsky"] = bsky_keys
                    _save_keys(keys_path, keys)

                    _make_post(refreshed, text, pds_url)
                    logger.success("BlueSky post successful after refresh")
                    return True
            except Exception as e2:
                logger.error("BlueSky refresh+retry failed", exception=e2)
        else:
            logger.error("BlueSky post failed", exception=e)
    except Exception as e:
        logger.error("BlueSky unexpected error", exception=e)

    return False

