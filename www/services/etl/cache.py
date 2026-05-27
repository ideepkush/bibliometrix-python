"""Lightweight on-disk cache for API responses.

Avoids hitting external rate limits during repeated calls with the
same query — particularly useful in CI, notebooks, and the dashboard.

Usage
-----
>>> from www.services.etl.cache import cached_get
>>> data = cached_get(url, params={"q": "machine learning"})

The cache key is the SHA-1 of (url, sorted params). Cached responses
expire after 24 hours by default.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import requests

CACHE_DIR = Path.home() / ".cache" / "bibliometrix_etl"
DEFAULT_TTL_SECONDS = 24 * 60 * 60  # 24 hours


def _ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_key(url: str, params: dict[str, Any] | None) -> str:
    payload = url + "|" + json.dumps(params or {}, sort_keys=True, default=str)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def cached_get(
    url: str,
    params: dict[str, Any] | None = None,
    timeout: int = 30,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> requests.Response:
    """GET with on-disk caching.

    Returns a `requests.Response`-like object backed either by a live
    HTTP call or a cached JSON file. On cache miss, the response is
    fetched once and stored.
    """
    _ensure_cache_dir()
    key = _cache_key(url, params)
    cache_file = CACHE_DIR / f"{key}.json"

    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < ttl_seconds:
            cached = json.loads(cache_file.read_text())
            return _MockResponse(
                status_code=cached["status_code"],
                _json=cached.get("json"),
                _text=cached.get("text", ""),
            )

    response = requests.get(url, params=params, timeout=timeout)
    if response.status_code == 200:
        try:
            body_json = response.json()
            body_text = None
        except ValueError:
            body_json = None
            body_text = response.text
        cache_file.write_text(json.dumps({
            "status_code": response.status_code,
            "json": body_json,
            "text": body_text,
        }))
    return response


def clear_cache() -> int:
    """Delete all cached responses. Returns the count removed."""
    if not CACHE_DIR.exists():
        return 0
    removed = 0
    for f in CACHE_DIR.glob("*.json"):
        f.unlink()
        removed += 1
    return removed


class _MockResponse:
    """A minimal stand-in for `requests.Response` used by the cache."""

    def __init__(self, status_code: int, _json: Any = None, _text: str = ""):
        self.status_code = status_code
        self._json = _json
        self.text = _text or ""

    def json(self) -> Any:
        if self._json is None:
            raise ValueError("No JSON body cached")
        return self._json
