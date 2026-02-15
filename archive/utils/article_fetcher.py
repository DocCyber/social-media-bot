"""
Article Fetcher and Extractor

Lightweight HTML fetch + content extraction to provide richer context to the
LLM teaser generator. Avoids heavy dependencies; uses BeautifulSoup if
available, otherwise a minimal fallback that strips tags.
"""

from __future__ import annotations

import re
from typing import Optional
from pathlib import Path


def _clean_text(text: str) -> str:
    # Collapse whitespace and trim
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_article_text(url: str, timeout: int = 15, max_chars: int = 4000) -> Optional[str]:
    """Fetch URL and extract readable article text (best-effort).

    - Tries BeautifulSoup + common content containers (article, main, content divs).
    - Falls back to stripping tags from body.
    - Returns a cleaned string capped at max_chars.
    """
    try:
        import requests  # type: ignore
        resp = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })
        resp.raise_for_status()
        html = resp.text
    except Exception:
        return None

    # Try BeautifulSoup if available
    try:
        from bs4 import BeautifulSoup  # type: ignore
        soup = BeautifulSoup(html, "html.parser")

        # Remove scripts/styles
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        candidates = []
        # Common containers
        candidates.extend(soup.find_all("article"))
        main = soup.find("main")
        if main:
            candidates.append(main)
        # Heuristic: divs with content-ish ids/classes
        for sel in [
            "div#content", "div.content", "div.post-content", "div.entry-content",
            "section#content", "section.content"
        ]:
            candidates.extend(soup.select(sel))

        text = ""
        for cand in candidates:
            cand_text = cand.get_text(" ", strip=True)
            cand_text = _clean_text(cand_text)
            if len(cand_text) > len(text):
                text = cand_text

        if not text:
            # Fallback to body text
            body = soup.find("body")
            if body:
                text = _clean_text(body.get_text(" ", strip=True))

        if not text:
            return None

        if len(text) > max_chars:
            text = text[: max_chars].rsplit(" ", 1)[0]
        return text
    except Exception:
        # Minimal fallback: strip tags with regex (crude)
        try:
            # Remove scripts/styles
            html2 = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
            html2 = re.sub(r"<style[\s\S]*?</style>", " ", html2, flags=re.I)
            # Strip tags
            text = re.sub(r"<[^>]+>", " ", html2)
            text = _clean_text(text)
            if len(text) > max_chars:
                text = text[: max_chars].rsplit(" ", 1)[0]
            return text or None
        except Exception:
            return None

