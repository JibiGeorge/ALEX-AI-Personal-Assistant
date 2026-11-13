"""
Background Topic News Monitor Service (GAP-11).

Provides user-configured topic and company news tracking:
- Daily headline checks via DuckDuckGo news with multi-tier fallback (ddgs, HTML scrape, web search).
- MD5 headline hashing to prevent duplicate alerts.
- Strict content gating blocking crypto, tokens, memecoins, and high-risk financial noise.
- Document persistence in JsonDocumentStore.
- Five-Word Outcome Contract adherence (done, failed).
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
import logging
from pathlib import Path
import re
from threading import RLock
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus

import httpx

from app.actions.base import ActionOutcomeResponse, done, failed
from app.core.storage import JsonDocumentStore, StorageError
from app.schemas.topic_monitor import TopicMonitorParameters
from app.schemas.web_search import WebSearchRequest
from app.services.web_search_service import WebSearchService

logger = logging.getLogger(__name__)

_DOCUMENT = "topic_monitors.json"

_BLOCKED_KEYWORDS = {
    # Brand / asset names
    "bitcoin", "ethereum", "dogecoin", "solana", "binance",
    "nft", "blockchain", "defi", "altcoin", "memecoin", "coin", "token",
    # Multilingual spellings of the crypto root
    "crypto", "kripto", "cripto", "krypto", "крипто", "仮想通貨", "暗号資産",
    "cryptocurrency",
}


def is_blocked_topic(topic: str) -> bool:
    """Check if the requested topic matches blocked crypto or financial speculation keywords."""
    clean = topic.lower()
    return any(word in clean for word in _BLOCKED_KEYWORDS)


def slugify_topic(topic: str) -> str:
    """Generate a clean alphanumeric slug identifier for a topic."""
    return re.sub(r"[^a-z0-9]+", "_", topic.lower().strip())[:40].strip("_")


def hash_headline(title: str) -> str:
    """Generate a 12-character MD5 hash of a headline to track uniqueness."""
    return hashlib.md5(title.encode("utf-8", errors="ignore")).hexdigest()[:12]


class TopicMonitorService:
    """Service managing background news topic monitors and daily headline checks."""

    def __init__(
        self,
        store: JsonDocumentStore,
        web_search_service: Optional[WebSearchService] = None,
    ) -> None:
        self._store = store
        self._web_search = web_search_service
        self._lock = RLock()

    def _read(self) -> Dict[str, Dict[str, Any]]:
        document = self._store.read(_DOCUMENT, {"version": 1, "monitors": {}})
        monitors = document.get("monitors", {})
        if not isinstance(monitors, dict):
            raise StorageError("Stored topic monitors must be a dictionary")
        return monitors

    def _write(self, monitors: Dict[str, Dict[str, Any]]) -> None:
        self._store.write(
            _DOCUMENT,
            {
                "version": 1,
                "monitors": monitors,
            },
        )

    def add_monitor(self, topic: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Add a new topic to background news monitoring."""
        clean = topic.strip()
        if not clean:
            return False, "Please specify a topic to monitor.", None

        if is_blocked_topic(clean):
            return False, "I don't monitor crypto or financial topics.", None

        slug = slugify_topic(clean)
        if not slug:
            return False, "Invalid topic name provided.", None

        today = datetime.now().strftime("%Y-%m-%d")
        with self._lock:
            monitors = self._read()
            if slug in monitors:
                existing = monitors[slug]["topic"]
                return False, f"Already monitoring: {existing}", monitors[slug]

            record = {
                "topic": clean,
                "added": today,
                "last_check": "",
                "last_hash": "",
                "last_title": "",
            }
            monitors[slug] = record
            self._write(monitors)

        logger.info("Added topic monitor: %s (slug: %s)", clean, slug)
        return True, f"Now monitoring: {clean}", record

    def remove_monitor(self, topic_or_slug: str) -> Tuple[bool, str]:
        """Remove a topic from background news monitoring by slug or name."""
        clean = topic_or_slug.strip().lower()
        if not clean:
            return False, "Please specify a topic to remove."

        target_slug = slugify_topic(clean)
        removed_name: Optional[str] = None

        with self._lock:
            monitors = self._read()
            if target_slug in monitors:
                removed_name = monitors.pop(target_slug).get("topic", target_slug)
            else:
                # Substring fallback
                for key, val in list(monitors.items()):
                    if clean in val.get("topic", "").lower():
                        removed_name = monitors.pop(key).get("topic", key)
                        break

            if removed_name is not None:
                self._write(monitors)

        if removed_name is not None:
            logger.info("Removed topic monitor: %s", removed_name)
            return True, f"Stopped monitoring: {removed_name}"

        return False, f"Not found in monitored topics: {topic_or_slug}"

    def list_monitors(self) -> List[Dict[str, Any]]:
        """List all active topic monitors."""
        with self._lock:
            monitors = self._read()
            return [
                {
                    "slug": slug,
                    "topic": data.get("topic", slug),
                    "added": data.get("added", ""),
                    "last_check": data.get("last_check", ""),
                    "last_title": data.get("last_title", ""),
                }
                for slug, data in monitors.items()
            ]

    def fetch_topic_news(self, topic: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Fetch latest news articles for topic across ddgs, direct HTML, and grounded search."""
        # Tier 1: Try duckduckgo_search / ddgs packages
        for pkg_name in ("ddgs", "duckduckgo_search"):
            try:
                mod = __import__(pkg_name, fromlist=["DDGS"])
                ddgs_cls = getattr(mod, "DDGS", None)
                if ddgs_cls:
                    results = []
                    with ddgs_cls() as ddgs:
                        for r in ddgs.news(topic, max_results=max_results):
                            results.append({
                                "title": r.get("title", "").strip(),
                                "snippet": r.get("body", "").strip(),
                                "source": r.get("source", "").strip() or "DuckDuckGo",
                                "url": r.get("url", "").strip(),
                            })
                    if results:
                        return results
            except Exception as exc:
                logger.debug("DDG library '%s' fetch failed for '%s': %s", pkg_name, topic, exc)

        # Tier 2: Direct DuckDuckGo HTML news scraping
        try:
            url = f"https://html.duckduckgo.com/html/?q=news+{quote_plus(topic)}"
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            with httpx.Client(headers=headers, timeout=10.0, follow_redirects=True) as client:
                resp = client.get(url)
                html = resp.text

            titles = re.findall(r'<a class="result__a"[^>]*>(.*?)</a>', html, flags=re.DOTALL)
            snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', html, flags=re.DOTALL)
            urls = re.findall(r'<a class="result__url"[^>]*href="([^"]+)"', html)

            parsed: List[Dict[str, str]] = []
            for i, raw_title in enumerate(titles):
                title = re.sub(r"<[^>]+>", "", raw_title).strip()
                if not title or len(title) < 5:
                    continue
                snippet = re.sub(r"<[^>]+>", "", snippets[i]).strip() if i < len(snippets) else ""
                link = urls[i].strip() if i < len(urls) else ""
                parsed.append({
                    "title": title,
                    "snippet": snippet,
                    "source": "DuckDuckGo",
                    "url": link,
                })
                if len(parsed) >= max_results:
                    break
            if parsed:
                return parsed
        except Exception as exc:
            logger.debug("Direct DDG HTML fetch failed for '%s': %s", topic, exc)

        # Tier 3: Grounded Gemini WebSearch fallback if configured
        if self._web_search:
            try:
                res = self._web_search.search(
                    WebSearchRequest(query=f"latest news {topic}", mode="news")
                )
                if res and res.answer:
                    first_url = res.sources[0].url if res.sources else ""
                    return [{
                        "title": f"News update on {topic}",
                        "snippet": res.answer[:250],
                        "source": "Web Grounding",
                        "url": first_url,
                    }]
            except Exception as exc:
                logger.debug("WebSearch fallback failed for '%s': %s", topic, exc)

        return []

    def check_topic(self, slug: str, force: bool = False) -> Optional[Dict[str, Any]]:
        """Check a single topic for breaking headlines. Returns an alert dict if a new headline appeared."""
        today = datetime.now().strftime("%Y-%m-%d")

        with self._lock:
            monitors = self._read()
            if slug not in monitors:
                return None
            data = monitors[slug]

        if not force and data.get("last_check") == today:
            logger.debug("Topic '%s' already checked today (%s); skipping", slug, today)
            return None

        topic = data.get("topic", slug)
        results = self.fetch_topic_news(topic, max_results=5)
        if not results:
            with self._lock:
                monitors = self._read()
                if slug in monitors:
                    monitors[slug]["last_check"] = today
                    self._write(monitors)
            return None

        top = results[0]
        title = top.get("title", "").strip()
        if not title:
            return None

        current_hash = hash_headline(title)
        with self._lock:
            monitors = self._read()
            if slug in monitors:
                monitors[slug]["last_check"] = today
                if current_hash == monitors[slug].get("last_hash"):
                    self._write(monitors)
                    return None  # Unchanged headline; no alert needed

                monitors[slug]["last_hash"] = current_hash
                monitors[slug]["last_title"] = title
                self._write(monitors)

        snippet = top.get("snippet", "")[:180]
        source = top.get("source", "")
        url = top.get("url", "")

        alert = {
            "topic": topic,
            "title": title,
            "snippet": snippet,
            "source": source,
            "url": url,
            "checked_at": today,
        }
        logger.info("[MONITOR_ALERT] New headline for '%s': %s", topic, title)
        return alert

    def check_all(self, force: bool = False) -> List[Dict[str, Any]]:
        """Run daily checks across all registered topic monitors."""
        with self._lock:
            slugs = list(self._read().keys())

        alerts: List[Dict[str, Any]] = []
        for slug in slugs:
            try:
                alert = self.check_topic(slug, force=force)
                if alert:
                    alerts.append(alert)
            except Exception as exc:
                logger.warning("Error checking topic '%s': %s", slug, exc)

        return alerts

    def execute(self, params: TopicMonitorParameters) -> ActionOutcomeResponse:
        """Execute a topic monitor action adhering to the Five-Word Outcome Contract."""
        action = (params.action or "list").lower().strip()

        if action == "add":
            if not params.topic:
                return failed(
                    "topic.monitor",
                    error="Missing topic",
                    message="Please specify a topic to monitor.",
                )
            success, msg, data = self.add_monitor(params.topic)
            if not success:
                return failed(
                    "topic.monitor",
                    error="Add monitor failed",
                    message=msg,
                )
            return done(
                "topic.monitor",
                msg,
                data=data or {},
            )

        if action == "remove":
            if not params.topic:
                return failed(
                    "topic.monitor",
                    error="Missing topic",
                    message="Please specify a topic to remove.",
                )
            success, msg = self.remove_monitor(params.topic)
            if not success:
                return failed(
                    "topic.monitor",
                    error="Topic not found",
                    message=msg,
                )
            return done(
                "topic.monitor",
                msg,
                data={"removed": params.topic},
            )

        if action == "list":
            monitors = self.list_monitors()
            if not monitors:
                return done(
                    "topic.monitor",
                    "No topics currently being monitored.",
                    data={"monitors": []},
                )
            names = [m["topic"] for m in monitors]
            return done(
                "topic.monitor",
                f"Currently monitoring {len(monitors)} topic(s): {', '.join(names)}",
                data={"monitors": monitors},
            )

        if action in ("check", "check_all"):
            alerts = self.check_all(force=params.force)
            if not alerts:
                return done(
                    "topic.monitor",
                    "Topic checks complete. No new headlines breaking today.",
                    data={"alerts": []},
                )
            lines = [f"Found {len(alerts)} new topic alert(s):"]
            for a in alerts:
                lines.append(f"[MONITOR_ALERT] {a['topic']}: {a['title']}")
                if a.get("snippet"):
                    lines.append(f"  {a['snippet']}")
            return done(
                "topic.monitor",
                "\n".join(lines),
                data={"alerts": alerts},
            )

        return failed(
            "topic.monitor",
            error="Unknown action",
            message=f"Unknown topic monitor action: '{action}'. Available: add, remove, list, check.",
        )

