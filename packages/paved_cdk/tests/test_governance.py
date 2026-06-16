"""Governance guardrails: mandatory tags and fail-closed encryption."""

from __future__ import annotations

import pytest
from aws_cdk import assertions
from aws_cdk import aws_s3 as s3
from conftest import ENV, VALID_TAGS
from paved_cdk import PlatformConfigError, PlatformStack


def test_missing_governance_tags_raises(app):
    with pytest.raises(PlatformConfigError, match="missing required governance tags"):
        PlatformStack(app, "NoTags", env=ENV, tags={"Owner": "a@example.com"})


def test_encryption_enforcer_errors_on_unencrypted_bucket(app):
    stack = PlatformStack(app, "Test", env=ENV, tags=VALID_TAGS)
    # A raw, unencrypted bucket must trip the fail-closed encryption aspect, which
    # adds an error annotation (cdk synth then fails in CI).
    s3.CfnBucket(stack, "RawBucket")
    annotations = assertions.Annotations.from_stack(stack)
    annotations.has_error("*", assertions.Match.string_like_regexp(".*must be encrypted.*"))
