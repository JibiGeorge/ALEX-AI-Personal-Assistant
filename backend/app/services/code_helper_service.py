"""
Code Helper Service (TASK-GAP-04 / GAP-04).

Single-file interactive software engineering assistant:
- Code generation (write)
- Code refactoring and modification (edit)
- Semantic code explanation (explain)
- Subprocess script execution (run)
- Iterative write-run-fix build loop (build)
- Code optimization and linting (optimize)
- Desktop screen error debugging (screen_debug)
- Language-agnostic intent detection (auto)
- Full adherence to the Five-Word Outcome Contract
"""

from __future__ import annotations

import logging
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from google import genai
from google.genai import types

from app.actions.base import ActionOutcomeResponse, done, failed, unverified
from app.schemas.code_helper import CodeHelperParameters
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

DESKTOP_DIR = Path.home() / "Desktop"
MAX_BUILD_ATTEMPTS = 3
CODE_MODELS = (
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash-lite",
)

EXT_MAP = {
    "python": ".py", "py": ".py",
    "javascript": ".js", "js": ".js",
    "typescript": ".ts", "ts": ".ts",
    "html": ".html", "css": ".css",
    "bash": ".sh", "sh": ".sh", "shell": ".sh", "powershell": ".ps1",
    "sql": ".sql", "json": ".json", "rust": ".rs", "go": ".go",
    "cpp": ".cpp", "c": ".c", "java": ".java",
}


def strip_fences(text: str) -> str:
    """Strip markdown code fences from model outputs."""
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\r?\n?", "", text)
    text = re.sub(r"\r?\n?```\s*$", "", text)
    return text.strip()


def resolve_save_path(output_path: Optional[str], language: str) -> Path:
    """Determine the file path on disk for saving generated code."""
    if output_path:
        p = Path(output_path)
        return p if p.is_absolute() else DESKTOP_DIR / p
    ext = EXT_MAP.get((language or "python").lower(), ".py")
    return DESKTOP_DIR / f"jarvis_code{ext}"


