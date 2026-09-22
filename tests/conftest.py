"""Tests must never read or change the developer's OS credential store."""
from types import SimpleNamespace

import pytest

from evren_agent import credentials


@pytest.fixture(autouse=True)
def credential_store(monkeypatch):
    values = {}
    backend = SimpleNamespace(
        get_password=lambda service, account: values.get((service, account)),
        set_password=lambda service, account, value: values.__setitem__((service, account), value),
        values=values,
        native_lookup=credentials._backend,
    )
    monkeypatch.setattr(credentials, "_backend", lambda: backend)
    return backend
