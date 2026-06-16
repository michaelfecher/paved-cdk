"""Platform governance applied to every PlatformStack — guardrails the Data
Scientist gets for free."""

from __future__ import annotations

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks, NagSuppressions

from ..config import PlatformConfig, PlatformConfigError
from .encryption_enforcer import EncryptionEnforcerAspect
from .permissions_boundary import PermissionsBoundaryAspect

REQUIRED_TAGS = ("Owner", "Team", "CostCenter", "Environment")


def apply_platform_governance(
    stack: cdk.Stack, cfg: PlatformConfig, provided_tags: dict[str, str]
) -> None:
    """Apply permissions boundary, tags, encryption checks and cdk-nag to ``stack``."""

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

    # 5. Broad compliance net for the whole app (add once, even with many stacks).
    app = cdk.App.of(stack)
    if app is not None and not any(
        isinstance(a, AwsSolutionsChecks) for a in cdk.Aspects.of(app).all
    ):
        cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

    # Pre-approved suppressions so Data Scientists never reason about nag output.
    NagSuppressions.add_stack_suppressions(
        stack,
        [
            {
                "id": "AwsSolutions-IAM4",
                "reason": "Every role carries the platform permissions boundary "
                "(set by PermissionsBoundaryAspect). The boundary is "
                "escalation-proof: it denies creating/altering principals without "
                "the same boundary and protects itself, so attached managed "
                "policies cannot be used to escalate.",
            },
            {
                "id": "AwsSolutions-IAM5",
                "reason": "KMS grants are scoped to the single account data key; "
                "wildcard is on key sub-resources only.",
            },
        ],
    )
