#!/usr/bin/env python3
"""Render a consumer's one-time bootstrap fileset for a chosen consumption variant.

The platform onboarding workflow runs this and opens a SINGLE PR into the consumer
repo (the platform writes once; thereafter updates are dependency pin bumps). The
heavy platform code is NEVER copied — only this thin, consumer-owned bootstrap.

Usage:
  onboard.py --variant {sdk|declarative|copier} --out DIR \
      --project-name "Payments" --service-id f-payments --owner team@example.com \
      --team ds --cost-center 4711 --platform-repo michaelfecher/paved-cdk \
      --platform-version v0.2.0
"""

from __future__ import annotations

import argparse
import json
import pathlib

VARIANTS = ("sdk", "declarative", "copier")


def _w(base: pathlib.Path, rel: str, content: str) -> None:
    p = base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content if content.endswith("\n") else content + "\n")


def _common(base: pathlib.Path, a: argparse.Namespace, cdk_app: str) -> None:
    _w(base, "pyproject.toml", f"""\
[project]
name = "{a.project_name.lower().replace(' ', '-')}"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["paved-cdk"]

[tool.uv.sources]
paved-cdk = {{ git = "https://github.com/{a.platform_repo}.git", tag = "{a.platform_version}", subdirectory = "packages/paved_cdk" }}
""")
    _w(base, "cdk.json", json.dumps({"app": cdk_app}, indent=2))
    _w(base, ".github/workflows/deploy.yml", f"""\
# Thin caller — NO AWS config. Platform owns deploy auth (ADR 0011).
name: deploy
on:
  push: {{ branches: [main], tags: ["v*"] }}
  pull_request: {{ types: [opened, synchronize, reopened, closed] }}
jobs:
  cdk:
    uses: {a.platform_repo}/.github/workflows/cdk-deploy.yml@{a.platform_version}
    with: {{ stack_name: {a.service_id} }}
""")
    _w(base, "notebooks/report.ipynb", json.dumps(
        {"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}))
    _w(base, "README.md", f"# {a.project_name}\n\nScaffolded by the platform (variant: {a.variant}). "
       f"Write your compute code under `handlers/` and `notebooks/`. "
       f"CDK runs only in CI; platform updates are dependency pin bumps.\n")


def render(a: argparse.Namespace) -> pathlib.Path:
    base = pathlib.Path(a.out)
    tags = f'{{"Owner": "{a.owner}", "Team": "{a.team}", "CostCenter": "{a.cost_center}"}}'

    if a.variant == "sdk":
        _common(base, a, cdk_app="python app.py")
        _w(base, "app.py", "from paved_cdk.sdk import synth\n\nsynth()\n")
        _w(base, "handlers/__init__.py", "")
        _w(base, "handlers/charge.py", 'from paved_cdk.sdk import api\n\n\n'
           '@api.post("/charge")\ndef charge(event, context):\n    return {"statusCode": 200}\n')
        _w(base, "handlers/nightly.py", 'from paved_cdk.sdk import scheduled\n\n\n'
           '@scheduled("rate(1 day)")\ndef nightly(event, context):\n    return {"ok": True}\n')

    elif a.variant == "declarative":
        _common(base, a, cdk_app="paved-cdk-synth")
        _w(base, "service.yaml", f"""\
service_id: {a.service_id}
owner: {a.owner}
functions:
  - name: charge
    handler: charge.charge
    api: {{ method: POST, path: /charge }}
  - name: nightly
    handler: nightly.nightly
    schedule: "rate(1 day)"
""")
        _w(base, "handlers/charge.py", 'def charge(event, context):\n    return {"statusCode": 200}\n')
        _w(base, "handlers/nightly.py", 'def nightly(event, context):\n    return {"ok": True}\n')

    elif a.variant == "copier":
        _common(base, a, cdk_app="python app.py")
        _w(base, "app.py", f'''\
"""Explicit model — you own this Python and declare resources directly."""
import aws_cdk as cdk
from paved_cdk import PlatformStack
from paved_cdk.service import ServiceSpec, FunctionSpec, NotebookSpec, ApiRoute, build_service

app = cdk.App()
stack = PlatformStack(app, "{a.service_id}", tags={tags})
build_service(stack, ServiceSpec(
    functions=[
        FunctionSpec(name="charge", code_path="handlers", handler="charge.charge",
                     api=ApiRoute("POST", "/charge")),
        FunctionSpec(name="nightly", code_path="handlers", handler="nightly.nightly",
                     schedule="rate(1 day)"),
    ],
    notebooks=[NotebookSpec(name="report", path="notebooks/report.ipynb")],
))
app.synth()
''')
        _w(base, "handlers/charge.py", 'def charge(event, context):\n    return {"statusCode": 200}\n')
        _w(base, "handlers/nightly.py", 'def nightly(event, context):\n    return {"ok": True}\n')
    else:
        raise SystemExit(f"unknown variant {a.variant!r} (one of {VARIANTS})")
    return base


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--variant", required=True, choices=VARIANTS)
    p.add_argument("--out", required=True)
    p.add_argument("--project-name", dest="project_name", default="My Service")
    p.add_argument("--service-id", dest="service_id", default="f-myservice")
    p.add_argument("--owner", default="team@example.com")
    p.add_argument("--team", default="ds")
    p.add_argument("--cost-center", dest="cost_center", default="4711")
    p.add_argument("--platform-repo", dest="platform_repo", default="michaelfecher/paved-cdk")
    p.add_argument("--platform-version", dest="platform_version", default="v0.2.0")
    a = p.parse_args()
    base = render(a)
    print(f"rendered {a.variant} bootstrap → {base}")


if __name__ == "__main__":
    main()
