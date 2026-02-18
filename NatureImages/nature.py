#!/usr/bin/env python3
"""
Nature Images Poster
Pulls landscape/nature images from NASA EPIC and Pexels, posts them
natively (image embedded, no link) to Twitter and BlueSky.

Sources:
  - NASA EPIC: full-Earth-disk photos, public domain, no API key needed
  - Pexels: licensed-for-free-use photography, landscape orientation,
             nature-only search terms to avoid images of people

Standalone: python NatureImages/nature.py
Scheduled:  called from main_launcher.py
"""

import os
import sys
import json
import io
import random
import time
import hashlib
import requests
from datetime import datetime, timezone
from requests_oauthlib import OAuth1

# ── Path setup ───────────────────────────────────────────────────────────────
NATURE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = os.path.dirname(NATURE_DIR)
sys.path.append(BASE_DIR)

# ── Constants ─────────────────────────────────────────────────────────────────
SECRETS_KEYS    = r"D:\secrets\keys.json"
NASA_KEY_FILE   = r"D:\secrets\ApiDataGov.txt"
PEXELS_KEY_FILE = r"D:\secrets\pexelsapi.txt"
CLAUDE_KEY_FILE = r"D:\secrets\CLAUDEAPI.txt"
BSKY_KEYS_FILE  = os.path.join(BASE_DIR, "keys.json")   # bsky JWT tokens
LOG_FILE        = os.path.join(NATURE_DIR, "posted_log.txt")
LOG_MAX         = 200   # keep last N image IDs

CLAUDE_API_URL  = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL    = "claude-sonnet-4-5-20250929"

EPIC_LIST_URL  = "https://epic.gsfc.nasa.gov/api/natural"
EPIC_IMG_BASE  = "https://epic.gsfc.nasa.gov/archive/natural"
PEXELS_URL     = "https://api.pexels.com/v1/search"

BSKY_PDS       = "https://bsky.social"
TWITTER_TWEET  = "https://api.twitter.com/2/tweets"
TWITTER_MEDIA  = "https://upload.twitter.com/1.1/media/upload.json"

TWITTER_LIMIT  = 280
BSKY_LIMIT     = 300
BSKY_IMG_MAX   = 950 * 1024   # 950 KB — Twitter has no practical limit for photos

# Nature search terms — landscape orientation + unambiguous scenery terms.
# Deliberately avoids terms that Pexels commonly returns portrait/people results for
# (e.g. "meadow wildflowers", "tropical jungle", "savanna" all attract people shots).
PEXELS_TERMS = [
    "mountain peak",       "ocean waves",        "forest trees",      "canyon rocks",
    "waterfall river",     "sand dunes desert",  "arctic ice",        "volcano eruption",
    "coral reef fish",     "glacier snow",        "northern lights",   "coastal cliffs",
    "autumn forest",       "lightning storm",     "lava flow",         "river rapids",
    "foggy mountains",     "sunset clouds",       "night sky stars",   "rocky shoreline",
    "bamboo forest",       "wheat field",         "lavender fields",   "mangrove swamp",
]

# ── Credential loading ────────────────────────────────────────────────────────
TWITTER_PAYG_FILE = r"D:\secrets\TwitterPayAsYouGo.txt"

def _read_file(path: str) -> str:
    with open(path, "r") as f:
        return f.read().strip()

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
    _tw      = _load_twitter_payg()
    _oauth1  = OAuth1(_tw["consumer_key"], _tw["consumer_secret"],
                      _tw["access_token"], _tw["access_token_secret"])
    _bearer  = _tw["bearer_token"]
    _tw_headers = {"Content-Type": "application/json",
                   "Authorization": f"Bearer {_bearer}"}
    print("[Nature] Twitter PAYG credentials loaded")
except Exception as _e:
    print(f"[Nature] Warning: Twitter PAYG credentials not loaded: {_e}")
    _oauth1 = None
    _tw_headers = {}

try:
    _pexels_key = _read_file(PEXELS_KEY_FILE)
except Exception as _e:
    print(f"[Nature] Warning: Pexels key not loaded: {_e}")
    _pexels_key = None

