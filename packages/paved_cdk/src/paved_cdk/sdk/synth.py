"""SDK synth entrypoint - the consumer's ``app.py`` calls :func:`synth`.

It is the SDK front end's convergence onto the shared service contract:

1. Derive governance tags from ``PAVED_CDK_*`` env vars.
2. Create the ``cdk.App`` and one :class:`~paved_cdk.PlatformStack`.
3. Import the consumer's ``handlers`` package (every ``handlers.*`` submodule)
   so the decorators run and fill :data:`~paved_cdk.sdk.decorators.REGISTRY`.
4. Translate the registry (+ auto-discovered ``notebooks/*.ipynb``) into a
   :class:`~paved_cdk.service.ServiceSpec`.
5. Hand it to :func:`~paved_cdk.service.build_service`, then ``app.synth()``.

This keeps consumers to a two-line ``app.py`` while reusing the exact same
governed resource builder as the YAML and Copier front ends.
"""

from __future__ import annotations

import importlib
import logging
import os
import pkgutil
import re
from pathlib import Path

import aws_cdk as cdk

from .. import PlatformStack
from ..service import (
    ApiRoute,
    DataApiSpec,
    FunctionSpec,
    NotebookSpec,
    ServiceSpec,
    build_service,
)
from .decorators import DATA_APIS, REGISTRY, Registration

logger = logging.getLogger(__name__)

#: Asset directory (consumer-owned) holding handler modules and the Python
#: package ``synth`` imports to trigger decoration.
HANDLERS_PKG = "handlers"
NOTEBOOKS_DIR = "notebooks"


def _tags() -> dict[str, str]:
    """Governance tags from env (PlatformStack requires Owner/Team/CostCenter)."""
    return {
        "Owner": os.environ.get("PAVED_CDK_OWNER", "ds@example.com"),
        "Team": os.environ.get("PAVED_CDK_TEAM", "ds"),
        "CostCenter": os.environ.get("PAVED_CDK_COST_CENTER", "4711"),
    }


def _sanitize(name: str) -> str:
    """CDK-safe FunctionSpec name: alnum/underscore, never empty.

    ``build_service`` further derives the construct id; we only need the source
    name to be free of characters CDK cannot carry through.
    """
    cleaned = re.sub(r"[^0-9A-Za-z_]", "_", name).strip("_")
    return cleaned or "Handler"


def _import_handlers() -> None:
    """Import the consumer's ``handlers`` package and every submodule.

    Importing each ``handlers.*`` module executes the decorators, populating
    :data:`REGISTRY`. Missing/empty packages degrade gracefully (logged, not
    fatal) so a notebooks-only service still synths.
    """
    try:
        pkg = importlib.import_module(HANDLERS_PKG)
    except ModuleNotFoundError:
        logger.warning("No '%s' package found; no decorated handlers to register.", HANDLERS_PKG)
        return

    for mod in pkgutil.iter_modules(pkg.__path__, prefix=f"{HANDLERS_PKG}."):
        try:
            importlib.import_module(mod.name)
        except Exception:  # noqa: BLE001 - one bad handler must not sink the synth
            logger.exception("Failed importing handler module '%s'; skipping.", mod.name)


def _function_spec(reg: Registration) -> FunctionSpec:
    """Map one registration onto a FunctionSpec on the shared contract."""
    return FunctionSpec(
        name=_sanitize(reg.name),
        code_path=HANDLERS_PKG,
        handler=f"{reg.module}.{reg.name}",
        memory_mb=reg.memory,
        timeout_seconds=reg.timeout,
        schedule=reg.schedule,
        api=ApiRoute(method=reg.method, path=reg.path) if reg.kind == "api" else None,
        environment=reg.environment,
    )


def _discover_notebooks() -> list[NotebookSpec]:
    """Auto-discover ``notebooks/*.ipynb`` as scheduled notebook runners."""
    nb_dir = Path(NOTEBOOKS_DIR)
    if not nb_dir.is_dir():
        return []
    specs: list[NotebookSpec] = []
    for ipynb in sorted(nb_dir.glob("*.ipynb")):
        specs.append(
            NotebookSpec(name=_sanitize(ipynb.stem), path=f"{NOTEBOOKS_DIR}/{ipynb.name}")
        )
    return specs


def _build_spec() -> ServiceSpec:
    functions = [_function_spec(reg) for reg in REGISTRY]
    notebooks = _discover_notebooks()
    data_apis = [DataApiSpec(name=name) for name in DATA_APIS]
    logger.info(
        "SDK spec: %d function(s), %d notebook(s), %d data api(s).",
        len(functions),
        len(notebooks),
        len(data_apis),
    )
    return ServiceSpec(functions=functions, notebooks=notebooks, data_apis=data_apis)


def synth(
    *,
    service: str | None = None,
    tags: dict[str, str] | None = None,
) -> cdk.App:
    """Build and synthesize the SDK-defined service. Returns the App (testable).

    ``service`` (stack id) and ``tags`` default to the ``PAVED_CDK_*`` env vars, so
    the scaffolded ``app.py`` can pass the project's identity explicitly while CI can
    still override via the environment.
    """
    app = cdk.App()
    stack = PlatformStack(
        app,
        service or os.environ.get("PAVED_CDK_SERVICE", "payments"),
        tags=tags or _tags(),
    )

    _import_handlers()
    spec = _build_spec()
    build_service(stack, spec)

    app.synth()
    return app


__all__ = ["synth"]
