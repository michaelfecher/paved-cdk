# ADR 0008 - Static account registry in code (supersedes SSM resolution)

- Status: Accepted
- Date: 2026-06-02
- Supersedes: ADR 0003 (SSM well-known paths), ADR 0004 (synth- vs deploy-time SSM resolution)

## Context

ADR 0003/0004 resolved the per-account baseline (VPC, subnets, AZs, KMS key,
security group, permissions boundary, environment) from **well-known SSM
parameters** at synth/deploy time. In use this had three sharp edges:

1. **Synth needs AWS credentials.** `value_from_lookup` calls the account at synth
   and caches into `cdk.context.json`. CI must assume a role just to *synthesize*,
   and a missing/stale context file silently pins old ids.
2. **Non-deterministic.** The value behind a path can change between two synths of
   the same commit. That conflicts with the goal we settled on: **source code is
   the single source of truth and builds must be deterministic.**
3. **Two resolution modes** (synth- vs deploy-time) added real complexity and a
   dummy-value pitfall that had to be reasoned about per parameter.

The platform is a **GitHub-first, GitOps** system: onboarding an account or
rotating a subnet should be a reviewed pull request, not an out-of-band console
edit. SSM put the source of truth *outside* git.

## Decision

Move the per-account baseline **into code** as a static, typed registry in the
platform repo:

- `PlatformAccount` (frozen dataclass) - one account's baseline, with validation.
- `AccountRegistry` - all managed accounts, keyed by AWS account id;
  `resolve(account_id)` returns the `PlatformAccount` or raises a
  `PlatformConfigError` naming the remediation (open a PR).
- `PlatformEnvironment.resolve(scope)` looks the stack's target account up in the
  registry and builds `PlatformConfig` from **concrete strings** via the CDK
  importers (`Vpc.from_vpc_attributes`,
  `InterfaceVpcEndpoint.from_interface_vpc_endpoint_attributes`, `Key.from_key_arn`) -
  none of which call AWS.

SSM is removed entirely from the resolution path (`ssm_paths.py` deleted). The
registry *is* the contract that the SSM paths used to be.

## Consequences

- **Deterministic & offline.** Same commit -> same config; `cdk synth` needs no AWS
  credentials. CI (and PR validation) synthesizes without assuming a role. The only
  SSM-typed item left in any template is CDK's own unavoidable bootstrap-version
  parameter.
- **GitHub is the source of truth.** Adding an account / changing a value is a PR
  with a readable diff, validated by CI (schema + a `cdk synth` proving it builds)
  before merge. No value exists outside git.
- **The library decouples from its config source.** Constructs only ever see the
  typed `PlatformConfig`; `resolve()` is the single seam. Swapping the registry for
  a different backend later (or a generated one) is a one-module change.
- **Tests simplify.** No mocked SSM context provider - fixtures seed the registry.
- **Trade-off - propagation is now pull-based.** SSM propagated Landing-Zone changes
  live; the registry propagates them only when a consumer runs `copier update`
  (which bumps the pinned platform tag). For this audience (DS who avoid IaC) and
  this data (near-static network topology) that is acceptable, but it must be made
  visible - see mitigations.
- **Trade-off - the registry must mirror reality.** The platform repo, not the LZ
  team's SSM, now owns the values. This shifts ownership and must be coordinated
  with the Landing-Zone team.

## Mitigations

- **Generate, don't hand-maintain:** a platform-repo CI job can read AWS
  Organizations / the LZ and regenerate the registry, keeping the LZ as upstream
  truth while consumers still synth offline.
- **Freshness gate:** the reusable pipeline (ADR 0007) compares the consumer's
  pinned platform version against the current release and warns/fails when a
  project's config pin is stale - turning silent drift into a visible "run
  `copier update`".

## Follow-ups

- Optional `resolve(team, environment)` lookup so an app can synth all three stages
  offline (selecting accounts from the registry instead of relying on the ambient
  `CDK_DEFAULT_ACCOUNT`).
- Platform-seed stack that *deploys* the per-account baseline (KMS key, boundary
  policy, VPC endpoints) and emits exactly the values the registry records - closing
  the loop between "what the registry claims" and "what exists in the account".

## Amendment (2026-06-16) - account ids from the environment

To keep real AWS account numbers out of a public repo, `account_id` is no longer a literal
in the registry: each stage reads it from `PAVED_CDK_{DEV,PREPROD,PROD}_ACCOUNT_ID` with an
illustrative placeholder fallback (so import / `cdk synth` / tests still work offline). The
KMS and permissions-boundary ARNs are **derived** from the resolved id; the rest of the
baseline stays static literals. Determinism is unchanged - the env vars are set once per
deploy target, not fetched at synth. `env.example` documents the variables; `.env` is
git-ignored.
