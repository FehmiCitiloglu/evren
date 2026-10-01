"""Tests must never read or change the developer's OS credential store."""
from types import SimpleNamespace
import gc

import pytest

from evren_agent import credentials


@pytest.fixture(autouse=True)
def collect_gui_objects_on_main_thread(request):
    if not request.node.path.name.startswith("test_ui"):
        yield
        return
    # Destroyed Tk widgets and fonts form reference cycles. Dispose of the
    # previous interpreter before opening another one, and never let an API
    # worker finalize those objects while a test window is alive.
    gc.collect()
    enabled = gc.isenabled()
    gc.disable()
    try:
        yield
    finally:
        gc.collect()
        if enabled:
            gc.enable()


@pytest.fixture(autouse=True)
def credential_store(monkeypatch):
    values = {}
    backend = SimpleNamespace(
        get_password=lambda service, account: values.get((service, account)),
        set_password=lambda service, account, value: values.__setitem__((service, account), value),
        delete_password=lambda service, account: values.pop((service, account), None),
        values=values,
        native_lookup=credentials._backend,
    )
    monkeypatch.setattr(credentials, "_backend", lambda: backend)
    return backend
