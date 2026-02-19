"""Payload and ID helpers for post operations."""

from __future__ import annotations

import re
from typing import Any, Literal
from urllib.parse import urlparse

from xcli.core.errors import UsageError

Operation = Literal["post", "reply", "quote"]

_TWEET_ID_RE = re.compile(r"^[0-9]{1,19}$")


def validate_post_id(value: str) -> str:
    post_id = value.strip()
    if not _TWEET_ID_RE.fullmatch(post_id):
        raise UsageError("Post id must be a numeric ID.")
    return post_id


def parse_post_reference(*, post_id: str | None = None, url: str | None = None) -> str:
    id_value = (post_id or "").strip()
    url_value = (url or "").strip()

    if bool(id_value) == bool(url_value):
        raise UsageError("Provide exactly one of --id or --url.")

    if id_value:
        return validate_post_id(id_value)

    parsed = urlparse(url_value)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host not in {"x.com", "twitter.com", "mobile.x.com", "mobile.twitter.com"}:
        raise UsageError("--url must be an x.com or twitter.com post URL.")

    parts = [part for part in parsed.path.split("/") if part]
    status_index = next((idx for idx, part in enumerate(parts) if part == "status"), -1)
    if status_index == -1 or status_index + 1 >= len(parts):
        raise UsageError("--url must include /status/<post_id>.")

    return validate_post_id(parts[status_index + 1])


def _normalize_media_ids(media_ids: list[str] | None) -> list[str]:
    if not media_ids:
        return []

    normalized: list[str] = []
    for media_id in media_ids:
        value = media_id.strip()
        if not value:
            continue
        if not _TWEET_ID_RE.fullmatch(value):
            raise UsageError("Media id must be numeric.")
        normalized.append(value)

    if len(normalized) > 4:
        raise UsageError("A post can include at most 4 media items.")
    return normalized


def build_post_payload(*, text: str | None, media_ids: list[str] | None = None) -> dict[str, Any]:
    media = _normalize_media_ids(media_ids)
    text_value = (text or "").strip()

    if not text_value and not media:
        raise UsageError("Post requires text or media.")

    payload: dict[str, Any] = {}
    if text_value:
        payload["text"] = text_value
    if media:
        payload["media"] = {"media_ids": media}
    return payload


def build_payload(
    *,
    op: Operation,
    text: str,
    to_id: str | None = None,
    media_ids: list[str] | None = None,
) -> dict[str, Any]:
    if op == "post":
        return build_post_payload(text=text, media_ids=media_ids)

    media = _normalize_media_ids(media_ids)
    if op == "reply":
        if not to_id:
            raise UsageError("reply requires --to <post_id>.")
        payload: dict[str, Any] = {
            "text": text,
            "reply": {"in_reply_to_tweet_id": validate_post_id(to_id)},
        }
        if media:
            payload["media"] = {"media_ids": media}
        return payload
    if op == "quote":
        if not to_id:
            raise UsageError("quote requires --to <post_id>.")
        if media:
            raise UsageError("quote does not support media attachments.")
        return {"text": text, "quote_tweet_id": validate_post_id(to_id)}
    raise UsageError(f"Unknown operation: {op}")


def op_requires_target(op: Operation) -> bool:
    return op in {"reply", "quote"}
