import asyncio
import hmac
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from fastapi import APIRouter, HTTPException, Request, Response, WebSocket, status
from fastapi.responses import FileResponse

from app.schemas.action import (
    ActionEnableRequest,
    ActionExecutionRequest,
    ActionListResponse,
)
from app.schemas.briefing import BriefingResponse
from app.schemas.conversation import (
    ConversationTurnRequest,
    ConversationTurnResponse,
)
from app.schemas.memory import (
    MemoryCategory,
    MemoryEntry,
    MemoryListResponse,
    MemoryWrite,
)
from app.schemas.platform_capability import PlatformCapabilityReport
from app.schemas.reminder import Reminder, ReminderCreate, ReminderList
from app.schemas.system_alert import SystemAlertList
from app.schemas.system_verification import FullSystemVerificationReport
from app.schemas.settings import (
    ApiKeyInput,
    ApiKeyResponse,
    SettingsResponse,
    SettingsUpdate,
)
from app.schemas.system_metrics import SystemMetricsResponse
from app.schemas.web_search import WebSearchRequest, WebSearchResponse
from app.actions.action_executor import ActionExecutionResult
from app.providers.ollama_provider import OllamaProvider, check_host_memory_for_model
from app.providers.lm_studio_provider import LMStudioProvider
from app.services.conversation_service import (
    ApiKeyNotConfigured,
    ModelServiceError,
)
from app.services.settings_service import CredentialStoreError
from app.schemas.mobile import (
    ActionApprovalDecision,
    EncryptedPayload,
    MobileGatewayStatus,
    MobileMemoriesResponse,
    MobileMemoryItem,
    MobileTurnRequest,
    MobileTurnResponse,
    MobileUploadResponse,
    MobileUploadedFileInfo,
    MobileUploadsListResponse,
    PairingInitResponse,
    PairingRequest,
    PairingResponse,
    PendingApprovalItem,
    PendingApprovalsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


@router.get("/actions", response_model=ActionListResponse)
def list_actions(request: Request) -> ActionListResponse:
    return ActionListResponse(
        actions=[
            action.public_view()
            for action in request.app.state.action_registry.list()
        ]
    )


@router.patch("/actions/{action_id}")
def set_action_enabled(
    request: Request,
    action_id: str,
    body: ActionEnableRequest,
) -> dict[str, object]:
    try:
        action = request.app.state.action_registry.set_enabled(action_id, body.enabled)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found",
        ) from exc
    return action.public_view()


@router.post("/actions/{action_id}/execute", response_model=ActionExecutionResult)
async def execute_action(
    request: Request,
    action_id: str,
    body: ActionExecutionRequest,
) -> ActionExecutionResult:
    result = await request.app.state.action_executor.execute(
        action_id,
        body.parameters,
        confirmed=body.confirmed,
    )
    return result


@router.get("/actions/history")
async def action_history(request: Request) -> dict[str, list[ActionExecutionResult]]:
    return {"executions": await request.app.state.action_executor.history()}


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ready", "name": "Alex"}


@router.get("/system/metrics", response_model=SystemMetricsResponse)
def system_metrics(request: Request) -> SystemMetricsResponse:
    return request.app.state.system_metrics_service.snapshot()


@router.get("/system/alerts", response_model=SystemAlertList)
def system_alerts(request: Request) -> SystemAlertList:
    metrics = request.app.state.system_metrics_service.snapshot()
    alerts = request.app.state.system_monitor_service.check(metrics)
    return SystemAlertList(alerts=alerts)


@router.get("/system/capabilities", response_model=PlatformCapabilityReport)
def system_capabilities(request: Request) -> PlatformCapabilityReport:
    return request.app.state.platform_capability_service.snapshot()


@router.get("/system/verification", response_model=FullSystemVerificationReport)
async def system_verification(request: Request) -> FullSystemVerificationReport:
    return await request.app.state.system_verification_service.verify_all()


@router.get("/system/briefing", response_model=BriefingResponse)
def system_briefing(request: Request) -> BriefingResponse:
    return request.app.state.briefing_service.generate_briefing()


@router.get("/system/engines/ollama")
async def ollama_diagnostics(request: Request) -> dict[str, object]:
    provider = OllamaProvider()
    healthy = await provider.health_check()
    version = await provider.get_ollama_version() if healthy else None
    models: list[dict[str, object]] = []
    if healthy:
        try:
            discovered = await provider.list_models()
            models = [m.model_dump() for m in discovered]
        except Exception:
            pass

    import psutil
    available_ram_gb = round(psutil.virtual_memory().available / (1024 ** 3), 2)
    return {
        "engine": "ollama",
        "running": healthy,
        "base_url": provider.base_url,
        "version": version,
        "models": models,
        "ram_diagnostics": {
            "available_ram_gb": available_ram_gb,
            "min_required_gb": 3.0,
            "sufficient": available_ram_gb >= 3.0,
        },
    }


