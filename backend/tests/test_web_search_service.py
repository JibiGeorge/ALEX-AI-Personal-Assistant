from types import SimpleNamespace

import pytest

from app.schemas.web_search import WebSearchRequest, WebSearchSource
from app.services.conversation_service import ApiKeyNotConfigured, ModelServiceError
from app.services.web_search_service import WebSearchService


class FakeSettings:
    def __init__(self, key="test-key"):
        self.key = key

    def get_api_key_for_service(self):
        return self.key


class FakeModels:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def generate_content(self, **request):
        self.requests.append(request)
        return self.response


class FakeClient:
    def __init__(self, models):
        self.models = models
        self.closed = False

    def close(self):
        self.closed = True


def grounded_response():
    return SimpleNamespace(
        text="Current grounded answer.",
        candidates=[
            SimpleNamespace(
                grounding_metadata=SimpleNamespace(
                    grounding_chunks=[
                        SimpleNamespace(
                            web=SimpleNamespace(
                                title="Example result",
                                uri="https://example.com/result",
                            )
                        ),
                        SimpleNamespace(
                            web=SimpleNamespace(title="Unsafe scheme", uri="javascript:alert(1)")
                        ),
                    ]
                )
            )
        ],
    )


def test_search_returns_grounded_answer_and_only_safe_source_urls(monkeypatch):
    models = FakeModels(grounded_response())
    client = FakeClient(models)
    monkeypatch.setattr("app.services.web_search_service.genai.Client", lambda **_: client)

    result = WebSearchService(FakeSettings()).search(
        WebSearchRequest(query="latest research", mode="research")
    )

    assert result.answer == "Current grounded answer."
    assert result.sources == [
        WebSearchSource(title="Example result", url="https://example.com/result")
    ]
    assert models.requests[0]["model"] == "gemini-2.5-flash"
    assert models.requests[0]["contents"].startswith("Research the following topic")
    assert models.requests[0]["config"].tools[0].google_search is not None
    assert client.closed


@pytest.mark.parametrize(
    ("search_request", "expected"),
    [
        (WebSearchRequest(query="latest AI news", mode="news"), "Latest news about: latest AI news"),
        (WebSearchRequest(query="laptop", mode="price"), "Current prices and purchasing information"),
        (
            WebSearchRequest(query="compare", mode="compare", items=["A", "B"], aspect="battery"),
            "Compare A, B in terms of battery.",
        ),
    ],
)
def test_search_modes_construct_explicit_queries(search_request, expected):
    assert expected in WebSearchService._build_query(search_request)


def test_search_requires_configured_key():
    with pytest.raises(ApiKeyNotConfigured):
        WebSearchService(FakeSettings(key=None)).search(WebSearchRequest(query="test"))


def test_compare_requires_two_items():
    with pytest.raises(ValueError, match="at least two"):
        WebSearchService._build_query(
            WebSearchRequest(query="compare", mode="compare", items=["A"])
        )


def test_grounding_cooldown_reports_rate_limit_without_repeating_request(monkeypatch):
    service = WebSearchService(FakeSettings())
    service._cooldown_until = 10**20
    monkeypatch.setattr(
        "app.services.web_search_service.genai.Client",
        lambda **_: pytest.fail("A cooled-down request must not call Gemini"),
    )

    with pytest.raises(ModelServiceError, match="rate-limited"):
        service.search(WebSearchRequest(query="test"))
