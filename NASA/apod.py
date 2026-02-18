#!/usr/bin/env python3
"""
NASA Astronomy Picture of the Day (APOD) Poster
Fetches today's APOD image and posts it natively to Twitter and BlueSky.
No links in post text — image is embedded directly to maximize reach.

Standalone: python NASA/apod.py
Scheduled:  called from main_launcher.py daily
"""

import os
import sys
import json
import io
import requests
from datetime import datetime, date, timezone
from requests_oauthlib import OAuth1

# ── Path setup ──────────────────────────────────────────────────────────────
NASA_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(NASA_DIR)

# Add bsky to path so we can reuse manage_session
sys.path.append(BASE_DIR)

# ── Constants ────────────────────────────────────────────────────────────────
SECRETS_FILE   = r"D:\secrets\keys.json"
LAST_POST_FILE = os.path.join(NASA_DIR, "last_posted.json")
APOD_URL       = "https://api.nasa.gov/planetary/apod"
BSKY_PDS       = "https://bsky.social"
BSKY_KEYS_FILE = os.path.join(BASE_DIR, "keys.json")   # bsky tokens live here

TWITTER_TWEET_URL  = "https://api.twitter.com/2/tweets"
TWITTER_MEDIA_URL  = "https://upload.twitter.com/1.1/media/upload.json"

TWITTER_CHAR_LIMIT = 280
BSKY_CHAR_LIMIT    = 300
BSKY_IMAGE_MAX     = 950 * 1024   # 950 KB

# ── Credential loading ───────────────────────────────────────────────────────
TWITTER_PAYG_FILE = r"D:\secrets\TwitterPayAsYouGo.txt"

def _load_secrets() -> dict:
    if not os.path.exists(SECRETS_FILE):
        raise FileNotFoundError(f"Secrets file not found: {SECRETS_FILE}")
    with open(SECRETS_FILE, "r") as f:
        return json.load(f)

def _load_twitter_payg() -> dict:
    """Load PAYG Twitter credentials from key: value text file."""
    config = {}
    with open(TWITTER_PAYG_FILE, "r") as f:
        for line in f:
            stripped = line.strip()
            if ":" in stripped:
                key, value = stripped.split(":", 1)
                config[key.strip().lower().replace(" ", "_")] = value.strip()
    return {
        "consumer_key":        config.get("consumer_key") or config.get("api_key"),
        "consumer_secret":     config.get("secret_key")   or config.get("api_secret"),
        "access_token":        config.get("access_token"),
        "access_token_secret": config.get("access_token_secret"),
        "bearer_token":        config.get("bearer_token"),
    }

try:
    _secrets  = _load_secrets()
    _nasa_key = _secrets.get("nasa", {}).get("api_key", "DEMO_KEY")
except Exception as _e:
    print(f"[APOD] Warning: could not load {SECRETS_FILE}: {_e}")
    _nasa_key = "DEMO_KEY"

try:
    _tw = _load_twitter_payg()
    _oauth1 = OAuth1(
        _tw["consumer_key"], _tw["consumer_secret"],
        _tw["access_token"], _tw["access_token_secret"]
    )
    _bearer_token   = _tw["bearer_token"]
    _twitter_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_bearer_token}"
    }
    print("[APOD] Twitter PAYG credentials loaded")
except Exception as _e:
    print(f"[APOD] Warning: could not load Twitter PAYG creds from {TWITTER_PAYG_FILE}: {_e}")
    _oauth1 = None
    _twitter_headers = {}
    _bearer_token = None

# ── Deduplication ────────────────────────────────────────────────────────────
def _already_posted_today() -> bool:
    today = date.today().isoformat()
    if not os.path.exists(LAST_POST_FILE):
        return False
    try:
        with open(LAST_POST_FILE, "r") as f:
            data = json.load(f)
        return data.get("last_date") == today
    except Exception:
        return False

def _mark_posted_today():
    with open(LAST_POST_FILE, "w") as f:
        json.dump({"last_date": date.today().isoformat()}, f)

# ── APOD fetch ───────────────────────────────────────────────────────────────
def fetch_apod() -> dict:
    """Fetch today's APOD metadata from NASA API."""
    resp = requests.get(APOD_URL, params={"api_key": _nasa_key}, timeout=30)
    resp.raise_for_status()
    return resp.json()

# ── Image download + compression ─────────────────────────────────────────────
def download_image(url: str) -> bytes:
    """Download image; compress if needed for BlueSky's 950 KB limit."""
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    raw = resp.content

    if len(raw) <= BSKY_IMAGE_MAX:
        return raw

    # Compress with PIL
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(raw))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        print(f"[APOD] Image {len(raw)//1024}KB > limit, compressing...")
        for quality in range(85, 19, -10):
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            compressed = buf.getvalue()
            if len(compressed) <= BSKY_IMAGE_MAX:
                print(f"[APOD] Compressed to {len(compressed)//1024}KB at quality={quality}")
                return compressed

        # Last resort: resize then compress
        img.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        return buf.getvalue()

    except ImportError:
        print("[APOD] Pillow not installed — skipping compression, image may be too large for BlueSky")
        return raw

# ── Caption formatting ───────────────────────────────────────────────────────
def _build_caption(title: str, explanation: str, char_limit: int) -> str:
    """Build caption: title + as much explanation as fits."""
    header = f"\U0001f30c {title}\n\n"  # 🌌
    budget = char_limit - len(header)
    if budget <= 0:
        return header.strip()

    if len(explanation) <= budget:
        return header + explanation

    # Truncate at word boundary
    truncated = explanation[:budget - 1]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return header + truncated + "\u2026"   # …

