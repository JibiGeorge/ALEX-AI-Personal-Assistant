"""
Unit tests for Background Topic News Monitor Service & Actions (GAP-11).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.actions.action_registry import ActionRegistry
from app.actions.base import ToolOutcome
from app.actions.builtins.topic_monitor import register_topic_monitor_actions
from app.core.storage import JsonDocumentStore
from app.schemas.topic_monitor import TopicMonitorParameters
from app.services.topic_monitor_service import (
    TopicMonitorService,
    hash_headline,
    is_blocked_topic,
    slugify_topic,
)


@pytest.fixture
def monitor_service(tmp_path: Path) -> TopicMonitorService:
    store = JsonDocumentStore(tmp_path)
    return TopicMonitorService(store)


# =============================================================================
# 1. Content Gating & Helpers
# =============================================================================

def test_is_blocked_topic():
    blocked = [
        "Bitcoin price today",
        "Ethereum ETF news",
        "Top solana memecoins",
        "NFT marketplace updates",
        "kripto para haberleri",
        "Decentralized defi protocol",
    ]
    for topic in blocked:
        assert is_blocked_topic(topic) is True

    allowed = [
        "DeepMind Gemini updates",
        "Quantum Computing",
        "SpaceX Starship launch",
        "James Webb Space Telescope",
        "Apple Silicon M5",
    ]
    for topic in allowed:
        assert is_blocked_topic(topic) is False


def test_slugify_topic():
    assert slugify_topic("Quantum Computing!") == "quantum_computing"
    assert slugify_topic("DeepMind AlphaFold 3") == "deepmind_alphafold_3"
    assert slugify_topic("  SpaceX   Starship  #9  ") == "spacex_starship_9"


def test_hash_headline():
    h1 = hash_headline("AlphaFold 3 open sourced")
    h2 = hash_headline("AlphaFold 3 open sourced")
    h3 = hash_headline("New breakthroughs in clean fusion energy")
    assert len(h1) == 12
    assert h1 == h2
    assert h1 != h3


# =============================================================================
# 2. Add, Remove & List Monitors
# =============================================================================

def test_add_and_list_monitor(monitor_service: TopicMonitorService):
    ok, msg, data = monitor_service.add_monitor("James Webb Telescope")
    assert ok is True
    assert "Now monitoring" in msg
    assert data["topic"] == "James Webb Telescope"

    # Add duplicate
    ok2, msg2, _ = monitor_service.add_monitor("James Webb Telescope")
    assert ok2 is False
    assert "Already monitoring" in msg2

    # List
    monitors = monitor_service.list_monitors()
    assert len(monitors) == 1
    assert monitors[0]["topic"] == "James Webb Telescope"
    assert monitors[0]["slug"] == "james_webb_telescope"


def test_add_blocked_topic(monitor_service: TopicMonitorService):
    ok, msg, _ = monitor_service.add_monitor("Bitcoin Halving")
    assert ok is False
    assert "crypto or financial" in msg


def test_remove_monitor(monitor_service: TopicMonitorService):
    monitor_service.add_monitor("Quantum Supremacy")
    monitor_service.add_monitor("DeepMind Robotics")

    # Remove by exact slug
    ok1, msg1 = monitor_service.remove_monitor("quantum_supremacy")
    assert ok1 is True
    assert "Stopped monitoring" in msg1

    # Remove by partial substring
    ok2, msg2 = monitor_service.remove_monitor("Robotics")
    assert ok2 is True
    assert "Stopped monitoring: DeepMind Robotics" in msg2

    # Remove non-existent
    ok3, msg3 = monitor_service.remove_monitor("NonExistent")
    assert ok3 is False
    assert "Not found" in msg3


# =============================================================================
# 3. Headline Fetching & Checks
# =============================================================================

def test_check_topic_new_headline(monitor_service: TopicMonitorService):
    monitor_service.add_monitor("Fusion Energy")
    mock_articles = [
        {
            "title": "Scientists achieve net energy gain in fusion experiment",
            "snippet": "Researchers at the National Ignition Facility announced...",
            "source": "Science Daily",
            "url": "https://example.com/fusion",
        }
    ]

    with patch.object(monitor_service, "fetch_topic_news", return_value=mock_articles):
        alert = monitor_service.check_topic("fusion_energy")
        assert alert is not None
        assert alert["topic"] == "Fusion Energy"
        assert "net energy gain" in alert["title"]
        assert alert["source"] == "Science Daily"

        # Subsequent check with same headline produces no alert
        alert2 = monitor_service.check_topic("fusion_energy", force=True)
        assert alert2 is None


def test_check_topic_skipped_if_already_checked_today(monitor_service: TopicMonitorService):
    monitor_service.add_monitor("Exoplanets")
    mock_articles = [{"title": "New Earth-like exoplanet detected", "snippet": "..."}]

    with patch.object(monitor_service, "fetch_topic_news", return_value=mock_articles):
        # First check
        alert = monitor_service.check_topic("exoplanets")
        assert alert is not None

        # Second check without force: skips network call
        with patch.object(monitor_service, "fetch_topic_news") as mock_fetch:
            alert2 = monitor_service.check_topic("exoplanets", force=False)
            assert alert2 is None
            mock_fetch.assert_not_called()

        # Second check WITH force: checks
        with patch.object(monitor_service, "fetch_topic_news", return_value=mock_articles):
            alert3 = monitor_service.check_topic("exoplanets", force=True)
            # Headline identical, so no alert
            assert alert3 is None


def test_check_all(monitor_service: TopicMonitorService):
    monitor_service.add_monitor("Topic A")
    monitor_service.add_monitor("Topic B")

    mock_news = {
        "Topic A": [{"title": "Headline A", "snippet": "Snippet A"}],
        "Topic B": [{"title": "Headline B", "snippet": "Snippet B"}],
    }

    def mock_fetch(topic, **_):
        return mock_news.get(topic, [])

    with patch.object(monitor_service, "fetch_topic_news", side_effect=mock_fetch):
        alerts = monitor_service.check_all(force=True)
        assert len(alerts) == 2
        titles = {a["title"] for a in alerts}
        assert "Headline A" in titles
        assert "Headline B" in titles


# =============================================================================
# 4. Direct HTML Scraping Fallback
# =============================================================================

def test_fetch_topic_news_html_scraping(monitor_service: TopicMonitorService):
    mock_html = """
    <html>
      <a class="result__a" href="https://news.com/article1">Breakthrough in Artificial Intelligence</a>
      <a class="result__snippet">New models achieve state-of-the-art benchmarks.</a>
      <a class="result__url" href="https://news.com/article1">news.com</a>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.text = mock_html

    with patch("httpx.Client.get", return_value=mock_resp):
        results = monitor_service.fetch_topic_news("Artificial Intelligence", max_results=1)
        assert len(results) == 1
        assert results[0]["title"] == "Breakthrough in Artificial Intelligence"
        assert "state-of-the-art" in results[0]["snippet"]


