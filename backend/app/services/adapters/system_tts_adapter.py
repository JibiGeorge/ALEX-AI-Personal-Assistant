"""
Cross-Platform System Text-to-Speech Adapter (TASK-P4-02 / CAT-09).

Synthesizes speech using operating system built-in synthesizers:
- Windows: System.Speech (SAPI5) via PowerShell
- macOS: /usr/bin/say
- Linux: espeak-ng / espeak / spd-say

Safety Invariant:
Text is always written to a UTF-8 temporary file and read by the engine,
never passed as shell command arguments to avoid multi-language code-page corruption.
"""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import re
import shutil
import subprocess
import tempfile
import threading
from typing import AsyncIterator, List, Optional, Tuple

from app.services.speech_service import SPEAKER_RATE, wav_to_pcm

logger = logging.getLogger(__name__)

_SYS = platform.system()
_NO_WINDOW = 0x08000000 if _SYS == "Windows" else 0

# Sentence-ending punctuation across Latin, CJK, Arabic and Devanagari scripts
_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+|(?<=[。！？؟۔।])\s*")

_voice_cache: Optional[List[str]] = None
_voice_lock = threading.Lock()


def split_sentences(text: str, max_chars: int = 240) -> List[str]:
    """Break input text into speakable sentence chunks at punctuation boundaries."""
    text = (text or "").strip()
    if not text:
        return []
    pieces: List[str] = []
    for part in _SENTENCE_END.split(text):
        part = part.strip()
        if not part:
            continue
        while len(part) > max_chars:
            cut = part.rfind(" ", 0, max_chars)
            if cut <= 0:
                cut = max_chars
            pieces.append(part[:cut].strip())
            part = part[cut:].strip()
        if part:
            pieces.append(part)
    return pieces


def _powershell() -> Optional[str]:
    return shutil.which("pwsh") or shutil.which("powershell")


def _run_cmd(
    args: List[str], timeout: float = 30.0, stdin_data: Optional[bytes] = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        input=stdin_data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        creationflags=_NO_WINDOW,
    )


def list_system_voices(refresh: bool = False) -> List[str]:
    """List voices installed on the operating system, cached for session performance."""
    global _voice_cache
    with _voice_lock:
        if _voice_cache is not None and not refresh:
            return list(_voice_cache)

    found: List[str] = []
    try:
        if _SYS == "Windows":
            ps = _powershell()
            if ps:
                cmd = (
                    "Add-Type -AssemblyName System.Speech; "
                    "(New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices() | "
                    "ForEach-Object { $_.VoiceInfo.Name }"
                )
                res = _run_cmd([ps, "-NoProfile", "-NonInteractive", "-Command", cmd], timeout=15)
                found = [line.strip() for line in res.stdout.decode("utf-8", "replace").splitlines() if line.strip()]

        elif _SYS == "Darwin":
            if shutil.which("say"):
                res = _run_cmd(["say", "-v", "?"], timeout=15)
                for line in res.stdout.decode("utf-8", "replace").splitlines():
                    name = line.split("  ")[0].strip()
                    if name:
                        found.append(name)

        elif _SYS == "Linux":
            exe = shutil.which("espeak-ng") or shutil.which("espeak")
            if exe:
                res = _run_cmd([exe, "--voices"], timeout=15)
                for line in res.stdout.decode("utf-8", "replace").splitlines()[1:]:
                    cols = line.split()
                    if len(cols) >= 4:
                        found.append(cols[3])
                found = sorted(set(found))
    except Exception as exc:
        logger.warning("Error enumerating system voices: %s", exc)

    with _voice_lock:
        _voice_cache = found
    return list(found)


