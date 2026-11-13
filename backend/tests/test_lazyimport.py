"""
Unit tests for Lazy Module Loading Utility (TASK-P7-02 / CAT-35).

Verifies PEP 690-style deferred module proxying, transparent attribute access,
thread safety, LazyCallable wrapping, and sys.modules installation.
"""

from __future__ import annotations

import concurrent.futures
import sys
from types import ModuleType
from typing import Any

import pytest

from app.core.lazyimport import (
    DEFAULT_LAZY_MODULES,
    LazyCallable,
    LazyModule,
    install_lazy_module,
    install_lazy_modules,
    lazy_callable,
    lazy_import,
    preload_modules,
)


def test_lazy_module_deferred_loading() -> None:
    """Verify that LazyModule does not load underlying module until attribute dereference."""
    lazy_csv = LazyModule("csv")
    assert not lazy_csv.is_loaded()
    assert "<LazyModule 'csv' (not loaded)>" in repr(lazy_csv)

    # First attribute dereference materializes module
    reader = getattr(lazy_csv, "reader")
    assert callable(reader)
    assert lazy_csv.is_loaded()
    assert "module 'csv'" in repr(lazy_csv)


def test_lazy_module_subsequent_attribute_access() -> None:
    """Verify that once loaded, attributes are cached and behave identically to the real module."""
    lazy_math = LazyModule("math")
    assert not lazy_math.is_loaded()

    # Dereference pi
    pi_val = lazy_math.pi
    assert abs(pi_val - 3.14159) < 0.001
    assert lazy_math.is_loaded()

    # Second dereference should use cached module
    sin_zero = lazy_math.sin(0)
    assert sin_zero == 0.0


def test_lazy_module_setattr_and_dir() -> None:
    """Verify __setattr__ and __dir__ delegation on LazyModule."""
    lazy_json = LazyModule("json")
    assert not lazy_json.is_loaded()

    # Calling dir() should materialize and return module contents
    entries = dir(lazy_json)
    assert "dumps" in entries
    assert "loads" in entries
    assert lazy_json.is_loaded()

    # Setting custom attribute should pass through to module dict
    lazy_json.CUSTOM_KEY = "test_custom_value"
    assert getattr(lazy_json, "CUSTOM_KEY") == "test_custom_value"


def test_lazy_callable_deferred_execution() -> None:
    """Verify LazyCallable defers module import and resolves callable at call time."""
    fn = lazy_callable("math", "cos")
    assert isinstance(fn, LazyCallable)
    assert not fn.is_loaded()
    assert "not loaded" in repr(fn)

    # Invoke callable
    res = fn(0)
    assert res == 1.0
    assert fn.is_loaded()
    assert "loaded" in repr(fn)


def test_lazy_module_thread_safety() -> None:
    """Verify that multiple concurrent threads accessing a LazyModule do not race or fail."""
    lazy_hashlib = LazyModule("hashlib")
    assert not lazy_hashlib.is_loaded()

    def worker(i: int) -> str:
        # Access sha256 and compute hash
        h = lazy_hashlib.sha256(f"thread_{i}".encode("utf-8")).hexdigest()
        return h

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker, i) for i in range(20)]
        results = [f.result() for f in futures]

    assert len(results) == 20
    assert lazy_hashlib.is_loaded()


def test_lazy_module_nonexistent_attribute_error() -> None:
    """Verify that non-existent attributes raise standard AttributeError."""
    lazy_math = LazyModule("math")
    with pytest.raises(AttributeError):
        _ = lazy_math.non_existent_function_xyz_123()


def test_lazy_module_unimportable_module_error() -> None:
    """Verify that importing an unimportable module raises ModuleNotFoundError on access."""
    lazy_ghost = LazyModule("non_existent_module_abc_xyz")
    with pytest.raises(ModuleNotFoundError):
        _ = lazy_ghost.some_attribute


def test_preload_modules() -> None:
    """Verify preload_modules materializes specified modules and handles missing ones."""
    lazy_time = LazyModule("time")
    sys.modules["_test_lazy_time"] = lazy_time

    try:
        report = preload_modules(["_test_lazy_time", "non_existent_pkg_definitely_missing"])
        assert report["_test_lazy_time"] is True
        assert lazy_time.is_loaded()
        assert report["non_existent_pkg_definitely_missing"] is False
    finally:
        sys.modules.pop("_test_lazy_time", None)


def test_install_lazy_module_and_modules() -> None:
    """Verify install_lazy_module inserts LazyModule into sys.modules."""
    # Test nonexistent package
    assert install_lazy_module("non_existent_package_12345") is None

    # Test default lazy module list contains expected heavy packages
    assert "faster_whisper" in DEFAULT_LAZY_MODULES
    assert "openwakeword" in DEFAULT_LAZY_MODULES
    assert "qrcode" in DEFAULT_LAZY_MODULES
    assert "pypdf" in DEFAULT_LAZY_MODULES

    # Test install_lazy_modules bulk run
    results = install_lazy_modules(["pypdf", "qrcode"])
    assert isinstance(results, dict)
    assert "pypdf" in results
    assert "qrcode" in results


def test_create_app_defers_heavy_dependencies() -> None:
    """Verify that backend application creation defers heavy AI/media modules."""
    from fastapi.testclient import TestClient
    from app.main import create_app

    app = create_app(api_token="lazy-test-token")
    client = TestClient(app)

    # Health endpoint works without materializing heavy packages
    res = client.get("/api/v1/health", headers={"Authorization": "Bearer lazy-test-token"})
    assert res.status_code == 200

    # Ensure heavy modules are registered as LazyModules and unmaterialized
    for mod_name in ("qrcode", "pypdf", "docx", "openpyxl"):
        mod = sys.modules.get(mod_name)
        if mod is not None and isinstance(mod, LazyModule):
            assert not mod.is_loaded(), f"Module {mod_name} should remain unmaterialized on health check"

    # Triggering dashboard pairing code materializes qrcode on demand
    pairing = app.state.dashboard_service.generate_pairing_info()
    assert pairing.pairing_code
    assert pairing.qr_data_uri.startswith("data:image/png;base64,")

    # Now qrcode is materialized while others remain deferred
    qrcode_mod = sys.modules.get("qrcode")
    assert qrcode_mod is not None
    if isinstance(qrcode_mod, LazyModule):
        assert qrcode_mod.is_loaded()

