"""SDK front end: decorators and the data_api helper record registrations that
``synth`` maps onto the shared ServiceSpec. Here we check the registration side
effects in isolation (resource correctness is covered by test_service.py)."""

from __future__ import annotations

import pytest
from paved_cdk.sdk import data_api, function
from paved_cdk.sdk.decorators import DATA_APIS, REGISTRY


@pytest.fixture(autouse=True)
def _clean_registries():
    REGISTRY.clear()
    DATA_APIS.clear()
    yield
    REGISTRY.clear()
    DATA_APIS.clear()


def test_function_decorator_registers_and_returns_callable():
    @function(memory=512)
    def predict(event, context):
        return {"ok": True}

    assert predict({}, None) == {"ok": True}  # returned unchanged, still callable
    assert len(REGISTRY) == 1
    assert REGISTRY[0].name == "predict"
    assert REGISTRY[0].memory == 512


def test_data_api_records_name():
    data_api("scoring-data")
    assert DATA_APIS == ["scoring-data"]


def test_data_api_defaults():
    data_api()
    assert DATA_APIS == ["data-api"]
