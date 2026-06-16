# ADR 0001 — Pure-Python CDK construct library (no JSII)

- Status: Accepted
- Date: 2026-05-27

## Context

The construct library targets Data Scientists who write Python. We could author it
in TypeScript + JSII to publish to multiple languages (Python, TS, Java), or as a
plain Python package.

## Decision

Author and publish as a **pure Python package**. No JSII, no TypeScript.

## Consequences

- Idiomatic Python API: dataclasses, real type hints, keyword args, `| None`.
- Simplest possible toolchain for the team (one language, `uv`).
- **Trade-off:** TypeScript/Java teams (e.g. the UVV project, which uses CDK in
  TypeScript) cannot consume this library — adopting it elsewhere would be a
  rewrite, not a wrapper. Accepted because the target audience is Python-only.
- If polyglot consumption becomes a hard requirement, revisit by re-authoring in
  JSII (which would constrain the API: no Python dataclasses as public types,
  limited typing).
- **Honest scope of "no Node":** this decision removes TypeScript/JSII *authoring* —
  the library and `app.synth()` are pure Python. It does **not** remove Node.js from
  the AWS **CDK CLI** (`cdk deploy` / `bootstrap` / `diff`), which is itself a Node
  application. Practically: authoring, `cdk synth`, and tests are Node-free (run via
  `uv run python app.py` / `pytest`); only the CLI needs Node. Deploys run in the CI
  pipeline (Node installed centrally), so data scientists need only Python + uv
  locally. Local `make deploy` is the sole exception that requires the CDK CLI (Node)
  on the developer machine.
