# Playbook - declarative variant (branch `feat/declarative`)

Goal: scaffold two consumer projects and synth both **offline**. In this variant there
is **no Python app** - `service.yaml` is the entire service definition and
`paved-cdk-synth` turns it into governed resources. Same two shapes:

- **Consumer A (scoring-service):** 1 S3 bucket + 1 private API + 1 Lambda
- **Consumer B (ingest-service):** 1 S3 bucket + 1 private API + 2 Lambdas

The manifest parses into the same `ServiceSpec` and the same `build_service` as the SDK
and explicit variants, so it produces identical governed resources.

## 0. Prerequisites

```bash
export PLATFORM=/path/to/paved-cdk
cd "$PLATFORM" && git checkout feat/declarative
export DEMO="$PWD/.demo"; mkdir -p "$DEMO"
```

Only Python + uv are needed; the CDK CLI (Node) is not required for synth.

## 1. Consumer A - scaffold

The scaffolded project already synths: the starter `service.yaml` has one function and
one data_api - exactly consumer A's shape.

```bash
uv run copier copy --vcs-ref HEAD "$PLATFORM" "$DEMO/consumer-a-scoring" \
  --data project_name="Scoring Service" --data project_slug="scoring-service" \
  --data owner_email="alice@example.com" --data team="ds-risk" \
  --data cost_center="4711" --defaults --trust
```

`--vcs-ref HEAD` is required: the declarative template lives on the `feat/declarative`
branch tip, not in a published tag yet.

Rendered `service.yaml`:

```yaml
service_id: scoring-service
owner: alice@example.com
team: ds-risk
cost_center: "4711"
data_apis:
  - scoring-service-data        # S3 bucket + private API Gateway
functions:
  - name: predict               # handlers/predict.py -> def predict(event, context)
    memory: 256
```

## 2. Consumer A - synth (offline)

```bash
cd "$DEMO/consumer-a-scoring"
CDK_DEFAULT_ACCOUNT=111111111111 CDK_DEFAULT_REGION=eu-west-1 CDK_OUTDIR=cdk.out \
  uv run --project "$PLATFORM" paved-cdk-synth

python3 -c "import json,glob;from collections import Counter; \
t=json.load(open(glob.glob('cdk.out/*.template.json')[0])); \
c=Counter(r['Type'] for r in t['Resources'].values()); \
print({k.split('::')[-1]:c[k] for k in ('AWS::S3::Bucket','AWS::ApiGateway::RestApi','AWS::Lambda::Function')})"
# -> {'Bucket': 1, 'RestApi': 1, 'Function': 1}
```

`--project "$PLATFORM"` runs the console script from the local platform source (the
working tree). In a real consumer repo you run `make smoke` (which runs `paved-cdk-synth`
from the pinned platform tag).

## 3. Consumer B - scaffold, edit the manifest

```bash
uv run copier copy --vcs-ref HEAD "$PLATFORM" "$DEMO/consumer-b-ingest" \
  --data project_name="Ingest Service" --data project_slug="ingest-service" \
  --data owner_email="bob@example.com" --data team="ds-data" \
  --data cost_center="4712" --defaults --trust
```

Replace `service.yaml` with two functions, and add their handler files:

```yaml
service_id: ingest-service
owner: bob@example.com
team: ds-data
cost_center: "4712"
data_apis:
  - ingest-service-data
functions:
  - name: ingest
  - name: transform
    memory: 512
```

```bash
cd "$DEMO/consumer-b-ingest"
printf 'def ingest(event, context):\n    return {"ok": "ingested"}\n'      > handlers/ingest.py
printf 'def transform(event, context):\n    return {"ok": "transformed"}\n' > handlers/transform.py
rm handlers/predict.py
```

## 4. Consumer B - synth

```bash
CDK_DEFAULT_ACCOUNT=111111111111 CDK_DEFAULT_REGION=eu-west-1 CDK_OUTDIR=cdk.out \
  uv run --project "$PLATFORM" paved-cdk-synth
# -> {'Bucket': 1, 'RestApi': 1, 'Function': 2}
```

## What this proves

Both consumers synth offline from YAML alone - no Python, no CDK objects. Adding a Lambda
is a `- name:` line plus a handler file; adding storage is a `data_apis:` entry. The
platform injected the same governance (private API, KMS bucket + Lambda env, permissions
boundary, tags) as the other two variants. AWS deployment is a later step.
