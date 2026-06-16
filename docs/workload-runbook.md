# Workload runbook — from a data-science team's point of view

How a workload team scaffolds a project from the platform, **requests resources**
(e.g. a Lambda) and later **pulls a platform update**. Everything except the actual
deploy is **Node-free** (pure Python + uv).

> Local replay: the platform repo is consumed by **git tag**. Until it is on GitHub,
> point at the local clone with its **plain path** (a `file://` URL is read as a non-git
> directory and fails); afterwards use `gh:michaelfecher/paved-cdk`.

```bash
# Pick the platform source once:
PLATFORM='/Users/mf/projects/kunden/wuerth/datascience-platform'   # local replay (plain path to the git repo)
# PLATFORM='gh:michaelfecher/paved-cdk'                                  # after push to GitHub
```

> **Two local-replay caveats** (gone once the platform is on GitHub):
> 1. The rendered `pyproject.toml` points the library at GitHub. For a local `uv sync`
>    before push, override `[tool.uv.sources] paved-cdk` to the local repo path
>    (`{ git = "<plain path>", tag = "v0.1.0", subdirectory = "packages/paved_cdk" }`),
>    or just push first.
> 2. Always run Copier via **`uvx copier …`** (isolated), not `uv run copier …` — the
>    latter first tries to sync the project env (hitting the not-yet-existing GitHub repo).

## 0. Prerequisites
- **Python + uv** — that's it for authoring, synth and tests.
- **Node.js** only if you want to `make deploy` locally (the CDK CLI is Node). Otherwise
  let the CI pipeline deploy.

## 1. Scaffold the project from a pinned platform version
```bash
uvx copier copy --vcs-ref v0.1.0 "$PLATFORM" orders-scoring \
  --data project_name="Orders Scoring" --data owner_email=ds@example.com \
  --data team=ds --data cost_center=4711
cd orders-scoring
git init -b main && git add -A && git commit -m "scaffold from paved-cdk v0.1.0"
```
You get a thin project: `app.py`, `pyproject.toml` (pins `paved-cdk` at the tag),
`cdk.json`, the pipeline caller, `.copier-answers.yml` (records the version), `Makefile`.

## 2. "Request" a resource — add a Lambda
Requesting infrastructure = **instantiate a catalog brick** in `app.py` and supply your
own code. No VPC/KMS/IAM/boundary — those come from the platform.

**2a.** Your handler (real business logic, lives in *this* repo):
```bash
mkdir -p src/scoring
cat > src/scoring/handler.py <<'PY'
def main(event, context):
    orders = event.get("orders", [])
    return {"statusCode": 200, "count": len(orders)}
PY
```

**2b.** Wire it in `app.py`:
```python
from aws_cdk import aws_lambda as _lambda
from paved_cdk import PlatformStack
from paved_cdk.compute import SecureLambda, SecureLambdaProps

app = cdk.App()
stack = PlatformStack(app, "orders-scoring",
    tags={"Owner": "ds@example.com", "Team": "ds", "CostCenter": "4711"})

SecureLambda(stack, "Scoring", props=SecureLambdaProps(
    code=_lambda.Code.from_asset("src/scoring"),   # <- your code
    handler="handler.main",
))
app.synth()
```

The brick gives the **secure envelope** (in-VPC, KMS-encrypted env, log retention,
permissions boundary); you give the **filling** (the handler). Browse the catalog:
`paved_cdk.storage`, `paved_cdk.compute`.

## 3. Validate locally — no Node
```bash
make validate     # = uv run python app.py (synth, cdk-nag aspects) + pytest
```
`app.py` synthesizes the CloudFormation template into `cdk.out/` and runs the governance
aspects (encryption, boundary, cdk-nag) — all in pure Python. Commit when green.

*(Deploy is separate: `make deploy` needs Node locally, or just push and let the pipeline
deploy dev → preprod → prod.)*

## 4. The platform ships a new version (platform team, in the master repo)
A change is only "released" once it is tagged — consumers never track `main`:
```bash
# in the platform repo, after CI is green:
git commit -am "feat: <something>"
git tag v0.2.0          # cut a tested, verified version
# (on GitHub this is a Release; pre-releases like v0.2.0rc1 are skipped by copier update)
```
Two kinds of change ride along on that tag:
- **Library** changes (construct internals, new brick, security default) — pulled by uv.
- **Template** changes (the thin scaffold: `app.py` skeleton, pipeline, a new question) —
  merged by `copier update`.

## 5. Pull the update (workload team)
```bash
uvx copier update --trust           # 3-way merge of the scaffold + bumps the tag in pyproject.toml
                                    # (or: make update)
uv lock --upgrade-package paved-cdk # re-resolve the library to the new tag
uv sync                             # install it
make validate                       # re-check, no Node
git add -A && git commit -m "chore: update to paved-cdk v0.2.0"
```
`copier update` defaults to the **latest tag**, re-renders the scaffold and writes the new
`platform_version` into `.copier-answers.yml` **and** the `tag=` in `pyproject.toml`
(one answer drives both). Conflicts only appear where you edited a scaffolded file by hand;
your own files (`src/…`, your `app.py` resource list) are merged, not overwritten.

> 90% of updates are just a library bump (steps `uv lock --upgrade` + `uv sync`) with **no
> file edits** in your repo — because the infra logic lives in versioned library classes,
> not in your scaffold.
