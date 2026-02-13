"""CLI entrypoint for xcli."""

from __future__ import annotations

import typer

from xcli.cmd.auth import app as auth_app
from xcli.cmd.compose import compose_cmd
from xcli.cmd.posts import app as posts_app
from xcli.cmd.publish import post_cmd, quote_cmd, reply_cmd
from xcli.cmd.timeline import timeline_cmd
from xcli.core.errors import XcliError

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Command line tool for interacting with the X API.",
)

app.add_typer(auth_app, name="auth")
app.add_typer(posts_app, name="posts")
app.command("compose")(compose_cmd)
app.command("post")(post_cmd)
app.command("reply")(reply_cmd)
app.command("quote")(quote_cmd)
app.command("timeline")(timeline_cmd)


def main() -> None:
    try:
        app()
    except XcliError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise SystemExit(1) from exc


if __name__ == "__main__":  # pragma: no cover
    main()
