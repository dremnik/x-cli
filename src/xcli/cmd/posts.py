"""Post read commands."""

from __future__ import annotations

import json
from typing import Any

import typer

from xcli.core.errors import ApiError
from xcli.core.output import emit
from xcli.core.posting import validate_post_id
from xcli.core.session import make_authed_client
from xcli.core.x_client import get_me, get_post_by_id, get_user_posts, post_url

app = typer.Typer(no_args_is_help=True, help="Read posts.")


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


@app.command("mine")
def mine(
    limit: int = typer.Option(10, "--limit", min=1, max=100, help="Number of posts to return."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    client = make_authed_client()
    me = get_me(client)

    user_id = me.get("id")
    if not isinstance(user_id, str) or not user_id:
        raise ApiError("Authenticated user lookup did not include an id.")

    posts = get_user_posts(client, user_id, limit=limit)
    output = {
        "message": "Fetched recent posts.",
        "user": {
            "id": me.get("id"),
            "username": me.get("username"),
            "name": me.get("name"),
        },
        "count": len(posts),
        "posts": posts,
    }

    if json_output:
        print(json.dumps(output, indent=2, sort_keys=True))
        return

    handle = me.get("username")
    message = "Recent posts"
    if isinstance(handle, str) and handle:
        message = f"Recent posts for @{handle}"

    emit({"message": message, "count": len(posts)}, json_output=False)
    if not posts:
        print("No posts found.")
        return
    _print_post_list(posts)


@app.command("get")
def get(
    id: str = typer.Option(..., "--id", help="Post id to fetch."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    post_id = validate_post_id(id)
    client = make_authed_client()
    post = get_post_by_id(client, post_id)

    output = {
        "message": "Fetched post.",
        "post": post,
        "url": post_url(post.get("author_username"), post_id),
    }
    if json_output:
        print(json.dumps(output, indent=2, sort_keys=True))
        return

    emit(
        {"message": "Fetched post.", "id": post.get("id"), "url": output["url"]},
        json_output=False,
    )
    if post.get("author_username"):
        print(f"author: @{post['author_username']}")
    if post.get("created_at"):
        print(f"created_at: {post['created_at']}")
    text = post.get("text")
    if isinstance(text, str) and text:
        print("---")
        print(text)
