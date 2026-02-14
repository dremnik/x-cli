from pathlib import Path
from typing import Any

import pytest

from xcli.core.errors import UsageError
from xcli.core.x_client import (
    _detect_upload_media_type,
    _detect_upload_subtitle_media_type,
    _detect_upload_video_media_type,
    get_user_posts,
    upload_video_with_subtitles,
    validate_media_files,
)


class _FakeUsers:
    def __init__(self) -> None:
        self.last_kwargs: dict[str, object] = {}

    def get_posts(self, **kwargs: object) -> list[dict[str, object]]:
        self.last_kwargs = kwargs
        return [{"data": []}]


class _FakeClient:
    def __init__(self) -> None:
        self.users = _FakeUsers()


class _FakeHttpError(Exception):
    def __init__(self, response: Any) -> None:
        super().__init__("http error")
        self.response = response


class _FakeResponse:
    def __init__(self, payload: dict[str, object], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.reason = "ok" if status_code < 400 else "error"
        self.text = ""

    def json(self) -> dict[str, object]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise _FakeHttpError(self)


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.subtitle_payload: dict[str, object] | None = None

    def post(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append(("POST", url))

        if url.endswith("/2/media/upload/101/append"):
            return _FakeResponse({"data": {}})
        if url.endswith("/2/media/upload/101/finalize"):
            return _FakeResponse({"data": {"id": "101", "processing_info": {"state": "succeeded"}}})
        if url.endswith("/2/media/upload/initialize"):
            if kwargs.get("json", {}).get("media_category") == "subtitles":
                return _FakeResponse({"data": {"id": "202", "media_key": "29_202"}})
            return _FakeResponse({"data": {"id": "101", "media_key": "13_101"}})
        if url.endswith("/2/media/upload/202/append"):
            return _FakeResponse({"data": {}})
        if url.endswith("/2/media/upload/202/finalize"):
            return _FakeResponse({"data": {"id": "202", "media_key": "17_202"}})
        if url.endswith("/2/media/subtitles"):
            payload = kwargs.get("json")
            if isinstance(payload, dict):
                self.subtitle_payload = payload
            return _FakeResponse({"data": {"id": "101"}})

        raise AssertionError(f"Unexpected POST url: {url}")

    def get(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append(("GET", url))
        return _FakeResponse({"data": {"processing_info": {"state": "succeeded"}}})


class _FakeUploadClient:
    def __init__(self) -> None:
        self.base_url = "https://api.x.com"
        self.access_token = "token"
        self.session = _FakeSession()


def test_detect_upload_media_type_accepts_png(tmp_path: Path) -> None:
    file_path = tmp_path / "image.png"
    file_path.write_bytes(b"png")
    assert _detect_upload_media_type(file_path) == "image/png"


def test_detect_upload_media_type_rejects_unsupported(tmp_path: Path) -> None:
    file_path = tmp_path / "notes.txt"
    file_path.write_text("hello")
    with pytest.raises(UsageError):
        _detect_upload_media_type(file_path)


def test_detect_upload_video_media_type_accepts_mp4(tmp_path: Path) -> None:
    file_path = tmp_path / "clip.mp4"
    file_path.write_bytes(b"video")
    assert _detect_upload_video_media_type(file_path) == "video/mp4"


def test_detect_upload_video_media_type_rejects_unsupported(tmp_path: Path) -> None:
    file_path = tmp_path / "clip.mkv"
    file_path.write_bytes(b"video")
    with pytest.raises(UsageError):
        _detect_upload_video_media_type(file_path)


def test_detect_upload_subtitle_media_type_accepts_srt(tmp_path: Path) -> None:
    file_path = tmp_path / "clip.srt"
    file_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nhey\n")
    assert _detect_upload_subtitle_media_type(file_path) == "text/srt"


def test_detect_upload_subtitle_media_type_rejects_unsupported(tmp_path: Path) -> None:
    file_path = tmp_path / "clip.ass"
    file_path.write_text("[Script Info]")
    with pytest.raises(UsageError):
        _detect_upload_subtitle_media_type(file_path)


def test_validate_media_files_rejects_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.png"
    with pytest.raises(UsageError):
        validate_media_files([missing])


def test_validate_media_files_rejects_too_many(tmp_path: Path) -> None:
    media_files = []
    for index in range(5):
        file_path = tmp_path / f"{index}.png"
        file_path.write_bytes(b"png")
        media_files.append(file_path)
    with pytest.raises(UsageError):
        validate_media_files(media_files)


def test_get_user_posts_sets_exclude_replies_when_requested() -> None:
    client = _FakeClient()
    posts = get_user_posts(client, "42", limit=5, exclude_replies=True)
    assert posts == []
    assert client.users.last_kwargs["exclude"] == ["replies"]


def test_get_user_posts_keeps_replies_by_default() -> None:
    client = _FakeClient()
    posts = get_user_posts(client, "42", limit=5)
    assert posts == []
    assert client.users.last_kwargs["exclude"] is None


def test_upload_video_with_subtitles_runs_expected_upload_sequence(tmp_path: Path) -> None:
    client = _FakeUploadClient()
    video_file = tmp_path / "clip.mp4"
    subtitle_file = tmp_path / "clip.srt"
    video_file.write_bytes(b"0000video")
    subtitle_file.write_text("1\n00:00:00,000 --> 00:00:01,000\nhello\n")

    out = upload_video_with_subtitles(
        client,
        video_file=video_file,
        subtitle_file=subtitle_file,
    )

    assert out["video_media_id"] == "101"
    assert out["subtitle_media_id"] == "202"

    assert client.session.calls == [
        ("POST", "https://api.x.com/2/media/upload/initialize"),
        ("POST", "https://api.x.com/2/media/upload/101/append"),
        ("POST", "https://api.x.com/2/media/upload/101/finalize"),
        ("POST", "https://api.x.com/2/media/upload/initialize"),
        ("POST", "https://api.x.com/2/media/upload/202/append"),
        ("POST", "https://api.x.com/2/media/upload/202/finalize"),
        ("POST", "https://api.x.com/2/media/subtitles"),
    ]

    assert client.session.subtitle_payload == {
        "id": "101",
        "media_category": "TweetVideo",
        "subtitles": {
            "id": "202",
            "language_code": "EN",
            "display_name": "English",
        },
    }