@router.get("/system/engines/lmstudio")
async def lm_studio_diagnostics(request: Request) -> dict[str, object]:
    provider = LMStudioProvider()
    healthy = await provider.health_check()
    active_model = await provider.get_active_model() if healthy else None
    models: list[dict[str, object]] = []
    if healthy:
        try:
            discovered = await provider.list_models()
            models = [m.model_dump() for m in discovered]
        except Exception:
            pass

    import psutil
    available_ram_gb = round(psutil.virtual_memory().available / (1024 ** 3), 2)
    return {
        "engine": "lm_studio",
        "running": healthy,
        "base_url": provider.base_url,
        "active_model": active_model,
        "models": models,
        "ram_diagnostics": {
            "available_ram_gb": available_ram_gb,
            "min_required_gb": 3.0,
            "sufficient": available_ram_gb >= 3.0,
        },
    }




@router.get("/reminders", response_model=ReminderList)
def list_reminders(request: Request) -> ReminderList:
    return ReminderList(reminders=request.app.state.reminder_service.list())


@router.post("/reminders", response_model=Reminder, status_code=status.HTTP_201_CREATED)
def create_reminder(request: Request, body: ReminderCreate) -> Reminder:
    try:
        return request.app.state.reminder_service.create(body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.get("/reminders/due", response_model=ReminderList)
def list_due_reminders(request: Request) -> ReminderList:
    return ReminderList(reminders=request.app.state.reminder_service.list_due())


@router.post("/reminders/{reminder_id}/delivered", response_model=Reminder)
def mark_reminder_delivered(request: Request, reminder_id: str) -> Reminder:
    try:
        valid_id = str(UUID(reminder_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Reminder identifier is invalid",
        ) from exc
    reminder = request.app.state.reminder_service.mark_delivered(valid_id)
    if reminder is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Due reminder not found",
        )
    return reminder


@router.delete("/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_reminder(request: Request, reminder_id: str) -> Response:
    try:
        valid_id = str(UUID(reminder_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Reminder identifier is invalid",
        ) from exc
    if not request.app.state.reminder_service.cancel(valid_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending reminder not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/shutdown", status_code=status.HTTP_202_ACCEPTED)
def shutdown(request: Request) -> dict[str, str]:
    request_shutdown = request.app.state.request_shutdown
    if request_shutdown is not None:
        request_shutdown()
    return {"status": "shutting_down"}


@router.post("/conversation/turn", response_model=ConversationTurnResponse)
def conversation_turn(
    request: Request,
    body: ConversationTurnRequest,
) -> ConversationTurnResponse:
    settings, _ = request.app.state.settings_service.get()
    try:
        return request.app.state.conversation_service.reply(
            body.text,
            body.conversation_id,
            settings.assistant_name,
            settings.user_name,
            body.attachment,
        )
    except ApiKeyNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except ModelServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post("/web/search", response_model=WebSearchResponse)
def web_search(request: Request, body: WebSearchRequest) -> WebSearchResponse:
    try:
        return request.app.state.web_search_service.search(body)
    except ApiKeyNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except ModelServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.websocket("/conversation/live")
async def live_conversation(websocket: WebSocket) -> None:
    expected = websocket.app.state.api_token
    supplied = websocket.query_params.get("token", "")
    if not expected or not supplied or not hmac.compare_digest(
        supplied.encode("utf-8"), expected.encode("utf-8")
    ):
        await websocket.close(code=1008)
        return

    await websocket.accept()
    await websocket.app.state.live_voice_service.serve(websocket)


@router.get("/settings", response_model=SettingsResponse)
def get_settings(request: Request) -> SettingsResponse:
    service = request.app.state.settings_service
    settings, configured = service.get()
    return SettingsResponse(settings=settings, api_key_configured=configured)


@router.patch("/settings", response_model=SettingsResponse)
def update_settings(
    request: Request,
    patch: SettingsUpdate,
) -> SettingsResponse:
    service = request.app.state.settings_service
    settings, configured = service.update(patch)
    return SettingsResponse(settings=settings, api_key_configured=configured)


@router.put("/settings/api-key", response_model=ApiKeyResponse)
def set_api_key(request: Request, body: ApiKeyInput) -> ApiKeyResponse:
    try:
        configured = request.app.state.settings_service.save_api_key(body.api_key)
    except CredentialStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return ApiKeyResponse(configured=configured)


@router.get("/memory", response_model=MemoryListResponse)
def list_memory(request: Request) -> MemoryListResponse:
    entries = request.app.state.memory_service.list_entries()
    return MemoryListResponse(entries=entries)


@router.get("/memory/search", response_model=MemoryListResponse)
def search_memory(
    request: Request,
    q: str = "",
    category: MemoryCategory | None = None,
) -> MemoryListResponse:
    entries = request.app.state.memory_service.search_entries(q, category)
    return MemoryListResponse(entries=entries)


@router.put(
    "/memory/{category}/{key}",
    response_model=MemoryEntry,
    status_code=status.HTTP_200_OK,
)
def upsert_memory(
    request: Request,
    category: MemoryCategory,
    key: str,
    body: MemoryWrite,
) -> MemoryEntry:
    return request.app.state.memory_service.upsert(category, key, body)


@router.delete(
    "/memory/{category}/{key}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_memory(
    request: Request,
    category: MemoryCategory,
    key: str,
) -> Response:
    deleted = request.app.state.memory_service.delete(category, key)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory entry not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


class TranscribeAudioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    audio_base64: str
    sample_rate: int = 16_000
    language: str = ""


class TranscribeAudioResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
    language: str
    language_probability: float
    duration_seconds: float


@router.post("/speech/transcribe", response_model=TranscribeAudioResponse)
async def transcribe_audio(
    request: Request, body: TranscribeAudioRequest
) -> TranscribeAudioResponse:
    import base64

    try:
        pcm = base64.b64decode(body.audio_base64)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 audio data: {exc}",
        ) from exc

    speech_service = getattr(request.app.state, "speech_service", None)
    if not speech_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Speech recognition service is not available",
        )

    res = await speech_service.transcribe(
        pcm, sample_rate=body.sample_rate, language=body.language
    )
    return TranscribeAudioResponse(
        text=res.text,
        language=res.language,
        language_probability=res.language_probability,
        duration_seconds=res.duration_seconds,
    )


class SynthesizeSpeechRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
    voice: str = ""
    language: str = ""


class SynthesizeSpeechResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    audio_base64: str
    sample_rate: int = 24000
    duration_seconds: float
    voice_used: str


class VoiceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    language: str
    engine: str
    sample_rate: int = 24000
    is_installed: bool = False


class VoiceListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    voices: list[VoiceItem]


@router.get("/speech/voices", response_model=VoiceListResponse)
def get_speech_voices(request: Request) -> VoiceListResponse:
    tts_service = getattr(request.app.state, "tts_service", None)
    if not tts_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Speech synthesis service is not available",
        )
    descriptors = tts_service.list_voices()
    return VoiceListResponse(
        voices=[
            VoiceItem(
                id=d.id,
                name=d.name,
                language=d.language,
                engine=d.engine,
                sample_rate=d.sample_rate,
                is_installed=d.is_installed,
            )
            for d in descriptors
        ]
    )


@router.post("/speech/synthesize", response_model=SynthesizeSpeechResponse)
async def synthesize_speech(
    request: Request, body: SynthesizeSpeechRequest
) -> SynthesizeSpeechResponse:
    import base64
    from app.services.speech_service import duration_s

    tts_service = getattr(request.app.state, "tts_service", None)
    if not tts_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Speech synthesis service is not available",
        )

    pcm = await tts_service.synthesize(body.text, voice=body.voice, language=body.language)
    dur = duration_s(pcm, rate=24000)
    b64 = base64.b64encode(pcm).decode("ascii")

    return SynthesizeSpeechResponse(
        audio_base64=b64,
        sample_rate=24000,
        duration_seconds=dur,
        voice_used=tts_service.last_voice_used or body.voice or "default",
    )


class WakeStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool
    running: bool
    ready: bool
    model: str
    threshold: float
    last_detected_at: float | None = None


class WakeToggleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool
    model: str | None = None
    threshold: float | None = None


class WakeFeedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    audio_base64: str


class WakeFeedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accepted: bool
    bytes_fed: int


@router.get("/wake/status", response_model=WakeStatusResponse)
def get_wake_status(request: Request) -> WakeStatusResponse:
    wake_service = getattr(request.app.state, "wake_word_service", None)
    if not wake_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wake-word engine service is not available",
        )
    status_obj = wake_service.get_status()
    return WakeStatusResponse(
        enabled=status_obj.enabled,
        running=status_obj.running,
        ready=status_obj.ready,
        model=status_obj.model,
        threshold=status_obj.threshold,
        last_detected_at=status_obj.last_detected_at,
    )


@router.post("/wake/toggle", response_model=WakeStatusResponse)
def toggle_wake_word(request: Request, body: WakeToggleRequest) -> WakeStatusResponse:
    wake_service = getattr(request.app.state, "wake_word_service", None)
    if not wake_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wake-word engine service is not available",
        )
    if body.model:
        wake_service.model_name = body.model.strip().lower()
    if body.threshold is not None:
        wake_service.threshold = max(0.1, min(1.0, float(body.threshold)))

    wake_service.set_enabled(body.enabled)
    status_obj = wake_service.get_status()
    return WakeStatusResponse(
        enabled=status_obj.enabled,
        running=status_obj.running,
        ready=status_obj.ready,
        model=status_obj.model,
        threshold=status_obj.threshold,
        last_detected_at=status_obj.last_detected_at,
    )


@router.post("/wake/feed", response_model=WakeFeedResponse)
def feed_wake_audio(request: Request, body: WakeFeedRequest) -> WakeFeedResponse:
    import base64

    wake_service = getattr(request.app.state, "wake_word_service", None)
    if not wake_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wake-word engine service is not available",
        )

    try:
        raw_pcm = base64.b64decode(body.audio_base64)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 audio payload: {exc}",
        ) from exc

    wake_service.feed(raw_pcm)
    return WakeFeedResponse(accepted=True, bytes_fed=len(raw_pcm))


@router.post("/wake/install")
async def install_wake_models(request: Request) -> dict[str, Any]:
    wake_service = getattr(request.app.state, "wake_word_service", None)
    if not wake_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wake-word engine service is not available",
        )
    loop = asyncio.get_running_loop()
    ok, msg = await loop.run_in_executor(None, wake_service.install)
    return {"ok": ok, "message": msg, "ready": wake_service.is_ready}



class MediaResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str


class MediaResolveResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str
    audio_url: str = ""
    title: str = ""
    source_type: str = "none"
    error: str | None = None


class MediaControlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str
    source: str | None = None
    title: str | None = None
    muted: bool | None = None


@router.get("/media/status")
def get_media_status(request: Request) -> dict[str, object]:
    media_service = getattr(request.app.state, "media_service", None)
    if not media_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Media service is not available",
        )
    return media_service.get_status().model_dump(mode="json")


@router.post("/media/resolve", response_model=MediaResolveResponse)
def resolve_media_source(request: Request, body: MediaResolveRequest) -> MediaResolveResponse:
    media_service = getattr(request.app.state, "media_service", None)
    if not media_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Media service is not available",
        )
    url, audio_url, title, source_type, error = media_service.resolve(body.source)
    return MediaResolveResponse(
        url=url,
        audio_url=audio_url,
        title=title,
        source_type=source_type,
        error=error,
    )


@router.post("/media/control")
def control_media(request: Request, body: MediaControlRequest) -> dict[str, object]:
    media_service = getattr(request.app.state, "media_service", None)
    if not media_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Media service is not available",
        )
    act = body.action.strip().lower()
    if act == "play":
        if not body.source:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source is required for play action",
            )
        state = media_service.play(
            body.source,
            title=body.title,
            muted=body.muted if body.muted is not None else True,
        )
    elif act == "pause":
        state = media_service.pause()
    elif act == "resume":
        state = media_service.resume()
    elif act in ("stop", "close"):
        state = media_service.stop()
    elif act in ("mute", "sound_off"):
        state = media_service.set_muted(True)
    elif act in ("unmute", "sound_on"):
        state = media_service.set_muted(False)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown media control action: {body.action}",
        )
    return state.model_dump(mode="json")


class WindowIdentifierRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    identifier: str
    timeout: float | None = 6.0


@router.get("/window/status")
def get_window_status(request: Request) -> dict[str, object]:
    window_service = getattr(request.app.state, "window_management_service", None)
    if not window_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Window management service is not available",
        )
    return window_service.get_platform_status()


@router.get("/window/list")
def list_desktop_windows(request: Request) -> dict[str, object]:
    window_service = getattr(request.app.state, "window_management_service", None)
    if not window_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Window management service is not available",
        )
    try:
        windows = window_service.list_windows()
        return {"windows": windows, "count": len(windows)}
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/window/active")
def get_active_desktop_window(request: Request) -> dict[str, object]:
    window_service = getattr(request.app.state, "window_management_service", None)
    if not window_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Window management service is not available",
        )
    try:
        active = window_service.get_active_window()
        return {"active": active}
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post("/window/focus")
def focus_desktop_window(request: Request, body: WindowIdentifierRequest) -> dict[str, object]:
    window_service = getattr(request.app.state, "window_management_service", None)
    if not window_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Window management service is not available",
        )
    try:
        return window_service.focus_window(body.identifier)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post("/window/close")
def close_desktop_window(request: Request, body: WindowIdentifierRequest) -> dict[str, object]:
    window_service = getattr(request.app.state, "window_management_service", None)
    if not window_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Window management service is not available",
        )
    try:
        timeout = body.timeout if body.timeout is not None else 6.0
        return window_service.close_window(body.identifier, timeout=timeout)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# Mobile Gateway & Companion Endpoints (TASK-P6-01 & TASK-P6-02 / CAT-37)
# ---------------------------------------------------------------------------


@router.get("/mobile/status", response_model=MobileGatewayStatus)
def get_mobile_status(request: Request) -> MobileGatewayStatus:
    dashboard_service = getattr(request.app.state, "dashboard_service", None)
    if not dashboard_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mobile Gateway service is not available",
        )
    return dashboard_service.get_status()


@router.get("/mobile/pair/init", response_model=PairingInitResponse)
def init_mobile_pairing(request: Request) -> PairingInitResponse:
    dashboard_service = getattr(request.app.state, "dashboard_service", None)
    if not dashboard_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mobile Gateway service is not available",
        )
    return dashboard_service.generate_pairing_info()


@router.post("/mobile/pair", response_model=PairingResponse)
def complete_mobile_pairing(request: Request, body: PairingRequest) -> PairingResponse:
    dashboard_service = getattr(request.app.state, "dashboard_service", None)
    if not dashboard_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mobile Gateway service is not available",
        )
    client_ip = request.client.host if request.client else "127.0.0.1"
    try:
        return dashboard_service.verify_and_pair(
            client_ip=client_ip,
            code=body.pairing_code,
            device_name=body.device_name or "Mobile Client",
            device_platform=body.device_platform or "iOS",
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/mobile/command")
def execute_mobile_command(request: Request, body: EncryptedPayload) -> dict[str, object]:
    dashboard_service = getattr(request.app.state, "dashboard_service", None)
    if not dashboard_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mobile Gateway service is not available",
        )
    session_token = request.headers.get("X-Mobile-Session")
    if not session_token or not dashboard_service.is_authenticated(session_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing mobile session token",
        )
    try:
        decrypted_bytes = dashboard_service.decrypt(session_token, body.iv, body.ciphertext)
        cmd_dict = json.loads(decrypted_bytes.decode("utf-8"))
        cmd_type = cmd_dict.get("type", "ping")

        if cmd_type == "ping":
            response_data = {"type": "pong", "timestamp": time.time()}
        elif cmd_type == "status":
            response_data = {"type": "status", "status": dashboard_service.get_status().model_dump(mode="json")}
        else:
            response_data = {"type": "ack", "received": cmd_type}

        enc = dashboard_service.encrypt(session_token, json.dumps(response_data))
        return enc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Command decryption or execution failed: {exc}",
        ) from exc


