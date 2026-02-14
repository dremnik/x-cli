"""Markdown rendering helpers for post export."""

from __future__ import annotations

import html
from collections.abc import Mapping
from typing import Any


def _first_non_empty(*values: Any) -> str:
    for value in values:
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
    return ""


def _yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _post_body_text(post: dict[str, Any]) -> str:
    article = post.get("article")
    if isinstance(article, dict):
        plain_text = article.get("plain_text")
        if isinstance(plain_text, str) and plain_text.strip():
            return plain_text.strip()

    note_tweet = post.get("note_tweet")
    if isinstance(note_tweet, dict):
        note_text = note_tweet.get("text")
        if isinstance(note_text, str) and note_text.strip():
            return note_text.strip()

    text = post.get("text")
    if isinstance(text, str):
        return text.strip()
    return ""


def _article_code_blocks(article_map: dict[str, Any]) -> list[tuple[str, str]]:
    entities = article_map.get("entities")
    entities_map = entities if isinstance(entities, dict) else {}
    raw_blocks = entities_map.get("code")
    if not isinstance(raw_blocks, list):
        return []

    blocks: list[tuple[str, str]] = []
    for block in raw_blocks:
        if not isinstance(block, dict):
            continue
        language = _first_non_empty(block.get("language"), "text").lower()
        content = _first_non_empty(block.get("code"), block.get("content"))
        if not content:
            continue
        blocks.append((language, content.rstrip()))
    return blocks


def _inject_code_blocks_into_body(body: str, code_blocks: list[tuple[str, str]]) -> str:
    if not body or not code_blocks:
        return body

    lines = body.splitlines()
    placeholder_indexes = [index for index, line in enumerate(lines) if line and not line.strip()]
    remaining = list(code_blocks)

    for index in placeholder_indexes:
        if not remaining:
            break
        language, content = remaining.pop(0)
        lines[index] = f"```{language}\n{content}\n```"

    rendered = "\n".join(lines).strip()

    if remaining:
        tail_lines: list[str] = []
        for language, content in remaining:
            tail_lines.append(f"```{language}")
            tail_lines.append(content)
            tail_lines.append("```")
            tail_lines.append("")

        tail = "\n".join(tail_lines).rstrip()
        if rendered:
            rendered = f"{rendered}\n\n{tail}"
        else:
            rendered = tail

    return rendered


def _url_replacement(entity: Mapping[str, Any]) -> str:
    target = _first_non_empty(
        entity.get("unwound_url"),
        entity.get("expanded_url"),
        entity.get("url"),
    )
    return target


def _rehydrate_urls(body: str, entities: Any) -> str:
    if not body or not isinstance(entities, dict):
        return body

    urls = entities.get("urls")
    if not isinstance(urls, list):
        return body

    text = body
    applied_offsets = 0

    sortable: list[Mapping[str, Any]] = []
    for entry in urls:
        if isinstance(entry, Mapping):
            sortable.append(entry)

    sortable.sort(key=lambda item: int(item.get("start", -1)), reverse=True)

    for entity in sortable:
        start = entity.get("start")
        end = entity.get("end")
        replacement = _url_replacement(entity)
        if not replacement:
            continue

        if isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(text):
            segment = text[start:end]
            short_url = entity.get("url")
            if (
                isinstance(short_url, str)
                and short_url
                and short_url not in segment
                and segment not in short_url
            ):
                continue
            text = f"{text[:start]}{replacement}{text[end:]}"
            applied_offsets += 1

    if applied_offsets > 0:
        return text

    for entity in sortable:
        replacement = _url_replacement(entity)
        if not replacement:
            continue
        short_url = entity.get("url")
        if isinstance(short_url, str) and short_url in text:
            text = text.replace(short_url, replacement)

    return text


def _extract_attached_media(post: dict[str, Any]) -> list[dict[str, Any]]:
    raw = post.get("raw")
    if not isinstance(raw, dict):
        return []

    includes = raw.get("includes")
    data = raw.get("data")
    if not isinstance(includes, dict) or not isinstance(data, dict):
        return []

    media = includes.get("media")
    attachments = data.get("attachments")
    if not isinstance(media, list) or not isinstance(attachments, dict):
        return []

    keys = attachments.get("media_keys")
    if not isinstance(keys, list):
        return []

    by_key: dict[str, dict[str, Any]] = {}
    for item in media:
        if not isinstance(item, dict):
            continue
        media_key = item.get("media_key")
        if isinstance(media_key, str) and media_key:
            by_key[media_key] = item

    ordered: list[dict[str, Any]] = []
    for key in keys:
        if isinstance(key, str) and key in by_key:
            ordered.append(by_key[key])

    return ordered


def render_post_markdown(post: dict[str, Any], *, url: str | None) -> str:
    post_id = post.get("id")
    post_id_str = str(post_id) if isinstance(post_id, str) and post_id else "unknown"
    author_name = _first_non_empty(post.get("author_name"), "Unknown")
    author_username = _first_non_empty(post.get("author_username"))
    created_at = _first_non_empty(post.get("created_at"), "unknown")

    article = post.get("article")
    article_map = article if isinstance(article, dict) else {}
    title = _first_non_empty(article_map.get("title"), f"Post {post_id_str}")
    metrics = post.get("public_metrics")
    metrics_map = metrics if isinstance(metrics, dict) else {}

    lines = ["---"]
    lines.append(f"id: {_yaml_quote(post_id_str)}")
    lines.append(f"title: {_yaml_quote(title)}")
    lines.append(f"author_name: {_yaml_quote(author_name)}")
    if author_username:
        lines.append(f"author_username: {_yaml_quote(author_username)}")
    lines.append(f"created_at: {_yaml_quote(created_at)}")
    if isinstance(url, str) and url:
        lines.append(f"url: {_yaml_quote(url)}")

    metric_keys = (
        "impression_count",
        "like_count",
        "retweet_count",
        "reply_count",
        "quote_count",
        "bookmark_count",
    )
    metric_lines: list[tuple[str, Any]] = []
    for key in metric_keys:
        value = metrics_map.get(key)
        if value is None:
            continue
        metric_lines.append((key, value))
    if metric_lines:
        lines.append("metrics:")
        for key, value in metric_lines:
            if isinstance(value, bool):
                lines.append(f"  {key}: {str(value).lower()}")
            elif isinstance(value, (int, float)):
                lines.append(f"  {key}: {value}")
            else:
                lines.append(f"  {key}: {_yaml_quote(str(value))}")

    lines.append("---")
    lines.append("")
    lines.append(f"# {title}")
    lines.append("")

    body = _post_body_text(post)
    if body:
        if article_map:
            code_blocks = _article_code_blocks(article_map)
            body = _inject_code_blocks_into_body(body, code_blocks)
        else:
            body = _rehydrate_urls(body, post.get("entities"))
        body = html.unescape(body)
        lines.append(body)
        lines.append("")

    attachments = _extract_attached_media(post)
    if attachments:
        lines.append("## Attachments")
        lines.append("")
        for media in attachments:
            media_key = _first_non_empty(media.get("media_key"), "unknown")
            media_type = _first_non_empty(media.get("type"), "media")
            source_url = _first_non_empty(media.get("url"), media.get("preview_image_url"))
            if source_url:
                lines.append(f"- {media_type} `{media_key}`: [source]({source_url})")
            else:
                lines.append(f"- {media_type} `{media_key}`")
        lines.append("")

    return "\n".join(lines).strip() + "\n"
