"""Parse a declarative ``service.yaml`` (+ ``notebooks/*.ipynb``) into a ServiceSpec.

This is the *only* place that knows the YAML shape; everything downstream consumes
the shared :class:`~paved_cdk.service.ServiceSpec` contract, guaranteeing that a
manifest yields exactly the same governed resources as the SDK or Copier frontends.
"""

from __future__ import annotations

import glob
import logging
import os

import yaml

from ..service import ApiRoute, FunctionSpec, NotebookSpec, ServiceSpec

log = logging.getLogger(__name__)

#: Consumer-owned handler code lives here, relative to the manifest's directory.
HANDLERS_DIR = "handlers"
#: Auto-discovered notebooks live here.
NOTEBOOKS_DIR = "notebooks"


def _function_from(entry: dict) -> FunctionSpec:
    """Map one ``functions:`` list entry to a :class:`FunctionSpec`.

    ``handler`` defaults to ``"<name>.<name>"`` (module = handler file, callable =
    same-named function) and every function's asset is the shared ``handlers`` dir.
    """
    name = entry["name"]
    handler = entry.get("handler") or f"{name}.{name}"

    api_entry = entry.get("api")
    api = ApiRoute(method=api_entry["method"], path=api_entry["path"]) if api_entry else None

    # ``memory`` is the manifest key; the spec field is ``memory_mb``.
    kwargs: dict = {}
    if "memory" in entry:
        kwargs["memory_mb"] = entry["memory"]
    if "timeout_seconds" in entry:
        kwargs["timeout_seconds"] = entry["timeout_seconds"]

    return FunctionSpec(
        name=name,
        code_path=HANDLERS_DIR,
        handler=handler,
        schedule=entry.get("schedule"),
        api=api,
        **kwargs,
    )


def _discover_notebooks() -> list[NotebookSpec]:
    """Auto-discover ``notebooks/*.ipynb`` in the cwd as scheduled runners."""
    notebooks: list[NotebookSpec] = []
    for path in sorted(glob.glob(os.path.join(NOTEBOOKS_DIR, "*.ipynb"))):
        stem = os.path.splitext(os.path.basename(path))[0]
        notebooks.append(NotebookSpec(name=stem, path=path))
        log.debug("discovered notebook %s -> %s", stem, path)
    return notebooks


def load(path: str = "service.yaml") -> ServiceSpec:
    """Read a manifest (relative to cwd) and return a :class:`ServiceSpec`.

    The manifest's ``service_id`` and ``owner`` are not part of the ServiceSpec —
    they steer the stack id / governance tags and are read by :mod:`.synth`.
    """
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    functions = [_function_from(entry) for entry in data.get("functions", [])]
    notebooks = _discover_notebooks()

    log.info(
        "loaded manifest %s: service_id=%s functions=%d notebooks=%d",
        path,
        data.get("service_id"),
        len(functions),
        len(notebooks),
    )
    return ServiceSpec(functions=functions, notebooks=notebooks)


def read_meta(path: str = "service.yaml") -> dict:
    """Return the top-level manifest metadata (``service_id``, ``owner``)."""
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return {"service_id": data.get("service_id"), "owner": data.get("owner")}
