# paved-cdk

Paved-road AWS CDK construct library for Data Scientists.

You write ~10 lines; the platform resolves VPC, subnets, KMS, IAM permissions
boundary, tags and governance **automatically from the target AWS account**.

```python
import aws_cdk as cdk
from paved_cdk import PlatformStack, SecureDataApi

app = cdk.App()
stack = PlatformStack(app, "MyDataProject",
                      tags={"Owner": "a@example.com", "Team": "ds", "CostCenter": "4711"})
SecureDataApi(stack, "DataApi")   # no vpc / env / kms / iam / tags args
app.synth()
```

See the monorepo root for `CONTEXT.md` and `docs/adr/`.
