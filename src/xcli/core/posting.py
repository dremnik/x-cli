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


def build_payload(*, op: Operation, text: str, to_id: str | None = None) -> dict[str, Any]:
    if op == "post":
        return {"text": text}
    if op == "reply":
        if not to_id:
            raise UsageError("reply requires --to <post_id>.")
        return {"text": text, "reply": {"in_reply_to_tweet_id": validate_post_id(to_id)}}
    if op == "quote":
        if not to_id:
            raise UsageError("quote requires --to <post_id>.")
        return {"text": text, "quote_tweet_id": validate_post_id(to_id)}
    raise UsageError(f"Unknown operation: {op}")


def op_requires_target(op: Operation) -> bool:
    return op in {"reply", "quote"}
