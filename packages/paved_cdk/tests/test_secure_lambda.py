"""SecureLambda: in-VPC, KMS-encrypted env, account log retention — all wired from
the baseline, with only code/handler supplied by the consumer."""

from __future__ import annotations

from aws_cdk import assertions
from aws_cdk import aws_lambda as _lambda
from conftest import ENV, VALID_TAGS
from paved_cdk import PlatformStack
from paved_cdk.compute import SecureLambda, SecureLambdaProps


def _synth(app):
    stack = PlatformStack(app, "Test", env=ENV, tags=VALID_TAGS)
    SecureLambda(
        stack,
        "Scoring",
        props=SecureLambdaProps(code=_lambda.Code.from_inline("def main(e, c):\n    return {}")),
    )
    return assertions.Template.from_stack(stack)


def test_lambda_runs_in_vpc(app):
    template = _synth(app)
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {"VpcConfig": assertions.Match.object_like({"SubnetIds": assertions.Match.any_value()})},
    )


def test_lambda_env_is_kms_encrypted(app):
    template = _synth(app)
    # environment_encryption sets KmsKeyArn on the function to the account key.
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {"KmsKeyArn": assertions.Match.any_value()},
    )


def test_lambda_has_dedicated_log_group(app):
    template = _synth(app)
    template.resource_count_is("AWS::Logs::LogGroup", 1)