@router.post("/mobile/turn", response_model=MobileTurnResponse)
async def mobile_conversation_turn(
    request: Request,
    body: MobileTurnRequest,
) -> MobileTurnResponse:
    import base64
    dashboard_service = getattr(request.app.state, "dashboard_service", None)
    session_token = request.headers.get("X-Mobile-Session")
    if dashboard_service and session_token and not dashboard_service.is_authenticated(session_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid mobile session token",
        )

    conv_service = getattr(request.app.state, "conversation_service", None)
    settings_service = getattr(request.app.state, "settings_service", None)
    reply_text = ""

    if conv_service and settings_service:
        try:
            settings, _ = settings_service.get()
            conv_id = UUID(body.conversation_id) if body.conversation_id else None
            res = conv_service.reply(
                body.text,
                conv_id,
                settings.assistant_name,
                settings.user_name,
                None,
            )
            reply_text = res.reply
        except Exception as exc:
            logger.warning("Conversation service reply error, using fallback: %s", exc)
            reply_text = f"Received: '{body.text}'."
    else:
        reply_text = f"Received: '{body.text}'."

    audio_base64 = None
    voice_used = ""
    tts_service = getattr(request.app.state, "tts_service", None)
    if body.synthesize_voice and tts_service and reply_text:
        try:
            pcm = await tts_service.synthesize(
                reply_text,
                voice=body.voice,
                language=body.language,
            )
            if pcm:
                audio_base64 = base64.b64encode(pcm).decode("ascii")
                voice_used = getattr(tts_service, "last_voice_used", "")
        except Exception as exc:
            logger.warning("TTS synthesis failed for mobile turn: %s", exc)

    return MobileTurnResponse(
        reply=reply_text,
        audio_base64=audio_base64,
        sample_rate=24000,
        voice_used=voice_used,
    )


@router.get("/mobile/memories", response_model=MobileMemoriesResponse)
def get_mobile_memories(request: Request) -> MobileMemoriesResponse:
    dashboard_service = getattr(request.app.state, "dashboard_service", None)
    session_token = request.headers.get("X-Mobile-Session")
    if dashboard_service and session_token and not dashboard_service.is_authenticated(session_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid mobile session token",
        )

    memory_service = getattr(request.app.state, "memory_service", None)
    if not memory_service:
        return MobileMemoriesResponse(memories=[])

    entries = memory_service.list_entries()
    items = [
        MobileMemoryItem(
            category=e.category,
            key=e.key,
            value=e.value,
            updated=str(e.updated) if getattr(e, "updated", None) else None,
        )
        for e in entries
    ]
    return MobileMemoriesResponse(memories=items)


@router.get("/mobile/approvals", response_model=PendingApprovalsResponse)
def get_pending_approvals(request: Request) -> PendingApprovalsResponse:
    dashboard_service = getattr(request.app.state, "dashboard_service", None)
    session_token = request.headers.get("X-Mobile-Session")
    if dashboard_service and session_token and not dashboard_service.is_authenticated(session_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid mobile session token",
        )
    if not dashboard_service:
        return PendingApprovalsResponse(approvals=[])

    pending = dashboard_service.list_pending_approvals()
    return PendingApprovalsResponse(
        approvals=[
            PendingApprovalItem(
                request_id=item["request_id"],
                action_id=item["action_id"],
                params=item["params"],
                created_at=item["created_at"],
                timeout=item["timeout"],
            )
            for item in pending
        ]
    )


@router.post("/mobile/approvals/{request_id}")
def submit_action_approval(
    request_id: str,
    request: Request,
    body: ActionApprovalDecision,
) -> dict[str, object]:
    dashboard_service = getattr(request.app.state, "dashboard_service", None)
    if not dashboard_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mobile Gateway service is not available",
        )
    session_token = request.headers.get("X-Mobile-Session")
    if not session_token or not dashboard_service.is_authenticated(session_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing mobile session token",
        )

    resolved = dashboard_service.resolve_approval(
        request_id=request_id,
        approved=body.approved,
        session_token=session_token,
        signature=body.signature,
    )
    if not resolved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending approval request not found, expired, or invalid signature",
        )

    return {
        "resolved": True,
        "request_id": request_id,
        "approved": body.approved,
    }


