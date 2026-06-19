"""Team-driven configuration: a consumer names its team, the platform resolves the
team's account (and thus VPC/KMS/boundary) for the deploy stage from the in-code
registry - no account id or VPC in consumer code, no runtime lookup."""

from __future__ import annotations

import pytest
from paved_cdk import DEFAULT_REGISTRY, PlatformConfigError, PlatformStack


# --- registry: team + stage -> account ---------------------------------------
def test_account_for_resolves_team_and_stage():
    a = DEFAULT_REGISTRY.account_for("ds", "dev")
    assert a.account_id == "111111111111"
    assert a.team == "ds" and a.environment == "dev"


def test_accounts_for_team_has_three_stages():
    by_stage = DEFAULT_REGISTRY.accounts_for_team("marketing")
    assert set(by_stage) == {"dev", "preprod", "prod"}


def test_teams_lists_all_onboarded_teams():
    assert DEFAULT_REGISTRY.teams == ("ds", "marketing")


def test_resolve_by_account_id_still_works():
    a = DEFAULT_REGISTRY.resolve("222222222222")
    assert a.team == "ds" and a.environment == "preprod"


def test_unknown_team_raises_actionable_error():
    with pytest.raises(PlatformConfigError, match="Onboard the team"):
        DEFAULT_REGISTRY.account_for("ghost", "dev")


# --- PlatformStack: team= drives account/region/VPC --------------------------
def test_team_drives_account_and_vpc(app, monkeypatch):
    monkeypatch.delenv("PAVED_CDK_STAGE", raising=False)  # default stage = dev
    stack = PlatformStack(app, "svc", team="marketing", tags={"Owner": "x", "CostCenter": "1"})
    assert stack.account == "444444444444"  # marketing dev placeholder
    assert stack.region == "eu-west-1"
    assert stack.platform_config.vpc.vpc_id == "vpc-0a11b22c33d44e550"  # marketing's VPC


def test_stage_env_selects_the_account(app, monkeypatch):
    monkeypatch.setenv("PAVED_CDK_STAGE", "prod")
    stack = PlatformStack(app, "svc", team="ds", tags={"Owner": "x", "CostCenter": "1"})
    assert stack.account == "333333333333"  # ds prod
    assert stack.platform_config.is_production


def test_conflicting_team_tag_raises(app, monkeypatch):
    monkeypatch.delenv("PAVED_CDK_STAGE", raising=False)
    with pytest.raises(PlatformConfigError, match="authoritative"):
        PlatformStack(app, "svc", team="ds", tags={"Team": "marketing"})
