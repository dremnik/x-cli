"""Tests for bookmark methods in x_client."""

import pytest
from typing import Any

from xcli.core.errors import ApiError
from xcli.core.x_client import (
    create_bookmark,
    delete_bookmark,
    fetch_bookmarks,
)


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
            raise Exception(f"HTTP {self.status_code}")


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.last_json: Any = None
        self.last_params: Any = None

    def get(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append(("GET", url))
        self.last_params = kwargs.get("params")
        if url.endswith("/bookmarks"):
            return _FakeResponse({
                "data": [
                    {"id": "101", "text": "bookmark 1", "author_id": "99"},
                    {"id": "102", "text": "bookmark 2", "author_id": "99"},
                ],
                "meta": {"result_count": 2},
                "includes": {
                    "users": [{"id": "99", "username": "author99", "name": "Author 99"}]
                }
            })
        return _FakeResponse({})

    def post(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append(("POST", url))
        self.last_json = kwargs.get("json")
        return _FakeResponse({"data": {"bookmarked": True}})

    def delete(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append(("DELETE", url))
        return _FakeResponse({"data": {"bookmarked": False}})


class _FakeClient:
    def __init__(self) -> None:
        self.base_url = "https://api.x.com"
        self.access_token = "token"
        self.session = _FakeSession()


def test_fetch_bookmarks_calls_correct_endpoint() -> None:
    client = _FakeClient()
    bookmarks = fetch_bookmarks(client, "123", limit=5)
    
    assert len(bookmarks) == 2
    assert bookmarks[0]["id"] == "101"
    assert bookmarks[0]["author_username"] == "author99"
    
    assert client.session.calls == [
        ("GET", "https://api.x.com/2/users/123/bookmarks"),
    ]
    assert client.session.last_params["max_results"] == 5


def test_create_bookmark_calls_correct_endpoint() -> None:
    client = _FakeClient()
    result = create_bookmark(client, "123", "999")
    
    assert result == {"bookmarked": True}
    assert client.session.calls == [
        ("POST", "https://api.x.com/2/users/123/bookmarks"),
    ]
    assert client.session.last_json == {"tweet_id": "999"}


def test_delete_bookmark_calls_correct_endpoint() -> None:
    client = _FakeClient()
    result = delete_bookmark(client, "123", "999")
    
    assert result == {"bookmarked": False}
    assert client.session.calls == [
        ("DELETE", "https://api.x.com/2/users/123/bookmarks/999"),
    ]
