"""Thin wrappers around XDK client calls."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from xcli.core.errors import ApiError


def _load_client_cls() -> Any:
    try:
        from xdk import Client
    except ImportError as exc:  # pragma: no cover
        raise ApiError("xdk is not installed. Install with `pip install x-cli`.") from exc
    return Client


def _to_data(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _to_data(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_data(v) for v in value]
    if hasattr(value, "model_dump"):
        return _to_data(value.model_dump(exclude_none=True))
    if hasattr(value, "dict"):
        return _to_data(value.dict())
    return value


def _format_api_exception(prefix: str, exc: Exception) -> str:
    response = getattr(exc, "response", None)
    if response is None:
        return f"{prefix}: {exc}"

    status_code = getattr(response, "status_code", "?")
    reason = getattr(response, "reason", "")
    base = f"{prefix}: {status_code} {reason}".strip()

    try:
        payload = response.json()
    except Exception:
        payload = None

    if isinstance(payload, Mapping):
        title = payload.get("title")
        detail = payload.get("detail")
        if isinstance(title, str) and isinstance(detail, str):
            return f"{base} - {title}: {detail}"
        if isinstance(detail, str):
            return f"{base} - {detail}"

    text = getattr(response, "text", "")
    if isinstance(text, str) and text:
        return f"{base} - {text[:500]}"

    return base


def make_user_client(access_token: str) -> Any:
    Client = _load_client_cls()
    return Client(access_token=access_token)


def get_me(client: Any) -> dict[str, Any]:
    try:
        response = client.users.get_me()
    except Exception as exc:  # pragma: no cover
        raise ApiError(_format_api_exception("Failed to fetch authenticated user", exc)) from exc

    raw = _to_data(response)
    data = raw.get("data", {}) if isinstance(raw, Mapping) else {}
    if not isinstance(data, Mapping):
        data = {}
    return {
        "id": data.get("id"),
        "username": data.get("username"),
        "name": data.get("name"),
        "raw": raw,
    }


def create_post(client: Any, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        response = client.posts.create(body=payload)
    except Exception as exc:  # pragma: no cover
        raise ApiError(_format_api_exception("Post create failed", exc)) from exc

    raw = _to_data(response)
    data = raw.get("data", {}) if isinstance(raw, Mapping) else {}
    if not isinstance(data, Mapping):
        data = {}

    post_id = data.get("id")
    text = data.get("text")

    if not post_id:
        raise ApiError("Post create response did not include an id.")

    return {
        "id": str(post_id),
        "text": text,
        "raw": raw,
    }


def post_url(username: str | None, post_id: str) -> str | None:
    if not username:
        return None
    return f"https://x.com/{username}/status/{post_id}"
