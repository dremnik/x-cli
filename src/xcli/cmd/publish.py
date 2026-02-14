"""Publish commands: post, reply, quote."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import typer

from xcli.core.errors import UsageError
from xcli.core.output import emit
from xcli.core.posting import Operation, build_payload, build_post_payload
from xcli.core.session import get_token_scopes, make_authed_client
from xcli.core.text_input import read_text_input
from xcli.core.x_client import (
    create_post,
    get_me,
    post_url,
    upload_media_files,
    upload_video_with_subtitles,
    validate_media_files,
)


def _build_confirmation_preview(
    *,
    op: Operation,
    text: str,
    to: str | None,
    media_files: list[Path],
    video_file: Path | None,
    subtitle_file: Path | None,
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

    if video_file:
        lines.append(f"Video file: {video_file}")
    if subtitle_file:
        lines.append(f"Subtitle file: {subtitle_file}")

    if media_files:
        lines.append(f"Media files: {len(media_files)}")
        for file_path in media_files:
            lines.append(f"  - {file_path}")

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
    media: list[Path] | None,
    video: Path | None,
    srt: Path | None,
    stdin: bool,
    dry_run: bool,
    yes: bool,
    json_output: bool,
) -> None:
    media_files = list(media or [])
    is_video_post = video is not None or srt is not None

    if is_video_post and op != "post":
        raise UsageError("`--video` and `--srt` are only supported for `xcli post`.")
    if (video is None) != (srt is None):
        raise UsageError("Use `--video` and `--srt` together.")
    if video and media_files:
        raise UsageError("Use either `--media` or `--video`/`--srt`, not both.")

    if is_video_post and text is None and file is None and not stdin:
        body = ""
    else:
        body = read_text_input(text=text, file_path=file, use_stdin=stdin)

    if op == "quote" and media_files:
        raise UsageError("quote does not support media attachments.")
    validate_media_files(media_files)
    if (media_files or is_video_post) and "media.write" not in get_token_scopes():
        raise UsageError(
            "Media upload requires `media.write` scope. "
            "Run `xcli auth login` again with scopes including media.write."
        )

    live = not dry_run

    if not live:
        if op == "post":
            payload = build_post_payload(text=body, media_ids=["1"] if is_video_post else None)
        else:
            payload = build_payload(op=op, text=body, to_id=to)

        dry_run_out: dict[str, Any] = {
            "message": f"Dry run: {op} payload ready.",
            "mode": "dry-run",
            "operation": op,
            "payload": payload,
            "media_files": [str(path) for path in media_files],
        }
        if video is not None:
            dry_run_out["video_file"] = str(video)
        if srt is not None:
            dry_run_out["subtitle_file"] = str(srt)

        emit(
            dry_run_out,
            json_output=json_output,
        )
        return

    if not yes:
        typer.echo(
            _build_confirmation_preview(
                op=op,
                text=body,
                to=to,
                media_files=media_files,
                video_file=video,
                subtitle_file=srt,
            )
        )
        confirmed = typer.confirm("Post this now?", default=False)
        if not confirmed:
            raise typer.Exit(code=0)

    client = make_authed_client()
    upload_result: dict[str, Any] | None = None
    if is_video_post and video is not None and srt is not None:
        upload_result = upload_video_with_subtitles(client, video_file=video, subtitle_file=srt)
        media_ids = [str(upload_result["video_media_id"])]
    else:
        media_ids = upload_media_files(client, media_files)

    if op == "post":
        payload = build_post_payload(text=body, media_ids=media_ids)
    else:
        payload = build_payload(op=op, text=body, to_id=to, media_ids=media_ids)

    created = create_post(client, payload)
    me = get_me(client)

    live_out: dict[str, Any] = {
        "message": f"Posted {op} successfully.",
        "mode": "live",
        "operation": op,
        "id": created["id"],
        "url": post_url(me.get("username"), created["id"]),
        "username": me.get("username"),
        "media_count": len(media_ids),
    }

    if upload_result:
        live_out["video_media_id"] = upload_result.get("video_media_id")
        live_out["subtitle_media_id"] = upload_result.get("subtitle_media_id")

    emit(live_out, json_output=json_output)


def post_cmd(
    text: str | None = typer.Argument(None, help="Post text."),
    file: Path | None = typer.Option(None, "--file", help="Read post text from a file."),
    media: list[Path] | None = typer.Option(
        None,
        "--media",
        help="Attach image file (repeatable).",
    ),
    video: Path | None = typer.Option(None, "--video", help="Attach a video file."),
    srt: Path | None = typer.Option(
        None,
        "--srt",
        help="Attach subtitle sidecar file (.srt or .vtt) for --video.",
    ),
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
        media=media,
        video=video,
        srt=srt,
        stdin=stdin,
        dry_run=dry_run,
        yes=yes,
        json_output=json_output,
    )


def reply_cmd(
    text: str | None = typer.Argument(None, help="Reply text."),
    to: str = typer.Option(..., "--to", help="Post ID to reply to."),
    file: Path | None = typer.Option(None, "--file", help="Read post text from a file."),
    media: list[Path] | None = typer.Option(
        None,
        "--media",
        help="Attach image file (repeatable).",
    ),
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
        media=media,
        video=None,
        srt=None,
        stdin=stdin,
        dry_run=dry_run,
        yes=yes,
        json_output=json_output,
    )


def quote_cmd(
    text: str | None = typer.Argument(None, help="Quote post text."),
    to: str = typer.Option(..., "--to", help="Post ID to quote."),
    file: Path | None = typer.Option(None, "--file", help="Read post text from a file."),
    media: list[Path] | None = typer.Option(
        None,
        "--media",
        help="Attach image file (repeatable).",
    ),
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
        media=media,
        video=None,
        srt=None,
        stdin=stdin,
        dry_run=dry_run,
        yes=yes,
        json_output=json_output,
    )
