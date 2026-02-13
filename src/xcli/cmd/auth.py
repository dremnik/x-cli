"""Auth commands."""

from __future__ import annotations

import typer

from xcli.core.config import load_settings
from xcli.core.errors import ApiError, AuthError
from xcli.core.output import emit
from xcli.core.token_store import TokenStore
from xcli.core.x_auth import refresh_if_needed, run_login
from xcli.core.x_client import get_me, make_user_client

app = typer.Typer(no_args_is_help=True, help="Authenticate xcli with the X API.")


@app.command("login")
def login(
    no_browser: bool = typer.Option(False, help="Do not auto-open a browser."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    settings = load_settings()
    token = run_login(settings, open_browser=not no_browser)

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
    settings = load_settings()
    store = TokenStore()
    token = store.load()
    if not token:
        raise AuthError("No token found. Run `xcli auth login` first.")
    if not token.get("access_token"):
        raise AuthError("Token file is missing access_token. Run `xcli auth login`.")

    refreshed = refresh_if_needed(settings, token)
    if refreshed != token:
        store.save(refreshed)

    client = make_user_client(refreshed["access_token"])
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
