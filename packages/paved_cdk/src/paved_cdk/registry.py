"""AccountRegistry - the source of truth for all managed accounts, in code.

This module is the contract that the SSM well-known paths (and the customer's old
DynamoDB table) used to be: it lists every AWS account the platform manages and the
baseline each one exposes. It is plain Python committed to the platform repo, so:

* **Deterministic** - same commit, same config; no value can change underneath a
  synth (unlike a live SSM/DynamoDB read).
* **Reviewable** - onboarding a team or rotating a subnet is a pull request with a
  readable diff, validated by CI before merge.
* **Offline** - CDK synthesizes without AWS credentials.

The ``from_*Attributes`` importers used downstream (``Vpc.from_vpc_attributes`` etc.)
are NOT AWS lookups - they take these id strings and bake them into the template as
literals. The registry just decides where those strings come from: a git-versioned
value, never a runtime read.

Accounts are grouped by **team**: every team gets three accounts (dev/preprod/prod),
each with its own VPC, subnets, KMS key and execute-api endpoint. A consumer never
names a VPC - it names its ``team``; the platform resolves the team's account for the
stage being deployed (see :meth:`AccountRegistry.account_for`) and reads the baseline
from there. Onboarding a team is a pull request adding its three accounts below.

Account ids are **not** hard-coded: each account reads its id from a per-team
environment variable and falls back to an illustrative placeholder when unset, so the
library imports, synthesizes and tests offline while real account numbers stay out of
the public repo. The KMS and permissions-boundary ARNs are derived from the resolved
account id. Everything else (VPC, subnets, AZs, KMS key id, execute-api endpoint) is
static config in code.

| Team      | Stage   | Account id env var                         | Placeholder  |
|-----------|---------|--------------------------------------------|--------------|
| ds        | dev     | ``PAVED_CDK_DS_DEV_ACCOUNT_ID``             | 111111111111 |
| ds        | preprod | ``PAVED_CDK_DS_PREPROD_ACCOUNT_ID``         | 222222222222 |
| ds        | prod    | ``PAVED_CDK_DS_PROD_ACCOUNT_ID``            | 333333333333 |
| marketing | dev     | ``PAVED_CDK_MARKETING_DEV_ACCOUNT_ID``      | 444444444444 |
| marketing | preprod | ``PAVED_CDK_MARKETING_PREPROD_ACCOUNT_ID``  | 555555555555 |
| marketing | prod    | ``PAVED_CDK_MARKETING_PROD_ACCOUNT_ID``     | 666666666666 |

Caveat (PoC): the ``ds`` baseline is wired to a **default VPC** and its subnets,
which are technically public; a real deployment uses dedicated private subnets. The
``marketing`` team is an **illustrative** second team - replace its ids with real ones
when it is actually onboarded. The preprod/prod execute-api endpoints are illustrative;
an interface endpoint must exist in the target account before deploying a private API.
"""

from __future__ import annotations

import os

from .account import PlatformAccount
from .config import PlatformConfigError

_REGION = "eu-west-1"
_BOUNDARY_POLICY_NAME = "platform-permissions-boundary"
_DEFAULT_AZS = ("eu-west-1a", "eu-west-1b", "eu-west-1c")


def _acct(team: str, stage: str, placeholder: str) -> str:
    """Account id from the per-team/stage env var, with an offline-safe placeholder."""
    return os.environ.get(f"PAVED_CDK_{team.upper()}_{stage.upper()}_ACCOUNT_ID", placeholder)


def _kms_arn(account_id: str, key_id: str) -> str:
    return f"arn:aws:kms:{_REGION}:{account_id}:key/{key_id}"


def _boundary_arn(account_id: str) -> str:
    return f"arn:aws:iam::{account_id}:policy/{_BOUNDARY_POLICY_NAME}"


def _account(
    team: str,
    stage: str,
    placeholder: str,
    *,
    vpc_id: str,
    subnets: tuple[str, ...],
    vpce: str,
    kms_key_id: str,
    azs: tuple[str, ...] = _DEFAULT_AZS,
) -> PlatformAccount:
    """Build one account's baseline; derives the id, KMS and boundary ARNs."""
    account_id = _acct(team, stage, placeholder)
    return PlatformAccount(
        account_id=account_id,
        region=_REGION,
        environment=stage,
        team=team,
        vpc_id=vpc_id,
        private_subnet_ids=subnets,
        availability_zones=azs,
        execute_api_vpc_endpoint_id=vpce,
        kms_key_arn=_kms_arn(account_id, kms_key_id),
        permissions_boundary_arn=_boundary_arn(account_id),
    )


