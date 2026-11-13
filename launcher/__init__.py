"""Alex Unified Application Launcher.

Provides a single CLI interface to start, stop, check, and manage
the complete Alex desktop assistant stack (FastAPI backend, React frontend,
and Electron desktop shell).
"""

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

__version__ = "0.1.0"
