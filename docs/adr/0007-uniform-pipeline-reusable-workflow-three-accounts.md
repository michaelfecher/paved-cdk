# ADR 0007 - Uniform pipelines via a reusable GitHub Actions workflow; three accounts

- Status: Accepted
- Date: 2026-05-27

## Context

DS teams must all run the *same* pipeline, on GitHub Actions, and each team is
always given three AWS accounts (dev/preprod/prod). We need uniformity that survives
updates without per-repo drift.

## Decision

- One **reusable workflow** (`.github/workflows/cdk-deploy.yml`, `workflow_call`)
  in the platform repo is the single source of truth for the pipeline. Consumer
  repos contain only a **thin caller** referencing it at a pinned tag
  (`uses: your-org/paved-cdk/.github/workflows/cdk-deploy.yml@v0.1.0`).
- Stages **dev -> preprod -> prod** are sequential jobs, each bound to a GitHub
  **Environment** of the same name holding that account's OIDC `AWS_DEPLOY_ROLE_ARN`
  and protection rules (required reviewers on `prod`). No long-lived AWS keys.
- The per-account paved-road config comes from the static account registry in code
  (ADR 0008), so the same `app.py` deploys correctly into all three accounts and
  synthesizes deterministically without AWS access.

## Consequences

- **Uniformity by reference, not by copy.** Unlike projen (which *copies* workflow
  YAML into each repo and relies on re-synthesis) or plain Copier (which renders a
  full pipeline per repo), the pipeline logic lives in exactly one place; bumping
  the caller's `@tag` updates every project. This is the strongest answer to
  "pipelines must run the same".
- Requires per-repo one-time setup of the three Environments + role ARNs (could be
  automated org-wide later).
- No `cdk.context.json` lookups are needed: config is static in code (ADR 0008), so
  the validate/synth job runs without assuming an AWS role; only the deploy jobs use
  OIDC.
- The CDK CLI (npm `aws-cdk`) is installed in CI; the app itself stays pure Python.
