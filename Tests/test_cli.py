import pytest

import Code.cli as cli_module
from Code.cli import build_parser, run
from Code.contracts import ListSize, LoggingLevel, Supermarket


@pytest.mark.parametrize(
    "option_string",
    [
        "--list_size",
        "--headless",
        "--logging_level",
        "--refresh_category_lists",
        "--proxy_server",
        "--supermarket",
    ],
)
def test_build_parser_includes_expected_options(option_string):
    # GIVEN: The CLI parser factory is available
    # WHEN: The parser is built
    parser = build_parser()

    # THEN: The expected option is present
    assert option_string in parser._option_string_actions


def test_build_parser_preserves_default_values():
    # GIVEN: The CLI parser factory is available
    parser = build_parser()

    # WHEN: The parser is invoked with no arguments
    args = parser.parse_args([])

    # THEN: The current default values are preserved
    assert args.list_size == "FULL"
    assert args.headless is False
    assert args.logging_level == "INFO"
    assert args.refresh_category_lists is False
    assert args.proxy_server is None
    assert args.supermarket == Supermarket.WOOLWORTHS.value


def test_build_parser_uses_current_list_size_help(monkeypatch):
    # GIVEN: The list-size help helper returns a known value
    monkeypatch.setattr(cli_module, "build_list_size_help", lambda: "sentinel help")

    # WHEN: The parser is built
    parser = build_parser()

    # THEN: The list-size help text comes from the helper
    list_size_action = parser._option_string_actions["--list_size"]
    assert list_size_action.help == "sentinel help"


@pytest.mark.parametrize(
    "total_products, expected",
    [
        (None, "n/a"),
        (0, "~0s"),
        (108, "~27s"),
        (600, "~2m 30s"),
        (14892, "~1h 2m 3s"),
        (14400, "~1h"),
    ],
)
def test_format_eta(total_products, expected):
    # GIVEN: A total_products value and its expected ETA text
    # WHEN: The ETA is formatted
    # THEN: The helper returns the expected formatted ETA string
    assert cli_module._format_eta(total_products) == expected


def test_build_list_size_help_uses_formatted_eta(monkeypatch):
    # GIVEN: Cached product totals are available for each list size
    monkeypatch.setattr(
        cli_module,
        "_load_list_product_totals",
        lambda: {
            "testing": 108,  # 27s
            "short": 600,  # 2m 30s
            "medium": 14400,  # 1h
            "long": 14892,  # 1h 2m 3s
            "full": 0,  # 0s
        },
    )

    # WHEN: build_list_size_help() is called
    help_text = cli_module.build_list_size_help()

    # THEN: Help text includes each list size with a formatted ETA
    assert "TESTING ~27s" in help_text
    assert "SHORT ~2m 30s" in help_text
    assert "MEDIUM ~1h" in help_text
    assert "LONG ~1h 2m 3s" in help_text
    assert "FULL ~0s" in help_text


def test_build_list_size_help_with_no_cache_returns_all_na(monkeypatch):
    # GIVEN: No cached product totals are available
    monkeypatch.setattr(cli_module, "_load_list_product_totals", lambda: {})

    # WHEN: build_list_size_help() is called
    help_text = cli_module.build_list_size_help()

    # THEN: Help text shows n/a for all list sizes
    assert "TESTING n/a" in help_text
    assert "SHORT n/a" in help_text
    assert "MEDIUM n/a" in help_text
    assert "LONG n/a" in help_text
    assert "FULL n/a" in help_text


@pytest.mark.parametrize(
    "list_size_value, logging_level_value, expected_list_size, expected_logging_level",
    [
        ("TESTING", "DEBUG", ListSize.TESTING, LoggingLevel.DEBUG),
        ("SHORT", "INFO", ListSize.SHORT, LoggingLevel.INFO),
        ("MEDIUM", "WARNING", ListSize.MEDIUM, LoggingLevel.WARNING),
        ("LONG", "ERROR", ListSize.LONG, LoggingLevel.ERROR),
    ],
)
def test_run_maps_string_values_to_enums(
    monkeypatch,
    list_size_value,
    logging_level_value,
    expected_list_size,
    expected_logging_level,
):
    # GIVEN: CLI string arguments for list size and logging level
    captured = {}

    def dummy_run_main(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(cli_module, "run_main", dummy_run_main)

    # WHEN: The CLI entry point is run
    run(
        [
            "--list_size",
            list_size_value,
            "--logging_level",
            logging_level_value,
            "--supermarket",
            Supermarket.WOOLWORTHS.value,
        ]
    )

    # THEN: The entry point calls main() with enum values
    assert captured["default_list_size"] == expected_list_size
    assert captured["logging_level"] == expected_logging_level
    assert captured["supermarket"] == Supermarket.WOOLWORTHS


def test_run_calls_main_with_expected_arguments(monkeypatch):
    # GIVEN: A fully populated CLI invocation
    captured = {}

    def dummy_run_main(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(cli_module, "run_main", dummy_run_main)

    # WHEN: The CLI entry point is run
    run(
        [
            "--list_size",
            "FULL",
            "--headless",
            "--logging_level",
            "ERROR",
            "--refresh_category_lists",
            "--proxy_server",
            "http://host:port",
            "--supermarket",
            Supermarket.WOOLWORTHS.value,
        ]
    )

    # THEN: The runtime entry point receives the expected arguments
    assert captured == {
        "headless": True,
        "logging_level": LoggingLevel.ERROR,
        "default_list_size": ListSize.FULL,
        "supermarket": Supermarket.WOOLWORTHS,
        "refresh_category_lists": True,
        "proxy_server": "http://host:port",
    }
