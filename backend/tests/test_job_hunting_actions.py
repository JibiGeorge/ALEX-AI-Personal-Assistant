"""
Unit and Integration Tests for Job Hunting Action Registration & Voice-Command Routing.
Verifies all 7 registered actions, approval workflow enforcement, and natural language command parsing.
"""

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest

from app.actions.action_executor import ActionExecutor
from app.actions.action_registry import ActionRegistry
from app.actions.builtins.job_hunting import register_job_hunting_actions
from app.schemas.job_hunting import (
    ApplicationApproval,
    ApplicationStatus,
    ApprovalChannel,
    ApprovalStatus,
    CandidateProfile,
    InterviewRound,
    JobApplication,
    JobListing,
    JobSource,
    WorkModality,
)
from app.services.job_hunting.command_router import clean_voice_input, route_job_command
from app.services.job_hunting.job_hunting_service import JobHuntingService


@pytest.fixture
def temp_service():
    with TemporaryDirectory() as tmp_dir:
        data_dir = Path(tmp_dir)
        service = JobHuntingService(data_dir=data_dir)

        # Seed candidate profile
        profile = CandidateProfile(
            id="test-cand-1",
            full_name="Alex Developer",
            email="alex@example.com",
            location="San Francisco, CA",
            headline="Full Stack Engineer",
            summary="4 years building React, TypeScript, and Python systems.",
            total_years_experience=4,
            seniority_level="Mid-Senior",
            programming_languages=["TypeScript", "JavaScript", "Python"],
            frameworks=["React", "FastAPI", "Next.js"],
            databases=["PostgreSQL", "SQLite"],
            skills=[],
            work_history=[],
            raw_resume_text="Alex Developer. 4 years of experience in Full Stack development with React and TypeScript.",
            is_verified=True,
        )
        service.update_profile(profile)

        # Seed sample job listing
        job = JobListing(
            id="job-voice-1",
            source=JobSource.LINKEDIN_URL,
            source_url="https://linkedin.com/jobs/view/123456",
            company_name="Acme Tech",
            title="Full Stack Developer",
            location="Remote",
            modality=WorkModality.REMOTE,
            experience_required_min=2,
            experience_required_max=5,
            raw_description="Looking for a Full Stack Developer experienced with React, TypeScript and Node.js.",
            cleaned_description="Looking for a Full Stack Developer experienced with React, TypeScript and Node.js.",
            required_skills=["React", "TypeScript", "Node.js"],
            preferred_skills=["Docker", "PostgreSQL"],
            benefits=["Health Insurance", "401k match"],
            content_hash="voice-hash-1",
        )
        service.storage.save_job(job)

        yield service


@pytest.fixture
def registry_and_executor(temp_service):
    registry = ActionRegistry()
    register_job_hunting_actions(registry, temp_service)
    executor = ActionExecutor(registry)
    return registry, executor, temp_service


class TestJobActionRegistration:
    """Verifies action registration and schema contracts for all 7 actions."""

    def test_all_seven_core_actions_are_registered(self, registry_and_executor):
        registry, _, _ = registry_and_executor

        expected_actions = [
            "job_search",
            "job_analyse",
            "job_match_resume",
            "job_prepare_application",
            "job_list_approvals",
            "job_track_application",
            "job_list_interviews",
        ]

        for action_id in expected_actions:
            action = registry.get(action_id)
            assert action is not None, f"Action '{action_id}' was not registered!"
            assert action.enabled is True
            assert action.category == "job_hunting"
            assert action.requires_confirmation is False, f"Action '{action_id}' should not block model calling"

    def test_submit_action_enforces_confirmation_gate(self, registry_and_executor):
        registry, _, _ = registry_and_executor
        submit_action = registry.get("job_hunting.submit_application")
        assert submit_action is not None
        assert submit_action.requires_confirmation is True, "Submit action MUST require explicit confirmation!"

    def test_model_declarations_expose_actions_to_ai(self, registry_and_executor):
        registry, _, _ = registry_and_executor
        declarations = registry.model_declarations()
        declaration_names = [d.name for d in declarations]

        for name in [
            "job_search",
            "job_analyse",
            "job_match_resume",
            "job_prepare_application",
            "job_list_approvals",
            "job_track_application",
            "job_list_interviews",
        ]:
            assert name in declaration_names