class SystemTTSAdapter:
    """System-level speech synthesis adapter providing guaranteed zero-download voice fallback."""

    def __init__(self, voice: str = "", speed_rate: int = 0) -> None:
        self.voice = voice.strip()
        self.speed_rate = speed_rate

    def _synth_windows(self, txt_path: str, wav_path: str) -> None:
        ps = _powershell()
        if not ps:
            raise RuntimeError("PowerShell is not available for Windows System.Speech")

        clean_voice = self.voice.replace("'", "''")
        select_clause = f"$s.SelectVoice('{clean_voice}');" if self.voice else ""
        rate_val = max(-10, min(10, self.speed_rate))

        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"{select_clause} "
            f"$s.Rate = {rate_val}; "
            f"$t = [System.IO.File]::ReadAllText('{txt_path}', [System.Text.Encoding]::UTF8); "
            f"$s.SetOutputToWaveFile('{wav_path}'); "
            "$s.Speak($t); "
            "$s.Dispose();"
        )
        res = _run_cmd([ps, "-NoProfile", "-NonInteractive", "-Command", script])
        if res.returncode != 0:
            raise RuntimeError(res.stderr.decode("utf-8", "replace")[:200] or "Windows SAPI synthesis failed")

    def _synth_macos(self, txt_path: str, wav_path: str) -> None:
        if not shutil.which("say"):
            raise RuntimeError("macOS 'say' executable was not found")

        args = [
            "say",
            "-f",
            txt_path,
            "-o",
            wav_path,
            "--data-format=LEI16@24000",  # Directly request 24kHz 16-bit mono
        ]
        if self.voice:
            args.extend(["-v", self.voice])
        if self.speed_rate:
            wpm = max(90, min(400, 175 + self.speed_rate * 15))
            args.extend(["-r", str(wpm)])

        res = _run_cmd(args)
        if res.returncode != 0:
            raise RuntimeError(res.stderr.decode("utf-8", "replace")[:200] or "macOS say synthesis failed")

    def _synth_linux(self, txt_path: str, wav_path: str) -> None:
        exe = shutil.which("espeak-ng") or shutil.which("espeak")
        if not exe:
            raise RuntimeError("No Linux speech engine found (install espeak-ng)")

        args = [exe, "-f", txt_path, "-w", wav_path]
        if self.voice:
            args.extend(["-v", self.voice])
        if self.speed_rate:
            wpm = max(80, min(450, 175 + self.speed_rate * 15))
            args.extend(["-s", str(wpm)])

        res = _run_cmd(args)
        if res.returncode != 0:
            raise RuntimeError(res.stderr.decode("utf-8", "replace")[:200] or "Linux espeak-ng synthesis failed")

    def synth_sentence_blocking(self, sentence: str) -> bytes:
        """Synthesize a single sentence chunk to 24 kHz mono PCM bytes via temp files."""
        if not sentence.strip():
            return b""

        temp_dir = tempfile.mkdtemp(prefix="alex_tts_")
        txt_path = os.path.join(temp_dir, "phrase.txt")
        wav_path = os.path.join(temp_dir, "output.wav")

        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(sentence.strip())

            if _SYS == "Windows":
                self._synth_windows(txt_path, wav_path)
            elif _SYS == "Darwin":
                self._synth_macos(txt_path, wav_path)
            else:
                self._synth_linux(txt_path, wav_path)

            if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
                return b""

            with open(wav_path, "rb") as f:
                wav_bytes = f.read()
            return wav_to_pcm(wav_bytes, want_rate=SPEAKER_RATE)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def speak(self, text: str, voice: str = "") -> bytes:
        """Synthesize full text to 24 kHz mono 16-bit PCM bytes."""
        if voice:
            self.voice = voice
        sentences = split_sentences(text)
        if not sentences:
            return b""

        pcm_chunks: List[bytes] = []
        for s in sentences:
            chunk = await asyncio.to_thread(self.synth_sentence_blocking, s)
            if chunk:
                pcm_chunks.append(chunk)
        return b"".join(pcm_chunks)

    async def stream_speak(self, text: str, voice: str = "") -> AsyncIterator[bytes]:
        """Stream synthesized 24 kHz mono PCM audio chunks sentence-by-sentence."""
        if voice:
            self.voice = voice
        for sentence in split_sentences(text):
            chunk = await asyncio.to_thread(self.synth_sentence_blocking, sentence)
            if chunk:
                yield chunk

    def probe(self) -> Tuple[bool, str]:
        """Probe platform TTS capability."""
        voices = list_system_voices()
        if _SYS == "Darwin":
            if shutil.which("say"):
                return True, f"macOS 'say' engine ready ({len(voices)} voices)"
            return False, "macOS 'say' is not available"
        if _SYS == "Windows":
            if _powershell():
                return True, f"Windows SAPI5 engine ready ({len(voices)} voices)"
            return False, "Windows PowerShell is not available"
        if shutil.which("espeak-ng") or shutil.which("espeak"):
            return True, f"Linux espeak engine ready ({len(voices)} voices)"
        return False, "Linux espeak-ng is not installed"