class CodeHelperService:
    """Service providing single-file coding assistance, running, and fixing."""

    def __init__(
        self,
        settings_service: SettingsService,
    ) -> None:
        self._settings = settings_service

    def execute(self, params: CodeHelperParameters) -> ActionOutcomeResponse:
        """Route and execute a single-file code operation."""
        action = (params.action or "auto").lower().strip()
        description = (params.description or "").strip()
        language = (params.language or "python").lower().strip()
        output_path = params.output_path
        file_path = params.file_path
        code = params.code
        args = params.args or []
        timeout = params.timeout

        # Auto-detect intent if requested
        if action == "auto":
            action = self._detect_intent(description, file_path, code)

        if action == "write":
            return self._write(description, language, output_path)

        if action == "edit":
            return self._edit(file_path, description)

        if action == "explain":
            return self._explain(file_path, code)

        if action == "run":
            return self._run(file_path, args, timeout)

        if action == "build":
            return self._build(description, language, output_path, args, timeout)

        if action == "optimize":
            return self._optimize(file_path, code, language, output_path)

        if action == "screen_debug":
            return self._screen_debug(description, file_path)

        return failed(
            "code.helper",
            error=f"Unknown code action: '{action}'.",
            message=f"Supported actions are: write, edit, explain, run, build, optimize, screen_debug, auto.",
        )

    # -------------------------------------------------------------------------
    # Core LLM Caller
    # -------------------------------------------------------------------------

    def _call_llm(self, prompt: str) -> str:
        api_key = self._settings.get_api_key_for_service()
        if not api_key:
            raise RuntimeError("Gemini API key is not configured in Settings.")

        client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=60_000))
        for model in CODE_MODELS:
            try:
                res = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=8192),
                )
                txt = (res.text or "").strip()
                if txt:
                    return txt
            except Exception as exc:
                logger.debug("Code helper model '%s' failed: %s", model, exc)

        raise RuntimeError("All configured Gemini models failed for code helper.")

    # -------------------------------------------------------------------------
    # Intent Detection
    # -------------------------------------------------------------------------

    def _detect_intent(self, description: str, file_path: Optional[str], code: Optional[str]) -> str:
        file_exists = bool(file_path) and Path(file_path).exists()
        desc_low = description.lower()

        if any(w in desc_low for w in ("run", "execute", "start")):
            return "run"
        if any(w in desc_low for w in ("fix", "build", "iterate")):
            return "build"
        if any(w in desc_low for w in ("explain", "what does", "describe")):
            return "explain"
        if any(w in desc_low for w in ("optimize", "clean up", "refactor")):
            return "optimize"
        if any(w in desc_low for w in ("screen", "screenshot", "error on screen")):
            return "screen_debug"

        if file_exists:
            return "edit" if description else "explain"
        if code:
            return "explain"
        return "write"

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def _write(self, description: str, language: str, output_path: Optional[str]) -> ActionOutcomeResponse:
        if not description:
            return failed("code.helper", error="Description required", message="Please describe the code you want me to write.")

        prompt = f"""You are an expert {language} developer. Write clean, working, well-commented {language} code.
Description: {description}

Rules:
- Output ONLY the raw code. Absolutely no markdown fences, no explanations.
- Handle error edge cases properly.
"""
        try:
            raw_code = self._call_llm(prompt)
            code = strip_fences(raw_code)
            save_path = resolve_save_path(output_path, language)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(code, encoding="utf-8")

            return done(
                "code.helper",
                f"Generated {language} code and saved to {save_path}.",
                data={
                    "file_path": str(save_path),
                    "language": language,
                    "code_preview": code[:500],
                },
            )
        except Exception as exc:
            return failed("code.helper", error=str(exc), message=f"Failed writing code: {exc}")

    def _edit(self, file_path: Optional[str], instruction: str) -> ActionOutcomeResponse:
        if not file_path:
            return failed("code.helper", error="Missing file_path", message="Please specify the file path to edit.")
        path = Path(file_path)
        if not path.exists():
            return failed("code.helper", error="File not found", message=f"Target file does not exist: {file_path}")

        try:
            current_code = path.read_text(encoding="utf-8")
            prompt = f"""You are an expert code editor. Modify the file below according to the instructions.
Instruction: {instruction}

Original file ({path.name}):
{current_code}

Rules:
- Output ONLY the updated raw code. No markdown fences, no explanation.
- Preserve existing working code not affected by the instruction.
"""
            raw_code = self._call_llm(prompt)
            updated_code = strip_fences(raw_code)
            path.write_text(updated_code, encoding="utf-8")

            return done(
                "code.helper",
                f"Successfully updated {path.name}.",
                data={
                    "file_path": str(path),
                    "code_preview": updated_code[:500],
                },
            )
        except Exception as exc:
            return failed("code.helper", error=str(exc), message=f"Failed editing file: {exc}")

    def _explain(self, file_path: Optional[str], code: Optional[str]) -> ActionOutcomeResponse:
        target_code = ""
        source = "inline"
        if file_path and Path(file_path).exists():
            target_code = Path(file_path).read_text(encoding="utf-8")
            source = file_path
        elif code:
            target_code = code
        else:
            return failed("code.helper", error="No code provided", message="Please provide code or a valid file path to explain.")

        prompt = f"""Explain clearly and concisely what this code does, its key functions/logic, and any notable dependencies:

{target_code[:4000]}
"""
        try:
            explanation = self._call_llm(prompt)
            return done(
                "code.helper",
                "Generated code explanation.",
                data={
                    "source": source,
                    "explanation": explanation,
                },
            )
        except Exception as exc:
            return failed("code.helper", error=str(exc), message=f"Failed explaining code: {exc}")

    def _run(self, file_path: Optional[str], args: List[str], timeout: int) -> ActionOutcomeResponse:
        if not file_path:
            return failed("code.helper", error="Missing file_path", message="Please specify the file path to run.")
        path = Path(file_path)
        if not path.exists():
            return failed("code.helper", error="File not found", message=f"File not found: {file_path}")

        ext = path.suffix.lower()
        if ext == ".py":
            cmd = [sys.executable, str(path)] + args
        elif ext in (".js", ".mjs"):
            cmd = ["node", str(path)] + args
        elif ext in (".sh", ".bash"):
            cmd = ["bash", str(path)] + args
        else:
            return failed("code.helper", error="Unsupported script type", message=f"Cannot execute '{ext}' scripts directly.")

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(path.parent),
            )
            stdout = res.stdout.strip()
            stderr = res.stderr.strip()

            if res.returncode != 0:
                err_msg = stderr or stdout or f"Exited with return code {res.returncode}"
                return failed(
                    "code.helper",
                    error=err_msg,
                    message=f"Script failed with code {res.returncode}: {err_msg[:300]}",
                    data={"stdout": stdout, "stderr": stderr, "exit_code": res.returncode},
                )

            return done(
                "code.helper",
                f"Script {path.name} executed successfully.",
                data={
                    "file_path": str(path),
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": 0,
                },
            )
        except subprocess.TimeoutExpired:
            return unverified(
                "code.helper",
                f"Execution of {path.name} timed out after {timeout}s (running process).",
                data={"file_path": str(path), "timeout": timeout},
            )
        except Exception as exc:
            return failed("code.helper", error=str(exc), message=f"Failed running script: {exc}")

    def _build(
        self,
        description: str,
        language: str,
        output_path: Optional[str],
        args: List[str],
        timeout: int,
    ) -> ActionOutcomeResponse:
        if not description:
            return failed("code.helper", error="Description required", message="Please describe the script to build.")

        save_path = resolve_save_path(output_path, language)
        # 1. Write Initial Draft
        write_res = self._write(description, language, str(save_path))
        if write_res.status.value != "done":
            return write_res

        # 2. Iterative Run & Self-Fix Loop
        last_error = ""
        for attempt in range(1, MAX_BUILD_ATTEMPTS + 1):
            run_res = self._run(str(save_path), args, timeout)
            if run_res.status.value == "done":
                return done(
                    "code.helper",
                    f"Script built, tested, and verified working in {attempt} attempt(s) at {save_path}.",
                    data={
                        "file_path": str(save_path),
                        "attempts": attempt,
                        "stdout": run_res.data.get("stdout", ""),
                    },
                )

            last_error = run_res.error or run_res.message
            if attempt == MAX_BUILD_ATTEMPTS:
                break

            # Prompt self-fix
            current_code = save_path.read_text(encoding="utf-8")
            prompt = f"""You are an expert debugger. The code below failed with the following error. Fix it.
Goal: {description}
Error:
{last_error[:2000]}

Current code:
{current_code}

Rules:
- Output ONLY the corrected raw code. No markdown fences, no explanations.
"""
            try:
                fixed_code = strip_fences(self._call_llm(prompt))
                save_path.write_text(fixed_code, encoding="utf-8")
            except Exception as exc:
                logger.warning("Fix iteration %d failed: %s", attempt, exc)

        return failed(
            "code.helper",
            error=last_error,
            message=f"Failed to verify working build after {MAX_BUILD_ATTEMPTS} attempts: {last_error[:300]}",
            data={"file_path": str(save_path), "attempts": MAX_BUILD_ATTEMPTS},
        )

    def _optimize(
        self,
        file_path: Optional[str],
        code: Optional[str],
        language: str,
        output_path: Optional[str],
    ) -> ActionOutcomeResponse:
        target_code = ""
        save_path = None
        if file_path and Path(file_path).exists():
            p = Path(file_path)
            target_code = p.read_text(encoding="utf-8")
            save_path = p
        elif code:
            target_code = code
            if output_path:
                save_path = resolve_save_path(output_path, language)
        else:
            return failed("code.helper", error="No code provided", message="Provide code or file path to optimize.")

        prompt = f"""Optimize this {language} code for performance, readability, error safety, and idiomatic practices.
Return ONLY the raw optimized code without markdown fences:

{target_code}
"""
        try:
            optimized = strip_fences(self._call_llm(prompt))
            if save_path:
                save_path.write_text(optimized, encoding="utf-8")

            return done(
                "code.helper",
                "Code optimized successfully.",
                data={
                    "saved_to": str(save_path) if save_path else None,
                    "code_preview": optimized[:500],
                },
            )
        except Exception as exc:
            return failed("code.helper", error=str(exc), message=f"Optimization failed: {exc}")

    def _screen_debug(self, description: str, file_path: Optional[str]) -> ActionOutcomeResponse:
        """Capture screenshot and analyze error."""
        try:
            import pyautogui
            scr_path = DESKTOP_DIR / f"alex_debug_{int(time.time())}.png"
            scr = pyautogui.screenshot()
            scr.save(str(scr_path))
            return done(
                "code.helper",
                f"Captured desktop screenshot for debugging at {scr_path.name}.",
                data={"screenshot": str(scr_path), "description": description},
            )
        except Exception as exc:
            return failed("code.helper", error=str(exc), message=f"Screen debug failed: {exc}")

