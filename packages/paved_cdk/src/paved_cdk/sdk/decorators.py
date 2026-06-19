"""SDK decorators - the lightweight, code-first consumption front end.

A Data Scientist annotates plain handler functions; each decorator records a
*registration* in the module-level :data:`REGISTRY` and returns the function
**unchanged** (so handlers stay ordinary, importable, testable callables).

``synth`` later turns these registrations into a
:class:`~paved_cdk.service.ServiceSpec`. Same intent -> same resources, exactly
as the YAML and Copier front ends.

A registration captures enough to build a :class:`~paved_cdk.service.FunctionSpec`:

* ``name``      - the function's ``__name__``.
* ``module``    - the handler module's short name (``fn.__module__`` last part),
  e.g. ``charge`` for ``handlers/charge.py``. The Lambda handler string is then
  ``"<module>.<name>"`` and the asset dir is the consumer's ``handlers`` package.
* ``kind``      - one of ``"plain" | "scheduled" | "api"``.
* ``memory`` / ``timeout`` / ``environment`` - passthrough Lambda sizing.
* ``schedule``  - EventBridge expression (``scheduled`` kind only).
* ``method`` / ``path`` - HTTP route (``api`` kind only).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

#: Every decorated handler appends one entry here at import time. ``synth`` reads
#: it after importing the consumer's ``handlers`` package. Module-level by design
#: so decoration is a pure side effect of importing the handler modules.
REGISTRY: list[Registration] = []

#: Names of declared data APIs (S3 bucket + private API Gateway). A consumer calls
#: ``data_api("scoring-data")`` at module level; ``synth`` maps each onto a
#: :class:`~paved_cdk.service.DataApiSpec`. Same module-level-side-effect model as the
#: handler decorators, so a plain ``import`` of the handlers package records them.
DATA_APIS: list[str] = []


@dataclass
class Registration:
    """One decorated handler, normalized for ``synth`` to consume."""

    name: str
    module: str
    kind: str  # "plain" | "scheduled" | "api"
    memory: int = 256
    timeout: int = 30
    environment: dict[str, str] | None = None
    schedule: str | None = None
    method: str | None = None
    path: str | None = None


def _short_module(fn: Callable[..., Any]) -> str:
    """``handlers.charge`` (or ``charge``) -> ``charge``.

    The handler module's short name doubles as the Lambda handler file stem, so
    ``build_service`` loads ``<module>.<func>`` from the ``handlers`` asset dir.
    """
    return (fn.__module__ or "").rsplit(".", 1)[-1]


def function(
    memory: int = 256,
    timeout: int = 30,
    environment: dict[str, str] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a plain (invoke-only) Lambda."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        REGISTRY.append(
            Registration(
                name=fn.__name__,
                module=_short_module(fn),
                kind="plain",
                memory=memory,
                timeout=timeout,
                environment=environment,
            )
        )
        return fn

    return decorator


def scheduled(
    expression: str,
    memory: int = 256,
    timeout: int = 30,
    environment: dict[str, str] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a Lambda triggered by an EventBridge schedule ``expression``."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        REGISTRY.append(
            Registration(
                name=fn.__name__,
                module=_short_module(fn),
                kind="scheduled",
                memory=memory,
                timeout=timeout,
                environment=environment,
                schedule=expression,
            )
        )
        return fn

    return decorator


class _Api:
    """HTTP-route decorators behind the shared private API Gateway.

    Usage: ``@api.post("/charge")``. One verb method per HTTP method; each
    records an ``api`` registration carrying the method + path.
    """

    def _route(
        self, method: str, path: str
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            REGISTRY.append(
                Registration(
                    name=fn.__name__,
                    module=_short_module(fn),
                    kind="api",
                    method=method,
                    path=path,
                )
            )
            return fn

        return decorator

    def get(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._route("GET", path)

    def post(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._route("POST", path)

    def put(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._route("PUT", path)

    def delete(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._route("DELETE", path)


#: Singleton route-decorator namespace: ``api.get/post/put/delete``.
api = _Api()


def data_api(name: str = "data-api") -> None:
    """Declare an encrypted S3 data bucket fronted by a private API Gateway.

    Not a decorator - a plain module-level call (``data_api("scoring-data")``) since
    storage is not a handler. Records the name for ``synth`` to map onto a
    :class:`~paved_cdk.service.DataApiSpec`.
    """
    DATA_APIS.append(name)


__all__ = ["REGISTRY", "DATA_APIS", "Registration", "function", "scheduled", "api", "data_api"]
