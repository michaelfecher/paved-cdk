# CONTEXT - Paved CDK

> **Scope - minimal v1.** Committed core = construct library (kernel + `SecureLambda` +
> `SecureDataApi`) + Copier template. Pipeline, SDK/declarative variants,
> service-orchestration, prototypes and onboarding are parked in `_parked/` (git-ignored)
> for a later phase.

## Why this exists

Data Scientists have little/no Infrastructure-as-Code experience and do
not want to acquire it. Without a platform, every project starts from vanilla CDK
and re-derives networking, encryption, IAM and tagging - slow to onboard and
inconsistent in governance. This repo is the **paved road**: an opinionated CDK
construct library plus a Copier project template so a Data Scientist ships a
secure, compliant stack writing ~10 lines and **zero** infrastructure decisions.

## Domain language

- **Paved road** - the supported, opinionated default path. Stepping off it is
  possible but unsupported.
- **PlatformConfig** - the resolved, account-specific configuration (VPC, subnets,
  KMS key, permissions boundary, environment, tags). Data Scientists never build
  it; constructs consume it internally.
- **PlatformEnvironment** - resolves a `PlatformConfig` from the target account.
  `.resolve(scope)` does the work once per stack; `.of(scope)` reuses the cached
  result. This is the single **seam**: constructs only ever see `PlatformConfig`,
  never the config source.
- **AccountRegistry** - the static, in-code source of truth for every managed
  account, **grouped by team** (each team has dev/preprod/prod). `PlatformAccount`
  (frozen dataclass) holds one account's baseline (VPC, subnets, AZs, KMS, permissions
  boundary, environment, team); `resolve(account_id)` and `account_for(team, stage)`
  return it. Replaces the former SSM/DynamoDB contract (ADR 0008, 0012): values live
  in git, deterministic, PR-reviewed.
- **Team** - a consumer names its `team`; the platform resolves that team's account
  (and VPC/KMS baseline) for the deploy stage. Consumers never name a VPC or account.
- **PlatformStack** - base stack; resolves `env` from `team=` (registry account for
  the stage) or explicit `env`/`CDK_DEFAULT_*`, names the stack
  `$stage-$stackPrefix-$project`, and applies governance automatically.
- **Governance** - permissions boundary, mandatory tags and fail-closed encryption,
  applied by `apply_platform_governance` without DS involvement. (cdk-nag removed for now.)
- **Deterministic resolution** - baseline values are concrete strings fed to the CDK
  `from_*` importers; account ids come from env vars (placeholder fallback), the rest is
  static. No live SSM/DynamoDB lookup, no AWS credentials at synth. See ADR 0008.
- **Catalog brick** - an opt-in, account-aware construct (namespaced `paved_cdk.storage`,
  `paved_cdk.compute`). Consumers instantiate only what they need; importing the library
  deploys nothing (*instantiation ≠ deployment*). Like `aws-cdk-lib`, à la carte. See ADR 0009.
- **Secure envelope vs filling** - a brick (e.g. `SecureLambda`) provides the secure wrapper
  (VPC, KMS, role/boundary, logs); the consumer supplies the code via `Code.from_asset(...)`.
  Application logic is never pre-baked; everything around it is.

## Layers

1. **Template** (`template/`) - Copier scaffold; `copier update` propagates changes.
2. **Library** (`packages/paved_cdk/`) - the product: constructs + resolver
   + governance + the account registry. Consumed via a git tag from GitHub (ADR 0006).
3. **Account registry** (`registry.py`) - static, in-code baseline for every account,
   the source of truth; changed via PR (ADR 0008).
4. **Reusable pipeline** (`.github/workflows/cdk-deploy.yml`) - one shared GitHub
   Actions workflow; consumer repos only hold a thin caller (ADR 0007).

## Stages

- **Three stages** - every team gets three AWS accounts (`dev`/`preprod`/`prod`),
  modelled as GitHub Environments. The pipeline deploys dev -> preprod -> prod; the
  paved-road config is resolved per account from the static registry (ADR 0008).
  Account ids come from environment variables (placeholders otherwise); the example
  baseline targets `eu-west-1`.

## Boundaries / non-goals

- This repo does **not** create networking - the Landing Zone owns VPCs/subnets/
  endpoints; the registry only records their ids (ADR 0008, superseding 0003).
- Pure Python only; no JSII/TypeScript (ADR 0001) - other-language consumers are
  out of scope.
