"""
Automated unit tests for Five-Word Outcome Contract (TASK-P3-08).

Verifies:
- ToolOutcome enum definition (done, unverified, failed, ask, started).
- ActionOutcomeResponse schema validation and backward-compatible properties.
- success property returns True strictly for DONE, never for STARTED, UNVERIFIED, FAILED, or ASK.
- is_started property identifies asynchronous running background processes.
- Unverified outcome behavior when operations cannot be verified on disk.
- Conformance of all built-in action handlers (files, search, memory, system) to the outcome contract.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import pytest
from pydantic import BaseModel

from app.actions.action_executor import ActionExecutor
from app.actions.action_registry import ActionDefinition, ActionRegistry
from app.actions.base import (
    ActionOutcomeResponse,
    ToolOutcome,
    ask,
    done,
    failed,
    started,
    unverified,
)
from app.actions.builtins.files import (
    DirectoryParameters,
    ReadParameters,
    WriteParameters,
    register_file_actions,
)
from app.actions.builtins.memory import RecallParameters, register_memory_actions
from app.actions.builtins.search import register_search_actions
from app.actions.builtins.system import NoParameters, register_system_actions
from app.core.storage import JsonDocumentStore
from app.schemas.memory import MemoryWrite
from app.schemas.web_search import WebSearchRequest
from app.services.file_workspace_service import FileWorkspaceService
from app.services.memory_service import MemoryService
from app.services.system_metrics_service import SystemMetricsService
from app.services.web_search_service import WebSearchService


# ==============================================================================
# Enum & Schema Contract Tests
# ==============================================================================

def test_action_base_returns_tool_outcome_enum():
    """Verify ToolOutcome enum values strictly match the five-word outcome contract."""
    assert ToolOutcome.DONE == "done"
    assert ToolOutcome.UNVERIFIED == "unverified"
    assert ToolOutcome.FAILED == "failed"
    assert ToolOutcome.ASK == "ask"
    assert ToolOutcome.STARTED == "started"

    resp = ActionOutcomeResponse(
        status=ToolOutcome.DONE,
        action="test.sample",
        message="Completed successfully",
        data={"value": 42},
    )
    assert resp.status == ToolOutcome.DONE
    assert resp.action == "test.sample"
    assert resp.data["value"] == 42


def test_success_property_returns_true_only_for_done():
    """Verify success property returns True ONLY for DONE, and False for all others."""
    done_resp = done("action.test")
    assert done_resp.success is True
    assert done_resp.is_done is True
    assert done_resp.is_started is False
    assert done_resp.is_failed is False
    assert done_resp.is_pending is False

    unverified_resp = unverified("action.test")
    assert unverified_resp.success is False
    assert unverified_resp.is_done is False
    assert unverified_resp.is_pending is True

    failed_resp = failed("action.test", error="Disk full")
    assert failed_resp.success is False
    assert failed_resp.is_done is False
    assert failed_resp.is_failed is True
    assert failed_resp.error == "Disk full"

    ask_resp = ask("action.test", question="Confirm delete?")
    assert ask_resp.success is False
    assert ask_resp.requires_clarification is True

    started_resp = started("action.test")
    assert started_resp.success is False
    assert started_resp.is_done is False


def test_success_property_returns_false_for_started():
    """Strict invariant: STARTED must NEVER be interpreted as completed success."""
    running_task = started("background.sync", message="Sync started in background", data={"job_id": "job_999"})
    assert running_task.status == ToolOutcome.STARTED
    assert running_task.success is False
    assert running_task.is_done is False
    assert running_task.is_started is True
    assert running_task.is_pending is True
    assert running_task.data["job_id"] == "job_999"


def test_is_started_property_identifies_running_jobs():
    """Verify that background callers can distinguish between terminal DONE and in-flight STARTED."""
    job_1 = started("render.video", message="Rendering video frame 1 of 500", data={"job_id": "v_1"})
    job_2 = done("render.video", message="Video render completed", data={"output_path": "out.mp4"})

    assert job_1.is_started is True
    assert job_1.is_done is False

    assert job_2.is_started is False
    assert job_2.is_done is True


# ==============================================================================
# Builtin Actions Conformance Tests
# ==============================================================================

def test_file_action_returns_unverified_if_write_not_flushed(tmp_path):
    """Verify file write returns UNVERIFIED if the target file cannot be verified on disk."""
    workspace = FileWorkspaceService(data_dir=tmp_path)
    registry = ActionRegistry()
    register_file_actions(registry, workspace)

    write_action = registry.get("files.write")
    assert write_action is not None

    # Normal verified write
    normal_res = write_action.handler(WriteParameters(path="hello.txt", content="Hello World"))
    assert isinstance(normal_res, ActionOutcomeResponse)
    assert normal_res.status == ToolOutcome.DONE
    assert normal_res.success is True

    # Simulate unverified state where write was initiated but file was not flushed/persisted
    orig_write = workspace.write_text
    def mock_unflushed_write(path, content):
        res = orig_write(path, content)
        target = workspace._resolve(path, allow_root=False)
        if target.is_file():
            target.unlink()
        return res
    workspace.write_text = mock_unflushed_write

    try:
        unverified_res = write_action.handler(WriteParameters(path="unflushed.txt", content="sample"))
        assert isinstance(unverified_res, ActionOutcomeResponse)
        assert unverified_res.status == ToolOutcome.UNVERIFIED
        assert unverified_res.success is False
        assert unverified_res.is_done is False
        assert unverified_res.is_pending is True
    finally:
        workspace.write_text = orig_write


def test_all_builtin_actions_conform_to_outcome_contract(tmp_path, monkeypatch):
    """Verify files, search, memory, and system built-ins return ActionOutcomeResponse."""
    registry = ActionRegistry()

    # Files
    workspace = FileWorkspaceService(data_dir=tmp_path)
    (workspace.root / "doc.txt").write_text("file content", encoding="utf-8")
    register_file_actions(registry, workspace)

    read_res = registry.get("files.read").handler(ReadParameters(path="doc.txt"))
    assert isinstance(read_res, ActionOutcomeResponse)
    assert read_res.status == ToolOutcome.DONE
    assert read_res.data["content"] == "file content"

    list_res = registry.get("files.list").handler(DirectoryParameters(path="."))
    assert isinstance(list_res, ActionOutcomeResponse)
    assert list_res.status == ToolOutcome.DONE

    # Memory
    store = JsonDocumentStore(tmp_path / "memory_store")
    memory_service = MemoryService(store)
    memory_service.upsert("preferences", "preferred_model", MemoryWrite(value="llama3"))
    register_memory_actions(registry, memory_service)

    mem_res = registry.get("memory.recall").handler(RecallParameters(query="preferred"))
    assert isinstance(mem_res, ActionOutcomeResponse)
    assert mem_res.status == ToolOutcome.DONE
    assert len(mem_res.data) >= 1
    assert mem_res[0]["key"] == "preferred_model"

    # System Metrics
    metrics_service = SystemMetricsService()
    register_system_actions(registry, metrics_service)

    sys_res = registry.get("system.get_metrics").handler(NoParameters())
    assert isinstance(sys_res, ActionOutcomeResponse)
    assert sys_res.status == ToolOutcome.DONE
    assert "cpu_percent" in sys_res.data

    # Web Search
    class FakeSettings:
        def get_api_key_for_service(self):
            return "test-key"

    class FakeModels:
        def generate_content(self, **kwargs):
            from types import SimpleNamespace
            return SimpleNamespace(
                text="Search answer",
                candidates=[
                    SimpleNamespace(
                        grounding_metadata=SimpleNamespace(
                            grounding_chunks=[
                                SimpleNamespace(web=SimpleNamespace(title="Example", uri="https://example.com"))
                            ]
                        )
                    )
                ],
            )

    class FakeClient:
        def __init__(self, models):
            self.models = models
        def close(self):
            pass

    monkeypatch.setattr("app.services.web_search_service.genai.Client", lambda **_: FakeClient(FakeModels()))
    search_service = WebSearchService(FakeSettings())
    register_search_actions(registry, search_service)

    search_res = registry.get("web.search").handler(WebSearchRequest(query="pytest test"))
    assert isinstance(search_res, ActionOutcomeResponse)
    assert search_res.status == ToolOutcome.DONE
    assert search_res.action == "web.search"


def test_action_executor_with_outcome_response(tmp_path):
    """Verify ActionExecutor executes handlers returning ActionOutcomeResponse seamlessly."""
    async def _test():
        registry = ActionRegistry()

        class DummyParams(BaseModel):
            operation: str

        def dummy_handler(p: DummyParams):
            if p.operation == "succeed":
                return done("dummy.test", "Done!", data={"result": 100})
            if p.operation == "fail":
                return failed("dummy.test", "Something broke")
            if p.operation == "start":
                return started("dummy.test", "Running in bg", data={"task_id": "t_1"})
            return ask("dummy.test", "Are you sure?")

        registry.register(ActionDefinition(
            action_id="dummy.test",
            name="Dummy Action",
            description="Dummy description",
            category="test",
            parameters=DummyParams,
            handler=dummy_handler,
        ))

        executor = ActionExecutor(registry)

        # Success execution
        exec_done = await executor.execute("dummy.test", {"operation": "succeed"})
        assert exec_done.status == "success"
        assert exec_done.data["result"] == 100
        assert exec_done.data["outcome_status"] == "done"

        # Failed execution
        exec_fail = await executor.execute("dummy.test", {"operation": "fail"})
        assert exec_fail.status == "failed"
        assert "broke" in exec_fail.error

        # Started execution
        exec_started = await executor.execute("dummy.test", {"operation": "start"})
        assert exec_started.status == "success"
        assert exec_started.data["task_id"] == "t_1"
        assert exec_started.data["outcome_status"] == "started"

    asyncio.run(_test())
