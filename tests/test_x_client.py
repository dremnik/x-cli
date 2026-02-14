from pathlib import Path

import pytest

from xcli.core.errors import UsageError
from xcli.core.x_client import _detect_upload_media_type, get_user_posts, validate_media_files


class _FakeUsers:
    def __init__(self) -> None:
        self.last_kwargs: dict[str, object] = {}

    def get_posts(self, **kwargs: object) -> list[dict[str, object]]:
        self.last_kwargs = kwargs
        return [{"data": []}]


class _FakeClient:
    def __init__(self) -> None:
        self.users = _FakeUsers()


def test_detect_upload_media_type_accepts_png(tmp_path: Path) -> None:
    file_path = tmp_path / "image.png"
    file_path.write_bytes(b"png")
    assert _detect_upload_media_type(file_path) == "image/png"


def test_detect_upload_media_type_rejects_unsupported(tmp_path: Path) -> None:
    file_path = tmp_path / "notes.txt"
    file_path.write_text("hello")
    with pytest.raises(UsageError):
        _detect_upload_media_type(file_path)


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
