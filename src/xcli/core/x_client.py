"""Thin wrappers around XDK client calls."""

from __future__ import annotations

import mimetypes
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from xcli.core.errors import ApiError, UsageError

DEFAULT_POST_FIELDS = ["created_at", "author_id", "public_metrics"]
DEFAULT_USER_FIELDS = ["id", "username", "name"]
UPLOAD_IMAGE_MEDIA_TYPES = {
    "image/jpeg",
    "image/bmp",
    "image/png",
    "image/webp",
    "image/pjpeg",
    "image/tiff",
}


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


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _as_mapping_list(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        return [value]
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _extract_user_lookup(raw: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    includes = raw.get("includes")
    include_map = _as_mapping(includes)
    users = _as_mapping_list(include_map.get("users"))
    lookup: dict[str, Mapping[str, Any]] = {}
    for user in users:
        user_id = user.get("id")
        if isinstance(user_id, str) and user_id:
            lookup[user_id] = user
    return lookup


def _with_author_fields(
    post: Mapping[str, Any],
    *,
    users_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    item = dict(post)
    author_id = item.get("author_id")
    if not isinstance(author_id, str):
        return item
    author = users_by_id.get(author_id)
    if not isinstance(author, Mapping):
        return item
    username = author.get("username")
    name = author.get("name")
    if isinstance(username, str) and username:
        item.setdefault("author_username", username)
    if isinstance(name, str) and name:
        item.setdefault("author_name", name)
    return item


def get_post_by_id(client: Any, post_id: str) -> dict[str, Any]:
    try:
        response = client.posts.get_by_id(
            id=post_id,
            tweet_fields=DEFAULT_POST_FIELDS,
            expansions=["author_id"],
            user_fields=DEFAULT_USER_FIELDS,
        )
    except Exception as exc:  # pragma: no cover
        raise ApiError(_format_api_exception("Failed to fetch post", exc)) from exc

    raw = _to_data(response)
    raw_map = _as_mapping(raw)
    posts = _as_mapping_list(raw_map.get("data"))
    if not posts:
        raise ApiError("Post lookup response did not include post data.")

    users_by_id = _extract_user_lookup(raw_map)
    data = _with_author_fields(posts[0], users_by_id=users_by_id)
    return {
        "id": data.get("id"),
        "text": data.get("text"),
        "created_at": data.get("created_at"),
        "author_id": data.get("author_id"),
        "author_username": data.get("author_username"),
        "author_name": data.get("author_name"),
        "raw": raw,
    }


def get_user_by_username(client: Any, username: str) -> dict[str, Any]:
    try:
        response = client.users.get_by_username(
            username=username,
            user_fields=DEFAULT_USER_FIELDS,
        )
    except Exception as exc:  # pragma: no cover
        raise ApiError(_format_api_exception("Failed to fetch user by handle", exc)) from exc

    raw = _to_data(response)
    raw_map = _as_mapping(raw)
    data = _as_mapping(raw_map.get("data"))
    if not data:
        raise ApiError("User lookup response did not include user data.")

    user_id = data.get("id")
    if not isinstance(user_id, str) or not user_id:
        raise ApiError("User lookup response did not include a user id.")

    return {
        "id": user_id,
        "username": data.get("username"),
        "name": data.get("name"),
        "raw": raw,
    }


def _collect_posts(pages: Iterator[Any], *, limit: int) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    if limit < 1:
        return collected

    for page in pages:
        raw = _to_data(page)
        raw_map = _as_mapping(raw)
        users_by_id = _extract_user_lookup(raw_map)
        page_posts = _as_mapping_list(raw_map.get("data"))
        for post in page_posts:
            collected.append(_with_author_fields(post, users_by_id=users_by_id))
            if len(collected) >= limit:
                return collected
    return collected


def get_user_posts(client: Any, user_id: str, *, limit: int = 10) -> list[dict[str, Any]]:
    try:
        pages = client.users.get_posts(
            id=user_id,
            max_results=min(max(limit, 5), 100),
            tweet_fields=DEFAULT_POST_FIELDS,
            expansions=["author_id"],
            user_fields=DEFAULT_USER_FIELDS,
        )
    except Exception as exc:  # pragma: no cover
        raise ApiError(_format_api_exception("Failed to fetch user posts", exc)) from exc

    return _collect_posts(pages, limit=limit)


def get_user_timeline(client: Any, user_id: str, *, limit: int = 10) -> list[dict[str, Any]]:
    try:
        pages = client.users.get_timeline(
            id=user_id,
            max_results=min(max(limit, 5), 100),
            tweet_fields=DEFAULT_POST_FIELDS,
            expansions=["author_id"],
            user_fields=DEFAULT_USER_FIELDS,
        )
    except Exception as exc:  # pragma: no cover
        raise ApiError(_format_api_exception("Failed to fetch timeline", exc)) from exc

    return _collect_posts(pages, limit=limit)


def _detect_upload_media_type(file_path: Path) -> str:
    media_type, _ = mimetypes.guess_type(file_path.name)
    if not isinstance(media_type, str) or media_type not in UPLOAD_IMAGE_MEDIA_TYPES:
        allowed = ", ".join(sorted(UPLOAD_IMAGE_MEDIA_TYPES))
        raise UsageError(f"Unsupported media type for `{file_path}`. Supported: {allowed}.")
    return media_type


def upload_media_file(client: Any, file_path: Path) -> dict[str, Any]:
    if not file_path.exists() or not file_path.is_file():
        raise UsageError(f"Media file not found: {file_path}")

    media_type = _detect_upload_media_type(file_path)

    access_token = getattr(client, "access_token", None)
    if not isinstance(access_token, str) or not access_token:
        raise ApiError("Media upload requires an OAuth user access token.")

    url = f"{client.base_url}/2/media/upload"
    headers = {"Authorization": f"Bearer {access_token}"}
    form_data = {
        "media_category": "tweet_image",
        "media_type": media_type,
    }

    try:
        with file_path.open("rb") as handle:
            files = {"media": (file_path.name, handle, media_type)}
            response = client.session.post(url, headers=headers, data=form_data, files=files)
        response.raise_for_status()
    except Exception as exc:  # pragma: no cover
        raise ApiError(
            _format_api_exception(f"Media upload failed for {file_path.name}", exc)
        ) from exc

    raw = _to_data(response.json())
    response_data = _as_mapping(_as_mapping(raw).get("data"))
    media_id = response_data.get("id")
    if not isinstance(media_id, str) or not media_id:
        raise ApiError("Media upload response did not include an id.")

    return {
        "id": media_id,
        "media_key": response_data.get("media_key"),
        "raw": raw,
    }


def validate_media_files(media_files: list[Path]) -> None:
    if len(media_files) > 4:
        raise UsageError("A post can include at most 4 media files.")

    for media_file in media_files:
        if not media_file.exists() or not media_file.is_file():
            raise UsageError(f"Media file not found: {media_file}")
        _detect_upload_media_type(media_file)


def upload_media_files(client: Any, media_files: list[Path]) -> list[str]:
    validate_media_files(media_files)

    media_ids: list[str] = []
    for media_file in media_files:
        uploaded = upload_media_file(client, media_file)
        media_ids.append(uploaded["id"])
    return media_ids
