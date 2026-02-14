import pytest

from xcli.core.errors import UsageError
from xcli.core.posting import build_payload, build_post_payload, validate_post_id


def test_validate_post_id_accepts_numeric() -> None:
    assert validate_post_id("123456") == "123456"


def test_validate_post_id_rejects_invalid() -> None:
    with pytest.raises(UsageError):
        validate_post_id("abc")


def test_build_reply_payload() -> None:
    payload = build_payload(op="reply", text="hey", to_id="123")
    assert payload == {"text": "hey", "reply": {"in_reply_to_tweet_id": "123"}}


def test_build_quote_payload_requires_target() -> None:
    with pytest.raises(UsageError):
        build_payload(op="quote", text="hey", to_id=None)


def test_build_post_payload_with_media() -> None:
    payload = build_payload(op="post", text="hey", media_ids=["1", "2"])
    assert payload == {"text": "hey", "media": {"media_ids": ["1", "2"]}}


def test_build_post_payload_allows_media_only() -> None:
    payload = build_post_payload(text="", media_ids=["1"])
    assert payload == {"media": {"media_ids": ["1"]}}


def test_build_post_payload_requires_text_or_media() -> None:
    with pytest.raises(UsageError):
        build_post_payload(text="", media_ids=None)


def test_build_quote_payload_rejects_media() -> None:
    with pytest.raises(UsageError):
        build_payload(op="quote", text="hey", to_id="123", media_ids=["1"])


def test_build_payload_rejects_too_many_media() -> None:
    with pytest.raises(UsageError):
        build_payload(op="post", text="hey", media_ids=["1", "2", "3", "4", "5"])
