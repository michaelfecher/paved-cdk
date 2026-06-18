"""Platform governance applied to every PlatformStack — guardrails the Data
Scientist gets for free."""

from __future__ import annotations

import aws_cdk as cdk

from ..config import PlatformConfig, PlatformConfigError
from .encryption_enforcer import EncryptionEnforcerAspect
from .permissions_boundary import PermissionsBoundaryAspect

REQUIRED_TAGS = ("Owner", "Team", "CostCenter", "Environment")


def apply_platform_governance(
    stack: cdk.Stack, cfg: PlatformConfig, provided_tags: dict[str, str]
) -> None:
    """Apply permissions boundary, mandatory tags and encryption checks to ``stack``."""

    # 1. Permissions boundary on EVERY IAM role the app creates (covers roles
    #    inside vendor constructs too).
    cdk.Aspects.of(stack).add(PermissionsBoundaryAspect(cfg.permissions_boundary_arn))

    # 2. Platform default tags + the environment tag.
    cdk.Tags.of(stack).add("Environment", cfg.environment)
    for key, value in cfg.default_tags.items():
        cdk.Tags.of(stack).add(key, value)

    # 3. Validate the mandatory governance tags are present (deterministic: we check
    #    the caller-provided dict, not fragile tag-propagation introspection).
    present = set(provided_tags) | {"Environment"} | set(cfg.default_tags)
    missing = [t for t in REQUIRED_TAGS if t not in present]
    if missing:
        raise PlatformConfigError(
            f"Stack '{stack.stack_name}' is missing required governance tags: {missing}. "
            f"The Copier template injects Owner/Team/CostCenter into app.py from your "
            f"answers — re-run `copier copy` / `copier update`, or pass them via "
            f"PlatformStack(..., tags={{...}})."
        )

    # 4. Fail-closed encryption enforcement on this stack.
    cdk.Aspects.of(stack).add(EncryptionEnforcerAspect())

    # NOTE: cdk-nag (AwsSolutionsChecks) was removed for now. The boundary, tag and
    # encryption guardrails above still apply. Re-add cdk-nag here when desired.
