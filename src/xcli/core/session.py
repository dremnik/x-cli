"""Authenticated session helpers for command handlers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from xcli.core.config import load_settings
from xcli.core.errors import AuthError
from xcli.core.token_store import TokenStore
from xcli.core.x_auth import refresh_if_needed
from xcli.core.x_client import make_user_client


def _get_refreshed_token() -> dict[str, Any]:
    settings = load_settings()
    store = TokenStore()
    token = store.load()
    if not token:
        raise AuthError("No token found. Run `xcli auth login` first.")

    refreshed = refresh_if_needed(settings, token)
    if refreshed != token:
        store.save(refreshed)

    if not isinstance(refreshed, Mapping):
        raise AuthError("Token store returned invalid data. Run `xcli auth login`.")

    return dict(refreshed)


def get_access_token() -> str:
    token = _get_refreshed_token()
    access_token = token.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise AuthError("Token file is missing access_token. Run `xcli auth login`.")
    return access_token


def get_token_scopes() -> set[str]:
    token = _get_refreshed_token()
    value = token.get("scope")
    if isinstance(value, str):
        return {item for item in value.split() if item}
    if isinstance(value, list):
        return {item for item in value if isinstance(item, str) and item}
    return set()


def make_authed_client() -> Any:
    return make_user_client(get_access_token())
