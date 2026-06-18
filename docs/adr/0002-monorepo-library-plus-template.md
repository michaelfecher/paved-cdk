# ADR 0002 - Monorepo: library + template together

- Status: Accepted
- Date: 2026-05-27

## Context

The construct library and the Copier template evolve together: a new construct API
is useless to scaffolded projects until the template references it.

## Decision

Keep the library, the Copier template and docs/ADRs in **one repository**.

## Consequences

- Atomic PRs bump construct API and template in lockstep; one CI; one ADR log.
- The Copier *output* is the consumer's own separate repo; `copier update` tracks a
  tag/branch of this repo.
- A `uv` workspace hosts the library under `packages/`; the template lives under
  `template/`.
