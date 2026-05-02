import pytest

import Code.supermarket_factory as supermarket_factory_module
from Code.contracts import Supermarket
from Code.supermarket_factory import resolve_supermarket, supermarket_factory
from Tests.test_helpers import (
    DummyFileHandler,
    DummyLogger,
    DummyProductParser,
    DummyWebDriver,
)


@pytest.mark.parametrize("supermarket_input", [None, "", "   "])
def test_resolve_supermarket_defaults_to_woolworths(supermarket_input):
    # GIVEN: A missing or blank supermarket input

    # WHEN: supermarket input is resolved
    resolved = resolve_supermarket(supermarket_input)

    # THEN: Woolworths is used as the default supermarket
    assert resolved == Supermarket.WOOLWORTHS


@pytest.mark.parametrize(
    "supermarket_input",
    ["WOOLWORTHS", "woolworths"],
)
def test_resolve_supermarket_matches_by_name_and_value(supermarket_input):
    # GIVEN: A supermarket key provided as enum name or enum value

    # WHEN: supermarket input is resolved
    resolved = resolve_supermarket(supermarket_input)

    # THEN: The matching supermarket enum member is returned
    assert resolved == Supermarket.WOOLWORTHS


def test_resolve_supermarket_raises_for_unsupported_key():
    # GIVEN: An unsupported supermarket key

    # WHEN: supermarket input is resolved
    # THEN: A ValueError is raised with the unsupported supermarket key
    with pytest.raises(ValueError, match="Unsupported supermarket 'unknown-market'"):
        resolve_supermarket("unknown-market")


def test_supermarket_factory_raises_when_registry_has_no_adapter(monkeypatch):
    # GIVEN: A valid supermarket key but a registry without a matching adapter
    file_handler = DummyFileHandler()
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    product_parser = DummyProductParser()
    monkeypatch.setattr(
        supermarket_factory_module,
        "SUPERMARKET_REGISTRY",
        {},
    )

    # WHEN: supermarket adapter creation is attempted
    # THEN: A ValueError is raised for the missing supermarket registry entry
    with pytest.raises(
        ValueError,
        match="No adapter registered for supermarket 'woolworths'",
    ):
        supermarket_factory(
            Supermarket.WOOLWORTHS,
            file_handler,
            logger,
            web_driver,
            product_parser,
        )
