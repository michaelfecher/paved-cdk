"""SecureLambda — the paved-road Lambda brick.

A data scientist supplies only the *code*, *handler* and *runtime*; everything
security- and network-relevant is wired from the resolved :class:`PlatformConfig`:

* runs **inside the account VPC** (private subnets from the registry),
* **environment variables encrypted** with the account KMS key,
* a dedicated **log group** with the account's retention (RETAIN in prod),
* the IAM execution role carries the **permissions boundary** automatically (via
  the platform aspect on the stack).

The ``code`` comes from the *consumer* repo (e.g. ``Code.from_asset("src/...")``) —
the construct is the secure envelope, the workload provides the filling.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_logs as logs
from constructs import Construct

from ..environment import PlatformEnvironment


@dataclass
class SecureLambdaProps:
    """The knobs a data scientist may turn. No vpc/kms/role/boundary args — those
    come from the account baseline."""

    code: _lambda.Code
    handler: str = "handler.main"
    runtime: _lambda.Runtime = field(default_factory=lambda: _lambda.Runtime.PYTHON_3_12)
    timeout_seconds: int = 30
    memory_mb: int = 256
    environment: dict[str, str] | None = None


class SecureLambda(Construct):
    """An in-VPC, KMS-encrypted Lambda wired from the account baseline."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        props: SecureLambdaProps,
    ) -> None:
        super().__init__(scope, id)
        cfg = PlatformEnvironment.of(self)

        # Dedicated log group (avoids the deprecated log_retention custom resource);
        # retention + removal follow the account's environment.
        log_group = logs.LogGroup(
            self,
            "Logs",
            retention=cfg.log_retention,
            removal_policy=RemovalPolicy.RETAIN if cfg.is_production else RemovalPolicy.DESTROY,
        )

        self.function = _lambda.Function(
            self,
            "Fn",
            runtime=props.runtime,
            handler=props.handler,
            code=props.code,
            vpc=cfg.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=cfg.vpc.private_subnets),
            environment=props.environment or {},
            environment_encryption=cfg.kms_key,  # encrypts env vars with the account key
            timeout=Duration.seconds(props.timeout_seconds),
            memory_size=props.memory_mb,
            log_group=log_group,
        )

    @property
    def function_name(self) -> str:
        return self.function.function_name