# --- The registry data. Three accounts per team. Onboard a team via PR. ------
_ACCOUNTS: tuple[PlatformAccount, ...] = (
    # === team "ds" (real baseline) ===========================================
    _account(
        "ds", "dev", "111111111111",
        vpc_id="vpc-0c867bce9f2e26b50",
        subnets=(
            "subnet-0c170a7b7245d3384",
            "subnet-0aaff7625fecf62a0",
            "subnet-0effb74af1e4a9ec2",
        ),
        vpce="vpce-02322cfeb68fa0bbf",
        kms_key_id="a6953c24-56c8-4cbe-b5a9-5eac7ad2a093",
    ),
    _account(
        "ds", "preprod", "222222222222",
        vpc_id="vpc-08e66b603bb4c0a15",
        subnets=(
            "subnet-0190a27c33d831ce2",
            "subnet-08c5c48fc5e4006fc",
            "subnet-0d2bb9eaa79d5a537",
        ),
        vpce="vpce-0c4658dc79ca9db62",
        kms_key_id="582af01d-d4fd-47dc-a051-a840009e7e94",
    ),
    _account(
        "ds", "prod", "333333333333",
        vpc_id="vpc-0d10221d7be12fba4",
        subnets=(
            "subnet-05519630e3f0fef45",
            "subnet-097ead93a71177125",
            "subnet-0bdc3a7d06f7349d9",
        ),
        vpce="vpce-02de7b987c7c3c33f",
        kms_key_id="f183202b-b6d7-4d76-b1da-2a843b0c39e5",
    ),
    # === team "marketing" (illustrative - replace ids on real onboarding) =====
    _account(
        "marketing", "dev", "444444444444",
        vpc_id="vpc-0a11b22c33d44e550",
        subnets=("subnet-0a11d00000000001", "subnet-0a11d00000000002", "subnet-0a11d00000000003"),
        vpce="vpce-0a11e00000000001",
        kms_key_id="11111111-1111-1111-1111-111111111111",
    ),
    _account(
        "marketing", "preprod", "555555555555",
        vpc_id="vpc-0b22c33d44e55f660",
        subnets=("subnet-0b22d00000000001", "subnet-0b22d00000000002", "subnet-0b22d00000000003"),
        vpce="vpce-0b22e00000000001",
        kms_key_id="22222222-2222-2222-2222-222222222222",
    ),
    _account(
        "marketing", "prod", "666666666666",
        vpc_id="vpc-0c33d44e55f66a770",
        subnets=("subnet-0c33d00000000001", "subnet-0c33d00000000002", "subnet-0c33d00000000003"),
        vpce="vpce-0c33e00000000001",
        kms_key_id="33333333-3333-3333-3333-333333333333",
    ),
)


class AccountRegistry:
    """Looks an account's baseline up by AWS account id or by team + stage.

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

    def accounts_for_team(self, team: str) -> dict[str, PlatformAccount]:
        """Map ``stage -> PlatformAccount`` for one team (empty if unknown team)."""
        return {a.environment: a for a in self._by_id.values() if a.team == team}

    def account_for(self, team: str, stage: str) -> PlatformAccount:
        """Resolve one team's account for a stage (dev/preprod/prod)."""
        by_stage = self.accounts_for_team(team)
        try:
            return by_stage[stage]
        except KeyError:
            raise PlatformConfigError(
                f"No account for team={team!r} stage={stage!r}. Known teams: "
                f"{', '.join(self.teams) or '(none)'}. Onboard the team with a pull "
                f"request adding its three accounts to registry.py (see docs/adr/0012)."
            ) from None

    @property
    def teams(self) -> tuple[str, ...]:
        """All onboarded team names, sorted and de-duplicated."""
        return tuple(sorted({a.team for a in self._by_id.values()}))

    @property
    def accounts(self) -> tuple[PlatformAccount, ...]:
        return tuple(self._by_id.values())


#: The registry production code resolves against.
DEFAULT_REGISTRY = AccountRegistry()
