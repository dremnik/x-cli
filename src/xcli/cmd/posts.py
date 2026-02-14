"""Post read commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from xcli.core.errors import ApiError, UsageError
from xcli.core.markdown import render_post_markdown
from xcli.core.output import emit
from xcli.core.posting import parse_post_reference
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


def _parse_bool_text(value: str, *, option_name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise typer.BadParameter(f"{option_name} must be true or false.")


def _render_post_markdown(post: dict[str, Any], *, url: str | None) -> str:
    return render_post_markdown(post, url=url)


def _render_post_text(post: dict[str, Any], *, url: str | None) -> str:
    lines: list[str] = []
    if post.get("author_username"):
        lines.append(f"author: @{post['author_username']}")
    if post.get("created_at"):
        lines.append(f"created_at: {post['created_at']}")
    if isinstance(url, str) and url:
        lines.append(f"url: {url}")

    note_tweet = post.get("note_tweet")
    if isinstance(note_tweet, dict):
        body = note_tweet.get("text")
    else:
        body = None
    if not isinstance(body, str) or not body.strip():
        text = post.get("text")
        body = text if isinstance(text, str) else ""
    if body:
        lines.append("---")
        lines.append(body.strip())

    return "\n".join(lines).rstrip() + "\n"


def _write_output_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@app.command("mine")
def mine(
    limit: int = typer.Option(10, "--limit", min=1, max=100, help="Number of posts to return."),
    replies: str = typer.Option("true", "--replies", help="Include replies: true or false."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    client = make_authed_client()
    me = get_me(client)

    user_id = me.get("id")
    if not isinstance(user_id, str) or not user_id:
        raise ApiError("Authenticated user lookup did not include an id.")

    include_replies = _parse_bool_text(replies, option_name="--replies")
    posts = get_user_posts(client, user_id, limit=limit, exclude_replies=not include_replies)
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
    id: str | None = typer.Option(None, "--id", help="Post id to fetch."),
    url: str | None = typer.Option(None, "--url", help="Post URL to fetch."),
    md: bool = typer.Option(False, "--md", help="Render output as Markdown."),
    out: Path | None = typer.Option(None, "--out", help="Write output to file."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    if md and json_output:
        raise UsageError("Use either --md or --json, not both.")

    post_id = parse_post_reference(post_id=id, url=url)
    client = make_authed_client()
    post = get_post_by_id(client, post_id)

    output = {
        "message": "Fetched post.",
        "post": post,
        "url": post_url(post.get("author_username"), post_id),
    }
    output_url = output.get("url")
    post_page_url = output_url if isinstance(output_url, str) else None
    if json_output:
        rendered_json = json.dumps(output, indent=2, sort_keys=True) + "\n"
        if out is not None:
            _write_output_file(out, rendered_json)
            emit(
                {
                    "message": "Fetched post and wrote JSON output.",
                    "id": post.get("id"),
                    "url": post_page_url,
                },
                json_output=False,
            )
            print(f"out: {out}")
            return
        print(rendered_json, end="")
        return

    if md:
        rendered_md = _render_post_markdown(post, url=post_page_url)
        if out is not None:
            _write_output_file(out, rendered_md)
            emit(
                {
                    "message": "Fetched post and wrote Markdown output.",
                    "id": post.get("id"),
                    "url": post_page_url,
                },
                json_output=False,
            )
            print(f"out: {out}")
            return
        print(rendered_md, end="")
        return

    rendered_text = _render_post_text(post, url=post_page_url)
    if out is not None:
        _write_output_file(out, rendered_text)
        emit(
            {
                "message": "Fetched post and wrote output.",
                "id": post.get("id"),
                "url": post_page_url,
            },
            json_output=False,
        )
        print(f"out: {out}")
        return

    emit(
        {"message": "Fetched post.", "id": post.get("id"), "url": post_page_url},
        json_output=False,
    )
    print(rendered_text, end="")
