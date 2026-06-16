# ADR 0004 — Synth-time vs deploy-time resolution of SSM values

- Status: **Superseded by ADR 0008** (static account registry in code)
- Date: 2026-05-27

> ⚠ Superseded on 2026-06-02. With the static registry there is no live SSM
> resolution at all: all values are concrete strings in code, fed to the CDK
> `from_*` importers, so neither synth-time nor deploy-time SSM modes apply. The
> synth-time AWS-credential requirement and the `cdk.context.json` staleness footgun
> documented below are exactly what motivated the move. See ADR 0008.

## Context

SSM values can be resolved two ways in CDK:

- `StringParameter.value_from_lookup` — **synth time**; concrete string baked into
  the template; cached in `cdk.context.json`; needs AWS read access at synth.
- `StringParameter.value_for_string_parameter` — **deploy time**; a CFN dynamic
  reference (token); resolved by CloudFormation at deploy; no synth-time AWS access.

A token cannot be branched on (`if is_production`), split (`","`), or fed to APIs
that parse it at synth (e.g. `Vpc.from_lookup`, ARN parsing).

## Decision

Resolve **per parameter**:

- **Synth time** for values we branch on or split: environment name, VPC id,
  private subnet ids, availability zones.
- **Deploy time** for ARNs/ids we never branch on: KMS key ARN, permissions
  boundary ARN, notebook security-group id.

## Consequences

- Deploy-time resolution keeps ARNs always-fresh and **avoids the first-pass
  "dummy-value-for-…" string breaking `Key.from_key_arn` ARN parsing**.
- Synth-time values require consumers to **commit `cdk.context.json`** (a lockfile)
  and to run `cdk context --clear` after a Landing-Zone change, or stale ids pin
  silently.
- CI needs AWS read access at synth for the synth-time lookups (or a committed
  context file).
