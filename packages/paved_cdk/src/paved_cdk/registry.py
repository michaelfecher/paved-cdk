"""AccountRegistry - the source of truth for all managed accounts, in code.

This module is the contract that the SSM well-known paths used to be: it lists
every AWS account the platform manages and the baseline each one exposes. It is
plain Python committed to the platform repo, so:

* **Deterministic** - same commit, same config; no value can change underneath a
  synth (unlike a live SSM/DynamoDB read).
* **Reviewable** - onboarding a team or rotating a subnet is a pull request with a
  readable diff, validated by CI before merge.
* **Offline** - CDK synthesizes without AWS credentials.

Account ids are **not** hard-coded here: each stage reads its id from an
environment variable and falls back to an illustrative placeholder when that var
is unset, so the library imports, synthesizes and tests offline
while real account numbers stay out of the public repo. The KMS and permissions
boundary ARNs are derived from the resolved account id, so they carry no real
account number either. Everything else (VPC, subnets, AZs, KMS key id, the
execute-api endpoint) is static config in code.

| Stage   | Account id env var              | Placeholder    |
|---------|---------------------------------|----------------|
| dev     | ``PAVED_CDK_DEV_ACCOUNT_ID``     | 111111111111   |
| preprod | ``PAVED_CDK_PREPROD_ACCOUNT_ID`` | 222222222222   |
| prod    | ``PAVED_CDK_PROD_ACCOUNT_ID``    | 333333333333   |

Caveat (PoC): the example baseline is wired to a **default VPC** and its subnets,
which are technically public (``MapPublicIpOnLaunch=true``); a real deployment
uses dedicated private subnets. The ``preprod``/``prod`` execute-api endpoints are
illustrative; an interface endpoint must exist in the target account before
deploying a private API (``SecureDataApi``), otherwise that deploy fails - synth
itself only needs the id string (``from_interface_vpc_endpoint_attributes`` makes
no AWS call).
"""

from __future__ import annotations

import os

from .account import PlatformAccount
from .config import PlatformConfigError

_REGION = "eu-west-1"
_BOUNDARY_POLICY_NAME = "platform-permissions-boundary"


def _account_id(env_var: str, placeholder: str) -> str:
    """Account id from the environment, with an offline-safe placeholder fallback."""
    return os.environ.get(env_var, placeholder)


def _kms_arn(account_id: str, key_id: str) -> str:
    return f"arn:aws:kms:{_REGION}:{account_id}:key/{key_id}"


def _boundary_arn(account_id: str) -> str:
    return f"arn:aws:iam::{account_id}:policy/{_BOUNDARY_POLICY_NAME}"


_DEV_ACCOUNT = _account_id("PAVED_CDK_DEV_ACCOUNT_ID", "111111111111")
_PREPROD_ACCOUNT = _account_id("PAVED_CDK_PREPROD_ACCOUNT_ID", "222222222222")
_PROD_ACCOUNT = _account_id("PAVED_CDK_PROD_ACCOUNT_ID", "333333333333")

# --- The registry data. One PlatformAccount per managed AWS account. ---------
# Onboard a team by adding their three accounts here via pull request.
_ACCOUNTS: tuple[PlatformAccount, ...] = (
    PlatformAccount(
        account_id=_DEV_ACCOUNT,
        region=_REGION,
        environment="dev",
        team="ds",
        vpc_id="vpc-0c867bce9f2e26b50",
        private_subnet_ids=(
            "subnet-0c170a7b7245d3384",
            "subnet-0aaff7625fecf62a0",
            "subnet-0effb74af1e4a9ec2",
        ),
        availability_zones=("eu-west-1a", "eu-west-1b", "eu-west-1c"),
        execute_api_vpc_endpoint_id="vpce-02322cfeb68fa0bbf",
        kms_key_arn=_kms_arn(_DEV_ACCOUNT, "a6953c24-56c8-4cbe-b5a9-5eac7ad2a093"),
        permissions_boundary_arn=_boundary_arn(_DEV_ACCOUNT),
    ),
    PlatformAccount(
        account_id=_PREPROD_ACCOUNT,
        region=_REGION,
        environment="preprod",
        team="ds",
        vpc_id="vpc-08e66b603bb4c0a15",
        private_subnet_ids=(
            "subnet-0190a27c33d831ce2",
            "subnet-08c5c48fc5e4006fc",
            "subnet-0d2bb9eaa79d5a537",
        ),
        availability_zones=("eu-west-1a", "eu-west-1b", "eu-west-1c"),
        execute_api_vpc_endpoint_id="vpce-0c4658dc79ca9db62",
        kms_key_arn=_kms_arn(_PREPROD_ACCOUNT, "582af01d-d4fd-47dc-a051-a840009e7e94"),
        permissions_boundary_arn=_boundary_arn(_PREPROD_ACCOUNT),
    ),
    PlatformAccount(
        account_id=_PROD_ACCOUNT,
        region=_REGION,
        environment="prod",
        team="ds",
        vpc_id="vpc-0d10221d7be12fba4",
        private_subnet_ids=(
            "subnet-05519630e3f0fef45",
            "subnet-097ead93a71177125",
            "subnet-0bdc3a7d06f7349d9",
        ),
        availability_zones=("eu-west-1a", "eu-west-1b", "eu-west-1c"),
        execute_api_vpc_endpoint_id="vpce-02de7b987c7c3c33f",
        kms_key_arn=_kms_arn(_PROD_ACCOUNT, "f183202b-b6d7-4d76-b1da-2a843b0c39e5"),
        permissions_boundary_arn=_boundary_arn(_PROD_ACCOUNT),
    ),
)


class AccountRegistry:
    """Looks an account's baseline up by its AWS account id.

    Construct with an explicit ``accounts`` tuple in tests; production code uses
    :data:`DEFAULT_REGISTRY`.
    """

    def __init__(self, accounts: tuple[PlatformAccount, ...] = _ACCOUNTS) -> None:
        self._by_id: dict[str, PlatformAccount] = {}
        for account in accounts:
            if account.account_id in self._by_id:
                raise PlatformConfigError(
                    f"Duplicate account_id {account.account_id} in the registry."
                )
            self._by_id[account.account_id] = account

    def resolve(self, account_id: str) -> PlatformAccount:
        try:
            return self._by_id[account_id]
        except KeyError:
            known = ", ".join(sorted(self._by_id)) or "(none)"
            raise PlatformConfigError(
                f"AWS account {account_id} is not in the platform registry. Onboard "
                f"it with a pull request adding a PlatformAccount entry (see "
                f"docs/adr/0008). Known accounts: {known}."
            ) from None

    @property
    def accounts(self) -> tuple[PlatformAccount, ...]:
        return tuple(self._by_id.values())


#: The registry production code resolves against.
DEFAULT_REGISTRY = AccountRegistry()