@router.websocket("/mobile/ws")
async def mobile_websocket_endpoint(websocket: WebSocket, token: Optional[str] = None) -> None:
    dashboard_service = getattr(websocket.app.state, "dashboard_service", None)
    if not dashboard_service or not token or not dashboard_service.is_authenticated(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    dashboard_service.register_websocket(websocket)
    try:
        welcome = dashboard_service.encrypt(token, json.dumps({"type": "connected", "server": "alex-mobile-gateway"}))
        await websocket.send_text(json.dumps(welcome))

        while True:
            text = await websocket.receive_text()
            try:
                frame = json.loads(text)
                if "iv" in frame and "ciphertext" in frame:
                    decrypted = dashboard_service.decrypt(token, frame["iv"], frame["ciphertext"])
                    msg = json.loads(decrypted.decode("utf-8"))
                    msg_type = msg.get("type")
                    if msg_type == "ping":
                        pong = dashboard_service.encrypt(token, json.dumps({"type": "pong", "time": time.time()}))
                        await websocket.send_text(json.dumps(pong))
                    elif msg_type == "turn":
                        user_text = msg.get("content") or msg.get("text", "")
                        conv_service = getattr(websocket.app.state, "conversation_service", None)
                        settings_service = getattr(websocket.app.state, "settings_service", None)
                        reply_text = ""
                        if conv_service and settings_service:
                            try:
                                settings, _ = settings_service.get()
                                res = conv_service.reply(
                                    user_text,
                                    None,
                                    settings.assistant_name,
                                    settings.user_name,
                                    None,
                                )
                                reply_text = res.reply
                            except Exception:
                                reply_text = f"Received: {user_text}"
                        else:
                            reply_text = f"Received: {user_text}"
                        resp_enc = dashboard_service.encrypt(
                            token,
                            json.dumps({"type": "response", "text": reply_text}),
                        )
                        await websocket.send_text(json.dumps(resp_enc))
                    elif msg_type == "action_approval":
                        req_id = msg.get("request_id", "")
                        decision = bool(msg.get("approved"))
                        sig = msg.get("signature")
                        resolved = dashboard_service.resolve_approval(
                            req_id,
                            decision,
                            session_token=token,
                            signature=sig,
                        )
                        ack = dashboard_service.encrypt(
                            token,
                            json.dumps({
                                "type": "action_approval_ack",
                                "request_id": req_id,
                                "resolved": resolved,
                                "approved": decision,
                            }),
                        )
                        await websocket.send_text(json.dumps(ack))
            except Exception as ex:
                logger.debug("Error processing mobile ws frame: %s", ex)
    except Exception:
        pass
    finally:
        dashboard_service.unregister_websocket(websocket)


@router.websocket("/mobile/ws/audio")
async def mobile_audio_websocket(
    websocket: WebSocket,
    token: Optional[str] = None,
) -> None:
    from starlette.websockets import WebSocketDisconnect
    dashboard_service = getattr(websocket.app.state, "dashboard_service", None)
    if not dashboard_service or not token or not dashboard_service.is_authenticated(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    dashboard_service.register_websocket(websocket)
    speech_service = getattr(websocket.app.state, "speech_service", None)
    tts_service = getattr(websocket.app.state, "tts_service", None)
    conv_service = getattr(websocket.app.state, "conversation_service", None)
    settings_service = getattr(websocket.app.state, "settings_service", None)

    pcm_buffer = bytearray()

    async def process_turn(text: str) -> None:
        reply_text = ""
        if conv_service and settings_service:
            try:
                settings, _ = settings_service.get()
                res = conv_service.reply(
                    text,
                    None,
                    settings.assistant_name,
                    settings.user_name,
                    None,
                )
                reply_text = res.reply
            except Exception as exc:
                logger.debug("Conversation reply error: %s", exc)
                reply_text = f"I heard: {text}."
        else:
            reply_text = f"Received: {text}."

        await websocket.send_text(json.dumps({"type": "response", "text": reply_text}))

        if tts_service and reply_text:
            try:
                pcm_out = await tts_service.synthesize(reply_text)
                if pcm_out:
                    await websocket.send_bytes(pcm_out)
            except Exception as exc:
                logger.debug("TTS synthesis error: %s", exc)

    try:
        while True:
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                pcm_buffer.extend(message["bytes"])
            elif "text" in message and message["text"]:
                try:
                    payload = json.loads(message["text"])
                    msg_type = payload.get("type")

                    if msg_type == "audio_start":
                        pcm_buffer.clear()

                    elif msg_type == "audio_end":
                        if len(pcm_buffer) > 0 and speech_service:
                            try:
                                result = await speech_service.transcribe(bytes(pcm_buffer))
                                user_text = result.text.strip()
                                if user_text:
                                    await websocket.send_text(json.dumps({
                                        "type": "transcript",
                                        "text": user_text,
                                        "language": result.language,
                                    }))
                                    await process_turn(user_text)
                                else:
                                    await websocket.send_text(json.dumps({
                                        "type": "response",
                                        "text": "I didn't catch that. Could you please repeat?",
                                    }))
                            except Exception as ex:
                                logger.warning("Speech recognition failed: %s", ex)
                                await websocket.send_text(json.dumps({
                                    "type": "error",
                                    "message": f"Transcription error: {ex}",
                                }))
                            pcm_buffer.clear()
                        else:
                            pcm_buffer.clear()

                    elif msg_type == "text":
                        user_text = payload.get("text", "").strip()
                        if user_text:
                            await process_turn(user_text)

                    elif msg_type == "ping":
                        await websocket.send_text(json.dumps({"type": "pong", "time": time.time()}))

                except json.JSONDecodeError:
                    pass
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug("Mobile audio websocket disconnected/error: %s", exc)
    finally:
        dashboard_service.unregister_websocket(websocket)


@router.get("/mobile/web/{file_path:path}")
def serve_mobile_web_asset(file_path: str = "index.html") -> Response:
    import mimetypes
    from pathlib import Path
    from starlette.responses import FileResponse

    if not file_path or file_path == "/":
        file_path = "index.html"

    base_dir = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "frontend"
        / "mobile"
        / "web"
    )
    target = (base_dir / file_path).resolve()
    if not str(target).startswith(str(base_dir.resolve())) or not target.exists() or not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    mime_type, _ = mimetypes.guess_type(str(target))
    return FileResponse(str(target), media_type=mime_type or "text/plain")


def _safe_filename(name: str) -> str:
    cleaned = Path(name).name
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]", "_", cleaned).strip("._")
    return cleaned or "upload"


