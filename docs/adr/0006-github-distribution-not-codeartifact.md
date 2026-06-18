# ADR 0006 - Distribute the library via GitHub (git install), not CodeArtifact

- Status: Accepted
- Date: 2026-05-27
- Supersedes the CodeArtifact distribution sketched in the original plan.

## Context

The organisation standardises on GitHub (repos + Actions), not AWS CodeArtifact. GitHub
Packages has no native PyPI/Python registry (it supports npm/Maven/NuGet/RubyGems/
containers only), so we cannot host a Python index there directly.

## Decision

Consumer projects depend on the platform library **directly from its GitHub repo,
pinned to a git tag**, via uv's git source:

```toml
[tool.uv.sources]
paved-cdk = { git = "https://github.com/michaelfecher/paved-cdk.git",
                       tag = "v0.1.0", subdirectory = "packages/paved_cdk" }
```

(pip equivalent: `paved-cdk @ git+https://github.com/.../#subdirectory=packages/paved_cdk`).

## Consequences

- No package registry to run or authenticate against; access control is the repo's
  GitHub permissions. CI uses the runner's `GITHUB_TOKEN` / checkout for private repos.
- Versioning is by git tag; `copier update` bumps the pinned tag in consumer repos.
- Trade-off vs a real index: no dependency-resolver metadata/caching benefits and
  slightly slower installs (a clone). Acceptable at this scale. If many consumers or
  external teams need it, revisit by publishing wheels to GitHub Releases behind a
  PEP 503 index, or to (public/private) PyPI.
