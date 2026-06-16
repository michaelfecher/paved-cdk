"""PlatformStack stack-naming: the pipeline-supplied STACK_PREFIX is applied so
per-PR preview stacks get isolated names, while normal deploys are unprefixed."""

from __future__ import annotations

from conftest import ENV, VALID_TAGS
from paved_cdk import PlatformStack


def test_no_prefix_by_default(app, monkeypatch):
    monkeypatch.delenv("STACK_PREFIX", raising=False)
    stack = PlatformStack(app, "demo-scoring", env=ENV, tags=VALID_TAGS)
    assert stack.stack_name == "demo-scoring"


def test_stack_prefix_applied(app, monkeypatch):
    monkeypatch.setenv("STACK_PREFIX", "pr-123-")
    stack = PlatformStack(app, "demo-scoring", env=ENV, tags=VALID_TAGS)
    assert stack.stack_name == "pr-123-demo-scoring"
