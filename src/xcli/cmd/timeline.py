"""Timeline lookup command."""

from __future__ import annotations

import json
from typing import Any

import typer

from xcli.core.errors import UsageError
from xcli.core.output import emit
from xcli.core.session import make_authed_client
from xcli.core.x_client import get_user_by_username, get_user_posts


def _normalize_handle(handle: str) -> str:
    normalized = handle.strip().lstrip("@")
    if not normalized:
        raise UsageError("Provide a valid handle with `--user <handle>`.")
    return normalized


def _one_line_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def _parse_bool_text(value: str, *, option_name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise typer.BadParameter(f"{option_name} must be true or false.")


def timeline_cmd(
    user: str = typer.Option(..., "--user", help="Target account handle."),
    limit: int = typer.Option(10, "--limit", min=1, max=100, help="Number of posts to return."),
    replies: str = typer.Option("true", "--replies", help="Include replies: true or false."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    handle = _normalize_handle(user)
    client = make_authed_client()
    profile = get_user_by_username(client, handle)

    user_id = profile.get("id")
    if not isinstance(user_id, str) or not user_id:
        raise UsageError(f"Unable to resolve user id for @{handle}.")

    include_replies = _parse_bool_text(replies, option_name="--replies")
    posts = get_user_posts(client, user_id, limit=limit, exclude_replies=not include_replies)
    output = {
        "message": "Fetched timeline.",
        "user": {
            "id": profile.get("id"),
            "username": profile.get("username"),
            "name": profile.get("name"),
        },
        "count": len(posts),
        "posts": posts,
    }

    if json_output:
        print(json.dumps(output, indent=2, sort_keys=True))
        return

    resolved = profile.get("username") or handle
    emit({"message": f"Timeline for @{resolved}", "count": len(posts)}, json_output=False)
    if not posts:
        print("No posts found.")
        return

    for post in posts:
        post_id = post.get("id", "?")
        created_at = post.get("created_at") or "unknown-time"
        text = _one_line_text(post.get("text"))
        print(f"- {post_id} | {created_at}")
        print(f"  {text}")
