import argparse
import logging
import os
import secrets
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.lazyimport import install_lazy_modules

# Defer heavy third-party packages to optimize cold sidecar startup
install_lazy_modules()

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router, mobile_upload_file, get_mobile_upload_file
from app.actions import ActionExecutor, ActionRegistry
from app.actions.builtins.files import register_file_actions
from app.actions.builtins.documents import register_document_actions
from app.actions.builtins.computer_control import register_computer_control_actions
from app.actions.builtins.memory import register_memory_actions
from app.actions.builtins.media import register_media_actions
from app.actions.builtins.window import register_window_actions
from app.actions.builtins.search import register_search_actions
from app.actions.builtins.system import register_system_actions
from app.actions.builtins.browser import register_browser_actions
from app.actions.builtins.system_settings import register_system_settings_actions
from app.actions.builtins.dev_agent import register_dev_agent_actions
from app.actions.builtins.code_helper import register_code_helper_actions
from app.actions.builtins.messaging import register_messaging_actions
from app.actions.builtins.desktop_environment import register_desktop_environment_actions
from app.actions.builtins.vision import register_vision_actions
from app.actions.builtins.elevenlabs import register_elevenlabs_actions
from app.actions.builtins.youtube_transcript import register_youtube_actions
from app.actions.builtins.reminder import register_reminder_actions
from app.actions.builtins.topic_monitor import register_topic_monitor_actions
from app.actions.builtins.proactive import register_proactive_actions
from app.actions.builtins.flight_finder import register_flight_actions
from app.actions.builtins.game_updater import register_game_updater_actions
from app.actions.builtins.job_hunting import register_job_hunting_actions
from app.api.job_hunting_routes import router as job_hunting_router
from app.core.config import RuntimeSettings, get_runtime_settings
from app.core.logging_config import configure_logging
from app.core.security import ApiTokenMiddleware
from app.core.storage import JsonDocumentStore, StorageError
from app.services.briefing_service import BriefingService
from app.services.conversation_service import ConversationService
from app.services.computer_control_service import ComputerControlService
from app.services.dashboard_service import DashboardService
from app.services.document_parser_service import DocumentParserService
from app.services.file_workspace_service import FileWorkspaceService
from app.services.live_voice_service import LiveVoiceService
from app.services.media_service import MediaService
from app.services.memory_service import MemoryService
from app.services.platform_capability_service import PlatformCapabilityService
from app.services.reminder_service import ReminderService
from app.services.os_scheduler_adapter import OSSchedulerAdapter
from app.services.settings_service import CredentialStoreError, SettingsService
from app.services.speech_service import SpeechService
from app.services.tts_service import TTSService
from app.services.wake_word_service import WakeWordService
from app.services.window_management_service import WindowManagementService
from app.services.system_metrics_service import SystemMetricsService
from app.services.system_monitor_service import SystemMonitorService
from app.services.system_verification_service import SystemVerificationService
from app.services.web_search_service import WebSearchService
from app.services.browser_control_service import BrowserControlService
from app.services.system_settings_service import SystemSettingsService
from app.services.dev_agent_service import DevAgentService
from app.services.code_helper_service import CodeHelperService
from app.services.messaging_service import MessagingService
from app.services.desktop_environment_service import DesktopEnvironmentService
from app.services.vision_service import VisionService
from app.services.elevenlabs_service import ElevenLabsService
from app.services.youtube_transcript_service import YouTubeTranscriptService
from app.services.topic_monitor_service import TopicMonitorService
from app.services.proactive_service import ProactiveEngine
from app.services.flight_finder_service import FlightFinderService
from app.services.game_updater_service import GameUpdaterService
from app.services.job_hunting import JobHuntingService
from app.services.model_ladder_service import model_ladder_service
from app.services.plugin_loader_service import PluginLoaderService
from app.services.voice_lifecycle_manager import VoiceLifecycleManager

logger = logging.getLogger(__name__)


