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
