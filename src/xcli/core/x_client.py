"""Thin wrappers around XDK client calls."""

from __future__ import annotations

import mimetypes
import re
import time
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from xcli.core.errors import ApiError, UsageError

DEFAULT_POST_FIELDS = ["created_at", "author_id", "public_metrics"]
DETAIL_POST_FIELDS = [
    "created_at",
    "author_id",
    "public_metrics",
    "entities",
    "article",
    "note_tweet",
    "attachments",
    "card_uri",
    "suggested_source_links",
    "suggested_source_links_with_counts",
]
DEFAULT_USER_FIELDS = ["id", "username", "name"]
DETAIL_MEDIA_FIELDS = [
    "media_key",
    "type",
    "url",
    "preview_image_url",
    "width",
    "height",
    "alt_text",
]
UPLOAD_IMAGE_MEDIA_TYPES = {
    "image/jpeg",
    "image/bmp",
    "image/png",
    "image/webp",
    "image/pjpeg",
    "image/tiff",
}
VIDEO_EXT_TO_MEDIA_TYPE = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".ts": "video/mp2t",
}
SUBTITLE_EXT_TO_MEDIA_TYPE = {
    ".srt": "text/srt",
    ".vtt": "text/vtt",
}
SUBTITLE_LANG_RE = re.compile(r"^[A-Z]{2}$")
VIDEO_CHUNK_BYTES = 4 * 1024 * 1024


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

    suffix = ""
    headers = getattr(response, "headers", {})
    if isinstance(headers, Mapping):
        # Attempt standard rate limit header extraction
        limit = headers.get("x-rate-limit-limit")
        remaining = headers.get("x-rate-limit-remaining")
        reset = headers.get("x-rate-limit-reset")
        
        if limit is not None and remaining is not None:
             suffix = f"{suffix}\nRate limit: {remaining}/{limit}"
        
        if reset is not None:
             try:
                 reset_ts = int(reset)
                 reset_time = time.strftime("%H:%M:%S", time.localtime(reset_ts))
                 suffix = f"{suffix} (resets at {reset_time})"
             except (ValueError, TypeError):
                 pass

    try:
        payload = response.json()
    except Exception:
        payload = None

    if isinstance(payload, Mapping):
        title = payload.get("title")
        detail = payload.get("detail")
        if isinstance(title, str) and isinstance(detail, str):
            return f"{base} - {title}: {detail}{suffix}"
        if isinstance(detail, str):
            return f"{base} - {detail}{suffix}"

    text = getattr(response, "text", "")
    if isinstance(text, str) and text:
        return f"{base} - {text[:500]}{suffix}"

    return f"{base}{suffix}"


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
            tweet_fields=DETAIL_POST_FIELDS,
            expansions=[
                "author_id",
                "article.cover_media",
                "article.media_entities",
                "attachments.media_keys",
            ],
            user_fields=DEFAULT_USER_FIELDS,
            media_fields=DETAIL_MEDIA_FIELDS,
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
        "article": data.get("article"),
        "note_tweet": data.get("note_tweet"),
        "entities": data.get("entities"),
        "public_metrics": data.get("public_metrics"),
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


def get_user_posts(
    client: Any,
    user_id: str,
    *,
    limit: int = 10,
    exclude_replies: bool = False,
) -> list[dict[str, Any]]:
    exclude_entities = ["replies"] if exclude_replies else None
    try:
        pages = client.users.get_posts(
            id=user_id,
            max_results=min(max(limit, 5), 100),
            exclude=exclude_entities,
            tweet_fields=DEFAULT_POST_FIELDS,
            expansions=["author_id"],
            user_fields=DEFAULT_USER_FIELDS,
        )
    except Exception as exc:  # pragma: no cover
        raise ApiError(_format_api_exception("Failed to fetch user posts", exc)) from exc

    return _collect_posts(pages, limit=limit)


def get_user_timeline(
    client: Any,
    user_id: str,
    *,
    limit: int = 10,
    exclude_replies: bool = False,
) -> list[dict[str, Any]]:
    exclude_entities = ["replies"] if exclude_replies else None
    try:
        pages = client.users.get_timeline(
            id=user_id,
            max_results=min(max(limit, 5), 100),
            exclude=exclude_entities,
            tweet_fields=DEFAULT_POST_FIELDS,
            expansions=["author_id"],
            user_fields=DEFAULT_USER_FIELDS,
        )
    except Exception as exc:  # pragma: no cover
        raise ApiError(_format_api_exception("Failed to fetch timeline", exc)) from exc

    return _collect_posts(pages, limit=limit)