# NASA API key available if needed for other endpoints; EPIC listing needs none
try:
    _nasa_key = _read_file(NASA_KEY_FILE)
except Exception:
    _nasa_key = "DEMO_KEY"

try:
    _claude_key = _read_file(CLAUDE_KEY_FILE)
    print("[Nature] Claude API key loaded")
except Exception as _e:
    print(f"[Nature] Warning: Claude API key not loaded: {_e}")
    _claude_key = None

# ── Deduplication (rolling log) ───────────────────────────────────────────────
def _load_posted_ids() -> set:
    if not os.path.exists(LOG_FILE):
        return set()
    with open(LOG_FILE, "r") as f:
        return {line.strip() for line in f if line.strip()}

def _append_posted_id(image_id: str):
    """Append ID to log, trim to last LOG_MAX lines."""
    existing = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            existing = [l.strip() for l in f if l.strip()]
    existing.append(str(image_id))
    existing = existing[-LOG_MAX:]
    with open(LOG_FILE, "w") as f:
        f.write("\n".join(existing) + "\n")

# ── Image download + compression ──────────────────────────────────────────────
def _download(url: str, headers: dict = None) -> bytes:
    resp = requests.get(url, headers=headers or {}, timeout=60)
    resp.raise_for_status()
    return resp.content

def _compress_for_bsky(raw: bytes) -> bytes:
    """
    Return image bytes safe for BlueSky's 950KB limit.
    Twitter receives the original full-resolution bytes — platforms resize on
    their end and serve the full version on click.
    """
    if len(raw) <= BSKY_IMG_MAX:
        return raw
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(raw))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        print(f"[Nature] Compressing {len(raw)//1024}KB for BlueSky...")
        for quality in range(85, 19, -10):
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            data = buf.getvalue()
            if len(data) <= BSKY_IMG_MAX:
                print(f"[Nature] Compressed to {len(data)//1024}KB (q={quality})")
                return data
        # Last resort: resize then compress
        img.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        return buf.getvalue()
    except ImportError:
        print("[Nature] Pillow not installed — returning raw (may exceed BlueSky limit)")
        return raw

# ── Caption helpers ───────────────────────────────────────────────────────────
def _truncate(text: str, budget: int) -> str:
    if len(text) <= budget:
        return text
    cut = text[:budget - 1]
    space = cut.rfind(" ")
    return (cut[:space] if space > 0 else cut) + "\u2026"

