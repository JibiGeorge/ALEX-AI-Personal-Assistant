"""
JARVIS-Style Centralized Voice Lifecycle Manager & State Machine.

Manages the full autonomous interaction cycle:
Startup -> Standby/Sleep -> Wake-Word Detection ("Hey Alex") -> Waking Up ->
Active Listening with VAD -> Speech-to-Text -> Intent & Tool Execution ->
Natural Voice Response (TTS) -> Continuous Conversation -> Voice Interruption ->
Auto-Sleep (30s inactivity) -> Standby -> Wake Again.
"""

from __future__ import annotations

import asyncio
from enum import Enum
import inspect
import io
import json
import logging
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from app.services.conversation_service import ConversationService
from app.services.speech_service import MIC_RATE, SPEAKER_RATE, SpeechService, to_float32, to_pcm16
from app.services.tts_service import TTSService
from app.services.wake_word_service import WakeWordService

logger = logging.getLogger(__name__)

# Default silence thresholds and timing
DEFAULT_INACTIVITY_TIMEOUT = 30.0  # seconds until auto-sleep
VAD_ENERGY_THRESHOLD = 0.025  # minimum float32 RMS for human voice
VAD_SILENCE_DURATION = 1.3  # seconds of silence to trigger speech endpoint
MIN_SPEECH_DURATION = 0.4  # seconds of minimum speech to prevent random clicks
MAX_UTTERANCE_DURATION = 15.0  # seconds max per turn before forced endpoint


class VoiceState(str, Enum):
    """Centralized voice interaction states."""
    INITIALIZING = "INITIALIZING"
    STANDBY = "STANDBY"
    SLEEPING = "SLEEPING"
    WAKE_WORD_DETECTED = "WAKE_WORD_DETECTED"
    WAKING_UP = "WAKING_UP"
    LISTENING = "LISTENING"
    SPEECH_DETECTED = "SPEECH_DETECTED"
    TRANSCRIBING = "TRANSCRIBING"
    UNDERSTANDING = "UNDERSTANDING"
    PROCESSING = "PROCESSING"
    EXECUTING_ACTION = "EXECUTING_ACTION"
    RESPONDING = "RESPONDING"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    WAITING_FOR_FOLLOWUP = "WAITING_FOR_FOLLOWUP"
    RETURNING_TO_SLEEP = "RETURNING_TO_SLEEP"
    MICROPHONE_DISABLED = "MICROPHONE_DISABLED"
    VOICE_ERROR = "VOICE_ERROR"


class VoiceStateSnapshot(BaseModel):
    """Immutable status snapshot for API and UI."""
    model_config = ConfigDict(extra="forbid")

    state: VoiceState
    awake: bool
    wake_enabled: bool
    wake_phrase: str
    is_speaking: bool
    inactivity_timeout_seconds: float
    last_interaction_seconds_ago: float
    message: str


