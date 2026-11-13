"""
Dev Agent Service (TASK-GAP-03 / GAP-03).

Autonomous multi-file software engineering agent:
- Project architecture planning into dependency-ordered files
- Multi-file code generation and scaffolding in ~/Desktop/JarvisProjects
- Automatic external dependency installation (pip)
- Subprocess build and test execution loop
- Automated traceback parsing and error classification
- Iterative self-correction loop (up to 5 attempts)
- Full adherence to the Five-Word Outcome Contract
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from google import genai
from google.genai import types

from app.actions.base import ActionOutcomeResponse, done, failed, unverified
from app.schemas.dev_agent import DevAgentParameters
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

DEFAULT_PROJECTS_DIR = Path.home() / "Desktop" / "AlexProjects"
MAX_FIX_ATTEMPTS = 5
DEV_MODELS = (
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash-lite",
)


def strip_fences(text: str) -> str:
    """Remove enclosing markdown code fences from LLM responses."""
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\r?\n?", "", text)
    text = re.sub(r"\r?\n?```\s*$", "", text)
    return text.strip()


def parse_traceback(output: str, project_files: List[str]) -> Tuple[Optional[str], Optional[int]]:
    """Locate the most relevant project file and line number in a Python traceback."""
    pattern = re.compile(r'File ["\']([^"\']+\.py)["\'],\s+line\s+(\d+)', re.IGNORECASE)
    matches = pattern.findall(output)

    for raw_path, line_str in reversed(matches):
        raw_name = Path(raw_path).name
        for pf in project_files:
            if Path(pf).name == raw_name or pf == raw_path or raw_path.endswith(pf):
                return pf, int(line_str)

    return None, None


def classify_error(output: str) -> str:
    """Classify runtime failure into diagnostic category."""
    low = output.lower()

    if any(x in low for x in ("no module named", "modulenotfounderror")):
        return "dependency_error"

    if "syntaxerror" in low or "invalid syntax" in low:
        return "syntax_error"

    if "cannot import" in low or "importerror" in low:
        return "import_error"

    if any(x in low for x in (
        "traceback", "exception", "error:", "nameerror", "typeerror",
        "attributeerror", "valueerror", "keyerror", "indexerror",
        "zerodivisionerror", "filenotfounderror", "permissionerror",
    )):
        return "runtime_error"

    return "none"


class DevAgentService:
    """Service providing end-to-end autonomous multi-file project creation and debugging."""

    def __init__(
        self,
        settings_service: SettingsService,
        projects_dir: Optional[Path] = None,
    ) -> None:
        self._settings = settings_service
        self._projects_dir = projects_dir or DEFAULT_PROJECTS_DIR

    def execute(self, params: DevAgentParameters) -> ActionOutcomeResponse:
        """Execute autonomous multi-file project scaffolding and verification."""
        description = params.description.strip()
        language = params.language.lower().strip() or "python"
        timeout = params.timeout

        api_key = self._settings.get_api_key_for_service()
        if not api_key:
            return failed(
                "dev.agent",
                error="Gemini API key is not configured.",
                message="Please configure a Gemini API key in Settings to use the Dev Agent.",
            )

        try:
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=60_000),
            )

            # 1. Project Planning Phase
            plan = self._plan_project(client, description, language)
            proj_name = params.project_name or plan.get("project_name", "alex_project")
            proj_name = re.sub(r"[^\w\-]", "_", proj_name)
            project_dir = self._projects_dir / proj_name
            project_dir.mkdir(parents=True, exist_ok=True)

            files = plan.get("files", [])
            entry_point = plan.get("entry_point", "main.py")
            run_cmd = plan.get("run_command", f"python {entry_point}")
            dependencies = plan.get("dependencies", [])

            if not files:
                return failed(
                    "dev.agent",
                    error="Project plan returned no files to generate.",
                    message=f"Architecture planner generated an empty file list for '{proj_name}'.",
                )

            # Sort files in dependency order (fewest imports first)
            sorted_files = sorted(files, key=lambda f: len(f.get("imports", [])))
            file_codes: Dict[str, str] = {}

            # 2. File Generation Phase
            for file_info in sorted_files:
                file_path = file_info.get("path")
                if not file_path:
                    continue
                code = self._write_file(
                    client=client,
                    file_info=file_info,
                    description=description,
                    all_files=files,
                    language=language,
                    project_dir=project_dir,
                    already_written=file_codes,
                )
                file_codes[file_path] = code

            # 3. Dependency Installation Phase
            if dependencies:
                self._install_dependencies(dependencies, project_dir)

            # 4. Optional Editor Launch
            if params.open_editor:
                self._open_editor(project_dir)

            # 5. Build, Test & Auto-Fix Loop
            last_output = ""
            auto_installs = 0
            file_names = list(file_codes.keys())

            for attempt in range(1, MAX_FIX_ATTEMPTS + 1):
                last_output = self._run_project(run_cmd, project_dir, timeout)

                if "timed out" in last_output.lower():
                    # Long-running service or GUI started cleanly
                    return unverified(
                        "dev.agent",
                        f"Project '{proj_name}' started and timed out after {timeout}s (likely a long-running service/app).",
                        project_dir=str(project_dir),
                        project_name=proj_name,
                        files=file_names,
                        output=last_output,
                    )

                err_type = classify_error(last_output)
                if err_type == "none":
                    return done(
                        "dev.agent",
                        f"Project '{proj_name}' built and verified successfully in {attempt} attempt(s).",
                        data={
                            "project_name": proj_name,
                            "project_dir": str(project_dir),
                            "files": file_names,
                            "attempts": attempt,
                            "output": last_output[:2000],
                        },
                    )

                if not params.auto_fix or attempt == MAX_FIX_ATTEMPTS:
                    break

                # Self-correction handling
                if err_type == "dependency_error" and auto_installs < 3:
                    installed = self._try_auto_install(last_output, project_dir)
                    if installed:
                        auto_installs += 1
                        time.sleep(1)
                        continue

                # Fix file with LLM
                updated = self._fix_files(
                    client=client,
                    error_output=last_output,
                    description=description,
                    all_files=files,
                    file_codes=file_codes,
                    language=language,
                    project_dir=project_dir,
                    entry_point=entry_point,
                )
                file_codes.update(updated)

            return failed(
                "dev.agent",
                error=f"Unresolved errors after {MAX_FIX_ATTEMPTS} attempts: {last_output[:400]}",
                message=f"Project '{proj_name}' created at {project_dir}, but tests did not pass cleanly after {MAX_FIX_ATTEMPTS} attempts.",
                data={
                    "project_name": proj_name,
                    "project_dir": str(project_dir),
                    "files": file_names,
                    "last_error": last_output[:2000],
                },
            )

        except Exception as exc:
            logger.exception("DevAgent execution error")
            return failed("dev.agent", error=str(exc), message=f"Dev agent failed: {exc}")

    def _call_llm(self, client: genai.Client, prompt: str) -> str:
        """Call Gemini model with fallback across DEV_MODELS."""
        for model in DEV_MODELS:
            try:
                res = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=8192),
                )
                txt = (res.text or "").strip()
                if txt:
                    return txt
            except Exception as e:
                logger.debug("Dev agent model '%s' failed: %s", model, e)
        raise RuntimeError("All configured Gemini models failed for dev agent.")

    def _plan_project(self, client: genai.Client, description: str, language: str) -> Dict[str, Any]:
        """Generate architectural multi-file project plan."""
        prompt = f"""You are a senior software architect. Create a minimal, complete file plan for this project.

