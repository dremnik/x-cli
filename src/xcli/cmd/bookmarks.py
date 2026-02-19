"""Bookmark commands."""

from __future__ import annotations

import json
from typing import Any

import typer

from xcli.core.errors import ApiError
from xcli.core.output import emit
from xcli.core.posting import parse_post_reference
from xcli.core.session import make_authed_client
from xcli.core.x_client import (
    create_bookmark,
    delete_bookmark,
    fetch_bookmarks,
    get_me,
)

app = typer.Typer(no_args_is_help=True, help="Manage bookmarks.")


def _one_line_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def _print_post_list(posts: list[dict[str, Any]]) -> None:
    for post in posts:
        post_id = post.get("id", "?")
        created_at = post.get("created_at") or "unknown-time"
        author = post.get("author_username")
        prefix = f"@{author}" if isinstance(author, str) and author else "unknown-author"
        text = _one_line_text(post.get("text"))
        print(f"- {post_id} | {created_at} | {prefix}")
        print(f"  {text}")


@app.command("fetch")
def fetch(
    limit: int = typer.Option(
        10, "--limit", "--max-results", min=1, max=100, help="Number of bookmarks to return (max_results). Default: 10."
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """List recent bookmarks."""
    client = make_authed_client()
    me = get_me(client)

    user_id = me.get("id")
    if not isinstance(user_id, str) or not user_id:
        raise ApiError("Authenticated user lookup did not include an id.")

    bookmarks = fetch_bookmarks(client, user_id, limit=limit)
    output = {
        "message": "Fetched bookmarks.",
        "user": {
            "id": me.get("id"),
            "username": me.get("username"),
            "name": me.get("name"),
        },
        "count": len(bookmarks),
        "bookmarks": bookmarks,
    }

    if json_output:
        print(json.dumps(output, indent=2, sort_keys=True))
        return

    emit({"message": "Fetched bookmarks", "count": len(bookmarks)}, json_output=False)
    if not bookmarks:
        print("No bookmarks found.")
        return
    _print_post_list(bookmarks)


@app.command("create")
def create(
    target: str = typer.Argument(..., help="Tweet URL or ID to bookmark."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Bookmark a tweet."""
    if target.isdigit():
        post_id = parse_post_reference(post_id=target)
    else:
        post_id = parse_post_reference(post_id=None, url=target)

    client = make_authed_client()
    me = get_me(client)
    user_id = me.get("id")
    if not isinstance(user_id, str) or not user_id:
        raise ApiError("Authenticated user lookup did not include an id.")

    result = create_bookmark(client, user_id, post_id)
    
    output = {
        "message": "Bookmark created.",
        "bookmarked": True,
        "id": post_id,
        "result": result,
    }

    if json_output:
        print(json.dumps(output, indent=2, sort_keys=True))
        return

    emit({"message": "Bookmark created.", "id": post_id}, json_output=False)


@app.command("delete")
def delete(
    target: str = typer.Argument(..., help="Tweet URL or ID to remove from bookmarks."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Remove a bookmark."""
    if target.isdigit():
        post_id = parse_post_reference(post_id=target)
    else:
        post_id = parse_post_reference(post_id=None, url=target)

    client = make_authed_client()
    me = get_me(client)
    user_id = me.get("id")
    if not isinstance(user_id, str) or not user_id:
        raise ApiError("Authenticated user lookup did not include an id.")

    result = delete_bookmark(client, user_id, post_id)

    output = {
        "message": "Bookmark deleted.",
        "bookmarked": False,
        "id": post_id,
        "result": result,
    }

    if json_output:
        print(json.dumps(output, indent=2, sort_keys=True))
        return

    emit({"message": "Bookmark deleted.", "id": post_id}, json_output=False)
