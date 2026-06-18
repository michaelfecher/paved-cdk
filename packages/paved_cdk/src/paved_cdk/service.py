"""Shared service layer — the single convergence point for all consumption models.

A consumer (via SDK decorators, a YAML manifest, or explicit Copier code) ultimately
produces a :class:`ServiceSpec`. ``build_service`` turns that spec into governed
resources on the enclosing :class:`PlatformStack`, reusing the catalog constructs.

This guarantees: **same intent → same resources**, regardless of the front end.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aws_cdk import aws_apigateway as apigateway
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from constructs import Construct

from .compute.secure_lambda import SecureLambda, SecureLambdaProps
from .environment import PlatformEnvironment


@dataclass(frozen=True)
class ApiRoute:
    method: str  # GET | POST | PUT | DELETE
    path: str  # e.g. "/charge"


@dataclass
class FunctionSpec:
    """One Lambda the consumer wants. Only code/handler are mandatory."""

    name: str
    code_path: str  # asset directory with the handler (consumer-owned code)
    handler: str = "handler.main"
    memory_mb: int = 256
    timeout_seconds: int = 30
    schedule: str | None = None  # EventBridge expression, e.g. "rate(1 day)"
    api: ApiRoute | None = None
    environment: dict[str, str] | None = None


@dataclass
class NotebookSpec:
    """A scheduled notebook runner. The .ipynb is consumer-owned code."""

    name: str
    path: str  # e.g. "notebooks/report.ipynb"
    schedule: str = "rate(1 day)"


@dataclass
class ServiceSpec:
    functions: list[FunctionSpec] = field(default_factory=list)
    notebooks: list[NotebookSpec] = field(default_factory=list)


def _cid(name: str) -> str:
    """CDK construct id — alnum only (underscores/dashes are not allowed in ids)."""
    return "".join(p.capitalize() for p in name.replace("-", "_").split("_"))


def build_service(scope: Construct, spec: ServiceSpec) -> None:
    """Materialize a ServiceSpec into governed resources on the enclosing stack.

    Every Lambda is a :class:`SecureLambda` (in-VPC, KMS-encrypted, bounded);
    API routes share one PRIVATE API Gateway locked to the account VPC endpoint;
    schedules and notebook runners use EventBridge.
    """
    cfg = PlatformEnvironment.of(scope)
    api: apigateway.RestApi | None = None

    for fn in spec.functions:
        secure = SecureLambda(
            scope,
            _cid(fn.name),
            props=SecureLambdaProps(
                code=_lambda.Code.from_asset(fn.code_path),
                handler=fn.handler,
                memory_mb=fn.memory_mb,
                timeout_seconds=fn.timeout_seconds,
                environment=fn.environment,
            ),
        )
        if fn.schedule:
            events.Rule(
                scope,
                _cid(fn.name) + "Schedule",
                schedule=events.Schedule.expression(fn.schedule),
                targets=[targets.LambdaFunction(secure.function)],
            )
        if fn.api:
            if api is None:
                api = _private_api(scope, cfg)
            resource = api.root.resource_for_path(fn.api.path)
            resource.add_method(
                fn.api.method,
                apigateway.LambdaIntegration(secure.function, proxy=True),
            )

    for nb in spec.notebooks:
        runner = SecureLambda(
            scope,
            _cid(nb.name) + "NotebookRunner",
            props=SecureLambdaProps(
                # Placeholder runner; a real runner executes the .ipynb (papermill /
                # Batch / Glue). The consumer contribution (the notebook) is unchanged.
                code=_lambda.Code.from_inline(
                    "def main(event, context):\n    return {'ran': True}\n"
                ),
                handler="index.main",
                environment={"NOTEBOOK_KEY": nb.path},
            ),
        )
        events.Rule(
            scope,
            _cid(nb.name) + "NotebookSchedule",
            schedule=events.Schedule.expression(nb.schedule),
            targets=[targets.LambdaFunction(runner.function)],
        )


def _private_api(scope: Construct, cfg) -> apigateway.RestApi:
    """A PRIVATE REST API reachable only via the account's execute-api VPC endpoint."""
    vpce_id = cfg.execute_api_vpc_endpoint.vpc_endpoint_id
    policy = iam.PolicyDocument(
        statements=[
            iam.PolicyStatement(
                effect=iam.Effect.DENY,
                principals=[iam.AnyPrincipal()],
                actions=["execute-api:Invoke"],
                resources=["execute-api:/*"],
                conditions={"StringNotEquals": {"aws:SourceVpce": vpce_id}},
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.AnyPrincipal()],
                actions=["execute-api:Invoke"],
                resources=["execute-api:/*"],
            ),
        ]
    )
    api = apigateway.RestApi(
        scope,
        "ServiceApi",
        rest_api_name="service-api",
        endpoint_configuration=apigateway.EndpointConfiguration(
            types=[apigateway.EndpointType.PRIVATE],
            vpc_endpoints=[cfg.execute_api_vpc_endpoint],
        ),
        policy=policy,
    )
    return api


__all__ = ["ApiRoute", "FunctionSpec", "NotebookSpec", "ServiceSpec", "build_service"]
