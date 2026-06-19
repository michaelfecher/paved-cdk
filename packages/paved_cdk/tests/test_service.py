"""The shared service contract: a ServiceSpec maps onto governed resources via
``build_service``, regardless of which front end produced it. Covers the data-api
addition (an encrypted S3 bucket + private API, reusing the SecureDataApi brick)
alongside functions."""

from __future__ import annotations

from aws_cdk import assertions
from conftest import ENV, VALID_TAGS
from paved_cdk import (
    ApiRoute,
    DataApiSpec,
    FunctionSpec,
    PlatformStack,
    ServiceSpec,
    build_service,
)


def _stack(app, spec):
    stack = PlatformStack(app, "Svc", env=ENV, tags=VALID_TAGS)
    build_service(stack, spec)
    return assertions.Template.from_stack(stack)


def test_data_api_only_adds_bucket_and_private_api(app):
    template = _stack(app, ServiceSpec(data_apis=[DataApiSpec(name="scoring-data")]))
    template.resource_count_is("AWS::S3::Bucket", 1)
    template.resource_count_is("AWS::ApiGateway::RestApi", 1)
    template.resource_count_is("AWS::Lambda::Function", 0)
    template.has_resource_properties(
        "AWS::ApiGateway::RestApi",
        {"EndpointConfiguration": {"Types": ["PRIVATE"]}},
    )


def test_functions_and_data_api_together(app, tmp_path):
    (tmp_path / "handler.py").write_text("def main(e, c):\n    return {}\n")
    spec = ServiceSpec(
        functions=[
            FunctionSpec(name="score", code_path=str(tmp_path)),
            FunctionSpec(name="batch", code_path=str(tmp_path)),
        ],
        data_apis=[DataApiSpec(name="scoring-data")],
    )
    template = _stack(app, spec)
    template.resource_count_is("AWS::Lambda::Function", 2)
    template.resource_count_is("AWS::S3::Bucket", 1)
    template.resource_count_is("AWS::ApiGateway::RestApi", 1)  # only the data-api's


def test_api_route_uses_a_separate_private_api(app, tmp_path):
    """A function with an HTTP route shares one ServiceApi; a data-api is its own
    private API. Both are PRIVATE, so a service with both has two REST APIs."""
    (tmp_path / "handler.py").write_text("def main(e, c):\n    return {}\n")
    spec = ServiceSpec(
        functions=[
            FunctionSpec(
                name="charge",
                code_path=str(tmp_path),
                api=ApiRoute(method="POST", path="/charge"),
            )
        ],
        data_apis=[DataApiSpec(name="ledger-data")],
    )
    template = _stack(app, spec)
    template.resource_count_is("AWS::Lambda::Function", 1)
    template.resource_count_is("AWS::ApiGateway::RestApi", 2)
