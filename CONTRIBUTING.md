# Contributing

Thanks for helping improve `xcli`.

## Local setup

```bash
pip install -e .[dev]
```

## Before opening a PR

```bash
ruff check
mypy src
pytest
```

## Commit style

- Keep changes focused and atomic.
- Add or update tests for behavior changes.
- Update docs for any user-facing command changes.

## Release process

- Bump version in `pyproject.toml`.
- Update `CHANGELOG.md`.
- Tag the release in git.
