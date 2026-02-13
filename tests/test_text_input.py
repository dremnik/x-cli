from pathlib import Path

import pytest

from xcli.core.errors import UsageError
from xcli.core.text_input import read_text_input


def test_read_text_input_inline() -> None:
    text = read_text_input(text="  hello world  ", file_path=None, use_stdin=False)
    assert text == "hello world"


def test_read_text_input_file(tmp_path: Path) -> None:
    file_path = tmp_path / "draft.txt"
    file_path.write_text("from file\n")
    text = read_text_input(text=None, file_path=file_path, use_stdin=False)
    assert text == "from file"


def test_read_text_input_rejects_multiple_sources(tmp_path: Path) -> None:
    file_path = tmp_path / "draft.txt"
    file_path.write_text("x")
    with pytest.raises(UsageError):
        read_text_input(text="x", file_path=file_path, use_stdin=False)


def test_read_text_input_rejects_empty() -> None:
    with pytest.raises(UsageError):
        read_text_input(text="   ", file_path=None, use_stdin=False)
