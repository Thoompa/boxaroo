import pytest
from logger import Logger, LoggingLevel
from unittest.mock import mock_open


@pytest.mark.parametrize(
    "logger_level,log_method,message,expected_output,should_appear",
    [
        # Logger at DEBUG: all methods should output
        (LoggingLevel.DEBUG, "debug", "debug message", "DEBUG: debug message", True),
        (LoggingLevel.DEBUG, "log", "info message", "INFO: info message", True),
        (LoggingLevel.DEBUG, "error", "error message", "ERROR: error message", True),
        # Logger at INFO: debug should be suppressed, info + error should output
        (LoggingLevel.INFO, "debug", "debug message", "DEBUG: debug message", False),
        (LoggingLevel.INFO, "log", "info message", "INFO: info message", True),
        (LoggingLevel.INFO, "error", "error message", "ERROR: error message", True),
        # Logger at ERROR: only error should output
        (LoggingLevel.ERROR, "debug", "debug message", "DEBUG: debug message", False),
        (LoggingLevel.ERROR, "log", "info message", "INFO: info message", False),
        (LoggingLevel.ERROR, "error", "error message", "ERROR: error message", True),
    ],
)
def test_logger_print_and_file(
    monkeypatch,
    capsys,
    logger_level,
    log_method,
    message,
    expected_output,
    should_appear,
):
    # --- Given: a Logger instance at the specified logging level, and file I/O is mocked ---
    m = mock_open()
    monkeypatch.setattr("builtins.open", m)
    logger = Logger(logging_level=logger_level)

    # --- When: logging a message at the specified level ---
    getattr(logger, log_method)(message)

    # --- Then: the message should appear or be suppressed in console output ---
    captured = capsys.readouterr()
    if should_appear:
        assert expected_output in captured.out, (
            f"Expected '{expected_output}' in console output "
            f"(logger={logger_level}, method={log_method})"
        )
    else:
        assert expected_output not in captured.out, (
            f"Did not expect '{expected_output}' in console output "
            f"(logger={logger_level}, method={log_method})"
        )

    # --- Then: the message should be written to the log file only if it should appear ---
    write_args = [call[0][0] if call[0] else "" for call in m().write.call_args_list]
    file_written = any(expected_output in arg for arg in write_args)
    if should_appear:
        assert file_written, (
            f"Expected file write containing '{expected_output}' "
            f"(logger={logger_level}, method={log_method})"
        )
    else:
        assert not file_written, (
            f"Did not expect file write containing '{expected_output}' "
            f"(logger={logger_level}, method={log_method})"
        )