def _get_uploads_dir(request: Request) -> Path:
    uploads_dir = getattr(request.app.state, "uploads_dir", None)
    if uploads_dir is None:
        uploads_dir = Path.home() / ".alex" / "uploads"
    uploads_dir = Path(uploads_dir).resolve()
    try:
        uploads_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return uploads_dir


async def _parse_upload(request: Request) -> tuple[str, bytes, Optional[str]]:
    content_type = request.headers.get("content-type", "")
    explicit_filename = request.headers.get("x-filename") or request.query_params.get("filename")

    body = await request.body()
    if not body:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty upload body")

    if "multipart/form-data" in content_type:
        match = re.search(r"boundary=([^;]+)", content_type)
        if match:
            boundary = match.group(1).strip("\"'").encode("utf-8")
            delimiter = b"--" + boundary
            parts = body.split(delimiter)
            for part in parts:
                if b"Content-Disposition" in part:
                    header_part, _, data = part.partition(b"\r\n\r\n")
                    if data.endswith(b"\r\n"):
                        data = data[:-2]
                    elif data.endswith(b"--\r\n"):
                        data = data[:-4]
                    elif data.endswith(b"--"):
                        data = data[:-2]
                    header_str = header_part.decode("utf-8", errors="ignore")
                    fn_match = re.search(r'filename="([^"]+)"', header_str)
                    ct_match = re.search(r"Content-Type:\s*([^\r\n]+)", header_str, re.IGNORECASE)
                    filename = fn_match.group(1) if fn_match else (explicit_filename or "upload")
                    mime = ct_match.group(1).strip() if ct_match else None
                    return filename, data, mime

    filename = explicit_filename or "upload"
    return filename, body, content_type or None


@router.post("/mobile/upload", response_model=MobileUploadResponse)
async def mobile_upload_file(request: Request) -> MobileUploadResponse:
    dashboard_service = getattr(request.app.state, "dashboard_service", None)
    session_token = (
        request.headers.get("X-Mobile-Session")
        or request.headers.get("X-Auth-Token")
        or request.query_params.get("token")
    )
    if session_token and dashboard_service and not dashboard_service.is_authenticated(session_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired mobile session token",
        )

    raw_name, data, mime_type = await _parse_upload(request)
    max_bytes = 100 * 1024 * 1024  # 100 MB limit
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds maximum allowed upload size (100MB)",
        )

    uploads_dir = _get_uploads_dir(request)
    safe_name = _safe_filename(raw_name)

    stem = Path(safe_name).stem
    suffix = Path(safe_name).suffix
    dest = uploads_dir / safe_name
    counter = 1
    while dest.exists():
        dest = uploads_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    dest.write_bytes(data)

    return MobileUploadResponse(
        ok=True,
        filename=dest.name,
        saved_path=str(dest),
        size=len(data),
        content_type=mime_type,
    )


@router.get("/mobile/uploads", response_model=MobileUploadsListResponse)
def list_mobile_uploads(request: Request) -> MobileUploadsListResponse:
    uploads_dir = _get_uploads_dir(request)
    items = []
    if uploads_dir.exists():
        for p in uploads_dir.iterdir():
            if p.is_file() and not p.name.startswith("."):
                stat = p.stat()
                items.append(
                    MobileUploadedFileInfo(
                        filename=p.name,
                        size=stat.st_size,
                        modified_at=stat.st_mtime,
                        download_url=f"/api/v1/mobile/uploads/{p.name}",
                    )
                )
    items.sort(key=lambda x: x.modified_at, reverse=True)
    return MobileUploadsListResponse(uploads=items, total=len(items))


@router.get("/mobile/uploads/{filename}")
def get_mobile_upload_file(filename: str, request: Request) -> Response:
    uploads_dir = _get_uploads_dir(request)
    safe = _safe_filename(filename)
    dest = (uploads_dir / safe).resolve()
    if not str(dest).startswith(str(uploads_dir)) or not dest.exists() or not dest.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return FileResponse(path=str(dest), filename=safe)


# =========================================================================
# JARVIS / ALEX Hands-Free Voice Lifecycle Routes & WebSocket Hub
# =========================================================================

