"""
LLM Teaser Generator

Generates a short cross-platform teaser from RSS article metadata using the
OpenAI API if available/configured. Falls back to deterministic formatting
when API key or library is missing.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parents[1]


def _read_openai_key() -> Optional[str]:
    """Resolve OpenAI API key from multiple sources.

    Priority:
    1) Env var OPENAI_API_KEY
    2) Env var OPENAI_API_KEY_FILE (path to file with the key)
    3) Default secrets file locations (Windows path D:\\secrets\\GPTAPI.txt, or repo secrets/GPTAPI.txt)
    4) keys.json -> {"openai": {"api_key": "..."}}
    """
    # 1) Env key directly
    key = os.getenv("OPENAI_API_KEY")
    if key and key.strip():
        return key.strip()

    # 2) Env key file path
    key_file_env = os.getenv("OPENAI_API_KEY_FILE")
    if key_file_env:
        p = Path(key_file_env)
        if p.exists():
            try:
                return p.read_text(encoding="utf-8").strip()
            except Exception:
                pass

    # 3) Default secrets files
    candidates = [
        Path(r"D:\\secrets\\GPTAPI.txt"),
        Path(r"D:/secrets/GPTAPI.txt"),
        BASE_DIR / "secrets" / "GPTAPI.txt",
    ]
    for cand in candidates:
        try:
            if cand.exists():
                text = cand.read_text(encoding="utf-8").strip()
                if text:
                    return text
        except Exception:
            continue

    # 4) keys.json fallback
    try:
        keys_path = BASE_DIR / "keys.json"
        if keys_path.exists():
            with open(keys_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                openai_block = data.get("openai", {})
                if isinstance(openai_block, dict):
                    k = openai_block.get("api_key")
                    if k and isinstance(k, str) and k.strip() and "YOUR_OPENAI_API_KEY_HERE" not in k:
                        return k
    except Exception:
        pass
    return None


def generate_teaser_llm(title: str, summary: str, link: str, model: str = "gpt-4.1", article_text: Optional[str] = None) -> Optional[str]:
    """Return LLM-generated teaser or None on any failure."""
    api_key = _read_openai_key()
    if not api_key:
        return None
    try:
        # Lazy import to avoid hard dependency
        from openai import OpenAI  # type: ignore
        client = OpenAI(api_key=api_key)

        def _complete(m: str) -> Optional[str]:
            content_hint = (article_text or "").strip()
            if content_hint:
                content_hint = content_hint[:2000]
            prompt = (
                "Write a single-sentence teaser (<= 240 chars) for the article below. "
                "Make it specific by referencing one concrete detail or angle from the content. "
                "Avoid hashtags, emojis, and line breaks. Sound intriguing but accurate. "
                "End with the URL.\n\n"
                f"Title: {title.strip()}\n"
                f"Summary: {summary.strip()}\n"
                f"Content excerpt: {content_hint}\n"
                f"URL: {link.strip()}\n"
            )
            resp = client.chat.completions.create(
                model=m,
                messages=[
                    {"role": "system", "content": "You create concise, engaging social post teasers."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=120,
            )
            return resp.choices[0].message.content.strip() if resp and resp.choices else None

        # Try requested model first, then fallback
        for m in [model, "gpt-4.1", "gpt-4o-mini"]:
            try:
                text = _complete(m)
                if text:
                    if len(text) > 300:
                        text = text[:299]
                    return text
            except Exception:
                continue
        return None
    except Exception:
        return None
