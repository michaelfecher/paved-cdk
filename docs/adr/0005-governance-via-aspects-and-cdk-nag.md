# ADR 0005 — Governance via Aspects + cdk-nag, applied automatically

- Status: Accepted — **amended 2026-06-18: cdk-nag removed for now**
- Date: 2026-05-27

> **Amendment (2026-06-18):** the cdk-nag `AwsSolutionsChecks` pass and its
> `NagSuppressions` were **removed for now** from `apply_platform_governance` and the
> constructs. The Aspect guardrails below (permissions boundary, mandatory tags,
> fail-closed encryption) **remain**. cdk-nag can be re-added in one place
> (`apply_platform_governance`) when desired; the rest of this ADR is kept as the rationale.

## Context

Guardrails (tagging, encryption, least privilege, permissions boundary) must hold
without Data Scientists thinking about them. Relying on documentation/discipline
fails.

## Decision

`apply_platform_governance(stack, cfg, provided_tags)`, called from
`PlatformStack.__init__`, applies:

1. **Permissions boundary** at **stack scope** via `PermissionsBoundary.of(stack)`
   — covers every IAM role, including those inside vendor constructs.
2. **Mandatory tags** validated deterministically against the caller-provided tag
   dict (not fragile tag-propagation introspection), then applied with
   `Tags.of(stack)`.
3. **Fail-closed encryption** via `EncryptionEnforcerAspect` (errors on synth if a
   known encryptable resource is unencrypted) — deterministic because properties
   are set before aspects visit.
4. **cdk-nag** `AwsSolutionsChecks` at **app scope** (added once), with
   pre-approved `NagSuppressions` so Data Scientists never read nag output.

## Consequences

- Guardrails are inherited by construction; opting out requires deliberate effort.
- Tag verification lives at the stack input boundary, where it is reliable;
  encryption verification lives in an aspect, where per-resource checks are
  deterministic.
- cdk-nag failures fail `cdk synth`, so CI enforces compliance without extra steps.