class VoiceLifecycleManager:
    """Coordinates local wake-word, real-time VAD, STT, AI routing, and TTS synthesis."""

    def __init__(
        self,
        wake_word_service: WakeWordService,
        speech_service: SpeechService,
        tts_service: TTSService,
        conversation_service: ConversationService,
        settings_service: Any = None,
        action_executor: Any = None,
        assistant_name: str = "Alex",
        user_name: str = "Commander",
        wake_phrase: str = "Hey Alex",
        inactivity_timeout: float = DEFAULT_INACTIVITY_TIMEOUT,
    ):
        self._wake_service = wake_word_service
        self._speech_service = speech_service
        self._tts_service = tts_service
        self._conversation_service = conversation_service
        self._settings_service = settings_service
        self._action_executor = action_executor

        self.assistant_name = assistant_name
        self.user_name = user_name
        self.wake_phrase = wake_phrase.strip().lower() or "hey alex"
        self.inactivity_timeout = max(10.0, float(inactivity_timeout))

        # Lifecycle State
        self._state: VoiceState = VoiceState.INITIALIZING
        self._awake: bool = False
        self._wake_enabled: bool = True
        self._microphone_enabled: bool = True
        self._is_speaking: bool = False
        self._last_interaction_time: float = time.monotonic()
        self._conversation_id: UUID = uuid4()

        # Buffering & VAD
        self._audio_buffer: bytearray = bytearray()
        self._speech_detected_at: float = 0.0
        self._last_speech_time: float = 0.0
        self._has_speech_in_buffer: bool = False
        self._consecutive_silent_frames: int = 0

        # Background loops & listeners
        self._lock = threading.RLock()
        self._active_listeners: Set[Callable[[Dict[str, Any]], None]] = set()
        self._current_tts_task: Optional[asyncio.Task] = None
        self._processing_lock = asyncio.Lock()

        # Register callback with wake word service
        self._wake_service.set_on_wake(self._on_wake_word_triggered)

        # Transition to initial standby/sleep
        self._transition_to(VoiceState.SLEEPING, "ALEX standing by. Say 'Hey Alex' to wake me.")

    @property
    def state(self) -> VoiceState:
        with self._lock:
            return self._state

    @property
    def is_awake(self) -> bool:
        with self._lock:
            return self._awake

    @property
    def is_wake_enabled(self) -> bool:
        with self._lock:
            return self._wake_enabled

    @property
    def wake_word_enabled(self) -> bool:
        with self._lock:
            return self._wake_enabled

    @property
    def mic_enabled(self) -> bool:
        with self._lock:
            return self._microphone_enabled

    @property
    def is_speaking(self) -> bool:
        with self._lock:
            return self._is_speaking

    def subscribe(self, listener: Callable[[Dict[str, Any]], None]) -> Callable[[], None]:
        """Subscribe to voice events. Returns unsubscribe function."""
        self.register_listener(listener)
        return lambda: self.unregister_listener(listener)

    def cleanup(self) -> None:
        """Stop background tasks, clean buffers, and unregister listeners."""
        with self._lock:
            self._awake = False
            self._is_speaking = False
            self._audio_buffer.clear()
            self._active_listeners.clear()
            self._state = VoiceState.STANDBY

    def get_snapshot(self) -> VoiceStateSnapshot:
        """Return current state snapshot."""
        with self._lock:
            elapsed = time.monotonic() - self._last_interaction_time
            msg = self._get_default_status_message(self._state)
            return VoiceStateSnapshot(
                state=self._state,
                awake=self._awake,
                wake_enabled=self._wake_enabled,
                wake_phrase=self.wake_phrase,
                is_speaking=self._is_speaking,
                inactivity_timeout_seconds=self.inactivity_timeout,
                last_interaction_seconds_ago=round(elapsed, 1),
                message=msg,
            )

    def register_listener(self, listener: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback for UI / WebSocket event dispatch."""
        with self._lock:
            self._active_listeners.add(listener)

    def unregister_listener(self, listener: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            self._active_listeners.discard(listener)

    def _broadcast(self, event: Dict[str, Any]) -> None:
        """Send an event to all connected listeners safely."""
        with self._lock:
            listeners = list(self._active_listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:
                logger.debug("Error delivering voice event to listener: %s", exc)

    def _transition_to(self, new_state: VoiceState, message: Optional[str] = None) -> None:
        """Thread-safe state change with listener notification."""
        with self._lock:
            if self._state == new_state:
                return
            old_state = self._state
            self._state = new_state
            if new_state in (VoiceState.SLEEPING, VoiceState.STANDBY):
                self._awake = False
            elif new_state in (VoiceState.WAKING_UP, VoiceState.LISTENING, VoiceState.SPEAKING, VoiceState.PROCESSING):
                self._awake = True

            text = message or self._get_default_status_message(new_state)
            logger.info("Voice State: %s -> %s (%s)", old_state.value, new_state.value, text)

        self._broadcast({
            "type": "state_changed",
            "old_state": old_state.value,
            "new_state": new_state.value,
            "state": new_state.value,
            "awake": self._awake,
            "message": text,
            "timestamp": time.time(),
        })

    def _get_default_status_message(self, state: VoiceState) -> str:
        messages = {
            VoiceState.INITIALIZING: "Initializing voice engine and audio pipeline...",
            VoiceState.STANDBY: "ALEX Standby • Awaiting your command",
            VoiceState.SLEEPING: "Sleeping • Say 'Hey Alex' to wake me",
            VoiceState.WAKE_WORD_DETECTED: "Wake phrase recognized",
            VoiceState.WAKING_UP: "Yes, sir? I'm listening.",
            VoiceState.LISTENING: "Listening...",
            VoiceState.SPEECH_DETECTED: "Speech detected...",
            VoiceState.TRANSCRIBING: "Transcribing speech...",
            VoiceState.UNDERSTANDING: "Analyzing intent...",
            VoiceState.PROCESSING: "Processing request...",
            VoiceState.EXECUTING_ACTION: "Executing system action...",
            VoiceState.RESPONDING: "Formulating response...",
            VoiceState.SPEAKING: "Responding...",
            VoiceState.INTERRUPTED: "Speech interrupted • Listening...",
            VoiceState.WAITING_FOR_FOLLOWUP: "Standing by for follow-up...",
            VoiceState.RETURNING_TO_SLEEP: "Returning to standby...",
            VoiceState.MICROPHONE_DISABLED: "Microphone disabled",
            VoiceState.VOICE_ERROR: "Voice engine error",
        }
        return messages.get(state, state.value)

    # ── Wake, Sleep & Interruption Controls ──────────────────────────────────

    async def wake(self, reason: str = "wake_word") -> None:
        """Wake up from sleep mode into active listening (async)."""
        self.wake_sync(reason)

    def wake_sync(self, reason: str = "wake_word") -> None:
        """Wake up from sleep mode into active listening (synchronous)."""
        with self._lock:
            self._awake = True
            self._last_interaction_time = time.monotonic()
            self._audio_buffer.clear()
            self._has_speech_in_buffer = False

        self._transition_to(VoiceState.WAKE_WORD_DETECTED, f"Wake detected: {reason}")
        self._transition_to(VoiceState.WAKING_UP, f"Yes, {self.user_name or 'sir'}? I'm listening.")
        self._transition_to(VoiceState.LISTENING, "Listening for command...")

    async def sleep(self, reason: str = "timeout") -> None:
        """Enter low-power standby mode with local wake-word monitoring (async)."""
        self.sleep_sync(reason)

    def sleep_sync(self, reason: str = "timeout") -> None:
        """Enter low-power standby mode with local wake-word monitoring (synchronous)."""
        with self._lock:
            self._awake = False
            self._is_speaking = False
            self._audio_buffer.clear()
            self._has_speech_in_buffer = False

        self._transition_to(VoiceState.RETURNING_TO_SLEEP, f"Entering sleep: {reason}")
        self._transition_to(VoiceState.SLEEPING, "ALEX Standby • Say 'Hey Alex' to wake me")

    async def interrupt(self, reason: str = "user") -> None:
        """Immediately halt assistant speech and switch to listening mode (async)."""
        self.interrupt_sync(reason)

    def interrupt_sync(self, reason: str = "user") -> None:
        """Immediately halt assistant speech and switch to listening mode (synchronous)."""
        with self._lock:
            self._is_speaking = False
            self._last_interaction_time = time.monotonic()
            self._audio_buffer.clear()
            self._has_speech_in_buffer = False

        logger.info("Assistant voice output interrupted by user: %s", reason)
        self._broadcast({"type": "interrupt", "timestamp": time.time(), "reason": reason})
        self._transition_to(VoiceState.INTERRUPTED, "Interrupted • Listening...")
        self._transition_to(VoiceState.LISTENING, "Listening...")

    def toggle_wake_word(self, enabled: Optional[bool] = None) -> bool:
        """Toggle local wake-word monitoring."""
        with self._lock:
            new_target = not self._wake_enabled if enabled is None else bool(enabled)
            self._wake_enabled = new_target
            self._wake_service.set_enabled(new_target)
            if not new_target and not self._awake:
                self.wake_sync("wake word disabled")
            elif new_target and self._awake:
                self.sleep_sync("wake word enabled")
        return self._wake_enabled

    def set_microphone_enabled(self, enabled: bool) -> None:
        """Physical or UI microphone mute toggle."""
        with self._lock:
            self._microphone_enabled = enabled
            if not enabled:
                self._transition_to(VoiceState.MICROPHONE_DISABLED, "Microphone muted")
            else:
                if self._awake:
                    self._transition_to(VoiceState.LISTENING, "Microphone active • Listening...")
                else:
                    self._transition_to(VoiceState.SLEEPING, "Microphone active • Standby")

    def _on_wake_word_triggered(self) -> None:
        """Callback from WakeWordService background worker."""
        if not self._wake_enabled:
            return
        logger.info("Wake-word triggered by local engine.")
        self.wake("local wake-word model")

    # ── Real-Time Audio Pipeline (16 kHz PCM Ingest) ──────────────────────────

    def feed_audio(self, pcm_bytes: bytes) -> Optional[str]:
        """
        Ingest a 16 kHz 16-bit mono PCM chunk from microphone.
        Dispatches to wake detection when asleep, or VAD endpointing when awake.
        Returns a prompt string if a completed utterance was finalized synchronously.
        """
        if not self._microphone_enabled or not pcm_bytes:
            return None

        # Measure audio energy (RMS)
        try:
            samples = to_float32(pcm_bytes)
            if samples.size == 0:
                return None
            rms = float(np.sqrt(np.mean(samples ** 2)))
        except Exception:
            rms = 0.0

        with self._lock:
            current_state = self._state
            awake = self._awake
            speaking = self._is_speaking

        # 1. State: SLEEPING -> Local Wake-Word Monitoring
        if not awake or current_state in (VoiceState.SLEEPING, VoiceState.STANDBY):
            if self._wake_enabled:
                # Feed to openwakeword queue
                self._wake_service.feed(pcm_bytes)

                # Fallback energy & phrase detector when openwakeword model file is not downloaded
                if rms > VAD_ENERGY_THRESHOLD * 1.5:
                    self._audio_buffer.extend(pcm_bytes)
                    if len(self._audio_buffer) >= MIC_RATE * 2:  # ~1 second
                        audio_slice = bytes(self._audio_buffer)
                        self._audio_buffer.clear()
                        # Quick check for keyword in speech
                        text = self._quick_check_wake_phrase(audio_slice)
                        if text:
                            self.wake(f"voice detected: '{text}'")
                else:
                    if len(self._audio_buffer) > MIC_RATE * 3:
                        self._audio_buffer.clear()
            return None

        # 2. State: SPEAKING -> Interruption Detection
        if speaking or current_state == VoiceState.SPEAKING:
            if rms > VAD_ENERGY_THRESHOLD * 2.2:
                # User is speaking over assistant output -> trigger interruption!
                self.interrupt()
            return None

        # 3. State: LISTENING / WAITING_FOR_FOLLOWUP / SPEECH_DETECTED -> Active VAD
        now = time.monotonic()
        is_speech = rms >= VAD_ENERGY_THRESHOLD

        if is_speech:
            with self._lock:
                self._last_speech_time = now
                self._consecutive_silent_frames = 0
                if not self._has_speech_in_buffer:
                    self._has_speech_in_buffer = True
                    self._speech_detected_at = now
                    self._transition_to(VoiceState.SPEECH_DETECTED, "Speech detected...")
                self._audio_buffer.extend(pcm_bytes)
        else:
            with self._lock:
                if self._has_speech_in_buffer:
                    self._audio_buffer.extend(pcm_bytes)
                    self._consecutive_silent_frames += 1
                    silence_elapsed = now - self._last_speech_time
                    speech_duration = self._last_speech_time - self._speech_detected_at

                    # Endpoint condition: sufficient speech duration + silence duration reached
                    if silence_elapsed >= VAD_SILENCE_DURATION and speech_duration >= MIN_SPEECH_DURATION:
                        utterance_audio = bytes(self._audio_buffer)
                        self._audio_buffer.clear()
                        self._has_speech_in_buffer = False
                        self._last_interaction_time = now
                        return self._finalize_utterance(utterance_audio)
                    elif silence_elapsed >= VAD_SILENCE_DURATION and speech_duration < MIN_SPEECH_DURATION:
                        # False trigger (cough / click) -> discard
                        self._audio_buffer.clear()
                        self._has_speech_in_buffer = False
                        self._transition_to(VoiceState.LISTENING, "Listening...")

        return None

    def _quick_check_wake_phrase(self, audio_bytes: bytes) -> Optional[str]:
        """Lightweight offline keyword matching for 'Hey Alex' or 'Alex'."""
        try:
            transcript = self._speech_service.transcribe(audio_bytes).strip().lower()
            if not transcript:
                return None
            # Check for alex / jarvis
            target_phrases = ["hey alex", "alex", "hey jarvis", "jarvis"]
            for target in target_phrases:
                if target in transcript:
                    return transcript
        except Exception:
            pass
        return None

    def _finalize_utterance(self, audio_bytes: bytes) -> Optional[str]:
        """Convert audio to text and begin asynchronous execution."""
        self._transition_to(VoiceState.TRANSCRIBING, "Transcribing speech...")
        try:
            text = self._speech_service.transcribe(audio_bytes).strip()
            if not text:
                self._transition_to(VoiceState.LISTENING, "No speech recognized • Listening...")
                return None

            logger.info("Voice Recognized: '%s'", text)
            self._broadcast({
                "type": "transcript",
                "role": "user",
                "text": text,
                "timestamp": time.time(),
            })

            # Check for immediate control phrases
            lower = text.lower()
            if any(p in lower for p in ["go to sleep", "sleep now", "stand by", "stop listening", "good night alex"]):
                self.sleep("user command")
                return None

            if lower in ("stop", "cancel", "shut up", "wait"):
                self.interrupt()
                return None

            return text
        except Exception as exc:
            logger.error("Error transcribing voice audio: %s", exc)
            self._transition_to(VoiceState.VOICE_ERROR, f"Transcription error: {exc}")
            return None

    # ── Voice Turn Processing & Speech Synthesis ─────────────────────────────

    async def process_turn(self, user_text: str) -> None:
        """
        Process a user command through AI, execute actions, synthesize natural speech,
        and stream audio output to listeners.
        """
        async with self._processing_lock:
            with self._lock:
                self._last_interaction_time = time.monotonic()

            self._transition_to(VoiceState.UNDERSTANDING, f"Processing: '{user_text}'")
            self._transition_to(VoiceState.PROCESSING, "Formulating intelligent response...")

            # Execute turn via conversation service
            loop = asyncio.get_running_loop()
            try:
                turn_response = await loop.run_in_executor(
                    None,
                    lambda: self._conversation_service.reply(
                        text=user_text,
                        conversation_id=self._conversation_id,
                        assistant_name=self.assistant_name,
                        user_name=self.user_name,
                    ),
                )
                reply_text = turn_response.text or "I have processed your request."
            except Exception as exc:
                logger.error("Error in conversation AI turn: %s", exc)
                reply_text = f"I encountered an issue processing that: {exc}"

            self._broadcast({
                "type": "transcript",
                "role": "assistant",
                "text": reply_text,
                "timestamp": time.time(),
            })
            self._broadcast({
                "type": "response",
                "text": reply_text,
                "timestamp": time.time(),
            })

            # Synthesize natural voice
            self._transition_to(VoiceState.RESPONDING, "Synthesizing spoken response...")
            with self._lock:
                self._is_speaking = True

            try:
                # Generate audio via TTSService (Piper / system)
                self._transition_to(VoiceState.SPEAKING, reply_text)
                if inspect.iscoroutinefunction(self._tts_service.synthesize):
                    pcm_audio = await self._tts_service.synthesize(reply_text)
                else:
                    synth_val = self._tts_service.synthesize(reply_text)
                    if inspect.iscoroutine(synth_val):
                        pcm_audio = await synth_val
                    else:
                        pcm_audio = synth_val

                if pcm_audio:
                    import base64
                    pcm_b64 = base64.b64encode(pcm_audio).decode("ascii")
                    self._broadcast({
                        "type": "audio",
                        "pcm_base64": pcm_b64,
                        "sample_rate": SPEAKER_RATE,
                        "text": reply_text,
                        "timestamp": time.time(),
                    })

                    # Calculate playback duration to keep state in SPEAKING
                    duration_sec = len(pcm_audio) / (SPEAKER_RATE * 2)
                    await asyncio.sleep(max(0.4, duration_sec))
            except Exception as exc:
                logger.error("TTS synthesis error: %s", exc)
            finally:
                with self._lock:
                    self._is_speaking = False
                    self._last_interaction_time = time.monotonic()

            # Continuous Conversation: enter WAITING_FOR_FOLLOWUP so user can speak again without 'Hey Alex'
            self._transition_to(
                VoiceState.WAITING_FOR_FOLLOWUP,
                "Awaiting follow-up instruction...",
            )

    async def check_inactivity(self) -> None:
        """Periodic watchdog checking for auto-sleep timeout (async)."""
        self.check_inactivity_sync()

    def check_inactivity_sync(self) -> None:
        """Periodic watchdog checking for auto-sleep timeout (sync)."""
        with self._lock:
            if not self._awake:
                return
            if self._is_speaking:
                return
            if self._state not in (VoiceState.WAITING_FOR_FOLLOWUP, VoiceState.LISTENING):
                return

            idle_duration = time.monotonic() - self._last_interaction_time
            if idle_duration >= self.inactivity_timeout:
                logger.info(
                    "Voice Assistant auto-sleep: inactivity timeout (%.1fs >= %.1fs)",
                    idle_duration,
                    self.inactivity_timeout,
                )
                self.sleep_sync("inactivity timeout")