class VoiceWakeWordRequest(BaseModel):
    enabled: Optional[bool] = None


class VoiceAudioFeedRequest(BaseModel):
    audio_base64: str


@router.get("/voice/state")
def get_voice_lifecycle_state(request: Request) -> dict[str, Any]:
    mgr = getattr(request.app.state, "voice_lifecycle_manager", None)
    if not mgr:
        return {"state": "STANDBY", "wake_word_enabled": False, "mic_enabled": True}
    return {
        "state": mgr.state.value,
        "wake_word_enabled": mgr.wake_word_enabled,
        "mic_enabled": mgr.mic_enabled,
    }


@router.post("/voice/wake")
async def wake_voice_assistant(request: Request) -> dict[str, Any]:
    mgr = getattr(request.app.state, "voice_lifecycle_manager", None)
    if not mgr:
        raise HTTPException(status_code=503, detail="VoiceLifecycleManager not initialized")
    await mgr.wake(reason="api_request")
    return {"status": "ok", "state": mgr.state.value}


@router.post("/voice/sleep")
async def sleep_voice_assistant(request: Request) -> dict[str, Any]:
    mgr = getattr(request.app.state, "voice_lifecycle_manager", None)
    if not mgr:
        raise HTTPException(status_code=503, detail="VoiceLifecycleManager not initialized")
    await mgr.sleep(reason="api_request")
    return {"status": "ok", "state": mgr.state.value}


@router.post("/voice/interrupt")
async def interrupt_voice_assistant(request: Request) -> dict[str, Any]:
    mgr = getattr(request.app.state, "voice_lifecycle_manager", None)
    if not mgr:
        raise HTTPException(status_code=503, detail="VoiceLifecycleManager not initialized")
    await mgr.interrupt(reason="api_request")
    return {"status": "ok", "state": mgr.state.value}


@router.post("/voice/toggle-wake-word")
def toggle_voice_wake_word(body: VoiceWakeWordRequest, request: Request) -> dict[str, Any]:
    mgr = getattr(request.app.state, "voice_lifecycle_manager", None)
    if not mgr:
        raise HTTPException(status_code=503, detail="VoiceLifecycleManager not initialized")
    enabled = mgr.toggle_wake_word(body.enabled)
    return {"status": "ok", "wake_word_enabled": enabled}


@router.post("/voice/audio-feed")
async def feed_voice_audio(body: VoiceAudioFeedRequest, request: Request) -> dict[str, Any]:
    mgr = getattr(request.app.state, "voice_lifecycle_manager", None)
    if not mgr:
        raise HTTPException(status_code=503, detail="VoiceLifecycleManager not initialized")
    try:
        pcm = base64.b64decode(body.audio_base64)
        await mgr.feed_audio(pcm)
        return {"status": "ok", "bytes_fed": len(pcm), "state": mgr.state.value}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid audio chunk: {exc}")


@router.websocket("/voice/hub")
async def voice_hub_websocket(websocket: WebSocket) -> None:
    expected = websocket.app.state.api_token
    supplied = websocket.query_params.get("token", "")
    if not expected or not supplied or not hmac.compare_digest(
        supplied.encode("utf-8"), expected.encode("utf-8")
    ):
        await websocket.close(code=1008)
        return

    await websocket.accept()
    mgr = getattr(websocket.app.state, "voice_lifecycle_manager", None)
    if not mgr:
        await websocket.send_text(json.dumps({"type": "error", "message": "Voice manager unavailable"}))
        await websocket.close(code=1011)
        return

    # Broadcast initial state snapshot
    await websocket.send_text(
        json.dumps({
            "type": "state_snapshot",
            "state": mgr.state.value,
            "wake_word_enabled": mgr.wake_word_enabled,
            "mic_enabled": mgr.mic_enabled,
        })
    )

    async def on_voice_event(event: dict[str, Any]) -> None:
        try:
            await websocket.send_text(json.dumps(event))
        except Exception:
            pass

    unsubscribe = mgr.subscribe(on_voice_event)
    try:
        while True:
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                await mgr.feed_audio(message["bytes"])
            elif "text" in message and message["text"]:
                try:
                    payload = json.loads(message["text"])
                    mtype = payload.get("type")
                    if mtype == "audio_chunk":
                        raw = base64.b64decode(payload.get("audio", ""))
                        await mgr.feed_audio(raw)
                    elif mtype == "wake":
                        await mgr.wake(reason="websocket_wake")
                    elif mtype == "sleep":
                        await mgr.sleep(reason="websocket_sleep")
                    elif mtype == "interrupt":
                        await mgr.interrupt(reason="websocket_interrupt")
                    elif mtype == "toggle_wake_word":
                        mgr.toggle_wake_word(payload.get("enabled"))
                    elif mtype == "text_command":
                        cmd = payload.get("text", "").strip()
                        if cmd:
                            asyncio.create_task(mgr.process_turn(cmd))
                    elif mtype == "ping":
                        await websocket.send_text(json.dumps({"type": "pong", "time": time.time()}))
                except json.JSONDecodeError:
                    pass
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug("Voice hub websocket disconnected: %s", exc)
    finally:
        unsubscribe()


