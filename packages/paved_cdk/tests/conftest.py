"""Shared test fixtures.

No mocked SSM context is needed any more: the account baseline comes from the
static AccountRegistry (in code), so resolution is deterministic and offline. The
constants below mirror the ``dev`` account in
``paved_cdk.registry`` (the dev placeholder, eu-west-1).
"""

from __future__ import annotations

import aws_cdk as cdk
import pytest

ACCOUNT = "111111111111"  # the dev placeholder account (env-overridable in registry)
REGION = "eu-west-1"
ENV = cdk.Environment(account=ACCOUNT, region=REGION)
UNKNOWN_ENV = cdk.Environment(account="999999999999", region=REGION)

VALID_TAGS = {"Owner": "alice@example.com", "Team": "ds", "CostCenter": "4711"}


@pytest.fixture
def app() -> cdk.App:
    return cdk.App()
