"""Account-aware resolution of the paved-road :class:`PlatformConfig`.

This is the heart of the platform: given any CDK scope, it looks the stack's
target account up in the :class:`AccountRegistry` (static config in code) and
builds a typed :class:`PlatformConfig` - so consumer code never passes ``vpc=`` /
``env=`` / ``kms=``.

All values come from concrete strings in the registry, fed into the CDK
``from_*`` importers (``Vpc.from_vpc_attributes``, ``Key.from_key_arn``,
``SecurityGroup.from_security_group_id``). These do **not** call AWS: resolution
is deterministic and works offline, without credentials. See ADR 0008 for why we
moved off synth-time SSM lookups to a static, source-controlled registry.
"""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_kms as kms
from aws_cdk.aws_logs import RetentionDays
from constructs import Construct

from .config import PlatformConfig, PlatformConfigError
from .registry import DEFAULT_REGISTRY, AccountRegistry


class PlatformEnvironment:
    """Resolves :class:`PlatformConfig` for the account a stack targets."""

    @staticmethod
    def of(scope: Construct) -> PlatformConfig:
        """Return the config cached on the enclosing :class:`PlatformStack`, or
        resolve it fresh if the scope is not inside a ``PlatformStack``.

        Constructs should call this (not :meth:`resolve`) so resolution happens
        exactly once per stack.
        """
        stack = cdk.Stack.of(scope)
        cached = getattr(stack, "platform_config", None)
        if cached is not None:
            return cached
        return PlatformEnvironment.resolve(scope)

    @staticmethod
    def resolve(
        scope: Construct, registry: AccountRegistry = DEFAULT_REGISTRY
    ) -> PlatformConfig:
        stack = cdk.Stack.of(scope)
        if cdk.Token.is_unresolved(stack.account) or cdk.Token.is_unresolved(stack.region):
            raise PlatformConfigError(
                "PlatformEnvironment needs a concrete AWS account and region. Use "
                "PlatformStack (which wires env from CDK_DEFAULT_ACCOUNT / "
                "CDK_DEFAULT_REGION), or pass env=cdk.Environment(account=..., "
                "region=...) to your stack."
            )

        account = registry.resolve(stack.account)

        # All importers below take concrete strings - no AWS lookup, fully
        # deterministic at synth.
        vpc = ec2.Vpc.from_vpc_attributes(
            scope,
            "PlatformVpc",
            vpc_id=account.vpc_id,
            availability_zones=list(account.availability_zones),
            private_subnet_ids=list(account.private_subnet_ids),
        )
        execute_api_endpoint = ec2.InterfaceVpcEndpoint.from_interface_vpc_endpoint_attributes(
            scope,
            "PlatformExecuteApiVpce",
            vpc_endpoint_id=account.execute_api_vpc_endpoint_id,
            port=443,
        )
        key = kms.Key.from_key_arn(scope, "PlatformKmsKey", account.kms_key_arn)

        return PlatformConfig(
            account=account.account_id,
            region=account.region,
            environment=account.environment,
            vpc=vpc,
            private_subnet_ids=list(account.private_subnet_ids),
            execute_api_vpc_endpoint=execute_api_endpoint,
            kms_key=key,
            permissions_boundary_arn=account.permissions_boundary_arn,
            log_retention=RetentionDays.SIX_MONTHS
            if account.is_production
            else RetentionDays.ONE_MONTH,
            default_tags={"ManagedBy": "paved-cdk"},
        )
