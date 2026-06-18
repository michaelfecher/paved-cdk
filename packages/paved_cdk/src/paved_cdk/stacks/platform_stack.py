"""PlatformStack - the base stack Data Scientists subclass or instantiate.

It wires the AWS environment from CDK_DEFAULT_ACCOUNT/REGION (so synth-time
lookups have a concrete account/region) and applies platform governance.

The stack name is optionally **prefixed** from the ``STACK_PREFIX`` environment
variable (set by the pipeline for per-PR preview stacks, e.g. ``pr-123-``). The
Data Scientist writes ``PlatformStack(app, "my-stack")`` and never deals with the
prefix - the platform applies it so PR previews get isolated, named stacks.
"""

from __future__ import annotations

import os

import aws_cdk as cdk
from constructs import Construct

from ..aspects.governance import apply_platform_governance
from ..environment import PlatformEnvironment


class PlatformStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        tags: dict[str, str] | None = None,
        **kwargs,
    ) -> None:
        env = kwargs.pop("env", None) or cdk.Environment(
            account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
            region=os.environ.get("CDK_DEFAULT_REGION"),
        )
        # Pipeline-supplied prefix for ephemeral PR-preview stacks; empty otherwise.
        # Applied to the stack id (-> CloudFormation stack name) so previews don't
        # collide with the persistent dev/preprod/prod stacks.
        prefix = os.environ.get("STACK_PREFIX", "")
        super().__init__(scope, f"{prefix}{id}" if prefix else id, env=env, **kwargs)

        # Governance tags supplied by the caller (the Copier template injects
        # Owner/Team/CostCenter into app.py from the scaffold answers).
        self._provided_tags = dict(tags or {})
        for key, value in self._provided_tags.items():
            cdk.Tags.of(self).add(key, value)

        # Resolve the account config ONCE; constructs reuse it via
        # PlatformEnvironment.of(scope).
        self.platform_config = PlatformEnvironment.resolve(self)
        apply_platform_governance(self, self.platform_config, self._provided_tags)
