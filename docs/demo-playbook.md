# Demo playbook — Master (platform) vs Consumer (workload)

A ~8-minute live demo showing the clean split: **what the platform/master does** vs
**what a workload/consumer project does**, and how updates flow. Everything except the
actual deploy is **Node-free** (pure Python + uv).

Platform repo: <https://github.com/michaelfecher/paved-cdk> — tags `v0.1.0`, `v0.2.0`.

## The model in one line
**Master** = the platform (library + Copier template + reusable pipeline), released by **git tag**.
**Consumer** = a thin project (wiring + its own code) that **pulls the platform by tag**.

| Step | **MASTER** (platform team, once) | **CONSUMER** (DS team, per project) |
|---|---|---|
| Building blocks | secure constructs (`SecureDataApi`, `SecureLambda`) + governance | — uses them |
| Accounts/baseline | maintain the registry (VPC/KMS/boundary; account ids from env) | — |
| Pipeline | define **one** reusable pipeline | thin caller (once, from template) |
| Release | **cut a tag `vX.Y.Z`** | — |
| New project | provide the template | `copier copy` (scaffold) |
| **Request a resource** | — | **instantiate a brick + supply own code** (`app.py` + `src/…`) |
| Validate | library tests | `make validate` (Node-free) |
| Deploy | — | push → pipeline (dev→preprod→prod) |
| Update | cut a new tag | `copier update` + `uv sync` |

## Prerequisites
- **Python + uv** locally — authoring, synth and tests are Node-free.
- **Node.js** only for a local `make deploy` (the CDK CLI is Node); otherwise the pipeline deploys.

---

## Part 1 — MASTER (platform view): *“here lives the HOW”*
```bash
uv run pytest -q          # constructs + governance tested
git tag                   # v0.1.0 / v0.2.0 = released versions
```
Show & narrate:
- `packages/paved_cdk/compute/secure_lambda.py` — the secure envelope (in-VPC, KMS, boundary, logs); the DS only passes code.
- `packages/paved_cdk/src/paved_cdk/registry.py` — account baseline in code, account ids from env.
- `.github/workflows/cdk-deploy.yml` — one pipeline for all; dev → preprod → prod.
- `docs/architecture.md` + `docs/adr/` — patterns & decisions recorded.

## Part 2 — CONSUMER (DS view): *“here lives the WHAT”* — request a Lambda
```bash
# scaffold a fresh project from a pinned platform version
uvx copier copy --vcs-ref v0.1.0 gh:michaelfecher/paved-cdk demo-scoring \
  --data project_name="Demo Scoring" --data owner_email=ds@example.com \
  --data team=ds --data cost_center=4711
cd demo-scoring
```
Add your handler (real business logic, in *this* repo):
```bash
mkdir -p src/scoring
cat > src/scoring/handler.py <<'PY'
def main(event, context):
    return {"statusCode": 200, "count": len(event.get("orders", []))}
PY
```
Wire it in `app.py` — this is *all* the DS writes (no vpc/kms/role):
```python
from aws_cdk import aws_lambda as _lambda
from paved_cdk import PlatformStack
from paved_cdk.compute import SecureLambda, SecureLambdaProps   # catalog: compute

stack = PlatformStack(app, "demo-scoring", tags={...})
SecureLambda(stack, "Scoring", props=SecureLambdaProps(
    code=_lambda.Code.from_asset("src/scoring"), handler="handler.main"))
```
Validate — **no Node, no AWS**:
```bash
make validate     # -> synthesized to cdk.out/
```
Open `cdk.out/demo-scoring.template.json` to show: Lambda + LogGroup + KMS bucket + private API — securely wired, none of which the DS had to write.

## Part 3 — UPDATE: platform ships v0.2.0, consumer pulls it
> Platform team cut `v0.2.0` (here: a new `make smoke` target). In the consumer:
```bash
uvx copier update --defaults --trust   # non-interactive; merges the scaffold to the latest tag
git diff                                # Makefile gained `smoke`; .copier-answers _commit → v0.2.0
make smoke                              # the brand-new target the platform just delivered
```
Narrative: *“One command, and my project gains the platform's improvement — my own `app.py`
and Lambda code stay untouched.”* `--defaults` = prompt-free (CI/stage-safe).

Optionally also bump the library pin: `uvx copier update --defaults --trust --data platform_version=v0.2.0 && uv sync`.

## Reset (to rehearse again)
```bash
cd demo-scoring && git checkout . && git clean -fd   # back to the pre-update state
```

## Notes
- `make validate` = offline synth via `python app.py` (Node-free, no AWS); the CDK CLI (Node)
  is only needed for `make deploy`, which the pipeline does anyway.
- `copier update` is **tag-driven**: it jumps to the latest released tag and 3-way-merges the
  thin scaffold; the library version follows the `platform_version` answer.
