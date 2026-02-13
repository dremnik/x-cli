from pathlib import Path

from xcli.core.token_store import TokenStore


def test_token_store_saves_and_loads_primary(tmp_path: Path) -> None:
    store = TokenStore(
        primary=tmp_path / "cfg" / "auth.json",
        legacy=tmp_path / "legacy" / "auth.json",
    )
    token = {"access_token": "abc", "refresh_token": "def"}
    store.save(token)
    assert store.load() == token


def test_token_store_syncs_legacy_if_present(tmp_path: Path) -> None:
    primary = tmp_path / "cfg" / "auth.json"
    legacy = tmp_path / "legacy" / "auth.json"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text("{}")

    store = TokenStore(primary=primary, legacy=legacy)
    token = {"access_token": "new"}
    store.save(token)

    assert primary.exists()
    assert legacy.exists()
    assert "new" in primary.read_text()
    assert "new" in legacy.read_text()


def test_token_store_clear_removes_primary_and_legacy(tmp_path: Path) -> None:
    primary = tmp_path / "cfg" / "auth.json"
    legacy = tmp_path / "legacy" / "auth.json"
    primary.parent.mkdir(parents=True, exist_ok=True)
    legacy.parent.mkdir(parents=True, exist_ok=True)
    primary.write_text('{"access_token":"a"}')
    legacy.write_text('{"access_token":"b"}')

    store = TokenStore(primary=primary, legacy=legacy)
    removed = store.clear()

    assert set(removed) == {primary, legacy}
    assert not primary.exists()
    assert not legacy.exists()
