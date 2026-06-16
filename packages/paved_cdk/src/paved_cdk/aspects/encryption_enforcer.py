"""Fail-closed encryption enforcement via a CDK Aspect.

Aspects visit every node after construction, so resource properties are already
set — this is deterministic (unlike trying to verify tag propagation in an
aspect). If a known encryptable resource has no encryption configured, we add an
error annotation, which fails ``cdk synth``.

Scope (be honest about it): this covers the high-value resource types below where
encryption is **not** on by default and a data scientist could realistically
create something unencrypted. It is a safety net, not a complete control —
services encrypted-by-default (e.g. DynamoDB) are intentionally omitted, and for
S3 it only asserts that *some* encryption is configured, not that it is KMS (the
platform's own constructs wire the account KMS key). Pair it with cdk-nag and an
SCP/permissions boundary for defence in depth.
"""

from __future__ import annotations

import aws_cdk as cdk
import jsii
from constructs import IConstruct

# CloudFormation resource type -> the CDK Python attribute(s) that signal
# encryption. A resource is flagged only if **all** listed attributes are unset or
# falsy (so a boolean ``encrypted=False`` is caught, not just ``None``, and a
# resource with any one valid encryption knob — e.g. SQS managed SSE — passes).
_ENCRYPTION_ATTRS: dict[str, tuple[str, ...]] = {
    "AWS::S3::Bucket": ("bucket_encryption",),
    "AWS::SageMaker::NotebookInstance": ("kms_key_id",),
    "AWS::SageMaker::Domain": ("kms_key_id",),
    "AWS::RDS::DBInstance": ("storage_encrypted",),
    "AWS::RDS::DBCluster": ("storage_encrypted",),
    "AWS::EFS::FileSystem": ("encrypted",),
    "AWS::EC2::Volume": ("encrypted",),
    "AWS::Redshift::Cluster": ("encrypted",),
    "AWS::OpenSearchService::Domain": ("encryption_at_rest_options",),
    "AWS::SNS::Topic": ("kms_master_key_id",),
    "AWS::SQS::Queue": ("kms_master_key_id", "sqs_managed_sse_enabled"),
}


@jsii.implements(cdk.IAspect)
class EncryptionEnforcerAspect:
    """Errors on synth if a known encryptable resource is unencrypted."""

    def visit(self, node: IConstruct) -> None:
        if not isinstance(node, cdk.CfnResource):
            return
        attrs = _ENCRYPTION_ATTRS.get(node.cfn_resource_type)
        if attrs is None:
            return
        # Unresolved tokens are truthy → treated as "configured" (cannot evaluate
        # at synth); only concrete None/False/empty values are flagged.
        if all(not getattr(node, attr, None) for attr in attrs):
            shown = " / ".join(attrs)
            cdk.Annotations.of(node).add_error(
                f"{node.cfn_resource_type} must be encrypted: none of [{shown}] is "
                f"set (paved-cdk policy). Use a platform construct, which wires the "
                f"account KMS key automatically."
            )
