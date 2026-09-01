"""The sync client exposes every method the async client does.

README claimed parity; the 2026-09-01 review (finding C3) counted about 40
missing methods and four resources with no sync proxy at all. This test
introspects both sides so the gap can never silently reopen: every public
method on every ``*Resource`` class must exist on the corresponding
``_Sync*Proxy``, and every resource attribute on ``AsyncGatecoClient`` must
exist on ``GatecoClient``.
"""

from __future__ import annotations

import inspect

import pytest

from gateco_sdk import AsyncGatecoClient, GatecoClient
from gateco_sdk import client as client_module


def _public_methods(cls) -> set[str]:
    return {
        name for name, member in inspect.getmembers(cls)
        if not name.startswith("_") and (inspect.isfunction(member) or inspect.ismethod(member))
    }


def _resource_attrs(instance) -> dict[str, object]:
    """name -> resource object, for every non-callable public attribute that looks like a resource."""
    out = {}
    for name in dir(instance):
        if name.startswith("_"):
            continue
        try:
            value = getattr(instance, name)
        except Exception:  # noqa: BLE001
            continue
        if callable(value):
            continue
        if type(value).__name__.endswith(("Resource", "Proxy")):
            out[name] = value
    return out


@pytest.fixture
def clients():
    a = AsyncGatecoClient(base_url="http://sync-parity.test", api_key="gck_test_x")
    s = GatecoClient(base_url="http://sync-parity.test", api_key="gck_test_x")
    return a, s


def test_every_async_resource_has_a_sync_counterpart(clients):
    a, s = clients
    async_attrs = _resource_attrs(a)
    sync_attrs = _resource_attrs(s)
    assert async_attrs, "no resources found on the async client (introspection broken?)"
    missing = sorted(set(async_attrs) - set(sync_attrs))
    assert not missing, f"GatecoClient lacks resources the async client has: {missing}"


def test_every_async_method_exists_on_the_sync_proxy(clients):
    a, s = clients
    gaps: dict[str, list[str]] = {}
    for name, resource in _resource_attrs(a).items():
        proxy = getattr(s, name, None)
        if proxy is None:
            continue  # reported by the test above
        missing = sorted(_public_methods(type(resource)) - _public_methods(type(proxy)))
        if missing:
            gaps[name] = missing
        # nested sub-resources (e.g. ingest.jobs)
        for sub_name, sub in _resource_attrs(resource).items():
            sub_proxy = getattr(proxy, sub_name, None)
            if sub_proxy is None:
                gaps[f"{name}.{sub_name}"] = ["<whole sub-resource>"]
                continue
            sub_missing = sorted(_public_methods(type(sub)) - _public_methods(type(sub_proxy)))
            if sub_missing:
                gaps[f"{name}.{sub_name}"] = sub_missing
    assert not gaps, "sync client is missing methods:\n" + "\n".join(
        f"  {k}: {v}" for k, v in sorted(gaps.items())
    )


def test_sync_proxies_do_not_return_coroutines(clients):
    """A proxy method that forgets to run the coroutine hands back a coroutine object."""
    _, s = clients
    offenders = []
    for name, proxy in _resource_attrs(s).items():
        for meth in _public_methods(type(proxy)):
            fn = getattr(type(proxy), meth)
            if inspect.iscoroutinefunction(fn):
                offenders.append(f"{name}.{meth}")
    assert not offenders, offenders


def test_module_exports_both_clients():
    assert client_module.GatecoClient is GatecoClient
    assert client_module.AsyncGatecoClient is AsyncGatecoClient
