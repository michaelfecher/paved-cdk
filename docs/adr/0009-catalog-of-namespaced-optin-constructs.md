# ADR 0009 - Catalog of namespaced, opt-in constructs

- Status: Accepted
- Date: 2026-06-16

## Context

The platform must feel **modular like `aws-cdk-lib`**: a workload pulls only the resources
it needs (an API + bucket here, a Lambda there), not a monolithic "everything" stack. At the
same time a few things must be opinionated and always-on (env wiring, governance). We needed
a structure that scales as bricks are added without forcing every consumer to carry them.

## Decision

Model the constructs as an **à-la-carte catalog**:

- **Mandatory paved road:** `PlatformStack` + governance (boundary, tags, encryption)
  - always applied, not opt-out.
- **Optional bricks:** account-aware constructs, **namespaced by domain**
  (`paved_cdk.storage`, `paved_cdk.compute`, ...) and re-exported at the top level. A consumer
  imports and **instantiates only what it needs**.
- **Secure envelope vs filling:** a brick provides the secure wrapper (VPC, KMS, role/
  boundary, logs); the consumer supplies the application code via `Code.from_asset(...)`.
  Reference bricks: `SecureDataApi` (storage), `SecureLambda` (compute).

Distribution stays a single library package (one git tag, one `copier update`), not many
packages - see Consequences.

## Consequences

- **Installing ≠ deploying.** The whole library wheel is installed, but only an instantiated
  construct lands in the synthesized template. Unused bricks are dead, un-synthesized code -
  zero infra, negligible disk. This is exactly the `aws-cdk-lib` model.
- **Type-safe selection, not feature flags.** Choosing a resource = explicit, typed
  instantiation (IDE-discoverable, carries props). We deliberately avoid a stringly-typed
  `features=[...]` selector. Behavioural opt-ins (e.g. adopting a stricter default) are a
  separate concern and, if needed, ride on CDK `cdk.json` context flags, resolved at synth.
- **New bricks ship in a version bump.** A consumer adopts a new brick by adding one line
  after `uv sync` to the new tag - no scaffold change.
- **Single package over many.** One library keeps the release/version matrix trivial; split
  into separate packages only if a brick drags heavy, conflicting non-CDK dependencies (then
  use optional extras, `paved-cdk[compute]`).

## Notes

- Application code is inherently the workload's and cannot be pre-baked; the catalog
  pre-bakes everything *around* it. See `docs/building-blocks.md` and
  `docs/workload-runbook.md`.
