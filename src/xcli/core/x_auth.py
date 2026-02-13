"""OAuth helpers backed by XDK."""

from __future__ import annotations

import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from xcli.core.config import Settings
from xcli.core.errors import AuthError


def _load_oauth2_auth_cls() -> Any:
    try:
        from xdk.oauth2_auth import OAuth2PKCEAuth
    except ImportError as exc:  # pragma: no cover
        raise AuthError("xdk is not installed. Install with `pip install x-cli`.") from exc
    return OAuth2PKCEAuth


def _load_client_cls() -> Any:
    try:
        from xdk import Client
    except ImportError as exc:  # pragma: no cover
        raise AuthError("xdk is not installed. Install with `pip install x-cli`.") from exc
    return Client


def make_oauth_client(settings: Settings) -> Any:
    if not settings.client_id:
        raise AuthError("TWITTER_CLIENT_ID is required for OAuth login.")

    Client = _load_client_cls()
    kwargs: dict[str, Any] = {
        "client_id": settings.client_id,
        "redirect_uri": settings.redirect_uri,
        "scope": " ".join(settings.scopes),
    }
    if settings.client_secret:
        kwargs["client_secret"] = settings.client_secret
    return Client(**kwargs)


def wait_for_callback(redirect_uri: str, *, timeout_sec: int = 300) -> str:
    parsed = urlparse(redirect_uri)
    host = parsed.hostname
    port = parsed.port
    path = parsed.path or "/"
    if parsed.scheme != "http" or not host or not port:
        raise AuthError("XCLI_REDIRECT_URI must be an http URL with host and port.")

    result: dict[str, str] = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            req = urlparse(self.path)
            if req.path != path:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not found")
                return

            query = parse_qs(req.query)
            if "error" in query:
                result["error"] = query["error"][0]
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Authorization failed. You can close this window.")
                return

            result["callback_url"] = f"{parsed.scheme}://{parsed.netloc}{self.path}"
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Authorization complete. You can close this window.")

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

    server = HTTPServer((host, port), CallbackHandler)
    server.timeout = timeout_sec
    started = time.monotonic()

    try:
        server.handle_request()
    finally:
        server.server_close()

    if "error" in result:
        raise AuthError(f"Authorization failed: {result['error']}")
    callback_url = result.get("callback_url")
    if not callback_url:
        elapsed = int(time.monotonic() - started)
        raise AuthError(f"Timed out waiting for OAuth callback after {elapsed}s.")
    return callback_url


def run_login(settings: Settings, *, open_browser: bool) -> dict[str, Any]:
    client = make_oauth_client(settings)
    auth_url = client.get_authorization_url()

    print("Open this URL to authorize xcli:")
    print(auth_url)
    if open_browser:
        webbrowser.open(auth_url)

    print(f"Waiting for callback at {settings.redirect_uri} ...")
    callback_url = wait_for_callback(settings.redirect_uri)

    try:
        token = client.fetch_token(authorization_response=callback_url)
    except Exception as exc:  # pragma: no cover
        raise AuthError(f"Token exchange failed: {exc}") from exc

    if not isinstance(token, dict) or "access_token" not in token:
        raise AuthError("Token exchange did not return an access token.")
    return token


def refresh_if_needed(settings: Settings, token: dict[str, Any]) -> dict[str, Any]:
    if "access_token" not in token:
        raise AuthError("Token file does not contain an access token. Run `xcli auth login`.")

    if not settings.client_id:
        return token

    if "refresh_token" not in token:
        return token

    OAuth2PKCEAuth = _load_oauth2_auth_cls()
    kwargs: dict[str, Any] = {
        "client_id": settings.client_id,
        "redirect_uri": settings.redirect_uri,
        "scope": " ".join(settings.scopes),
        "token": dict(token),
    }
    if settings.client_secret:
        kwargs["client_secret"] = settings.client_secret

    auth = OAuth2PKCEAuth(**kwargs)

    try:
        expired = bool(auth.is_token_expired())
    except Exception:
        expired = False

    if not expired:
        return token

    try:
        refreshed = auth.refresh_token()
    except Exception as exc:  # pragma: no cover
        raise AuthError(f"Token refresh failed: {exc}") from exc

    if not isinstance(refreshed, dict) or "access_token" not in refreshed:
        raise AuthError("Token refresh did not return an access token.")
    return refreshed
