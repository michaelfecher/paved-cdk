# Consumption-model prototypes — three surfaces, one governed result

Three runnable consumer examples implement the **same service** and synthesize the
**same governed resources** on the **same Paved CDK kernel** — they differ only in
*what the consumer writes*.

Service (identical in all three):
- `POST /charge` → Lambda behind a private API Gateway
- `nightly` → scheduled Lambda (`rate(1 day)`)
- `report.ipynb` → scheduled notebook runner (`rate(1 day)`)

## The shared kernel (identical underneath all variants)
`build_service(stack, ServiceSpec)` in `packages/paved_cdk/.../service.py` is the single
convergence point. Per stage it pulls the **preconfigured baseline from the registry**
(VPC, subnets, KMS, permissions boundary, execute-api endpoint; Databricks via a
Secrets-Manager reference) — the consumer sets **none** of that, in any variant.

## The three variants

| | `sdk-payments` | `declarative-payments` | `copier-payments` |
|---|---|---|---|
| Consumer writes | handlers + `@api/@scheduled` | `service.yaml` + handlers | `app.py` (explicit) + handlers |
| Frontend | `paved_cdk.sdk` (decorators) | `paved_cdk.engine` (YAML) | `paved_cdk.service` (direct) |
| Declarative (YAML)? | no | **yes** | no |
| One language (Python)? | yes | no | yes |
| Consumer IaC effort | lowest | low | highest |
| `cdk.json` `app` | `python app.py` | `paved-cdk-synth` | `python app.py` |

## Verified parity (synth, against the installed kernel only)

| Resource | SDK | declarative | copier |
|---|---|---|---|
| `AWS::Lambda::Function` | 3 | 3 | 3 |
| `AWS::Events::Rule` | 2 | 2 | 2 |
| `AWS::ApiGateway::Method` | 1 | 1 | 1 |

Governance (boundary, KMS, tags, cdk-nag, in-VPC, private API) is identical in all three.
**Difference = only who writes what.** See [`COMPARISON.md`](COMPARISON.md).

## Run them yourself (offline, no Node beyond the CDK assembly, no AWS)
```bash
PY=../../.venv/bin/python   # the platform venv (has paved_cdk installed)
# SDK
cd consumers/sdk-payments && CDK_DEFAULT_ACCOUNT=111111111111 CDK_DEFAULT_REGION=eu-west-1 $PY app.py
# declarative (uses the platform console-script)
cd consumers/declarative-payments && CDK_DEFAULT_ACCOUNT=111111111111 CDK_DEFAULT_REGION=eu-west-1 ../../../.venv/bin/paved-cdk-synth
# copier / explicit
cd consumers/copier-payments && CDK_DEFAULT_ACCOUNT=111111111111 CDK_DEFAULT_REGION=eu-west-1 $PY app.py
```
