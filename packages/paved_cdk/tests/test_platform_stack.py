"""PlatformStack stack-naming: ``$stage-$stackPrefix-$project``. The stage prefixes
every stack; the optional STACK_PREFIX (e.g. for PR previews) sits between stage and
project; empty parts are dropped (no double dash)."""

from __future__ import annotations

from conftest import ENV, VALID_TAGS
from paved_cdk import PlatformStack


def test_stage_prefixed_name_by_default(app, monkeypatch):
    monkeypatch.delenv("STACK_PREFIX", raising=False)
    monkeypatch.delenv("PAVED_CDK_STAGE", raising=False)  # default stage = dev
    stack = PlatformStack(app, "demo-scoring", env=ENV, tags=VALID_TAGS)
    assert stack.stack_name == "dev-demo-scoring"


def test_stack_prefix_sits_between_stage_and_project(app, monkeypatch):
    monkeypatch.delenv("PAVED_CDK_STAGE", raising=False)
    monkeypatch.setenv("STACK_PREFIX", "pr123")
    stack = PlatformStack(app, "demo-scoring", env=ENV, tags=VALID_TAGS)
    assert stack.stack_name == "dev-pr123-demo-scoring"


def test_stage_comes_from_env(app, monkeypatch):
    monkeypatch.delenv("STACK_PREFIX", raising=False)
    monkeypatch.setenv("PAVED_CDK_STAGE", "prod")
    stack = PlatformStack(app, "demo-scoring", env=ENV, tags=VALID_TAGS)
    assert stack.stack_name == "prod-demo-scoring"
