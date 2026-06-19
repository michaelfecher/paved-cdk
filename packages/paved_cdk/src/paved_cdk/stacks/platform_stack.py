"""PlatformStack - the base stack Data Scientists subclass or instantiate.

It resolves the target AWS environment and applies platform governance. There are
two ways the account/region get set:

* ``team=`` (recommended): the consumer names its **team**; the stack resolves the
  team's account for the deploy ``stage`` (``PAVED_CDK_STAGE``, default ``dev``)
  from the :class:`AccountRegistry`. The consumer never sees an account id or VPC.
* ``env=`` / ``CDK_DEFAULT_ACCOUNT`` (fallback): an explicit account/region, used by
  tests and by callers that already know the target account.

The stack name is optionally **prefixed** from the ``STACK_PREFIX`` environment
variable (set by the pipeline for per-PR preview stacks, e.g. ``pr-123-``).
"""

from __future__ import annotations

import os

import aws_cdk as cdk
from constructs import Construct

from ..aspects.governance import apply_platform_governance
from ..config import PlatformConfigError
from ..environment import PlatformEnvironment
from ..registry import DEFAULT_REGISTRY


class PlatformStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        tags: dict[str, str] | None = None,
        team: str | None = None,
        stage: str | None = None,
        **kwargs,
    ) -> None:
        env = kwargs.pop("env", None)
        provided_tags = dict(tags or {})
        stage = stage or os.environ.get("PAVED_CDK_STAGE", "dev")

        # Team-driven resolution: name the team, the platform picks the account for
        # the deploy stage from the registry. The team becomes the authoritative
        # Team tag.
        if env is None and team is not None:
            account = DEFAULT_REGISTRY.account_for(team, stage)
            env = cdk.Environment(account=account.account_id, region=account.region)
            existing = provided_tags.get("Team")
            if existing is not None and existing != team:
                raise PlatformConfigError(
                    f"Team tag {existing!r} conflicts with team={team!r}. The team "
                    f"argument is authoritative; drop the Team tag or align them."
                )
            provided_tags["Team"] = team

        # Fallback: explicit account/region from CDK_DEFAULT_* (tests, known target).
        if env is None:
            env = cdk.Environment(
                account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
                region=os.environ.get("CDK_DEFAULT_REGION"),
            )

        # Stack name: ``$stage-$stackPrefix-$project``. STACK_PREFIX is optional (e.g.
        # ``pr123`` for PR-preview deploys); empty parts are dropped so there is no
        # double dash. The stage prefix keeps dev/test/prod (and PR previews) from
        # colliding in the same account.
        prefix = os.environ.get("STACK_PREFIX", "")
        stack_name = "-".join(part for part in (stage, prefix, id) if part)
        super().__init__(scope, stack_name, env=env, **kwargs)

        # Governance tags supplied by the caller (the Copier template injects
        # Owner/Team/CostCenter from the scaffold answers).
        self._provided_tags = provided_tags
        for key, value in self._provided_tags.items():
            cdk.Tags.of(self).add(key, value)

        # Resolve the account config ONCE; constructs reuse it via
        # PlatformEnvironment.of(scope).
        self.platform_config = PlatformEnvironment.resolve(self)
        apply_platform_governance(self, self.platform_config, self._provided_tags)
