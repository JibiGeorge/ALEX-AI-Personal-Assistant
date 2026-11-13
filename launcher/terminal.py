import os
import sys
import time
from dataclasses import dataclass
from typing import Sequence

# Color support detection
_COLOR_ENABLED = (
    "NO_COLOR" not in os.environ
    and (
        sys.stdout.isatty()
        or os.environ.get("TERM") in ("xterm", "xterm-256color", "vt100", "screen")
        or os.environ.get("WT_SESSION") is not None
        or os.environ.get("COLORTERM") is not None
        or sys.platform == "win32"
    )
)


def _c(code: str, text: str) -> str:
    if not _COLOR_ENABLED:
        return text
    return f"\033[{code}m{text}\033[0m"


def cyan(text: str) -> str:
    return _c("36", text)


def bright_cyan(text: str) -> str:
    return _c("96", text)


def green(text: str) -> str:
    return _c("32", text)


def bright_green(text: str) -> str:
    return _c("92", text)


def yellow(text: str) -> str:
    return _c("33", text)


def red(text: str) -> str:
    return _c("31", text)


def bright_red(text: str) -> str:
    return _c("91", text)


def bold(text: str) -> str:
    return _c("1", text)


def dim(text: str) -> str:
    return _c("2", text)


@dataclass
class ServiceStatusEntry:
    name: str
    status: str
    port: str
    pid: str
    target: str


def print_banner(version: str = "0.1.0") -> None:
    banner = f"""
{bright_cyan("  █████╗ ██╗     ███████╗██╗  ██╗")}
{bright_cyan(" ██╔══██╗██║     ██╔════╝╚██╗██╔╝")}
{bright_cyan(" ███████║██║     █████╗   ╚███╔╝ ")}
{bright_cyan(" ██╔══██║██║     ██╔══╝   ██╔██╗ ")}
{bright_cyan(" ██║  ██║███████╗███████╗██╔╝ ██╗")}
{bright_cyan(" ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝")}
  {bold("Alex Desktop Assistant")} {dim(f"v{version}")}
  {dim("Unified Application Launcher")}
"""
    print(banner)


def print_step(step: int, total: int, message: str, status: str = "", detail: str = "") -> None:
    prefix = cyan(f" [{step}/{total}]")
    padded_msg = f"{message:<46}"

    if status.upper() in ("OK", "PASS", "HEALTHY", "READY", "ONLINE"):
        badge = bright_green(f"[{status.upper()}]")
    elif status.upper() in ("WARN", "WARNING"):
        badge = yellow(f"[{status.upper()}]")
    elif status.upper() in ("FAIL", "ERROR", "CRITICAL"):
        badge = bright_red(f"[{status.upper()}]")
    elif status.upper() in ("WAIT", "STARTING", "PENDING"):
        badge = cyan(f"[{status.upper()}]")
    else:
        badge = f"[{status}]" if status else ""

    extra = f"  {dim(detail)}" if detail else ""
    print(f"{prefix} {padded_msg} {badge}{extra}")


def print_info(message: str) -> None:
    print(f" {cyan('i')} {message}")


def print_success(message: str) -> None:
    print(f" {bright_green('✔')} {message}")


def print_warning(message: str) -> None:
    print(f" {yellow('!')} {message}")


def print_error(message: str, detail: str = "") -> None:
    print(f"\n {bright_red('✖ Error:')} {bold(message)}")
    if detail:
        print(f"   {dim(detail)}")


def print_summary_table(services: Sequence[ServiceStatusEntry], startup_duration: float | None = None) -> None:
    divider = dim(" ────────────────────────────────────────────────────────────────────────")
    header = (
        f"  {bold('Service'):<16} "
        f"{bold('Status'):<10} "
        f"{bold('Port'):<8} "
        f"{bold('PID'):<8} "
        f"{bold('Target')}"
    )

    print(f"\n{divider}")
    print(header)
    print(divider)

    for s in services:
        status_colored = (
            bright_green(f"{s.status:<10}")
            if s.status.upper() in ("ONLINE", "HEALTHY", "RUNNING")
            else yellow(f"{s.status:<10}")
            if s.status.upper() in ("WAITING", "DEGRADED")
            else bright_red(f"{s.status:<10}")
        )
        line = (
            f"  {cyan(s.name):<25} "
            f"{status_colored} "
            f"{dim(s.port):<17} "
            f"{dim(s.pid):<17} "
            f"{s.target}"
        )
        print(line)

    print(f"{divider}\n")
    if startup_duration is not None:
        print(f"  {bright_green('✔')} Startup completed in {bold(f'{startup_duration:.2f}s')}.")
        print(f"  {dim('Press Ctrl+C to stop all services cleanly.')}\n")

