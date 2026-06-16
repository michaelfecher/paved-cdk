"""Typed, account-specific platform configuration."""

from __future__ import annotations

from dataclasses import dataclass, field

from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_kms as kms
from aws_cdk.aws_logs import RetentionDays


class PlatformConfigError(RuntimeError):
    """Raised when the account's paved-road configuration cannot be resolved.

    Messages name the cause (e.g. an account missing from the registry) and the
    remediation, so a Data Scientist with no IaC background gets an actionable error
    instead of a CDK stack trace.
    """


@dataclass(frozen=True)
class PlatformConfig:
    """Resolved configuration for the AWS account a stack deploys into.

    Produced by :class:`paved_cdk.environment.PlatformEnvironment`. Data
    Scientists never build this by hand — the platform constructs consume it
    internally so that no ``vpc=`` / ``env=`` / ``kms=`` arguments leak into user
    code.
    """

    account: str
    region: str
    environment: str  # dev | preprod | prod
    vpc: ec2.IVpc
    private_subnet_ids: list[str]
    execute_api_vpc_endpoint: ec2.IInterfaceVpcEndpoint
    kms_key: kms.IKey
    permissions_boundary_arn: str
    log_retention: RetentionDays
    default_tags: dict[str, str] = field(default_factory=dict)

    @property
    def is_production(self) -> bool:
        return self.environment == "prod"