Language: {language}
Description: {description}

Return ONLY valid JSON — no markdown, no explanation:
{{
  "project_name": "snake_case_name",
  "entry_point": "main.py",
  "files": [
    {{
      "path": "main.py",
      "description": "Entry point — what it does and which modules it imports",
      "imports": ["utils.helpers"]
    }},
    {{
      "path": "utils/helpers.py",
      "description": "Helper utilities — what functions it exposes",
      "imports": []
    }}
  ],
  "run_command": "python main.py",
  "dependencies": []
}}
"""
        raw = self._call_llm(client, prompt)
        clean = strip_fences(raw)
        return json.loads(clean)

    def _write_file(
        self,
        client: genai.Client,
        file_info: Dict[str, Any],
        description: str,
        all_files: List[Dict[str, Any]],
        language: str,
        project_dir: Path,
        already_written: Dict[str, str],
    ) -> str:
        """Generate and save code for a specific file."""
        file_path = file_info["path"]
        file_desc = file_info.get("description", "")
        file_imports = file_info.get("imports", [])

        dep_context = ""
        for dep in file_imports:
            dep_path = dep.replace(".", "/") + ".py"
            if dep_path in already_written:
                dep_context += f"\n\n--- {dep_path} ---\n{already_written[dep_path][:2000]}"

        prompt = f"""You are a senior {language} engineer. Write production-quality code for: {file_path}
