"""``paved-cdk-synth`` console script — synth a declarative consumer with no Python.

A declarative consumer's ``cdk.json`` is just ``{"app": "paved-cdk-synth"}``. The CDK
CLI runs this entry point in the consumer's directory; we load ``service.yaml``, derive
governance tags, and materialize the shared :class:`ServiceSpec` onto a PlatformStack.
"""

from __future__ import annotations

import logging
import os

import aws_cdk as cdk

from .. import PlatformStack, build_service
from . import manifest

log = logging.getLogger(__name__)


def _cdk_safe_id(value: str | None, default: str) -> str:
    """A CDK/CloudFormation-safe construct id: alnum only, never empty."""
    raw = value or default
    cleaned = "".join(ch for ch in raw.title() if ch.isalnum())
    return cleaned or default


def _tags(owner: str | None) -> dict[str, str]:
    """Governance tags: manifest owner (or env) + team/cost-center from env."""
    return {
        "Owner": owner or os.environ.get("PAVED_CDK_OWNER", "ds@example.com"),
        "Team": os.environ.get("PAVED_CDK_TEAM", "ds"),
        "CostCenter": os.environ.get("PAVED_CDK_COST_CENTER", "4711"),
    }


def main() -> None:
    logging.basicConfig(level=os.environ.get("PAVED_CDK_LOG_LEVEL", "INFO"))

    spec = manifest.load("service.yaml")
    meta = manifest.read_meta("service.yaml")

    stack_id = _cdk_safe_id(meta.get("service_id"), "payments")
    tags = _tags(meta.get("owner"))
    log.info("synth: stack_id=%s tags=%s", stack_id, tags)

    app = cdk.App()
    stack = PlatformStack(app, stack_id, tags=tags)
    build_service(stack, spec)
    app.synth()


if __name__ == "__main__":
    main()
