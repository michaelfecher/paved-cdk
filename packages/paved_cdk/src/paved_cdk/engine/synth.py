"""``paved-cdk-synth`` console script - synth a declarative consumer with no Python.

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


def _tags(meta: dict) -> dict[str, str]:
    """Governance tags from the manifest (owner/team/cost_center), env as fallback."""
    return {
        "Owner": meta.get("owner") or os.environ.get("PAVED_CDK_OWNER", "ds@example.com"),
        "Team": meta.get("team") or os.environ.get("PAVED_CDK_TEAM", "ds"),
        "CostCenter": (
            meta.get("cost_center") or os.environ.get("PAVED_CDK_COST_CENTER", "4711")
        ),
    }


def main() -> None:
    logging.basicConfig(level=os.environ.get("PAVED_CDK_LOG_LEVEL", "INFO"))

    spec = manifest.load("service.yaml")
    meta = manifest.read_meta("service.yaml")

    project = meta.get("service_id") or "payments"
    tags = _tags(meta)
    log.info("synth: project=%s team=%s tags=%s", project, meta.get("team"), tags)

    app = cdk.App()
    # team drives the account baseline (PlatformStack); the stack is named
    # $stage-$stackPrefix-$project from there.
    stack = PlatformStack(app, project, team=meta.get("team"), tags=tags)
    build_service(stack, spec)
    app.synth()


if __name__ == "__main__":
    main()