def fetch_bookmarks(
    client: Any,
    user_id: str,
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Fetch user bookmarks using raw session calls."""
    collected: list[dict[str, Any]] = []
    if limit < 1:
        return collected

    access_token = _require_access_token(client)
    url = f"{client.base_url}/2/users/{user_id}/bookmarks"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "max_results": min(max(limit, 1), 100),
        "tweet.fields": ",".join(DEFAULT_POST_FIELDS),
        "expansions": "author_id",
        "user.fields": ",".join(DEFAULT_USER_FIELDS),
    }

    pagination_token: str | None = None
    while True:
        current_params = params.copy()
        if pagination_token:
            current_params["pagination_token"] = pagination_token

        try:
            response = client.session.get(url, headers=headers, params=current_params)
            response.raise_for_status()
        except Exception as exc:  # pragma: no cover
            raise ApiError(_format_api_exception("Failed to fetch bookmarks", exc)) from exc

        raw = _to_data(response.json())
        raw_map = _as_mapping(raw)
        meta = _as_mapping(raw_map.get("meta"))
        
        users_by_id = _extract_user_lookup(raw_map)
        page_posts = _as_mapping_list(raw_map.get("data"))
        
        for post in page_posts:
            collected.append(_with_author_fields(post, users_by_id=users_by_id))
            if len(collected) >= limit:
                return collected

        pagination_token = meta.get("next_token")
        if not isinstance(pagination_token, str) or not pagination_token:
            break

    return collected


def create_bookmark(client: Any, user_id: str, tweet_id: str) -> dict[str, Any]:
    """Create a bookmark for the authenticated user."""
    access_token = _require_access_token(client)
    url = f"{client.base_url}/2/users/{user_id}/bookmarks"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {"tweet_id": tweet_id}

    try:
        response = client.session.post(url, headers=headers, json=payload)
        response.raise_for_status()
    except Exception as exc:  # pragma: no cover
        raise ApiError(_format_api_exception("Failed to create bookmark", exc)) from exc

    raw = _to_data(response.json())
    return dict(_as_mapping(raw.get("data")))


def delete_bookmark(client: Any, user_id: str, tweet_id: str) -> dict[str, Any]:
    """Delete a bookmark for the authenticated user."""
    access_token = _require_access_token(client)
    url = f"{client.base_url}/2/users/{user_id}/bookmarks/{tweet_id}"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        response = client.session.delete(url, headers=headers)
        response.raise_for_status()
    except Exception as exc:  # pragma: no cover
        raise ApiError(_format_api_exception("Failed to delete bookmark", exc)) from exc

    raw = _to_data(response.json())
    return dict(_as_mapping(raw.get("data")))


def _detect_upload_media_type(file_path: Path) -> str:
    media_type, _ = mimetypes.guess_type(file_path.name)
    if not isinstance(media_type, str) or media_type not in UPLOAD_IMAGE_MEDIA_TYPES:
        allowed = ", ".join(sorted(UPLOAD_IMAGE_MEDIA_TYPES))
        raise UsageError(f"Unsupported media type for `{file_path}`. Supported: {allowed}.")
    return media_type


def _detect_upload_video_media_type(file_path: Path) -> str:
    media_type = VIDEO_EXT_TO_MEDIA_TYPE.get(file_path.suffix.lower())
    if not isinstance(media_type, str):
        allowed = ", ".join(sorted(VIDEO_EXT_TO_MEDIA_TYPE))
        raise UsageError(f"Unsupported video format for `{file_path}`. Supported: {allowed}.")
    return media_type


def _detect_upload_subtitle_media_type(file_path: Path) -> str:
    media_type = SUBTITLE_EXT_TO_MEDIA_TYPE.get(file_path.suffix.lower())
    if not isinstance(media_type, str):
        allowed = ", ".join(sorted(SUBTITLE_EXT_TO_MEDIA_TYPE))
        raise UsageError(f"Unsupported subtitle format for `{file_path}`. Supported: {allowed}.")
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


def _require_access_token(client: Any) -> str:
    access_token = getattr(client, "access_token", None)
    if not isinstance(access_token, str) or not access_token:
        raise ApiError("Media upload requires an OAuth user access token.")
    return access_token


def _extract_media_id(raw: Mapping[str, Any], *, context: str) -> str:
    response_data = _as_mapping(raw.get("data"))
    media_id = response_data.get("id")
    if not isinstance(media_id, str) or not media_id:
        raise ApiError(f"{context} response did not include an id.")
    return media_id


def _extract_processing_info(raw: Mapping[str, Any]) -> Mapping[str, Any]:
    return _as_mapping(_as_mapping(raw.get("data")).get("processing_info"))


def _processing_error_message(info: Mapping[str, Any]) -> str | None:
    error = _as_mapping(info.get("error"))
    name = error.get("name")
    message = error.get("message")
    if isinstance(name, str) and isinstance(message, str) and name and message:
        return f"{name}: {message}"
    if isinstance(message, str) and message:
        return message
    return None


def _wait_for_video_processing(
    client: Any,
    media_id: str,
    *,
    timeout_sec: int,
    initial_info: Mapping[str, Any],
) -> None:
    info: Mapping[str, Any] = initial_info
    deadline = time.monotonic() + timeout_sec

    while info:
        state = info.get("state")
        if state == "succeeded":
            return
        if state == "failed":
            detail = _processing_error_message(info)
            if detail:
                raise ApiError(f"Video processing failed: {detail}")
            raise ApiError("Video processing failed.")
        if state not in {"pending", "in_progress"}:
            return

        now = time.monotonic()
        if now >= deadline:
            raise ApiError(f"Timed out waiting for video processing after {timeout_sec}s.")

        wait_value = info.get("check_after_secs")
        if isinstance(wait_value, (int, float)):
            wait_sec = max(1.0, float(wait_value))
        else:
            wait_sec = 1.0

        remaining = deadline - now
        time.sleep(min(wait_sec, max(0.1, remaining)))

        access_token = _require_access_token(client)
        url = f"{client.base_url}/2/media/upload"
        params = {"command": "STATUS", "media_id": media_id}
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            response = client.session.get(url, headers=headers, params=params)
            response.raise_for_status()
        except Exception as exc:  # pragma: no cover
            raise ApiError(_format_api_exception("Media status check failed", exc)) from exc

        status_raw = _as_mapping(_to_data(response.json()))
        info = _extract_processing_info(status_raw)


def upload_video_media_file(
    client: Any,
    file_path: Path,
    *,
    poll_timeout_sec: int = 120,
) -> dict[str, Any]:
    if not file_path.exists() or not file_path.is_file():
        raise UsageError(f"Media file not found: {file_path}")
    if poll_timeout_sec < 1:
        raise UsageError("poll_timeout_sec must be >= 1")

    media_type = _detect_upload_video_media_type(file_path)
    access_token = _require_access_token(client)

    total_bytes = file_path.stat().st_size
    if total_bytes <= 0:
        raise UsageError(f"Video file is empty: {file_path}")

    headers = {"Authorization": f"Bearer {access_token}"}
    init_url = f"{client.base_url}/2/media/upload/initialize"
    init_payload = {
        "media_type": media_type,
        "media_category": "tweet_video",
        "total_bytes": total_bytes,
    }

    try:
        init_response = client.session.post(init_url, headers=headers, json=init_payload)
        init_response.raise_for_status()
    except Exception as exc:  # pragma: no cover
        raise ApiError(_format_api_exception("Video upload initialize failed", exc)) from exc

    init_raw = _as_mapping(_to_data(init_response.json()))
    media_id = _extract_media_id(init_raw, context="Video upload initialize")

    append_url = f"{client.base_url}/2/media/upload/{media_id}/append"
    try:
        with file_path.open("rb") as handle:
            segment_index = 0
            while True:
                chunk = handle.read(VIDEO_CHUNK_BYTES)
                if not chunk:
                    break
                files = {"media": (f"chunk-{segment_index}.bin", chunk, media_type)}
                data = {"segment_index": str(segment_index)}
                append_response = client.session.post(
                    append_url,
                    headers=headers,
                    data=data,
                    files=files,
                )
                append_response.raise_for_status()
                segment_index += 1
    except Exception as exc:  # pragma: no cover
        raise ApiError(_format_api_exception("Video upload append failed", exc)) from exc

    finalize_url = f"{client.base_url}/2/media/upload/{media_id}/finalize"
    try:
        finalize_response = client.session.post(finalize_url, headers=headers)
        finalize_response.raise_for_status()
    except Exception as exc:  # pragma: no cover
        raise ApiError(_format_api_exception("Video upload finalize failed", exc)) from exc

    finalize_raw = _as_mapping(_to_data(finalize_response.json()))
    processing_info = _extract_processing_info(finalize_raw)
    if processing_info:
        _wait_for_video_processing(
            client,
            media_id,
            timeout_sec=poll_timeout_sec,
            initial_info=processing_info,
        )

    return {
        "id": media_id,
        "media_key": _as_mapping(finalize_raw.get("data")).get("media_key"),
        "raw": finalize_raw,
    }


def upload_subtitle_media_file(client: Any, file_path: Path) -> dict[str, Any]:
    if not file_path.exists() or not file_path.is_file():
        raise UsageError(f"Media file not found: {file_path}")

    media_type = _detect_upload_subtitle_media_type(file_path)
    access_token = _require_access_token(client)

    total_bytes = file_path.stat().st_size
    if total_bytes <= 0:
        raise UsageError(f"Subtitle file is empty: {file_path}")

    headers = {"Authorization": f"Bearer {access_token}"}

    init_url = f"{client.base_url}/2/media/upload/initialize"
    init_payload = {
        "media_category": "subtitles",
        "media_type": media_type,
        "total_bytes": total_bytes,
    }

    try:
        init_response = client.session.post(init_url, headers=headers, json=init_payload)
        init_response.raise_for_status()
    except Exception as exc:  # pragma: no cover
        raise ApiError(_format_api_exception("Subtitle upload initialize failed", exc)) from exc

    init_raw = _as_mapping(_to_data(init_response.json()))
    media_id = _extract_media_id(init_raw, context="Subtitle upload initialize")

    append_url = f"{client.base_url}/2/media/upload/{media_id}/append"
    try:
        with file_path.open("rb") as handle:
            files = {"media": (file_path.name, handle, media_type)}
            data = {"segment_index": "0"}
            append_response = client.session.post(
                append_url,
                headers=headers,
                data=data,
                files=files,
            )
        append_response.raise_for_status()
    except Exception as exc:  # pragma: no cover
        raise ApiError(
            _format_api_exception(f"Subtitle upload append failed for {file_path.name}", exc)
        ) from exc

    finalize_url = f"{client.base_url}/2/media/upload/{media_id}/finalize"
    try:
        finalize_response = client.session.post(finalize_url, headers=headers)
        finalize_response.raise_for_status()
    except Exception as exc:  # pragma: no cover
        raise ApiError(_format_api_exception("Subtitle upload finalize failed", exc)) from exc

    raw = _as_mapping(_to_data(finalize_response.json()))
    media_id = _extract_media_id(raw, context="Subtitle upload finalize")
    return {
        "id": media_id,
        "media_key": _as_mapping(raw.get("data")).get("media_key"),
        "raw": raw,
    }


def attach_subtitle_to_video(
    client: Any,
    *,
    video_media_id: str,
    subtitle_media_id: str,
    language_code: str = "EN",
    display_name: str = "English",
) -> dict[str, Any]:
    lang = language_code.strip().upper()
    if not SUBTITLE_LANG_RE.fullmatch(lang):
        raise UsageError("Subtitle language code must be 2 letters (example: EN).")

    title = display_name.strip()
    if not title:
        raise UsageError("Subtitle display name cannot be empty.")

    access_token = _require_access_token(client)
    url = f"{client.base_url}/2/media/subtitles"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "id": video_media_id,
        "media_category": "TweetVideo",
        "subtitles": {
            "id": subtitle_media_id,
            "language_code": lang,
            "display_name": title,
        },
    }

    try:
        response = client.session.post(url, headers=headers, json=payload)
        response.raise_for_status()
    except Exception as exc:  # pragma: no cover
        raise ApiError(_format_api_exception("Subtitle association failed", exc)) from exc

    raw = _as_mapping(_to_data(response.json()))
    return {"raw": raw}


def upload_video_with_subtitles(
    client: Any,
    *,
    video_file: Path,
    subtitle_file: Path,
    subtitle_language_code: str = "EN",
    subtitle_display_name: str = "English",
    poll_timeout_sec: int = 120,
) -> dict[str, Any]:
    if not video_file.exists() or not video_file.is_file():
        raise UsageError(f"Media file not found: {video_file}")
    if not subtitle_file.exists() or not subtitle_file.is_file():
        raise UsageError(f"Media file not found: {subtitle_file}")

    _detect_upload_video_media_type(video_file)
    _detect_upload_subtitle_media_type(subtitle_file)

    uploaded_video = upload_video_media_file(client, video_file, poll_timeout_sec=poll_timeout_sec)
    uploaded_subtitle = upload_subtitle_media_file(client, subtitle_file)
    associated = attach_subtitle_to_video(
        client,
        video_media_id=uploaded_video["id"],
        subtitle_media_id=uploaded_subtitle["id"],
        language_code=subtitle_language_code,
        display_name=subtitle_display_name,
    )

    return {
        "video_media_id": uploaded_video["id"],
        "subtitle_media_id": uploaded_subtitle["id"],
        "video": uploaded_video,
        "subtitle": uploaded_subtitle,
        "association": associated,
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
