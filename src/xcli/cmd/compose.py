"""Compose command."""

from __future__ import annotations

from pathlib import Path

import typer

from xcli.core.output import emit
from xcli.core.text_input import read_text_input


def compose_cmd(
    text: str | None = typer.Argument(None, help="Post text."),
    file: Path | None = typer.Option(None, "--file", help="Read post text from a file."),
    stdin: bool = typer.Option(False, "--stdin", help="Read post text from stdin."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    body = read_text_input(text=text, file_path=file, use_stdin=stdin)

    emit(
        {
            "message": "Compose preview:",
            "mode": "compose",
            "chars": len(body),
            "text": body,
        },
        json_output=json_output,
    )

    if not json_output:
        print("---")
        print(body)