class TestJobActionExecution:
    """Verifies execution of each action through authenticated service layer."""

    def test_execute_job_search(self, registry_and_executor):
        _, executor, _ = registry_and_executor
        result = asyncio.run(executor.execute("job_search", {"query": "React Developer", "location": "Remote", "max_results": 3}))

        assert result.status == "success"
        assert result.action_id == "job_search"
        assert "count" in result.data

    def test_execute_job_analyse_with_url(self, registry_and_executor):
        _, executor, _ = registry_and_executor
        result = asyncio.run(executor.execute("job_analyse", {
            "url": "https://boards.greenhouse.io/demo/jobs/999",
            "title": "React Engineer",
            "company": "Tech Corp",
            "text": "Requires React and TypeScript with 3 years experience.",
        }))

        assert result.status == "success"
        assert result.action_id == "job_analyse"
        assert result.data["title"] == "React Engineer"
        assert result.data["company"] == "Tech Corp"

    def test_execute_job_match_resume(self, registry_and_executor):
        _, executor, service = registry_and_executor
        result = asyncio.run(executor.execute("job_match_resume", {"job_id": "job-voice-1"}))

        assert result.status == "success"
        assert result.action_id == "job_match_resume"
        assert "match_percentage" in result.data
        assert result.data["match_percentage"] >= 70

    def test_execute_job_prepare_application_and_approval_gate(self, registry_and_executor):
        registry, executor, service = registry_and_executor

        # Run prepare application
        result = asyncio.run(executor.execute("job_prepare_application", {
            "job_id": "job-voice-1",
            "instructions": "Highlight React 19 architecture",
        }))

        assert result.status == "success"
        assert result.action_id == "job_prepare_application"
        assert result.data["requires_user_approval"] is True
        assert result.data["approval_status"] == "pending"

        # Verify application created with pending approval
        apps = service.list_applications()
        assert len(apps) == 1
        app = apps[0]
        assert app.job_id == "job-voice-1"

        # Verify AI cannot bypass approval workflow:
        # Direct execution without human confirmation is rejected by ActionExecutor
        submit_result = asyncio.run(executor.execute("job_hunting.submit_application", {
            "application_id": app.id,
            "confirm": True,
        }))
        assert submit_result.status == "rejected"
        assert submit_result.error == "confirmation_required"

        # Also test the underlying handler directly to verify verify_approval logic blocks unapproved apps
        from app.actions.builtins.job_hunting import SubmitApplicationActionParams
        submit_def = registry.get("job_hunting.submit_application")
        assert submit_def is not None
        direct_result = submit_def.handler(SubmitApplicationActionParams(application_id=app.id, confirm=True))
        assert direct_result.status.value == "failed"
        assert "Submission Blocked" in (direct_result.error or direct_result.message)

        # Verify explicit user decision unlocks submission
        service.decide_approval(app.id, approved=True, channel=ApprovalChannel.UI, confirmation_text="Approved by user")
        approved_result = submit_def.handler(SubmitApplicationActionParams(application_id=app.id, confirm=True))
        assert approved_result.status.value == "done"

    def test_execute_job_list_approvals(self, registry_and_executor):
        _, executor, service = registry_and_executor

        # Prepare an application to generate a pending approval
        asyncio.run(executor.execute("job_prepare_application", {"job_id": "job-voice-1"}))

        result = asyncio.run(executor.execute("job_list_approvals", {"limit": 10}))
        assert result.status == "success"
        assert result.data["count"] >= 1
        assert result.data["approvals"][0]["requested_action"] == "SUBMIT_APPLICATION"

    def test_execute_job_track_application(self, registry_and_executor):
        _, executor, service = registry_and_executor
        asyncio.run(executor.execute("job_prepare_application", {"job_id": "job-voice-1"}))

        result = asyncio.run(executor.execute("job_track_application", {}))
        assert result.status == "success"
        assert result.data["count"] >= 1
        assert result.data["applications"][0]["job_id"] == "job-voice-1"

    def test_execute_job_list_interviews(self, registry_and_executor):
        _, executor, service = registry_and_executor

        # Prepare and log an interview round
        asyncio.run(executor.execute("job_prepare_application", {"job_id": "job-voice-1"}))
        apps = service.list_applications()
        app = apps[0]
        service.record_interview(
            application_id=app.id,
            round_name="Technical Phone Screen",
            scheduled_at="2026-11-20T14:00:00Z",
            interviewer="Engineering Director",
            feedback="Discuss system design and React state machines",
        )

        result = asyncio.run(executor.execute("job_list_interviews", {}))
        assert result.status == "success"
        assert result.data["count"] == 1
        assert result.data["interviews"][0]["round_name"] == "Technical Phone Screen"
        assert result.data["interviews"][0]["company"] == "Acme Tech"


