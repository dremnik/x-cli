"""Payload and ID helpers for post operations."""

from __future__ import annotations

import re
from typing import Any, Literal

from xcli.core.errors import UsageError

Operation = Literal["post", "reply", "quote"]

_TWEET_ID_RE = re.compile(r"^[0-9]{1,19}$")


def validate_post_id(value: str) -> str:
    post_id = value.strip()
    if not _TWEET_ID_RE.fullmatch(post_id):
        raise UsageError("Post id must be a numeric ID.")
    return post_id


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


def build_payload(
    *,
    op: Operation,
    text: str,
    to_id: str | None = None,
    media_ids: list[str] | None = None,
) -> dict[str, Any]:
    media = _normalize_media_ids(media_ids)

    if op == "post":
        payload: dict[str, Any] = {"text": text}
        if media:
            payload["media"] = {"media_ids": media}
        return payload
    if op == "reply":
        if not to_id:
            raise UsageError("reply requires --to <post_id>.")
        payload = {"text": text, "reply": {"in_reply_to_tweet_id": validate_post_id(to_id)}}
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
