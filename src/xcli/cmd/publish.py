"""Publish commands: post, reply, quote."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer

from xcli.core.config import load_settings
from xcli.core.output import emit
from xcli.core.posting import Operation, build_payload
from xcli.core.text_input import read_text_input
from xcli.core.token_store import TokenStore
from xcli.core.x_auth import refresh_if_needed
from xcli.core.x_client import create_post, get_me, make_user_client, post_url


def _build_confirmation_preview(
    *,
    op: Operation,
    text: str,
    to: str | None,
    now: datetime | None = None,
) -> str:
    stamp_dt = now or datetime.now().astimezone()
    timestamp = stamp_dt.strftime("%Y-%m-%d %H:%M:%S %z")

    lines = [
        "----- Live publish preview -----",
        f"Timestamp: {timestamp}",
        f"Operation: {op}",
    ]

    if op == "reply" and to:
        lines.append(f"Reply to: {to}")
    if op == "quote" and to:
        lines.append(f"Quote target: {to}")

    lines.extend(
        [
            f"Characters: {len(text)}",
            "Content:",
            "-----",
            text,
            "-----",
        ]
    )
    return "\n".join(lines)


def _run_publish(
    *,
    op: Operation,
    to: str | None,
    text: str | None,
    file: Path | None,
    stdin: bool,
    dry_run: bool,
    yes: bool,
    json_output: bool,
) -> None:
    body = read_text_input(text=text, file_path=file, use_stdin=stdin)
    payload = build_payload(op=op, text=body, to_id=to)
    live = not dry_run

    if not live:
        emit(
            {
                "message": f"Dry run: {op} payload ready.",
                "mode": "dry-run",
                "operation": op,
                "payload": payload,
            },
            json_output=json_output,
        )
        return

    if not yes:
        typer.echo(_build_confirmation_preview(op=op, text=body, to=to))
        confirmed = typer.confirm("Post this now?", default=False)
        if not confirmed:
            raise typer.Exit(code=0)

    settings = load_settings()
    store = TokenStore()
    token = store.load()
    if not token:
        raise typer.BadParameter("No token found. Run `xcli auth login` first.")
    if not token.get("access_token"):
        raise typer.BadParameter("Token file is missing access_token. Run `xcli auth login`.")

    refreshed = refresh_if_needed(settings, token)
    if refreshed != token:
        store.save(refreshed)

    access_token = refreshed.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise typer.BadParameter("Token file is missing access_token. Run `xcli auth login`.")

    client = make_user_client(access_token)
    created = create_post(client, payload)
    me = get_me(client)

    out = {
        "message": f"Posted {op} successfully.",
        "mode": "live",
        "operation": op,
        "id": created["id"],
        "url": post_url(me.get("username"), created["id"]),
        "username": me.get("username"),
    }
    emit(out, json_output=json_output)


def post_cmd(
    text: str | None = typer.Argument(None, help="Post text."),
    file: Path | None = typer.Option(None, "--file", help="Read post text from a file."),
    stdin: bool = typer.Option(False, "--stdin", help="Read post text from stdin."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview payload without posting."),
    yes: bool = typer.Option(False, "--yes", help="Skip send confirmation prompt."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    _run_publish(
        op="post",
        to=None,
        text=text,
        file=file,
        stdin=stdin,
        dry_run=dry_run,
        yes=yes,
        json_output=json_output,
    )


def reply_cmd(
    text: str | None = typer.Argument(None, help="Reply text."),
    to: str = typer.Option(..., "--to", help="Post ID to reply to."),
    file: Path | None = typer.Option(None, "--file", help="Read post text from a file."),
    stdin: bool = typer.Option(False, "--stdin", help="Read post text from stdin."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview payload without posting."),
    yes: bool = typer.Option(False, "--yes", help="Skip send confirmation prompt."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    _run_publish(
        op="reply",
        to=to,
        text=text,
        file=file,
        stdin=stdin,
        dry_run=dry_run,
        yes=yes,
        json_output=json_output,
    )


def quote_cmd(
    text: str | None = typer.Argument(None, help="Quote post text."),
    to: str = typer.Option(..., "--to", help="Post ID to quote."),
    file: Path | None = typer.Option(None, "--file", help="Read post text from a file."),
    stdin: bool = typer.Option(False, "--stdin", help="Read post text from stdin."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview payload without posting."),
    yes: bool = typer.Option(False, "--yes", help="Skip send confirmation prompt."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    _run_publish(
        op="quote",
        to=to,
        text=text,
        file=file,
        stdin=stdin,
        dry_run=dry_run,
        yes=yes,
        json_output=json_output,
    )
