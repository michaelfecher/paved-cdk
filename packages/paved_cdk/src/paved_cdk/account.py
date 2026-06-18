"""PlatformAccount - one managed AWS account's baseline configuration, in code.

Each team gets three AWS accounts (dev/preprod/prod). The
per-account baseline - which VPC, subnets, AZs, KMS key, security group and IAM
permissions boundary the paved road uses - is recorded as plain, typed Python
data. No SSM, no DynamoDB, no live lookup: CDK reads it deterministically when
the app runs, so the same commit always yields the same configuration and the
app synthesizes offline, without AWS credentials.

Adding or changing an account is a reviewed pull request against the registry
(see ``registry.py`` and ``docs/adr/0008``). CI validates the entry and proves it
synthesizes before merge - GitHub stays the single source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import PlatformConfigError

_VALID_ENVIRONMENTS = ("dev", "preprod", "prod")


@dataclass(frozen=True)
class PlatformAccount:
    """The baseline an account exposes to the platform. Immutable and hashable so
    it is safe to share across constructs and cache.

    Tuples (not lists) for the id collections keep the dataclass hashable and make
    accidental mutation impossible.
    """

    account_id: str
    region: str
    environment: str  # dev | preprod | prod
    team: str
    vpc_id: str
    private_subnet_ids: tuple[str, ...]
    availability_zones: tuple[str, ...]
    # Interface VPC endpoint for execute-api, so a PRIVATE API Gateway resolves
    # privately inside the account (no public internet path).
    execute_api_vpc_endpoint_id: str
    kms_key_arn: str
    permissions_boundary_arn: str

    def __post_init__(self) -> None:
        # Fail fast with an actionable message; CI runs the same checks on the PR
        # so a bad entry never reaches main.
        if not (self.account_id.isdigit() and len(self.account_id) == 12):
            raise PlatformConfigError(
                f"PlatformAccount.account_id must be a 12-digit AWS account id, "
                f"got {self.account_id!r} (team={self.team!r})."
            )
        if self.environment not in _VALID_ENVIRONMENTS:
            raise PlatformConfigError(
                f"PlatformAccount.environment must be one of {_VALID_ENVIRONMENTS}, "
                f"got {self.environment!r} (account={self.account_id})."
            )
        if not self.private_subnet_ids:
            raise PlatformConfigError(
                f"PlatformAccount {self.account_id} ({self.environment}) has no "
                f"private_subnet_ids - the paved road needs at least one."
            )

    @property
    def is_production(self) -> bool:
        return self.environment == "prod"
