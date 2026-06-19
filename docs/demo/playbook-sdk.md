# Playbook - SDK variant (branch `feat/sdk`)

Goal: scaffold two consumer projects and synth both **offline**. In this variant the
Data Scientist writes **plain decorated functions** in `handlers/*.py` and declares
storage with `data_api(...)`; `app.py` only calls `synth()`. Same two shapes:

- **Consumer A (scoring-service):** 1 S3 bucket + 1 private API + 1 Lambda
- **Consumer B (ingest-service):** 1 S3 bucket + 1 private API + 2 Lambdas

`synth()` imports the `handlers` package (running the decorators), turns the
registrations into a `ServiceSpec`, and hands it to the same `build_service` the other
variants use - so the SDK produces identical governed resources.

## 0. Prerequisites

```bash
export PLATFORM=/path/to/paved-cdk
cd "$PLATFORM" && git checkout feat/sdk
export DEMO="$PWD/.demo"; mkdir -p "$DEMO"
```

Only Python + uv are needed; the CDK CLI (Node) is not required for synth.

## 1. Consumer A - scaffold

The scaffolded project already synths: the starter `handlers/example.py` has one
`@function` and one `data_api(...)` - exactly consumer A's shape.

```bash
uv run copier copy --vcs-ref HEAD "$PLATFORM" "$DEMO/consumer-a-scoring" \
  --data project_name="Scoring Service" --data project_slug="scoring-service" \
  --data owner_email="alice@example.com" --data team="ds" \
  --data cost_center="4711" --defaults --trust
```

`--vcs-ref HEAD` is required: the SDK template lives on the `feat/sdk` branch tip, not
in a published tag yet. (Without it copier renders the latest tag, i.e. the explicit
template.)

The starter `handlers/example.py`:

```python
from paved_cdk.sdk import data_api, function

data_api("scoring-service-data")     # S3 bucket + private API Gateway

@function()
def predict(event, context):
    return {"statusCode": 200, "body": "ok"}
```

## 2. Consumer A - synth (offline)

```bash
cd "$DEMO/consumer-a-scoring"
PAVED_CDK_STAGE=dev CDK_OUTDIR=cdk.out \
  uv run --project "$PLATFORM" python app.py

python3 -c "import json,glob;from collections import Counter; \
t=json.load(open(glob.glob('cdk.out/*.template.json')[0])); \
c=Counter(r['Type'] for r in t['Resources'].values()); \
print({k.split('::')[-1]:c[k] for k in ('AWS::S3::Bucket','AWS::ApiGateway::RestApi','AWS::Lambda::Function')})"
# -> {'Bucket': 1, 'RestApi': 1, 'Function': 1}
```

`--project "$PLATFORM"` runs against the local platform source (the working tree), so
unreleased SDK changes synth without a tag. In a real consumer repo you run `make smoke`.

## 3. Consumer B - scaffold + add a second handler

```bash
uv run copier copy --vcs-ref HEAD "$PLATFORM" "$DEMO/consumer-b-ingest" \
  --data project_name="Ingest Service" --data project_slug="ingest-service" \
  --data owner_email="bob@example.com" --data team="marketing" \
  --data cost_center="4712" --defaults --trust
```

Add a second function (the starter already gives one function + one data_api):

```bash
cat > "$DEMO/consumer-b-ingest/handlers/transform.py" <<'PY'
from paved_cdk.sdk import function

@function(memory=512)
def transform(event, context):
    return {"ok": "transformed"}
PY
```

(Optionally rename the starter's `data_api("ingest-service-data")` to taste.)

## 4. Consumer B - synth

```bash
cd "$DEMO/consumer-b-ingest"
PAVED_CDK_STAGE=dev CDK_OUTDIR=cdk.out \
  uv run --project "$PLATFORM" python app.py
# -> {'Bucket': 1, 'RestApi': 1, 'Function': 2}
```

## What this proves

Both consumers synth offline from plain decorated functions - no `app.py` edits, no CDK
objects. The platform injected the same governance (private API, KMS bucket + Lambda env,
permissions boundary, tags) as the explicit variant. Adding a Lambda is one decorated
function; adding storage is one `data_api(...)` call. AWS deployment is a later step.
