# ADR 0003 — SSM well-known paths as the Landing-Zone contract

- Status: **Superseded by ADR 0008** (static account registry in code)
- Date: 2026-05-27

> **Superseded.** Superseded on 2026-06-02. The baseline contract is no longer SSM paths but a
> static `AccountRegistry` in the platform repo (deterministic, GitHub as source of
> truth). `ssm_paths.py` has been removed. Kept for the rationale of *why* a contract
> seam between Landing Zone and platform was needed in the first place — that need
> still holds; only its implementation changed. See ADR 0008.

## Context

A Landing Zone already provisions shared VPCs/subnets/endpoints, KMS keys and IAM
permissions boundaries per account. Constructs must resolve these automatically so
Data Scientists never pass `vpc=`/`env=`/`kms=`. We must avoid hard-coding account
specifics in the library.

## Decision

The Landing-Zone team publishes **well-known SSM parameters** under `/platform/...`
per account/region. The library hard-codes only the **paths** (`ssm_paths.py`),
never the values. Constructs build networking via `Vpc.from_vpc_attributes` fed by
these parameters.

## Consequences

- Full decoupling: account changes are SSM edits, not library releases.
- The path set is a versioned contract; changing a path is a breaking change.
- The library does **not** create networking (Landing Zone owns it).
- New requirement on the Landing Zone: it must publish all paths in
  `ssm_paths.py` (vpc-id, private-subnet-ids, availability-zones, notebook SG, KMS
  key ARN, permissions-boundary ARN, environment) plus the VPC endpoints SageMaker
  needs when internet access is disabled.
