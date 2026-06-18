"""SecureDataApi — the reference paved-road construct.

Demonstrates the platform pattern with two account-aware resources:

* an **encrypted S3 data bucket** (account KMS key, no public access, TLS-only), and
* a **private REST API Gateway** that is only reachable through the account's
  ``execute-api`` interface VPC endpoint — i.e. it resolves privately inside the
  VPC, with no public internet path.

A Data Scientist passes at most an API name; everything security- and
network-relevant (KMS key, private endpoint, removal policy) is wired from the
resolved :class:`PlatformConfig`.
"""

from __future__ import annotations

from dataclasses import dataclass

from aws_cdk import RemovalPolicy
from aws_cdk import aws_apigateway as apigateway
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from constructs import Construct

from ..environment import PlatformEnvironment


@dataclass
class SecureDataApiProps:
    """The only knobs a Data Scientist may turn. Deliberately no vpc/kms/endpoint/
    policy arguments — those come from the account baseline."""

    api_name: str = "data-api"


class SecureDataApi(Construct):
    """An encrypted S3 bucket plus a private REST API, wired from the account
    baseline. The API is PRIVATE: callable only via the account's execute-api VPC
    endpoint, so it has no public internet path."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        props: SecureDataApiProps | None = None,
    ) -> None:
        super().__init__(scope, id)
        props = props or SecureDataApiProps()
        cfg = PlatformEnvironment.of(self)

        # 1. Encrypted data bucket — account KMS key, no public access, TLS-only.
        self.bucket = s3.Bucket(
            self,
            "DataBucket",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=cfg.kms_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            versioned=cfg.is_production,
            removal_policy=RemovalPolicy.RETAIN if cfg.is_production else RemovalPolicy.DESTROY,
        )

        # 2. Private REST API — only the account's execute-api VPC endpoint may
        #    invoke it; everything else is denied. This is the "private
        #    resolution": clients in the VPC reach it via the endpoint's private
        #    DNS, never the public internet.
        vpce_id = cfg.execute_api_vpc_endpoint.vpc_endpoint_id
        resource_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.DENY,
                    principals=[iam.AnyPrincipal()],
                    actions=["execute-api:Invoke"],
                    resources=["execute-api:/*"],
                    conditions={"StringNotEquals": {"aws:SourceVpce": vpce_id}},
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    principals=[iam.AnyPrincipal()],
                    actions=["execute-api:Invoke"],
                    resources=["execute-api:/*"],
                ),
            ]
        )
        self.api = apigateway.RestApi(
            self,
            "DataApi",
            rest_api_name=props.api_name,
            endpoint_configuration=apigateway.EndpointConfiguration(
                types=[apigateway.EndpointType.PRIVATE],
                vpc_endpoints=[cfg.execute_api_vpc_endpoint],
            ),
            policy=resource_policy,
        )
        # At least one method is required to deploy; a mock keeps the reference
        # construct self-contained (real projects wire a Lambda/integration).
        self.api.root.add_method(
            "GET",
            apigateway.MockIntegration(
                integration_responses=[apigateway.IntegrationResponse(status_code="200")],
                request_templates={"application/json": '{"statusCode": 200}'},
            ),
            method_responses=[apigateway.MethodResponse(status_code="200")],
        )

    @property
    def bucket_name(self) -> str:
        return self.bucket.bucket_name

    @property
    def api_id(self) -> str:
        return self.api.rest_api_id
