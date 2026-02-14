"""Auth commands."""

from __future__ import annotations

from datetime import datetime, timezone

import typer

from xcli.core.config import load_settings
from xcli.core.errors import ApiError, AuthError
from xcli.core.output import emit
from xcli.core.session import make_authed_client
from xcli.core.token_store import TokenStore
from xcli.core.x_auth import run_login
from xcli.core.x_client import get_me, make_user_client

app = typer.Typer(no_args_is_help=True, help="Authenticate xcli with the X API.")


@app.command("login")
def login(
    open_browser: bool = typer.Option(
        False,
        "--open-browser",
        help="Try to auto-open browser for authorization.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    settings = load_settings()
    token = run_login(settings, open_browser=open_browser)

    store = TokenStore()
    store.save(token)

    out: dict[str, object] = {
        "message": "Login successful.",
        "token_path": str(store.primary),
    }

    access_token = token.get("access_token")
    if isinstance(access_token, str) and access_token:
        try:
            client = make_user_client(access_token)
            me = get_me(client)
            out["username"] = me.get("username")
            out["name"] = me.get("name")
            out["id"] = me.get("id")
        except ApiError as exc:
            out["message"] = (
                "Login successful, but profile lookup failed. "
                "Run `xcli auth whoami` to retry."
            )
            out["warning"] = str(exc)

    emit(out, json_output=json_output)


@app.command("whoami")
def whoami(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    client = make_authed_client()
    me = get_me(client)

    emit(
        {
            "message": "Authenticated user:",
            "username": me.get("username"),
            "name": me.get("name"),
            "id": me.get("id"),
        },
        json_output=json_output,
    )


@app.command("status")
def status(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    store = TokenStore()
    token = store.load()
    if not token:
        emit(
            {
                "message": "Not authenticated.",
                "logged_in": False,
                "token_path": str(store.primary),
            },
            json_output=json_output,
        )
        return

    out: dict[str, object] = {
        "message": "Authentication status:",
        "logged_in": bool(token.get("access_token")),
        "token_path": str(store.primary),
    }

    expires_at = token.get("expires_at")
    if isinstance(expires_at, (int, float)):
        out["expires_at"] = datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()

    try:
        client = make_authed_client()
        me = get_me(client)
        out["username"] = me.get("username")
        out["name"] = me.get("name")
        out["id"] = me.get("id")
    except (AuthError, ApiError) as exc:
        out["warning"] = str(exc)

    emit(out, json_output=json_output)


@app.command("logout")
def logout(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    store = TokenStore()
    removed = store.clear()

    out: dict[str, object] = {
        "message": "Logged out." if removed else "No token files found. Already logged out.",
        "count": len(removed),
        "token_path": str(store.primary),
        "removed": [str(path) for path in removed],
    }
    emit(out, json_output=json_output)
