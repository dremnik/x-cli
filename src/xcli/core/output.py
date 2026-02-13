"""Output helpers for human and JSON modes."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


def emit(data: Mapping[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(data, indent=2, sort_keys=True))
        return

    message = data.get("message")
    if isinstance(message, str) and message:
        print(message)

    for key in ("id", "url", "username", "name", "mode", "chars", "token_path", "warning"):
        value = data.get(key)
        if value is None:
            continue
        print(f"{key}: {value}")
