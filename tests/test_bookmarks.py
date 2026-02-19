"""Tests for bookmark commands."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from xcli.cli import app
from xcli.core.errors import ApiError

runner = CliRunner()


@patch("xcli.cmd.bookmarks.make_authed_client")
@patch("xcli.cmd.bookmarks.get_me")
@patch("xcli.cmd.bookmarks.fetch_bookmarks")
def test_bookmark_fetch_prints_results(
    mock_fetch: MagicMock,
    mock_get_me: MagicMock,
    mock_client: MagicMock,
) -> None:
    mock_get_me.return_value = {"id": "123", "username": "me", "name": "Me"}
    mock_fetch.return_value = [
        {"id": "100", "text": "saved tweet", "author_username": "coolUser", "created_at": "2023-01-01"},
    ]

    result = runner.invoke(app, ["bookmark", "fetch"])
    assert result.exit_code == 0
    assert "Fetched bookmarks" in result.stdout
    assert "saved tweet" in result.stdout
    assert "@coolUser" in result.stdout


@patch("xcli.cmd.bookmarks.make_authed_client")
@patch("xcli.cmd.bookmarks.get_me")
@patch("xcli.cmd.bookmarks.fetch_bookmarks")
def test_bookmark_fetch_with_max_results_alias(
    mock_fetch: MagicMock,
    mock_get_me: MagicMock,
    mock_client: MagicMock,
) -> None:
    mock_get_me.return_value = {"id": "123"}
    mock_fetch.return_value = []

    result = runner.invoke(app, ["bookmark", "fetch", "--max-results", "5"])
    assert result.exit_code == 0
    mock_fetch.assert_called_with(mock_client(), "123", limit=5)


@patch("xcli.cmd.bookmarks.make_authed_client")
@patch("xcli.cmd.bookmarks.get_me")
@patch("xcli.cmd.bookmarks.create_bookmark")
def test_bookmark_create_success(
    mock_create: MagicMock,
    mock_get_me: MagicMock,
    mock_client: MagicMock,
) -> None:
    mock_get_me.return_value = {"id": "123"}
    mock_create.return_value = {"bookmarked": True}

    result = runner.invoke(app, ["bookmark", "create", "https://x.com/user/status/999", "--json"])
    assert result.exit_code == 0
    assert "Bookmark created." in result.stdout
    assert '"id": "999"' in result.stdout
    
    mock_create.assert_called_with(mock_client(), "123", "999")


@patch("xcli.cmd.bookmarks.make_authed_client")
@patch("xcli.cmd.bookmarks.get_me")
@patch("xcli.cmd.bookmarks.delete_bookmark")
def test_bookmark_delete_success(
    mock_delete: MagicMock,
    mock_get_me: MagicMock,
    mock_client: MagicMock,
) -> None:
    mock_get_me.return_value = {"id": "123"}
    mock_delete.return_value = {"bookmarked": False}

    result = runner.invoke(app, ["bookmark", "delete", "999", "--json"])
    assert result.exit_code == 0
    assert "Bookmark deleted." in result.stdout
    assert '"id": "999"' in result.stdout
    
    mock_delete.assert_called_with(mock_client(), "123", "999")
