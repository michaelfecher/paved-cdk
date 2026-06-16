"""The core proof: a Data Scientist writes ~3 lines with NO vpc/env/kms/iam args,
yet the synthesized template carries a KMS-encrypted bucket with public access
blocked, and a PRIVATE API Gateway locked to the account's execute-api VPC
endpoint — all resolved from the account baseline."""

from __future__ import annotations

from aws_cdk import assertions
from conftest import ENV, VALID_TAGS
from paved_cdk import PlatformStack, SecureDataApi


def _synth(app):
    stack = PlatformStack(app, "Test", env=ENV, tags=VALID_TAGS)
    SecureDataApi(stack, "DataApi")  # <-- the entire DS-facing surface
    return assertions.Template.from_stack(stack)


def test_bucket_is_kms_encrypted_and_private(app):
    template = _synth(app)
    template.resource_count_is("AWS::S3::Bucket", 1)
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "ServerSideEncryptionByDefault": {
                                    "SSEAlgorithm": "aws:kms",
                                    # KMS key ARN came from the registry, never typed by the DS.
                                    "KMSMasterKeyID": (
                                        "arn:aws:kms:eu-west-1:111111111111:key/"
                                        "a6953c24-56c8-4cbe-b5a9-5eac7ad2a093"
                                    ),
                                }
                            }
                        )
                    ]
                )
            },
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "RestrictPublicBuckets": True,
            },
        },
    )


def test_api_is_private_and_locked_to_the_account_vpc_endpoint(app):
    template = _synth(app)
    template.has_resource_properties(
        "AWS::ApiGateway::RestApi",
        {
            "EndpointConfiguration": {
                "Types": ["PRIVATE"],
                "VpcEndpointIds": ["vpce-02322cfeb68fa0bbf"],  # from the registry
            },
            # Resource policy denies anything not arriving via that VPC endpoint.
            "Policy": assertions.Match.object_like(
                {
                    "Statement": assertions.Match.array_with(
                        [
                            assertions.Match.object_like(
                                {
                                    "Effect": "Deny",
                                    "Condition": {
                                        "StringNotEquals": {
                                            "aws:SourceVpce": "vpce-02322cfeb68fa0bbf"
                                        }
                                    },
                                }
                            )
                        ]
                    )
                }
            ),
        },
    )


def test_config_is_static_and_deterministic(app):
    """No live lookup: the synthesized values are concrete literals from the
    registry, not deploy-time tokens."""
    template = _synth(app)
    template.has_resource_properties(
        "AWS::ApiGateway::RestApi",
        {"EndpointConfiguration": {"VpcEndpointIds": ["vpce-02322cfeb68fa0bbf"]}},
    )