def _generate_caption(alt_text: str, credit: str, limit: int) -> str:
    """
    Ask Claude to write an eye-catching caption for a nature image.
    Falls back to a plain caption if the API call fails.

    alt_text : what the image shows (photographer's description or EPIC caption)
    credit   : attribution line, e.g. "photo by Jane Smith on Pexels" or "NASA EPIC Camera"
    limit    : max characters for the finished caption
    """
    if not _claude_key:
        return _fallback_caption(alt_text, credit, limit)

    prompt = f"""Write a short, eye-catching caption for a nature/landscape photo being posted to social media.

Image description: {alt_text}
Credit: {credit}

Rules:
- Keep it under {limit - 10} characters total (leave a small buffer)
- Incorporate the credit naturally somewhere in the caption — not bolted on at the end with an emoji, but woven into the sentence in a way that reads naturally and is grammatically correct
- Do not use more than one emoji in the entire caption, and only use one if it genuinely adds something; no emoji at all is fine
- Do not invent details that are not in the image description; you may make the language evocative but stay grounded in what is actually described
- Write in a calm, observational voice — not hype, not hashtags, not exclamation points
- Return only the caption text, no quotes, no commentary

Caption:"""

    headers = {
        "x-api-key": _claude_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    data = {
        "model": CLAUDE_MODEL,
        "max_tokens": 120,
        "temperature": 0.7,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        resp = requests.post(CLAUDE_API_URL, headers=headers, json=data, timeout=30)
        if resp.status_code == 200:
            caption = resp.json()["content"][0]["text"].strip().strip('"')
            # Hard-truncate if Claude went over despite instructions
            if len(caption) > limit:
                caption = _truncate(caption, limit)
            print(f"[Nature] Claude caption ({len(caption)} chars): {caption[:80]}{'...' if len(caption) > 80 else ''}")
            return caption
        else:
            print(f"[Nature] Claude API error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"[Nature] Claude caption request failed: {e}")

    return _fallback_caption(alt_text, credit, limit)

def _fallback_caption(alt_text: str, credit: str, limit: int) -> str:
    """Plain caption used when Claude is unavailable."""
    body   = alt_text.strip() if alt_text and alt_text.strip() else "Nature photography."
    footer = f"\n\n{credit}"
    budget = limit - len(footer)
    return _truncate(body, budget) + footer

# ── NASA EPIC source ──────────────────────────────────────────────────────────
def _fetch_epic(posted_ids: set):
    """
    Returns (image_id, raw_bytes, bsky_bytes, caption_str) or None.
    raw_bytes  → sent to Twitter at full resolution
    bsky_bytes → compressed to ≤950KB for BlueSky
    """
    try:
        resp = requests.get(EPIC_LIST_URL, timeout=30)
        resp.raise_for_status()
        images = resp.json()
    except Exception as e:
        print(f"[Nature] EPIC list fetch failed: {e}")
        return None

    if not images:
        print("[Nature] EPIC returned no images today")
        return None

    random.shuffle(images)
    for img in images:
        filename = img.get("image", "")        # "epic_1b_20260217142955"
        if not filename:
            continue

        date_str = img.get("date", "")[:10]   # "2026-02-17"
        caption  = img.get("caption", "")
        if not date_str:
            continue

        y, m, d = date_str.split("-")
        url     = f"{EPIC_IMG_BASE}/{y}/{m}/{d}/png/{filename}.png"

        try:
            print(f"[Nature] Downloading EPIC image: {filename}")
            raw    = _download(url)
            img_id = hashlib.md5(raw).hexdigest()   # dedup key = hash of actual pixels

            if img_id in posted_ids:
                print(f"[Nature] EPIC skipping already-posted: {filename} (md5={img_id[:8]}...)")
                continue

            bsky_bytes = _compress_for_bsky(raw)
            print(f"[Nature] EPIC: {len(raw)//1024}KB raw, {len(bsky_bytes)//1024}KB for BlueSky "
                  f"(md5={img_id[:8]}...)")
            return img_id, raw, bsky_bytes, caption
        except Exception as e:
            print(f"[Nature] EPIC image download failed: {e}")
            continue

    print("[Nature] All EPIC images already posted")
    return None

# ── Pexels source ─────────────────────────────────────────────────────────────
def _fetch_pexels(posted_ids: set):
    """
    Returns (image_id, raw_bytes, bsky_bytes, photographer, term) or None.

    Randomisation strategy: seed Python's RNG with the current time in
    microseconds so each run — even seconds apart — picks a different
    starting term and page.  The dedup log handles any accidental repeats.

    raw_bytes  → sent to Twitter at full resolution (original Pexels URL)
    bsky_bytes → compressed to ≤950KB for BlueSky
    """
    if not _pexels_key:
        print("[Nature] Pexels key not available")
        return None

    # Seed from current microsecond timestamp for maximum per-run variation
    seed = int(time.time() * 1_000_000)
    rng  = random.Random(seed)

    headers = {"Authorization": _pexels_key}
    terms   = PEXELS_TERMS.copy()
    rng.shuffle(terms)

    for term in terms:
        # Different page per term per run — rng advances with each call
        page = rng.randint(1, 30)

        params = {
            "query":       term,
            "orientation": "landscape",
            # No size filter — "large" (≥24MP) is too restrictive and returns
            # near-zero results for many terms, silently falling back to EPIC.
            "per_page":    80,            # max allowed; bigger pool per request
            "page":        page,
        }
        try:
            resp = requests.get(PEXELS_URL, headers=headers, params=params, timeout=30)
            if resp.status_code != 200:
                print(f"[Nature] Pexels HTTP {resp.status_code} for '{term}': {resp.text[:200]}")
                continue
            data   = resp.json()
            photos = data.get("photos", [])
            total  = data.get("total_results", "?")
            print(f"[Nature] Pexels '{term}' p{page}: {len(photos)} photos "
                  f"(total={total})")
            if not photos:
                continue
        except Exception as e:
            print(f"[Nature] Pexels search failed for '{term}': {e}")
            continue

        rng.shuffle(photos)
        for photo in photos:
            img_id = str(photo.get("id", ""))
            if img_id in posted_ids:
                continue

            # Use original for Twitter (full res), large as fallback
            src          = photo.get("src", {})
            url_original = src.get("original", "") or src.get("large", "")
            photographer = photo.get("photographer", "Unknown")
            photo_alt    = photo.get("alt", "")   # photographer's own description
            if not url_original:
                continue

            try:
                print(f"[Nature] Downloading Pexels photo id={img_id} "
                      f"('{term}' p{page}, seed={seed})")
                if photo_alt:
                    print(f"[Nature] Pexels alt: {photo_alt[:80]}")
                raw        = _download(url_original)
                bsky_bytes = _compress_for_bsky(raw)
                print(f"[Nature] Pexels: {len(raw)//1024}KB raw, "
                      f"{len(bsky_bytes)//1024}KB for BlueSky")
                return img_id, raw, bsky_bytes, photographer, term, photo_alt
            except Exception as e:
                print(f"[Nature] Pexels download failed: {e}")
                continue

    print("[Nature] No new Pexels images found")
    return None

# ── Twitter posting ───────────────────────────────────────────────────────────
def _post_twitter(caption: str, image_bytes: bytes) -> bool:
    if not _oauth1:
        print("[Nature] Twitter credentials missing, skipping")
        return False
    try:
        media_resp = requests.post(TWITTER_MEDIA,
                                   files={"media": image_bytes},
                                   auth=_oauth1, timeout=60)
        media_resp.raise_for_status()
        media_id = media_resp.json()["media_id_string"]
        print(f"[Nature] Twitter media uploaded: id={media_id}")
    except Exception as e:
        print(f"[Nature] Twitter media upload failed: {e}")
        return False

    try:
        resp = requests.post(TWITTER_TWEET,
                             headers=_tw_headers,
                             data=json.dumps({"text": caption,
                                              "media": {"media_ids": [media_id]}}),
                             auth=_oauth1, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        if "data" in result:
            print(f"[Nature] Tweet posted: id={result['data']['id']}")
            return True
        print(f"[Nature] Twitter unexpected response: {result}")
        return False
    except Exception as e:
        print(f"[Nature] Twitter post failed: {e}")
        return False

# ── BlueSky posting ───────────────────────────────────────────────────────────
def _post_bluesky(alt_text: str, caption: str, image_bytes: bytes) -> bool:
    try:
        from bsky import bsky as bsky_module
    except ImportError:
        print("[Nature] bsky module not available, skipping BlueSky")
        return False

    try:
        session = bsky_module.manage_session(BSKY_PDS, BSKY_KEYS_FILE)
        if not session:
            print("[Nature] BlueSky session failed")
            return False
    except Exception as e:
        print(f"[Nature] BlueSky session error: {e}")
        return False

    access_jwt = session.get("accessJwt") or session.get("bsky", {}).get("accessJwt")
    did        = session.get("did")       or session.get("bsky", {}).get("did")
    if not access_jwt or not did:
        print(f"[Nature] BlueSky session missing accessJwt/did")
        return False

    # Upload blob
    try:
        blob_resp = requests.post(
            f"{BSKY_PDS}/xrpc/com.atproto.repo.uploadBlob",
            headers={"Authorization": f"Bearer {access_jwt}",
                     "Content-Type": "image/jpeg"},
            data=image_bytes, timeout=60)
        blob_resp.raise_for_status()
        blob = blob_resp.json()["blob"]
        print(f"[Nature] BlueSky blob uploaded ({len(image_bytes)//1024}KB)")
    except Exception as e:
        print(f"[Nature] BlueSky blob upload failed: {e}")
        return False

    # Create post
    try:
        record = {
            "$type":     "app.bsky.feed.post",
            "text":      caption,
            "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "embed": {
                "$type":  "app.bsky.embed.images",
                "images": [{"image": blob, "alt": alt_text}]
            }
        }
        create_resp = requests.post(
            f"{BSKY_PDS}/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {access_jwt}"},
            json={"repo": did, "collection": "app.bsky.feed.post", "record": record},
            timeout=30)
        create_resp.raise_for_status()
        print("[Nature] BlueSky post created")
        return True
    except Exception as e:
        print(f"[Nature] BlueSky post failed: {e}")
        return False

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] Nature Images poster starting...")

    posted_ids = _load_posted_ids()
    print(f"[Nature] {len(posted_ids)} images in dedup log")

    # Choose source: 80% Pexels, 20% EPIC; fall back to the other if primary fails
    use_pexels_first = random.random() < 0.8
    sources = ["pexels", "epic"] if use_pexels_first else ["epic", "pexels"]

    image_id    = None
    tw_bytes    = None   # full resolution → Twitter
    bsky_bytes  = None   # compressed     → BlueSky
    tw_caption  = None
    bsky_caption= None
    alt_text    = None

    for source in sources:
        if source == "epic":
            print("[Nature] Trying NASA EPIC...")
            result = _fetch_epic(posted_ids)
            if result:
                img_id, tw_bytes, bsky_bytes, caption = result
                image_id     = img_id
                alt_text     = caption or "Full-disk Earth image from NASA EPIC camera"
                credit       = "NASA EPIC Camera"
                print(f"[Nature] EPIC image selected: id={img_id} — generating caption...")
                tw_caption   = _generate_caption(alt_text, credit, TWITTER_LIMIT)
                bsky_caption = _generate_caption(alt_text, credit, BSKY_LIMIT)
                break

        elif source == "pexels":
            print("[Nature] Trying Pexels...")
            result = _fetch_pexels(posted_ids)
            if result:
                img_id, tw_bytes, bsky_bytes, photographer, term, photo_alt = result
                image_id     = img_id
                alt_text     = photo_alt or f"{term.title()} landscape"
                credit       = f"photo by {photographer} on Pexels"
                print(f"[Nature] Pexels image selected: id={img_id}, '{term}' — generating caption...")
                tw_caption   = _generate_caption(alt_text, credit, TWITTER_LIMIT)
                bsky_caption = _generate_caption(alt_text, credit, BSKY_LIMIT)
                break

    if not image_id or tw_bytes is None:
        print("[Nature] No image found from any source — aborting")
        return

    print(f"[Nature] Caption preview: {tw_caption[:80]}...")

    # Twitter gets full-resolution bytes; BlueSky gets the size-capped version
    tw_ok   = _post_twitter(tw_caption, tw_bytes)
    bsky_ok = _post_bluesky(alt_text, bsky_caption, bsky_bytes)

    if tw_ok or bsky_ok:
        _append_posted_id(image_id)
        print(f"[Nature] Done — Twitter: {'OK' if tw_ok else 'FAILED'}, "
              f"BlueSky: {'OK' if bsky_ok else 'FAILED'}")
    else:
        print("[Nature] Both posts failed — ID not logged (will retry next run)")


def test_pexels():
    """
    Diagnostic: run ONE Pexels search and print what comes back.
    No download, no post, no log entry.
    Usage: python NatureImages/nature.py test
    """
    if not _pexels_key:
        print(f"[test] Pexels key not loaded — check {PEXELS_KEY_FILE}")
        return
    print(f"[test] Pexels key loaded: {_pexels_key[:6]}...{_pexels_key[-4:]}")
    term   = "ocean waves"
    params = {"query": term, "orientation": "landscape", "per_page": 5, "page": 1}
    headers = {"Authorization": _pexels_key}
    print(f"[test] GET {PEXELS_URL} params={params}")
    resp = requests.get(PEXELS_URL, headers=headers, params=params, timeout=30)
    print(f"[test] HTTP {resp.status_code}")
    if resp.status_code == 200:
        data   = resp.json()
        photos = data.get("photos", [])
        total  = data.get("total_results", "?")
        print(f"[test] {len(photos)} photos returned, total_results={total}")
        for p in photos[:3]:
            print(f"  id={p['id']}  photographer={p['photographer']}")
            print(f"  src.original={p['src'].get('original','')[:80]}")
    else:
        print(f"[test] Response body: {resp.text[:500]}")


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) > 1 and _sys.argv[1] == "test":
        test_pexels()
    else:
        main()
