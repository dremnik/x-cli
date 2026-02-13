"""Token persistence helpers."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from xcli.core.config import legacy_token_file_path, token_file_path


class TokenStore:
    def __init__(self, primary: Path | None = None, legacy: Path | None = None) -> None:
        self.primary = primary or token_file_path()
        self.legacy = legacy or legacy_token_file_path()

    def load(self) -> dict[str, Any] | None:
        for path in (self.primary, self.legacy):
            if not path.exists():
                continue
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                return data
        return None

    def save(self, token: Mapping[str, Any], *, sync_legacy_if_exists: bool = True) -> None:
        payload = dict(token)
        self._write_json(self.primary, payload)
        if sync_legacy_if_exists and self.legacy.exists():
            self._write_json(self.legacy, payload)

    def clear(self) -> list[Path]:
        removed: list[Path] = []
        for path in (self.primary, self.legacy):
            if path.exists():
                path.unlink()
                removed.append(path)
        return removed

    @staticmethod
    def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n")
