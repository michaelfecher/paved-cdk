# ADR 0011 — CI/CD trigger model & platform-owned deploy auth

- Status: Accepted
- Date: 2026-06-16
- Amends: ADR 0007 (uniform pipeline), ADR 0010 (the explicit-secret caller is superseded)

## Context

One reusable pipeline must serve the master repo and every consumer repo
identically. We want: continuous dev, **preprod/prod reachable only via a release**,
and a **live preview per pull request**. Crucially, a Data Scientist must set
**nothing AWS-specific** — deploy roles, account ids, OIDC and environments are the
platform's job, not the DS's.

## Decision

### Trigger model (one reusable workflow, `if:`-gated by event)
| Event | Action | Stage/account | Stack name |
|---|---|---|---|
| `pull_request` (open/sync, **same-repo only**) | deploy ephemeral preview | **dev** | `pr-<n>-<slug>` |
| `pull_request` closed/merged | `cdk destroy` the preview | dev | `pr-<n>-<slug>` |
| `push` to `main` | deploy | dev | `<slug>` |
| `push` tag `vX.Y.Z` | promote dev → preprod → prod | all three | `<slug>` |

- **preprod & prod are reachable only by a release tag** — never by an arbitrary
  push or PR. `prod` carries Required Reviewers (GitHub Environment).
- **PR previews land in the dev account** (not preprod/prod): PR code is executed
  during synth/deploy, so the blast radius is dev, and the job is gated to
  same-repo PRs (forks get no credentials — ADR 0010).

### Stack prefix (DS-transparent)
`PlatformStack` reads `STACK_PREFIX` (set by the pipeline to `pr-<n>-`) and prepends
it to the stack id. The DS writes `PlatformStack(app, "my-stack")` and never sees
the prefix; previews get isolated names; deploys use `cdk deploy --all` /
`cdk destroy --all` so prefixed and plain stacks are handled uniformly.

### Platform-owned deploy auth — the DS sets nothing
- The platform team provisions, **once per stage** (GitHub **variables**, repo or
  org level — ARNs/ids are not secrets): `PAVED_CDK_{DEV,PREPROD,PROD}_ACCOUNT_ID`.
- The deploy **role ARN is derived** by convention:
  `arn:aws:iam::<account-id>:role/paved-cdk-github-deploy` (name overridable via the
  `deploy_role_name` input). No per-repo secret, no `secrets: inherit`.
- The same account-id variables **feed the registry**, so synth resolves the right
  baseline deterministically (ADR 0008).
- The OIDC **trust policy** of each deploy role allows
  `repo:<owner>/<repo>:environment:<stage>` (or `repo:<org>/*:…` org-wide) — the one
  AWS-side thing, owned by the platform/cloud team.
- The consumer's thin caller passes only `stack_name`. **No `secrets:` block.**

## Consequences

- **Clean DS boundary:** scaffold → write `app.py` (+ own code) → push. No role ARNs,
  no account ids, no environment/secret setup ever touches the DS.
- **Supersedes ADR 0010's explicit-secret caller:** there is no per-repo deploy
  secret anymore; the multi-account model needs per-stage values, now provided as
  platform variables. (ADR 0010's other hardening — SHA-pinned actions, fork-gated
  PR jobs, escalation-proof boundary — still stands.)
- **Uniform master ⇄ consumer:** the master deploys its platform-seed stack through
  the same workflow; consumers deploy their app. Same triggers, same auth.
- **Cost:** ephemeral preview stacks are destroyed on PR close; a dedicated sandbox
  account for previews (instead of dev) is a later option if dev isolation isn't enough.

## Notes / follow-ups
- A platform automation (GitHub App / Terraform `integrations/github`) can create the
  three Environments + set the account-id variables on a new consumer repo, so even
  that one-time wiring is hands-off for the DS.
- The OIDC trust scope (`repo:owner/repo:…` vs `repo:org/*:…`) is a platform security
  decision: per-repo is tighter, org-wide removes per-repo setup.
