"""Apply the platform IAM permissions boundary to every role in a scope.

aws-cdk-lib's ``PermissionsBoundary`` value object is normally attached at Stage
construction, before the platform config is resolved. An Aspect setting
``permissionsBoundary`` on every ``CfnRole`` is applied after the stack is built and
uniformly covers *every* role - including those created inside vendor constructs -
without each construct having to wire it.
"""

from __future__ import annotations

import aws_cdk as cdk
import jsii
from aws_cdk import aws_iam as iam
from constructs import IConstruct


@jsii.implements(cdk.IAspect)
class PermissionsBoundaryAspect:
    def __init__(self, boundary_arn: str) -> None:
        self._arn = boundary_arn

    def visit(self, node: IConstruct) -> None:
        if isinstance(node, iam.CfnRole):
            node.permissions_boundary = self._arn
