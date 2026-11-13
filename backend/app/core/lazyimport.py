"""
Lazy Module Loading Utility (TASK-P7-02 / CAT-35).

Provides high-performance, thread-safe lazy module proxying (PEP 690 semantics)
to defer heavy package imports (faster-whisper, openwakeword, piper, cv2, playwright, qrcode,
pypdf, docx, openpyxl, pptx, yt_dlp) until attribute access or first functional invocation.

Reduces cold-boot sidecar startup latency by eliminating synchronous module graph evaluation.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
import threading
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

logger = logging.getLogger(__name__)

# List of heavy third-party modules eligible for lazy installation
DEFAULT_LAZY_MODULES: List[str] = [
    "cv2",
    "playwright",
    "faster_whisper",
    "openwakeword",
    "piper",
    "qrcode",
    "pypdf",
    "docx",
    "openpyxl",
    "pptx",
    "yt_dlp",
]


class LazyModule(ModuleType):
    """Transparent proxy module that defers actual import until first attribute access."""

    def __init__(
        self,
        name: str,
        package: Optional[str] = None,
        spec: Optional[Any] = None,
    ) -> None:
        super().__init__(name)
        object.__setattr__(self, "_lazy_name", name)
        object.__setattr__(self, "_lazy_package", package)
        object.__setattr__(self, "_real_module", None)
        object.__setattr__(self, "_load_lock", threading.RLock())

        # Resolve spec if not provided to preserve importlib.util.find_spec behavior
        resolved_spec = spec
        if resolved_spec is None:
            try:
                resolved_spec = importlib.util.find_spec(name, package)
            except Exception:
                resolved_spec = None

        object.__setattr__(self, "_lazy_spec", resolved_spec)
        if resolved_spec is not None:
            object.__setattr__(self, "__spec__", resolved_spec)
            if (
                hasattr(resolved_spec, "submodule_search_locations")
                and resolved_spec.submodule_search_locations is not None
            ):
                object.__setattr__(self, "__path__", resolved_spec.submodule_search_locations)
            if hasattr(resolved_spec, "origin") and resolved_spec.origin is not None:
                object.__setattr__(self, "__file__", resolved_spec.origin)

    def _load(self) -> ModuleType:
        """Atomically import and bind the underlying real module."""
        real = object.__getattribute__(self, "_real_module")
        if real is not None:
            return real

        lock = object.__getattribute__(self, "_load_lock")
        with lock:
            real = object.__getattribute__(self, "_real_module")
            if real is not None:
                return real

            name = object.__getattribute__(self, "_lazy_name")
            package = object.__getattribute__(self, "_lazy_package")

            logger.debug("LazyModule: Materializing deferred module '%s'...", name)

            # Evict self from sys.modules if present to avoid recursion
            current_in_sys = sys.modules.get(name)
            is_registered_in_sys = current_in_sys is self
            if is_registered_in_sys:
                del sys.modules[name]

            try:
                real = importlib.import_module(name, package)
                sys.modules[name] = real
            except Exception:
                if is_registered_in_sys:
                    sys.modules[name] = self
                raise

            object.__setattr__(self, "_real_module", real)

            # Mirror __dict__ for fast subsequent attribute lookups
            self.__dict__.update(real.__dict__)
            return real

    def is_loaded(self) -> bool:
        """Check if the target module has been imported."""
        return object.__getattribute__(self, "_real_module") is not None

    def __getattr__(self, item: str) -> Any:
        # Standard special attributes check before loading if possible
        if item in ("_lazy_name", "_lazy_package", "_real_module", "_load_lock", "_lazy_spec"):
            return object.__getattribute__(self, item)
        module = self._load()
        return getattr(module, item)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in (
            "_lazy_name",
            "_lazy_package",
            "_real_module",
            "_load_lock",
            "_lazy_spec",
            "__spec__",
            "__path__",
            "__file__",
            "__name__",
            "__doc__",
        ):
            object.__setattr__(self, name, value)
            return
        module = self._load()
        setattr(module, name, value)
        self.__dict__[name] = value

    def __dir__(self) -> List[str]:
        module = self._load()
        return dir(module)

    def __repr__(self) -> str:
        real = object.__getattribute__(self, "_real_module")
        if real is not None:
            return repr(real)
        name = object.__getattribute__(self, "_lazy_name")
        return f"<LazyModule '{name}' (not loaded)>"


class LazyCallable:
    """Defers module import and attribute resolution until the function is invoked."""

    def __init__(self, module_name: str, attribute_name: str) -> None:
        self._module_name = module_name
        self._attribute_name = attribute_name
        self._resolved: Optional[Callable[..., Any]] = None
        self._lock = threading.Lock()

    def _resolve(self) -> Callable[..., Any]:
        if self._resolved is not None:
            return self._resolved

        with self._lock:
            if self._resolved is not None:
                return self._resolved
            mod = importlib.import_module(self._module_name)
            fn = getattr(mod, self._attribute_name)
            self._resolved = fn
            return fn

    def is_loaded(self) -> bool:
        """Check if the underlying callable has been imported."""
        return self._resolved is not None

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        fn = self._resolve()
        return fn(*args, **kwargs)

    def __repr__(self) -> str:
        status = "loaded" if self._resolved is not None else "not loaded"
        return f"<LazyCallable '{self._module_name}.{self._attribute_name}' ({status})>"


def lazy_import(name: str, package: Optional[str] = None) -> LazyModule:
    """Return a transparent lazy proxy for a module name."""
    return LazyModule(name, package)


def lazy_callable(module_name: str, attribute_name: str) -> LazyCallable:
    """Return a transparent lazy proxy for a callable attribute inside a module."""
    return LazyCallable(module_name, attribute_name)


def install_lazy_module(name: str) -> Optional[LazyModule]:
    """
    Install a LazyModule into sys.modules if the package is installed and not yet loaded.
    Returns the LazyModule instance, or None if the module is already loaded or not found.
    """
    existing = sys.modules.get(name)
    if existing is not None:
        if isinstance(existing, LazyModule):
            return existing
        # Already fully loaded
        return None

    try:
        spec = importlib.util.find_spec(name)
        if spec is None:
            return None
    except Exception:
        return None

    lazy = LazyModule(name, spec=spec)
    sys.modules[name] = lazy
    logger.debug("Installed LazyModule for '%s' into sys.modules", name)
    return lazy


def install_lazy_modules(names: Sequence[str] = DEFAULT_LAZY_MODULES) -> Dict[str, bool]:
    """
    Install lazy module proxies into sys.modules for a collection of module names.
    Returns a dictionary mapping module names to whether a LazyModule was installed.
    """
    results: Dict[str, bool] = {}
    for name in names:
        lazy = install_lazy_module(name)
        results[name] = lazy is not None
    return results


def preload_modules(names: List[str]) -> Dict[str, bool]:
    """Background helper to trigger materialization of lazy modules."""
    results: Dict[str, bool] = {}
    for name in names:
        try:
            mod = sys.modules.get(name)
            if isinstance(mod, LazyModule):
                mod._load()
            else:
                importlib.import_module(name)
            results[name] = True
        except Exception as exc:
            logger.debug("Preload for %s failed: %s", name, exc)
            results[name] = False
    return results
