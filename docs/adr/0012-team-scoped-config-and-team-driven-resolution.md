# ADR 0012 - Team-scoped account registry and team-driven resolution

- Status: accepted
- Extends: ADR 0008 (static in-code account registry)

## Context

Each team gets three AWS accounts (dev/preprod/prod), and different teams have different
pre-provisioned infrastructure (VPC id, subnets, KMS key, execute-api endpoint). We need:

1. per-account configuration (the baseline) - **already** solved by the static, in-code
   `AccountRegistry` (ADR 0008): reviewable PR diffs, deterministic, offline, no DynamoDB;
2. multiple teams, each with their own three accounts and baseline;
3. per-consumer configuration that selects a team without the consumer ever naming a VPC,
   KMS key or account id;
4. the same model expressed across the three consumption variants.

The customer's current implementation reads this config from DynamoDB at runtime. That is
explicitly rejected: it is non-deterministic (a value can change between synth and deploy),
needs credentials/network (no offline synth), and has no review or diff.

## Decision

**Group the registry by team and resolve the account by `team + stage`.**

- `PlatformAccount` carries a `team`. The registry holds three accounts per team; account
  ids come from per-team env vars `PAVED_CDK_<TEAM>_<STAGE>_ACCOUNT_ID` (offline-safe
  placeholders). New helpers: `account_for(team, stage)`, `accounts_for_team(team)`, `teams`.
- `PlatformStack(team=...)` resolves the team's account for the deploy `stage`
  (`PAVED_CDK_STAGE`, default `dev`) and uses it as the stack environment; the team becomes
  the authoritative `Team` tag. The explicit `env=` path is unchanged for tests and callers
  that already know the account.
- The consumer config is variant-specific and names only `team` + identity + resources:
  `PlatformStack(team=...)` (explicit), `synth(team=...)` (SDK), `team:` in `service.yaml`
  (declarative). No infra ids leak into consumer code.

Resolution is an in-memory dict access; the downstream `from_*Attributes` importers bake
ids into the template as literals (no AWS call). See `docs/configuration.md`.

## Consequences

- Onboarding a team is one PR (three `_account(...)` rows + three repo variables); CI
  validates the entries and proves an offline synth before merge.
- The same consumer code yields a different VPC/KMS baseline purely by changing `team`,
  proven in the demo (`team="ds"` -> `vpc-0c867...`, `team="marketing"` -> `vpc-0a11...`).
- Multiple consumers share a team's three accounts; each gets its own stack.
- Trade-off: a config change is a code release of the platform library, not a live edit -
  which is the point (determinism + review), and the reason DynamoDB is rejected.
