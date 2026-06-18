"""Copier/explicit model — the consumer owns this Python and declares resources directly."""
import aws_cdk as cdk
from paved_cdk import PlatformStack
from paved_cdk.service import ApiRoute, FunctionSpec, NotebookSpec, ServiceSpec, build_service

app = cdk.App()
stack = PlatformStack(app, "copier-payments",
    tags={"Owner": "payments@example.com", "Team": "ds", "CostCenter": "4711"})
build_service(stack, ServiceSpec(
    functions=[
        FunctionSpec(name="charge", code_path="handlers", handler="charge.charge",
                     api=ApiRoute("POST", "/charge")),
        FunctionSpec(name="nightly", code_path="handlers", handler="nightly.nightly",
                     memory_mb=512, schedule="rate(1 day)"),
    ],
    notebooks=[NotebookSpec(name="report", path="notebooks/report.ipynb")],
))
app.synth()
