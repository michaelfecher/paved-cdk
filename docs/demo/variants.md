# The three consumption variants

Paved CDK can be consumed three ways. All three converge on the **same governed
resources** (same VPC/KMS/boundary/tags, same catalog constructs) - they differ only
in how a Data Scientist *expresses intent*. One variant will be chosen as the standard
(customer + platform team); until then each lives on its own branch:

| | Explicit / Copier (`main`) | SDK (`feat/sdk`) | Declarative (`feat/declarative`) |
|---|---|---|---|
| Consumer writes | `app.py` with constructs | decorated `handlers/*.py` | `service.yaml` manifest |
| CDK knowledge needed | some (App/Stack/constructs) | almost none (plain functions) | none (YAML only) |
| Flexibility | highest (any construct) | medium (functions + data API) | medium (functions + data API) |
| `app.py` | hand-written | two lines (`synth()`) | none (`paved-cdk-synth`) |
| Best for | teams comfortable with CDK | Python-first Data Scientists | non-coders / config-driven |

All three resolve account baseline (VPC, subnets, KMS, permissions boundary, log
retention, tags) automatically. None of them lets a consumer touch vpc/kms/role/boundary.

## Same workload, three ways

Workload: an **S3 data bucket + private API Gateway** (`SecureDataApi`) and one
**in-VPC, KMS-encrypted Lambda** (`SecureLambda`).

### Explicit / Copier (`main`)

```python
# app.py
SecureDataApi(stack, "Data", props=SecureDataApiProps(api_name="scoring-data"))
SecureLambda(stack, "Score", props=SecureLambdaProps(code=Code.from_asset("src/score")))
```

### SDK (`feat/sdk`)

```python
# handlers/score.py
from paved_cdk.sdk import function, data_api

data_api("scoring-data")            # S3 bucket + private API

@function()                          # in-VPC, KMS-encrypted Lambda
def score(event, context):
    return {"statusCode": 200}
```
```python
# app.py  (the whole file)
from paved_cdk.sdk import synth
synth()
```

### Declarative (`feat/declarative`)

```yaml
# service.yaml
service_id: scoring-service
owner: alice@example.com
data_apis:
  - name: scoring-data            # S3 bucket + private API
functions:
  - name: score                  # in-VPC, KMS-encrypted Lambda
```
```json
// cdk.json
{ "app": "paved-cdk-synth" }
```

## Convergence

Each front end produces a `ServiceSpec` (or explicit constructs) that `build_service`
turns into the **identical** CloudFormation: same Lambda config, same private API locked
to the account `execute-api` VPC endpoint, same KMS-encrypted bucket. The choice of
variant is a question of consumer ergonomics, not of what gets deployed.

Per-variant step-by-step guides (each on its branch):
[explicit](playbook-explicit.md) (`main`), `playbook-sdk.md` (`feat/sdk`),
`playbook-declarative.md` (`feat/declarative`).
