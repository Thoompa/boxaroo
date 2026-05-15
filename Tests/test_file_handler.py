import csv

import pytest

from Code.file_handler import FileHandler
from Tests.test_helpers import DummyLogger, make_file_handler, FILE_HANDLER_HEADER


# ---------------------------------------------------------------------------
# _create_file behaviour (called on construction)
# ---------------------------------------------------------------------------


def test_file_handler_creates_file_with_header_row(tmp_path):
    # GIVEN: a FileHandler with a known header and a writable output directory
    logger = DummyLogger()

    # WHEN: the handler is constructed
    FileHandler(
        file_name="out.csv",
        file_path=str(tmp_path),
        header=FILE_HANDLER_HEADER,
        logger=logger,
    )
    output_file = tmp_path / "out.csv"

    # THEN: the file exists and its first row matches the header exactly
    assert output_file.exists()
    with open(output_file, newline="") as f:
        rows = list(csv.reader(f))
    assert rows == [FILE_HANDLER_HEADER]


def test_file_handler_creates_nested_directory_if_missing(tmp_path):
    # GIVEN: a destination path whose intermediate directories do not yet exist
    nested = tmp_path / "a" / "b" / "c"
    logger = DummyLogger()

    # WHEN: the handler is constructed with the nested path
    FileHandler(
        file_name="out.csv",
        file_path=str(nested),
        header=FILE_HANDLER_HEADER,
        logger=logger,
    )

    # THEN: the full directory tree is created and the file is present
    assert (nested / "out.csv").exists()


def test_file_handler_logs_created_message(tmp_path):
    # GIVEN: a DummyLogger and a valid output directory
    logger = DummyLogger()

    # WHEN: the handler is constructed
    FileHandler(
        file_name="products.csv",
        file_path=str(tmp_path),
        header=FILE_HANDLER_HEADER,
        logger=logger,
    )

    # THEN: an INFO record confirming the file name is present in the log
    info_messages = [msg for level, msg in logger.records if level == "INFO"]
    assert any("products.csv" in msg for msg in info_messages)


def test_file_handler_logs_append_message_when_file_already_exists(tmp_path):
    # GIVEN: a CSV file path that has already been initialised
    logger = DummyLogger()
    FileHandler(
        file_name="products.csv",
        file_path=str(tmp_path),
        header=FILE_HANDLER_HEADER,
        logger=logger,
    )

    # WHEN: the same file is initialised again
    FileHandler(
        file_name="products.csv",
        file_path=str(tmp_path),
        header=FILE_HANDLER_HEADER,
        logger=logger,
    )

    # THEN: an INFO message indicates appending to an existing file
    info_messages = [msg for level, msg in logger.records if level == "INFO"]
    assert any(
        "Appending to existing file products.csv" in msg for msg in info_messages
    )


def test_file_handler_logs_error_when_directory_creation_fails(tmp_path, monkeypatch):
    # GIVEN: the output directory cannot be created due to insufficient permissions
    monkeypatch.setattr(
        "Code.file_handler.os.makedirs",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("permission denied")),
    )
    logger = DummyLogger()

    # WHEN: the handler is constructed
    # THEN: an ERROR record is logged and the exception escapes to fail fast
    with pytest.raises(OSError):
        FileHandler(
            file_name="out.csv",
            file_path=str(tmp_path),
            header=FILE_HANDLER_HEADER,
            logger=logger,
        )
    error_messages = [msg for level, msg in logger.records if level == "ERROR"]
    assert any("out.csv" in msg for msg in error_messages)


# ---------------------------------------------------------------------------
# store_data behaviour
# ---------------------------------------------------------------------------


def test_file_handler_store_data_appends_rows_after_header(tmp_path):
    # GIVEN: a handler whose file has been created with a header
    handler, _ = make_file_handler(tmp_path)
    rows = [
        ["Apple each", "$1.00", "$1.00 / 1EA", ""],
        ["Bread each", "$3.50", "$3.50 / 1EA", ""],
    ]

    # WHEN: store_data is called with two product rows
    handler.store_data(rows)

    # THEN: the CSV contains the header followed by both data rows
    with open(tmp_path / "out.csv", newline="") as f:
        all_rows = list(csv.reader(f))
    assert all_rows[0] == FILE_HANDLER_HEADER
    assert all_rows[1:] == rows

    # AND: an INFO message confirms successful persistence count
    info_messages = [msg for level, msg in handler.logger.records if level == "INFO"]
    assert any("Successfully stored 2 rows" in msg for msg in info_messages)


def test_file_handler_store_data_logs_data_size(tmp_path):
    # GIVEN: a handler and a batch of three product rows
    handler, logger = make_file_handler(tmp_path)
    rows = [["A", "1", "1", ""], ["B", "2", "2", ""], ["C", "3", "3", ""]]

    # WHEN: store_data is called with the batch
    handler.store_data(rows)

    # THEN: an INFO log entry records the size of the batch
    info_messages = [msg for level, msg in logger.records if level == "INFO"]
    assert any("3" in msg for msg in info_messages)


def test_file_handler_multiple_store_data_calls_accumulate_rows(tmp_path):
    # GIVEN: a handler and two separate product batches (mirrors coordinator multi-category flow)
    handler, _ = make_file_handler(tmp_path)
    batch_one = [["Apple each", "$1.00", "$1.00 / 1EA", ""]]
    batch_two = [
        ["Bread each", "$3.50", "$3.50 / 1EA", ""],
        ["Bagel each", "$1.50", "$1.50 / 1EA", ""],
    ]

    # WHEN: store_data is called once per batch
    handler.store_data(batch_one)
    handler.store_data(batch_two)

    # THEN: all three data rows appear after the header in insertion order
    with open(tmp_path / "out.csv", newline="") as f:
        all_rows = list(csv.reader(f))
    assert all_rows[0] == FILE_HANDLER_HEADER
    assert all_rows[1:] == batch_one + batch_two