# ── Twitter posting ───────────────────────────────────────────────────────────
def post_to_twitter(caption: str, image_bytes: bytes) -> bool:
    """Upload image to Twitter then post tweet with native image embed."""
    if _oauth1 is None:
        print("[APOD] Twitter credentials not loaded, skipping")
        return False

    # Step 1: Upload media (v1.1 endpoint — still the only way to upload media)
    try:
        media_resp = requests.post(
            TWITTER_MEDIA_URL,
            files={"media": image_bytes},
            auth=_oauth1,
            timeout=60
        )
        media_resp.raise_for_status()
        media_id = media_resp.json()["media_id_string"]
        print(f"[APOD] Twitter media uploaded: id={media_id}")
    except Exception as e:
        print(f"[APOD] Twitter media upload failed: {e}")
        return False

    # Step 2: Post tweet with media attached (v2 endpoint)
    try:
        tweet_data = json.dumps({
            "text": caption,
            "media": {"media_ids": [media_id]}
        })
        tweet_resp = requests.post(
            TWITTER_TWEET_URL,
            headers=_twitter_headers,
            data=tweet_data,
            auth=_oauth1,
            timeout=30
        )
        tweet_resp.raise_for_status()
        result = tweet_resp.json()
        if "data" in result:
            print(f"[APOD] Tweet posted: id={result['data']['id']}")
            return True
        else:
            print(f"[APOD] Twitter post unexpected response: {result}")
            return False
    except Exception as e:
        print(f"[APOD] Twitter post failed: {e}")
        return False

# ── BlueSky posting ───────────────────────────────────────────────────────────
def post_to_bluesky(title: str, caption: str, image_bytes: bytes) -> bool:
    """Upload image blob to BlueSky then create a post record with embed."""
    try:
        from bsky import bsky as bsky_module
    except ImportError:
        print("[APOD] bsky module not available, skipping BlueSky post")
        return False

    try:
        session = bsky_module.manage_session(BSKY_PDS, BSKY_KEYS_FILE)
        if not session:
            print("[APOD] Could not establish BlueSky session")
            return False
    except Exception as e:
        print(f"[APOD] BlueSky session error: {e}")
        return False

    access_jwt = session.get("accessJwt") or session.get("bsky", {}).get("accessJwt")
    did        = session.get("did")       or session.get("bsky", {}).get("did")

    if not access_jwt or not did:
        print(f"[APOD] BlueSky session missing accessJwt or did: {list(session.keys())}")
        return False

    # Step 1: Upload image blob
    try:
        blob_resp = requests.post(
            f"{BSKY_PDS}/xrpc/com.atproto.repo.uploadBlob",
            headers={
                "Authorization": f"Bearer {access_jwt}",
                "Content-Type": "image/jpeg"
            },
            data=image_bytes,
            timeout=60
        )
        blob_resp.raise_for_status()
        blob = blob_resp.json()["blob"]
        print(f"[APOD] BlueSky blob uploaded ({len(image_bytes)//1024}KB)")
    except Exception as e:
        print(f"[APOD] BlueSky blob upload failed: {e}")
        return False

    # Step 2: Create post record with image embed
    try:
        post_record = {
            "$type": "app.bsky.feed.post",
            "text": caption,
            "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "embed": {
                "$type": "app.bsky.embed.images",
                "images": [{
                    "image": blob,
                    "alt": title
                }]
            }
        }
        create_resp = requests.post(
            f"{BSKY_PDS}/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {access_jwt}"},
            json={
                "repo": did,
                "collection": "app.bsky.feed.post",
                "record": post_record
            },
            timeout=30
        )
        create_resp.raise_for_status()
        print(f"[APOD] BlueSky post created")
        return True
    except Exception as e:
        print(f"[APOD] BlueSky post failed: {e}")
        return False

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] NASA APOD poster starting...")

    if _already_posted_today():
        print(f"[{now}] APOD already posted today, skipping")
        return

    # Fetch APOD metadata
    try:
        apod = fetch_apod()
    except Exception as e:
        print(f"[APOD] Failed to fetch APOD: {e}")
        return

    title       = apod.get("title", "NASA APOD")
    explanation = apod.get("explanation", "")
    media_type  = apod.get("media_type", "image")
    image_url   = apod.get("hdurl") or apod.get("url", "")

    print(f"[APOD] Today: '{title}' ({media_type})")

    if media_type != "image":
        print(f"[APOD] Today's APOD is a {media_type}, not an image — skipping")
        return

    if not image_url:
        print("[APOD] No image URL in APOD response — skipping")
        return

    # Download image
    try:
        image_bytes = download_image(image_url)
        print(f"[APOD] Downloaded {len(image_bytes)//1024}KB from {image_url[:60]}...")
    except Exception as e:
        print(f"[APOD] Image download failed: {e}")
        return

    # Post to both platforms
    tw_caption   = _build_caption(title, explanation, TWITTER_CHAR_LIMIT)
    bsky_caption = _build_caption(title, explanation, BSKY_CHAR_LIMIT)

    print(f"[APOD] Caption preview ({len(tw_caption)} chars): {tw_caption[:80]}...")

    tw_ok   = post_to_twitter(tw_caption, image_bytes)
    bsky_ok = post_to_bluesky(title, bsky_caption, image_bytes)

    if tw_ok or bsky_ok:
        _mark_posted_today()
        print(f"[APOD] Done — Twitter: {'OK' if tw_ok else 'FAILED'}, BlueSky: {'OK' if bsky_ok else 'FAILED'}")
    else:
        print("[APOD] Both posts failed — not marking as posted (will retry next run)")


if __name__ == "__main__":
    main()
