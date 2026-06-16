"""Account-aware resolution behaviour (static registry)."""

from __future__ import annotations

import aws_cdk as cdk
import pytest
from conftest import ENV, UNKNOWN_ENV
from paved_cdk import PlatformConfigError, PlatformEnvironment


def test_resolve_requires_concrete_account_and_region(app):
    # An env-agnostic stack (no account/region) must fail fast with a clear error.
    stack = cdk.Stack(app, "Agnostic")
    with pytest.raises(PlatformConfigError, match="concrete AWS account"):
        PlatformEnvironment.resolve(stack)


def test_resolve_reads_baseline_from_registry(app):
    stack = cdk.Stack(app, "Concrete", env=ENV)
    cfg = PlatformEnvironment.resolve(stack)
    assert cfg.account == "111111111111"
    assert cfg.environment == "dev"
    assert cfg.is_production is False
    # Values come straight from the registry — no SSM, no lookup.
    assert cfg.private_subnet_ids == [
        "subnet-0c170a7b7245d3384",
        "subnet-0aaff7625fecf62a0",
        "subnet-0effb74af1e4a9ec2",
    ]


def test_resolve_unknown_account_raises(app):
    stack = cdk.Stack(app, "Unknown", env=UNKNOWN_ENV)
    with pytest.raises(PlatformConfigError, match="not in the platform registry"):
        PlatformEnvironment.resolve(stack)