class TestNaturalLanguageVoiceRouting:
    """Verifies natural-language voice command parsing and routing."""

    def test_clean_voice_input_strips_wake_words(self):
        assert clean_voice_input("Alex, find full-stack developer jobs.") == "find full-stack developer jobs"
        assert clean_voice_input("Hey Alex, show my interviews!") == "show my interviews"
        assert clean_voice_input("Computer: prepare my application.") == "prepare my application"

    def test_route_find_developer_jobs(self):
        cmd = route_job_command("Alex, find full-stack developer jobs.")
        assert cmd is not None
        action, params = cmd
        assert action == "job_search"
        assert "full-stack developer" in params["query"]

    def test_route_find_remote_react_jobs_worldwide(self):
        cmd = route_job_command("Find remote React jobs worldwide.")
        assert cmd is not None
        action, params = cmd
        assert action == "job_search"
        assert "React" in params["query"]
        assert params.get("location") == "Worldwide"
        assert "remote" in params.get("modalities", [])

    def test_route_analyse_linkedin_job(self):
        cmd = route_job_command("Analyse this LinkedIn job.")
        assert cmd is not None
        action, params = cmd
        assert action == "job_analyse"

    def test_route_analyse_job_with_url(self):
        cmd = route_job_command("Analyse this job: https://www.linkedin.com/jobs/view/987654321")
        assert cmd is not None
        action, params = cmd
        assert action == "job_analyse"
        assert params["url"] == "https://www.linkedin.com/jobs/view/987654321"

    def test_route_compare_job_with_resume(self):
        cmd = route_job_command("Compare this job with my resume.")
        assert cmd is not None
        action, params = cmd
        assert action == "job_match_resume"

    def test_route_prepare_my_application(self):
        cmd = route_job_command("Prepare my application.")
        assert cmd is not None
        action, params = cmd
        assert action == "job_prepare_application"

    def test_route_show_pending_applications(self):
        cmd = route_job_command("Show my pending applications.")
        assert cmd is not None
        action, params = cmd
        assert action == "job_track_application"

    def test_route_show_my_interviews(self):
        cmd = route_job_command("Show my interviews.")
        assert cmd is not None
        action, params = cmd
        assert action == "job_list_interviews"

    def test_route_open_job_hunting_on_hud(self):
        cmd = route_job_command("Alex, open job hunting on hud")
        assert cmd is not None
        action, params = cmd
        assert action == "job_search"

        cmd2 = route_job_command("open job hunting")
        assert cmd2 is not None
        assert cmd2[0] == "job_search"

        cmd3 = route_job_command("career radar")
        assert cmd3 is not None
        assert cmd3[0] == "job_search"

    def test_unrelated_command_returns_none(self):
        assert route_job_command("What is the weather in Tokyo?") is None
        assert route_job_command("Play some relaxing music.") is None
        assert route_job_command("Open the camera on hud display.") is None

    def test_phase_8_natural_language_job_commands(self):
        # 1. "Show remote React jobs over 80%"
        cmd1 = route_job_command("Show remote React jobs over 80%")
        assert cmd1 is not None
        assert cmd1[0] == "job_filter_jobs"
        assert cmd1[1]["min_score"] == 80
        assert cmd1[1]["is_remote"] is True
        assert "react" in cmd1[1]["query"].lower()

        # 2. "Tailor my resume for the Bjak role"
        cmd2 = route_job_command("Tailor my resume for the Bjak role")
        assert cmd2 is not None
        assert cmd2[0] == "job_tailor_resume"
        assert cmd2[1]["target"].lower() == "bjak"

        # 3. "Move Bjak to Applied"
        cmd3 = route_job_command("Move Bjak to Applied")
        assert cmd3 is not None
        assert cmd3[0] == "job_update_status"
        assert cmd3[1]["target"].lower() == "bjak"
        assert cmd3[1]["status"] == "applied"

        # 4. "What jobs did you find today?"
        cmd4 = route_job_command("What jobs did you find today?")
        assert cmd4 is not None
        assert cmd4[0] == "job_summary_today"


