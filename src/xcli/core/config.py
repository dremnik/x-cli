"""Configuration loading and path helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from platformdirs import user_config_path

DEFAULT_REDIRECT_URI = "http://localhost:3000/callback"
DEFAULT_SCOPES = (
    "tweet.read",
    "tweet.write",
    "users.read",
    "offline.access",
)


@dataclass(frozen=True)
class Settings:
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: tuple[str, ...]


def token_file_path() -> Path:
    return user_config_path("xcli", appauthor=False, ensure_exists=True) / "auth.json"


def legacy_token_file_path() -> Path:
    return Path.home() / ".twitter" / "auth.json"


def load_settings() -> Settings:
    load_dotenv(override=False)
    load_dotenv(".env.local", override=False)

    scope_str = os.getenv("XCLI_SCOPES", "").strip()
    scopes = tuple(scope_str.split()) if scope_str else DEFAULT_SCOPES

    return Settings(
        client_id=os.getenv("TWITTER_CLIENT_ID", "").strip(),
        client_secret=os.getenv("TWITTER_CLIENT_SECRET", "").strip(),
        redirect_uri=os.getenv("XCLI_REDIRECT_URI", DEFAULT_REDIRECT_URI).strip()
        or DEFAULT_REDIRECT_URI,
        scopes=scopes,
    )