def create_app(
    *,
    data_dir: Path | None = None,
    api_token: str | None = None,
) -> FastAPI:
    runtime = get_runtime_settings()
    resolved_data_dir = (data_dir or runtime.resolved_data_dir()).expanduser().resolve()
    token = api_token if api_token is not None else runtime.api_token
    computer_control_service = ComputerControlService()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("Alex backend started")
        try:
            yield
        finally:
            computer_control_service.set_permission(False)
            if hasattr(application.state, "wake_word_service"):
                application.state.wake_word_service.stop()
            if hasattr(application.state, "voice_lifecycle_manager"):
                application.state.voice_lifecycle_manager.cleanup()
            logger.info("Alex backend stopped")

    application = FastAPI(
        title="Alex Backend",
        version="0.1.0",
        description="Local authenticated API for the Alex desktop application.",
        lifespan=lifespan,
    )
    application.state.api_token = token
    application.state.request_shutdown = None
    store = JsonDocumentStore(resolved_data_dir)
    application.state.settings_service = SettingsService(store)
    application.state.memory_service = MemoryService(store)
    os_scheduler = OSSchedulerAdapter(scripts_dir=resolved_data_dir / "reminders")
    application.state.os_scheduler = os_scheduler
    application.state.reminder_service = ReminderService(store, scheduler=os_scheduler)
    application.state.system_metrics_service = SystemMetricsService()
    application.state.system_monitor_service = SystemMonitorService()
    application.state.file_workspace_service = FileWorkspaceService(resolved_data_dir)
    application.state.document_parser_service = DocumentParserService()
    application.state.speech_service = SpeechService()
    application.state.tts_service = TTSService(voice_dir=resolved_data_dir / "piper-voices")
    application.state.wake_word_service = WakeWordService(model_name="hey_jarvis", enabled=False)
    application.state.media_service = MediaService()
    application.state.window_management_service = WindowManagementService()
    application.state.dashboard_service = DashboardService()
    application.state.computer_control_service = computer_control_service
    application.state.web_search_service = WebSearchService(application.state.settings_service)
    application.state.browser_control_service = BrowserControlService()
    application.state.system_settings_service = SystemSettingsService()
    application.state.dev_agent_service = DevAgentService(application.state.settings_service)
    application.state.code_helper_service = CodeHelperService(application.state.settings_service)
    application.state.messaging_service = MessagingService()
    application.state.desktop_environment_service = DesktopEnvironmentService()
    application.state.vision_service = VisionService()
    uploads_dir = resolved_data_dir / "uploads"
    try:
        uploads_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    application.state.uploads_dir = uploads_dir
    application.state.resolved_data_dir = resolved_data_dir

    application.state.elevenlabs_service = ElevenLabsService(application.state.settings_service)
    application.state.youtube_transcript_service = YouTubeTranscriptService(application.state.settings_service)
    application.state.media_service.set_youtube_transcript_service(application.state.youtube_transcript_service)
    application.state.topic_monitor_service = TopicMonitorService(
        store, web_search_service=application.state.web_search_service
    )
    application.state.proactive_engine = ProactiveEngine(
        memory_service=application.state.memory_service,
        settings_service=application.state.settings_service,
    )
    application.state.flight_finder_service = FlightFinderService(
        application.state.settings_service,
        reports_dir=resolved_data_dir / "reports",
    )
    application.state.game_updater_service = GameUpdaterService()
    plugins_dir = resolved_data_dir / "plugins"
    try:
        plugins_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    application.state.plugin_loader_service = PluginLoaderService(plugins_dir=plugins_dir)
    application.state.platform_capability_service = PlatformCapabilityService(
        application.state.settings_service
    )
    application.state.system_verification_service = SystemVerificationService(
        application.state.settings_service,
        application.state.system_metrics_service,
        application.state.memory_service,
        application.state.reminder_service,
    )
    application.state.briefing_service = BriefingService(
        application.state.settings_service,
        application.state.memory_service,
        application.state.reminder_service,
        application.state.system_metrics_service,
        application.state.system_monitor_service,
    )
    application.state.job_hunting_service = JobHuntingService(
        data_dir=resolved_data_dir,
        settings_service=application.state.settings_service,
        document_parser_service=application.state.document_parser_service,
        web_search_service=application.state.web_search_service,
        model_ladder_service=model_ladder_service,
    )
    action_registry = ActionRegistry()
    register_system_actions(action_registry, application.state.system_metrics_service)
    register_memory_actions(action_registry, application.state.memory_service)
    register_file_actions(action_registry, application.state.file_workspace_service)
    register_document_actions(action_registry, application.state.document_parser_service, application.state.file_workspace_service)
    register_computer_control_actions(action_registry, application.state.computer_control_service)
    register_search_actions(action_registry, application.state.web_search_service)
    register_media_actions(action_registry, application.state.media_service)
    register_window_actions(action_registry, application.state.window_management_service)
    register_browser_actions(action_registry, application.state.browser_control_service)
    register_system_settings_actions(action_registry, application.state.system_settings_service)
    register_dev_agent_actions(action_registry, application.state.dev_agent_service)
    register_code_helper_actions(action_registry, application.state.code_helper_service)
    register_messaging_actions(action_registry, application.state.messaging_service)
    register_desktop_environment_actions(action_registry, application.state.desktop_environment_service)
    register_vision_actions(action_registry, application.state.vision_service)
    register_elevenlabs_actions(action_registry, application.state.elevenlabs_service)
    register_youtube_actions(action_registry, application.state.youtube_transcript_service)
    register_reminder_actions(action_registry, application.state.reminder_service)
    register_topic_monitor_actions(action_registry, application.state.topic_monitor_service)
    register_proactive_actions(action_registry, application.state.proactive_engine)
    register_flight_actions(action_registry, application.state.flight_finder_service)
    register_game_updater_actions(action_registry, application.state.game_updater_service)
    register_job_hunting_actions(action_registry, application.state.job_hunting_service)
    application.state.plugin_loader_service.discover_and_register(action_registry)
    application.state.action_registry = action_registry
    application.state.action_executor = ActionExecutor(action_registry)
    application.state.action_executor.set_remote_authorizer(application.state.dashboard_service)
    application.state.conversation_service = ConversationService(
        application.state.settings_service,
        application.state.memory_service,
        action_registry,
        application.state.action_executor,
    )
    application.state.live_voice_service = LiveVoiceService(
        application.state.settings_service,
        application.state.memory_service,
        action_registry,
        application.state.action_executor,
    )
    application.state.voice_lifecycle_manager = VoiceLifecycleManager(
        settings_service=application.state.settings_service,
        speech_service=application.state.speech_service,
        tts_service=application.state.tts_service,
        wake_word_service=application.state.wake_word_service,
        conversation_service=application.state.conversation_service,
        action_executor=application.state.action_executor,
    )
    application.state.computer_control_service.set_screen_finder(
        application.state.conversation_service.locate_screen_element
    )

    def get_user_identity_field(field_name: str) -> str | None:
        clean = field_name.strip().casefold()
        for entry in application.state.memory_service.list_entries():
            if entry.category == "identity" and entry.key.strip().casefold() == clean:
                return entry.value
        return None

    application.state.computer_control_service.set_user_data_provider(
        get_user_identity_field
    )
    application.add_middleware(ApiTokenMiddleware)
    application.include_router(router)
    application.include_router(job_hunting_router)

    @application.post("/api/upload")
    async def legacy_upload_alias(req: Request):
        return await mobile_upload_file(request=req)

    @application.get("/uploads/{filename}")
    def legacy_get_upload_alias(filename: str, req: Request):
        return get_mobile_upload_file(filename=filename, request=req)

    @application.exception_handler(StorageError)
    async def storage_error_handler(
        _: Request,
        exc: StorageError,
    ) -> JSONResponse:
        logger.error(
            "Application data operation failed",
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Application data could not be read or saved"},
        )

    @application.exception_handler(CredentialStoreError)
    async def credential_error_handler(
        _: Request,
        exc: CredentialStoreError,
    ) -> JSONResponse:
        logger.error(
            "Credential store is unavailable",
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return JSONResponse(
            status_code=503,
            content={"detail": "OS credential store is unavailable"},
        )

    return application


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Alex backend sidecar")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Loopback port for the API (default: 8765)",
    )
    args = parser.parse_args()

    if args.host not in ("127.0.0.1", "::1", "localhost"):
        raise SystemExit("The Alex desktop backend must bind to loopback only")

    runtime = get_runtime_settings()
    token = runtime.api_token or secrets.token_urlsafe(32)
    configure_logging(runtime.log_level)
    logger.info("Starting authenticated backend on %s:%s", args.host, args.port)
    application = create_app(api_token=token)
    server = uvicorn.Server(
        uvicorn.Config(
            application,
            host=args.host,
            port=args.port,
            log_config=None,
            access_log=False,
        )
    )
    application.state.request_shutdown = lambda: setattr(server, "should_exit", True)
    server.run()


app = create_app()

if __name__ == "__main__":
    main()
