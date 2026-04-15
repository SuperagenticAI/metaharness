from __future__ import annotations

import importlib
import inspect
from typing import Any


def create_backend_from_factory(
    factory_ref: str,
    *,
    backend_name: str,
    project: Any,
    options: dict[str, Any],
):
    factory = _load_factory(factory_ref)
    backend = _call_factory(
        factory,
        {
            "backend_name": backend_name,
            "project": project,
            "options": dict(options),
        },
    )
    _validate_backend(backend=backend, factory_ref=factory_ref)
    return backend


def _load_factory(factory_ref: str):
    text = str(factory_ref).strip()
    if ":" not in text:
        raise ValueError(f"invalid backend plugin factory reference {factory_ref!r}; expected 'module:callable'")
    module_name, _, attr_name = text.partition(":")
    module_name = module_name.strip()
    attr_name = attr_name.strip()
    if not module_name or not attr_name:
        raise ValueError(f"invalid backend plugin factory reference {factory_ref!r}; expected 'module:callable'")
    module = importlib.import_module(module_name)
    if not hasattr(module, attr_name):
        raise ValueError(f"backend plugin factory {factory_ref!r} not found")
    return getattr(module, attr_name)


def _call_factory(factory: Any, kwargs: dict[str, Any]):
    if not callable(factory):
        raise ValueError("backend plugin factory must be callable")

    signature = inspect.signature(factory)
    accepts_var_kwargs = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values()
    )
    if accepts_var_kwargs:
        return factory(**kwargs)

    accepted = {key: value for key, value in kwargs.items() if key in signature.parameters}
    return factory(**accepted)


def _validate_backend(*, backend: Any, factory_ref: str) -> None:
    if backend is None:
        raise ValueError(f"backend plugin factory {factory_ref!r} returned None")

    missing: list[str] = []
    for method_name in ("prepare", "invoke", "collect"):
        method = getattr(backend, method_name, None)
        if not callable(method):
            missing.append(method_name)
    if not hasattr(backend, "name"):
        missing.append("name")

    if missing:
        missing_fields = ", ".join(missing)
        raise ValueError(f"backend plugin factory {factory_ref!r} returned invalid backend; missing {missing_fields}")
