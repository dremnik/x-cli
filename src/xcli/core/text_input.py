"""Text input resolution helpers for compose and publish commands."""

from __future__ import annotations

import sys
from pathlib import Path

from xcli.core.errors import UsageError

MAX_POST_LEN = 25_000


def normalize_text(raw: str, *, max_chars: int = MAX_POST_LEN) -> str:
    text = raw.replace("\r\n", "\n").strip()
    if not text:
        raise UsageError("Post text is empty.")
    if len(text) > max_chars:
        raise UsageError(f"Post text is too long ({len(text)} > {max_chars}).")
    return text


def read_text_input(
    *,
    text: str | None,
    file_path: Path | None,
    use_stdin: bool,
    max_chars: int = MAX_POST_LEN,
) -> str:
    selected = sum(
        [
            1 if text is not None else 0,
            1 if file_path is not None else 0,
            1 if use_stdin else 0,
        ]
    )
    if selected > 1:
        raise UsageError("Use only one input source: <text>, --file, or --stdin.")

    if text is not None:
        return normalize_text(text, max_chars=max_chars)

    if file_path is not None:
        return normalize_text(file_path.read_text(encoding="utf-8"), max_chars=max_chars)

    if use_stdin or not sys.stdin.isatty():
        return normalize_text(sys.stdin.read(), max_chars=max_chars)

    raise UsageError("Provide post text with <text>, --file, or piped stdin.")