class TestConversationVoiceIntegration:
    """Verifies that ConversationService and LiveVoiceService execute Job Hunting actions."""

    def test_conversation_service_routes_job_search_tool_call(self, monkeypatch, registry_and_executor):
        registry, executor, _ = registry_and_executor
        import app.services.conversation_service as cs

        class FakeSettings:
            def get_api_key_for_service(self):
                return "test-key"

        fake_models = type(
            "FakeToolModels",
            (),
            {
                "requests": [],
                "responses": iter([
                    type(
                        "ToolCallResponse",
                        (),
                        {
                            "text": None,
                            "function_calls": [
                                cs.types.FunctionCall(
                                    id="call-1",
                                    name="job_search",
                                    args={"query": "React Developer"},
                                )
                            ],
                            "candidates": [
                                type(
                                    "Candidate",
                                    (),
                                    {
                                        "content": cs.types.Content(
                                            role="model",
                                            parts=[
                                                cs.types.Part(
                                                    function_call=cs.types.FunctionCall(
                                                        id="call-1",
                                                        name="job_search",
                                                        args={"query": "React Developer"},
                                                    )
                                                )
                                            ],
                                        )
                                    },
                                )()
                            ],
                        },
                    )(),
                    type("Response", (), {"text": "I discovered jobs matching React Developer for you."})(),
                ]),
                "generate_content": lambda self, **req: next(self.responses),
            },
        )()

        monkeypatch.setattr(
            cs.ConversationService,
            "_create_client",
            staticmethod(lambda api_key, timeout_ms=30000: type("Client", (), {"models": fake_models})()),
        )

        service = cs.ConversationService(
            settings=FakeSettings(),
            memory=None,
            action_registry=registry,
            action_executor=executor,
        )

        reply = service.reply(
            text="Alex, find full-stack developer jobs.",
            conversation_id=None,
            assistant_name="Alex",
            user_name="Commander",
        )

        assert "I discovered jobs matching React Developer" in reply.text

    def test_live_voice_service_executes_job_action_tool_call(self, registry_and_executor):
        registry, executor, _ = registry_and_executor
        from app.services.live_voice_service import LiveVoiceService

        class FakeSession:
            def __init__(self):
                self.responses = []

            async def send_tool_response(self, *, function_responses):
                self.responses.extend(function_responses)

        voice_service = LiveVoiceService(
            settings=None,
            memory=None,
            action_registry=registry,
            action_executor=executor,
        )

        session = FakeSession()
        function_call = type(
            "FunctionCall",
            (),
            {"id": "call-voice-1", "name": "job_list_interviews", "args": {}},
        )()

        executed = asyncio.run(voice_service._handle_tool_calls(session, [function_call], 0))

        assert executed == 1
        assert len(session.responses) == 1
        assert session.responses[0].id == "call-voice-1"
        assert session.responses[0].response["status"] == "success"
        assert "interviews" in session.responses[0].response["output"]
