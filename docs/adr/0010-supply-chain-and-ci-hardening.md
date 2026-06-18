# ADR 0010 — Supply-chain & CI hardening

- Status: Accepted
- Date: 2026-06-16

## Context

A security review of the reusable pipeline and distribution surface (ahead of making the
repo public) found several real risks: the `cdk diff` job ran untrusted PR code with the
deploy role; `cdk diff` output (with the resolved account id) was posted to PR comments;
third-party actions were pinned to mutable major tags; the caller forwarded all secrets via
`secrets: inherit`; and the IAM permissions boundary was permissive enough to allow
privilege escalation. These are decisions worth recording, not just patches.

## Decision

- **No untrusted code with deploy credentials.** The `diff` job is gated to same-repo PRs
  (`github.event.pull_request.head.repo.full_name == github.repository`); forks get neither
  secrets nor an OIDC token. A read-only diff role and required reviewers on the `dev`
  Environment are recommended for untrusted contributors.
- **Redact the plan.** The posted `cdk diff` is stripped of 12-digit account ids before it
  reaches a (potentially public) PR comment.
- **Pin actions to commit SHAs.** `checkout`, `setup-node`, `setup-uv`,
  `configure-aws-credentials`, `github-script` are pinned to full SHAs (mutable tags can be
  moved by a compromised maintainer). The library/pipeline are still consumed by git tag
  (ADR 0006); committing `uv.lock` + `uv sync --frozen` is the consumer-side reproducibility
  recommendation.
- **Least-privilege secrets.** The caller passes only `AWS_DEPLOY_ROLE_ARN`, declared
  explicitly in the reusable workflow's `workflow_call.secrets`. **(Superseded by ADR 0011:**
  the multi-account model needs per-stage values, so deploy auth moved to platform-set GitHub
  **variables** — there is no per-repo deploy secret anymore.)
- **No GitHub-expression injection.** Values flow into `github-script` via `env:`, read as
  `process.env.*` — never interpolated into the script body.
- **Escalation-proof permissions boundary.** The boundary denies creating/altering IAM
  principals without the same boundary, and protects itself (deny edits to its own policy).

## Consequences

- The pipeline is safe to run on a public repo; PR diffs do not leak account ids.
- Builds resist mutable-tag tampering on third-party actions.
- Stricter boundary means roles created by a bounded principal must themselves be bounded —
  intended; document it when teams create their own roles.

## Notes

- Out of repo and still required: the OIDC **trust policy** of `AWS_DEPLOY_ROLE_ARN` must
  restrict `sub` to `repo:<org>/<repo>:environment:<stage>`, else any repo could assume it.
- `EncryptionEnforcerAspect` coverage was broadened in the same pass: it checks 11
  resource types (S3, RDS, EFS, EBS, SNS, SQS, SageMaker, OpenSearch, Redshift) with correct
  boolean semantics; `SecureDataApi`/`SecureLambda` carry scoped, justified suppressions only.