Project goal: {description}
File purpose: {file_desc}
Imports: {file_imports}
{dep_context}

Rules:
- Output ONLY raw code. Absolutely no markdown fences, no explanations.
- Write COMPLETE, RUNNABLE code.
- Ensure import paths match the project structure exactly.
"""
        code = strip_fences(self._call_llm(client, prompt))
        full_path = project_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(code, encoding="utf-8")
        return code

    def _install_dependencies(self, dependencies: List[str], project_dir: Path) -> None:
        """Install external dependencies via pip."""
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install"] + dependencies,
                capture_output=True,
                text=True,
                timeout=90,
                cwd=str(project_dir),
            )
        except Exception as exc:
            logger.warning("Dependency install encountered error: %s", exc)

    def _try_auto_install(self, error_output: str, project_dir: Path) -> bool:
        """Auto-install missing module detected in error output."""
        pattern = re.compile(r"No module named ['\"]([a-zA-Z0-9_\-\.]+)['\"]", re.IGNORECASE)
        m = pattern.search(error_output)
        if not m:
            return False
        pkg = m.group(1).replace("_", "-").split(".")[0]
        try:
            res = subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(project_dir),
            )
            return res.returncode == 0
        except Exception:
            return False

    def _open_editor(self, project_dir: Path) -> None:
        """Launch VS Code or file explorer for the project."""
        try:
            if shutil.which("code"):
                subprocess.Popen(["code", str(project_dir)])
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(project_dir)])
            elif platform.system() == "Windows":
                subprocess.Popen(["explorer", str(project_dir)])
            else:
                subprocess.Popen(["xdg-open", str(project_dir)])
        except Exception as exc:
            logger.debug("Failed opening editor for '%s': %s", project_dir, exc)

    def _run_project(self, run_command: str, project_dir: Path, timeout: int) -> str:
        """Execute project in subprocess."""
        try:
            parts = run_command.split()
            if parts and parts[0].lower() == "python":
                parts[0] = sys.executable

            res = subprocess.run(
                parts,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(project_dir),
            )
            out = []
            if res.stdout.strip():
                out.append(f"STDOUT:\n{res.stdout.strip()}")
            if res.stderr.strip():
                out.append(f"STDERR:\n{res.stderr.strip()}")
            return "\n\n".join(out) if out else "Ran cleanly with no output."
        except subprocess.TimeoutExpired:
            return f"Timed out after {timeout}s (running process)."
        except Exception as exc:
            return f"Run execution error: {exc}"

    def _fix_files(
        self,
        client: genai.Client,
        error_output: str,
        description: str,
        all_files: List[Dict[str, Any]],
        file_codes: Dict[str, str],
        language: str,
        project_dir: Path,
        entry_point: str,
    ) -> Dict[str, str]:
        """Fix broken files using LLM diagnostics."""
        error_file, error_line = parse_traceback(error_output, list(file_codes.keys()))
        fix_path = error_file or entry_point
        current_code = file_codes.get(fix_path, "")

        prompt = f"""You are an expert {language} debugger. Fix the broken file below.
Project goal: {description}
File to fix: {fix_path}
Error output:
{error_output[:2000]}

Current code:
{current_code}

Rules:
- Output ONLY the complete fixed code. No explanations, no markdown fences.
- Fix the error while preserving working logic.
"""
        fixed_code = strip_fences(self._call_llm(client, prompt))
        full_path = project_dir / fix_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(fixed_code, encoding="utf-8")
        return {fix_path: fixed_code}
