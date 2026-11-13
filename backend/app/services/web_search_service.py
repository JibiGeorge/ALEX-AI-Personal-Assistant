import logging
import threading
import time
from urllib.parse import urlparse

import httpx
from google import genai
from google.genai import errors, types

from app.schemas.web_search import (
    WebSearchRequest,
    WebSearchResponse,
    WebSearchSource,
)
from app.services.conversation_service import ApiKeyNotConfigured, ModelServiceError
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)
_SEARCH_MODELS = (
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
)
_GROUNDING_QUOTA_COOLDOWN_SECONDS = 15 * 60


class WebSearchService:
    def __init__(self, settings: SettingsService) -> None:
        self._settings = settings
        self._cooldown_until = 0.0
        self._cooldown_lock = threading.Lock()

    def search(self, request: WebSearchRequest) -> WebSearchResponse:
        query = self._build_query(request)
        with self._cooldown_lock:
            if time.monotonic() < self._cooldown_until:
                raise ModelServiceError(
                    "Grounded web search is temporarily rate-limited. Try again later."
                )

        api_key = self._settings.get_api_key_for_service()
        if not api_key:
            raise ApiKeyNotConfigured("Configure a Gemini API key in Settings to search.")

        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=30_000),
        )
        try:
            for model in _SEARCH_MODELS:
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=query,
                        config=types.GenerateContentConfig(
                            tools=[types.Tool(google_search=types.GoogleSearch())],
                            temperature=0.2,
                            max_output_tokens=2048,
                        ),
                    )
                    answer = (response.text or "").strip()
                    if not answer:
                        raise ModelServiceError(
                            "Grounded search returned an empty answer. Please try again."
                        )
                    from app.core.sanitizer import defang_data_tags
                    return WebSearchResponse(
                        query=request.query,
                        mode=request.mode,
                        answer=defang_data_tags(answer),
                        sources=self._sources(response),
                    )
                except errors.APIError as exc:
                    if exc.code == 429:
                        with self._cooldown_lock:
                            self._cooldown_until = (
                                time.monotonic() + _GROUNDING_QUOTA_COOLDOWN_SECONDS
                            )
                        logger.warning("Gemini grounded-search quota exhausted")
                    if exc.code in (404, 429, 500, 502, 503, 504):
                        logger.warning(
                            "Grounded search model %s unavailable (HTTP %s)",
                            model,
                            exc.code,
                        )
                        continue
                    if exc.code in (401, 403):
                        raise ModelServiceError(
                            "Gemini rejected the saved API key. Check your credential in Settings."
                        ) from exc
                    raise ModelServiceError(
                        f"Grounded search failed (HTTP {exc.code}). Please try again."
                    ) from exc
                except (httpx.HTTPError, TimeoutError) as exc:
                    logger.warning(
                        "Grounded search model %s timed out or could not connect",
                        model,
                    )
                    continue
            raise ModelServiceError(
                "Grounded web search is unavailable. Please try again later."
            )
        finally:
            client.close()

    @staticmethod
    def _build_query(request: WebSearchRequest) -> str:
        if request.mode == "compare":
            if len(request.items) < 2:
                raise ValueError("Compare mode requires at least two items.")
            return (
                f"Compare {', '.join(request.items)} in terms of {request.aspect}. "
                "Use current web sources and include specific factual differences."
            )
        if request.mode == "news":
            return f"Latest news about: {request.query}"
        if request.mode == "research":
            return (
                f"Research the following topic using current web sources: {request.query}. "
                "Include background, key facts, current state, and important nuances."
            )
        if request.mode == "price":
            return f"Current prices and purchasing information for: {request.query}"
        return request.query

    @staticmethod
    def _sources(response: object) -> list[WebSearchSource]:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return []
        metadata = getattr(candidates[0], "grounding_metadata", None)
        chunks = getattr(metadata, "grounding_chunks", None) or []
        sources: list[WebSearchSource] = []
        seen: set[str] = set()
        for chunk in chunks:
            web = getattr(chunk, "web", None)
            url = getattr(web, "uri", None)
            title = getattr(web, "title", None)
            if not isinstance(url, str) or not isinstance(title, str):
                continue
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https") or not parsed.hostname or url in seen:
                continue
            sources.append(WebSearchSource(title=title[:500] or url, url=url[:2048]))
            seen.add(url)
            if len(sources) == 30:
                break
        return sources
