# Playbook - explicit / Copier variant (branch `main`)

Goal: scaffold two consumer projects from the template and synth both **offline**
(no AWS login). Two different shapes:

- **Consumer A (scoring-service):** 1 S3 bucket + 1 private API + 1 Lambda
- **Consumer B (ingest-service):** 1 S3 bucket + 1 private API + 2 Lambdas

In this variant the Data Scientist edits `app.py` and adds catalog constructs by hand.
`SecureDataApi` = encrypted S3 bucket + private API Gateway; `SecureLambda` = one
in-VPC, KMS-encrypted Lambda. Everything network/security-related is resolved from the
account baseline - the consumer never passes vpc/kms/role/boundary.

## 0. Prerequisites

```bash
# the platform repo checkout (this repo); branch main
export PLATFORM=/path/to/paved-cdk          # this checkout
cd "$PLATFORM" && git checkout main
export DEMO="$PWD/.demo"                     # scratch output (gitignored)
mkdir -p "$DEMO"
```

`uv` is the only tool needed; the CDK CLI (Node) is NOT required for synth - we run
`python app.py`, which writes `cdk.out/` via the bundled JSII runtime.

## 1. Consumer A - scaffold

```bash
uv run copier copy --vcs-ref HEAD "$PLATFORM" "$DEMO/consumer-a-scoring" \
  --data project_name="Scoring Service" --data project_slug="scoring-service" \
  --data owner_email="alice@example.com" --data team="ds" \
  --data cost_center="4711" --defaults --trust
```

`--vcs-ref HEAD` uses the branch tip (the team-aware template is not tagged yet).
`team` must be a team onboarded in the registry (`ds` or, illustratively, `marketing`).

## 2. Consumer A - add the workload

Create the Lambda's own code asset:

```bash
mkdir -p "$DEMO/consumer-a-scoring/src/score"
cat > "$DEMO/consumer-a-scoring/src/score/handler.py" <<'PY'
def main(event, context):
    return {"statusCode": 200, "body": "scored"}
PY
```

Replace `app.py` with:

```python
import aws_cdk as cdk
from aws_cdk import aws_lambda as _lambda

from paved_cdk import (
    PlatformStack, SecureDataApi, SecureDataApiProps,
    SecureLambda, SecureLambdaProps,
)

app = cdk.App()
stack = PlatformStack(
    app, "scoring-service",
    team="ds",                                   # selects the account baseline (VPC/KMS/...)
    tags={"Owner": "alice@example.com", "CostCenter": "4711"},
)
SecureDataApi(stack, "Data", props=SecureDataApiProps(api_name="scoring-data"))
SecureLambda(stack, "Score", props=SecureLambdaProps(code=_lambda.Code.from_asset("src/score")))
app.synth()
```

## 3. Consumer A - synth (offline)

```bash
cd "$DEMO/consumer-a-scoring"
PAVED_CDK_STAGE=dev CDK_OUTDIR=cdk.out \
  uv run --project "$PLATFORM" python app.py
ls cdk.out/*.template.json && echo "SYNTH OK"
```

No account id needed: `team="ds"` + `PAVED_CDK_STAGE=dev` resolves the ds-dev account
and its VPC from the registry.

`--project "$PLATFORM"` runs against the local platform source (the working tree),
so you synth unreleased changes without a published tag. In the real consumer repo you
instead run `make smoke` (it pulls the platform library from the pinned git tag).

Verify the shape:

```bash
python3 -c "import json,glob;from collections import Counter; \
t=json.load(open(glob.glob('cdk.out/*.template.json')[0])); \
c=Counter(r['Type'] for r in t['Resources'].values()); \
print({k:c[k] for k in ('AWS::S3::Bucket','AWS::ApiGateway::RestApi','AWS::Lambda::Function')})"
# -> {'AWS::S3::Bucket': 1, 'AWS::ApiGateway::RestApi': 1, 'AWS::Lambda::Function': 1}
```

## 4. Consumer B - scaffold, add 2 Lambdas, synth

Put consumer B in a **different team** (`marketing`) to show the per-team baseline: the
same code resolves a different VPC.

```bash
uv run copier copy --vcs-ref HEAD "$PLATFORM" "$DEMO/consumer-b-ingest" \
  --data project_name="Ingest Service" --data project_slug="ingest-service" \
  --data owner_email="bob@example.com" --data team="marketing" \
  --data cost_center="4712" --defaults --trust

mkdir -p "$DEMO/consumer-b-ingest/src/ingest" "$DEMO/consumer-b-ingest/src/transform"
printf 'def main(event, context):\n    return {"ok": "ingested"}\n'   > "$DEMO/consumer-b-ingest/src/ingest/handler.py"
printf 'def main(event, context):\n    return {"ok": "transformed"}\n' > "$DEMO/consumer-b-ingest/src/transform/handler.py"
```

`app.py`:

```python
import aws_cdk as cdk
from aws_cdk import aws_lambda as _lambda

from paved_cdk import (
    PlatformStack, SecureDataApi, SecureDataApiProps,
    SecureLambda, SecureLambdaProps,
)

app = cdk.App()
stack = PlatformStack(
    app, "ingest-service",
    team="marketing",                            # different team -> different VPC/KMS
    tags={"Owner": "bob@example.com", "CostCenter": "4712"},
)
SecureDataApi(stack, "Data", props=SecureDataApiProps(api_name="ingest-data"))
SecureLambda(stack, "Ingest", props=SecureLambdaProps(code=_lambda.Code.from_asset("src/ingest")))
SecureLambda(stack, "Transform", props=SecureLambdaProps(
    code=_lambda.Code.from_asset("src/transform"), memory_mb=512))
app.synth()
```

```bash
cd "$DEMO/consumer-b-ingest"
PAVED_CDK_STAGE=dev CDK_OUTDIR=cdk.out \
  uv run --project "$PLATFORM" python app.py
# shape: 1 S3 bucket, 1 RestApi, 2 Lambda functions; stack name dev-ingest-service
# grep the template: it resolves marketing's VPC (vpc-0a11...), not ds's (vpc-0c86...)
grep -o 'vpc-[0-9a-f]*' cdk.out/dev-ingest-service.template.json | sort -u
```

## What this proves

Both consumers synth to valid CloudFormation offline. The platform injected the same
governance into both (private API locked to the `execute-api` VPC endpoint, KMS-encrypted
bucket + Lambda env, permissions boundary, mandatory tags) without either consumer
specifying any of it. AWS deployment is a later step (`make deploy` / the pipeline).