# =============================================================================
# 5. Action Execution & Five-Word Contract
# =============================================================================

def test_execute_actions(monitor_service: TopicMonitorService):
    # Add
    add_res = monitor_service.execute(TopicMonitorParameters(action="add", topic="Robotics"))
    assert add_res.status == ToolOutcome.DONE
    assert "Now monitoring: Robotics" in add_res.message

    # Blocked add
    blocked_res = monitor_service.execute(TopicMonitorParameters(action="add", topic="Solana token"))
    assert blocked_res.status == ToolOutcome.FAILED
    assert "crypto or financial" in blocked_res.message

    # List
    list_res = monitor_service.execute(TopicMonitorParameters(action="list"))
    assert list_res.status == ToolOutcome.DONE
    assert "Robotics" in list_res.message

    # Check
    with patch.object(
        monitor_service,
        "check_all",
        return_value=[{"topic": "Robotics", "title": "Humanoid robot dances"}],
    ):
        check_res = monitor_service.execute(TopicMonitorParameters(action="check"))
        assert check_res.status == ToolOutcome.DONE
        assert "Humanoid robot dances" in check_res.message

    # Remove
    rem_res = monitor_service.execute(TopicMonitorParameters(action="remove", topic="Robotics"))
    assert rem_res.status == ToolOutcome.DONE
    assert "Stopped monitoring: Robotics" in rem_res.message


# =============================================================================
# 6. Action Registry Registration
# =============================================================================

def test_action_registry_registration(monitor_service: TopicMonitorService):
    registry = ActionRegistry()
    register_topic_monitor_actions(registry, monitor_service)

    action = registry.get("topic.monitor")
    assert action is not None
    assert action.category == "search"
    assert action.requires_confirmation is False
    assert action.timeout_seconds == 30.0
    assert action.parameters == TopicMonitorParameters

