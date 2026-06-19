# Paved CDK

A paved-road AWS CDK platform for Data Scientists: an opinionated, account-aware
construct library (`packages/paved_cdk`) plus a Copier project template
(`template/`). Data Scientists write ~10 lines and get a secure, governed stack -
no VPC, env, KMS, IAM or tagging decisions.

See [`CONTEXT.md`](CONTEXT.md) for the domain language and [`docs/adr/`](docs/adr/)
for decisions.

> **This branch = the SDK variant.** Consumers declare their service as plain decorated
> functions in `handlers/*.py` (`@function` / `@scheduled` / `@api`) plus `data_api(...)`
> for storage; `app.py` only calls `synth()`. It converges on the shared
> `build_service`, so it yields the same governed resources as the other variants.
> See [`docs/demo/variants.md`](docs/demo/variants.md) for the side-by-side and
> [`docs/demo/playbook-sdk.md`](docs/demo/playbook-sdk.md) for a step-by-step. The
> reusable **pipeline**, **prototypes** and **onboarding** automation are **parked** in a
> local, git-ignored `_parked/` folder. Some docs and diagrams still describe the fuller design.

## Layout

```
packages/paved_cdk/   # the construct library (consumed via git tag from GitHub)
template/                      # Copier template that scaffolds consumer projects
docs/adr/                      # architecture decision records
```

## Tooling - what actually needs Node

The Python library and `app.synth()` are **pure Python - no Node.js**. Only the AWS
**CDK CLI** (`cdk deploy` / `bootstrap` / `diff`) is a Node app. So:

| Task | Tool | Node? |
|---|---|---|
| Author `app.py`, import the library | Python + uv | **No** |
| `cdk synth` / validate / `pytest` | Python (`uv run python app.py`) | **No** |
| `cdk deploy` / `bootstrap` / `diff` | CDK CLI | **Yes** |

A data scientist therefore needs only **Python + uv** locally - authoring, synth and
tests are Node-free. Deploys run in the **CI pipeline** (which installs Node centrally),
so nobody installs Node by hand. Local `make deploy` is the one exception that needs the
CDK CLI (Node) on the machine. See [ADR 0001](docs/adr/0001-pure-python-cdk-no-jsii.md).

## Develop

```bash
uv sync                                   # install the workspace
uv run pytest                             # run the offline synth/unit tests (no Node)
uv run copier copy . /tmp/demo \          # scaffold a sample consumer project (copier.yml is at the repo root)
  --data project_name="Demo" --data owner_email=a@example.com \
  --data team=ds --data cost_center=4711 --defaults
```

A consumer team scaffolds from the **git tag** instead:
`copier copy --vcs-ref v0.1.0 gh:michaelfecher/paved-cdk my-project`.

## Consumer (Data Scientist) experience

```python
import aws_cdk as cdk
from paved_cdk import PlatformStack, SecureDataApi

app = cdk.App()
stack = PlatformStack(app, "MyDataProject",
                      tags={"Owner": "a@example.com", "Team": "ds", "CostCenter": "4711"})
SecureDataApi(stack, "DataApi")
app.synth()
```

## AWS account ids

Account ids are **not** hard-coded - the registry reads them from environment
variables, with placeholder fallbacks so everything synthesizes and tests offline:

```bash
cp env.example .env            # then fill in your real account ids
export $(grep -v '^#' .env | xargs)
```

Account ids are per team and stage: `PAVED_CDK_<TEAM>_<STAGE>_ACCOUNT_ID`.

| Team | Stage   | Env var                              |
|------|---------|--------------------------------------|
| ds   | dev     | `PAVED_CDK_DS_DEV_ACCOUNT_ID`         |
| ds   | preprod | `PAVED_CDK_DS_PREPROD_ACCOUNT_ID`     |
| ds   | prod    | `PAVED_CDK_DS_PROD_ACCOUNT_ID`        |

The rest of each account's baseline (VPC, subnets, KMS key, permissions boundary,
execute-api endpoint) is static config in [`registry.py`](packages/paved_cdk/src/paved_cdk/registry.py).
