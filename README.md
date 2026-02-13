# xcli

`xcli` is a command line tool for interacting with the X API.

It is designed for local-first usage, safe publishing defaults, and open-source packaging.

## Install

Install from PyPI:

```bash
pip install x-cli
```

## Quickstart

1. Set OAuth app credentials:

```bash
export TWITTER_CLIENT_ID="..."
export TWITTER_CLIENT_SECRET="..."
```

2. Run login flow:

```bash
xcli auth login
```

3. Draft content:

```bash
xcli compose "shipping small daily"
```

4. Post from terminal text (default):

```bash
xcli post "shipping small daily"
```

5. Preview without posting:

```bash
xcli post "shipping small daily" --dry-run
```

6. Post from file:

```bash
xcli post --file draft.txt
```

## Commands

- `xcli auth login`
- `xcli auth whoami`
- `xcli compose`
- `xcli post`
- `xcli reply --to <tweet_id>`
- `xcli quote --to <tweet_id>`

## Safety model

- Posting commands send by default (with confirmation prompt).
- Use `--dry-run` to preview payload without posting.
- Non-interactive workflows can use `--yes`.
- Machine output is available with `--json`.

## Auth storage

Default token path uses platform config directories:

- macOS: `~/Library/Application Support/xcli/auth.json`
- Linux: `~/.config/xcli/auth.json`
- Windows: `%APPDATA%\\xcli\\auth.json`

Legacy compatibility fallback is supported for `~/.twitter/auth.json`.

## Development

```bash
pip install -e .[dev]
pytest
ruff check
mypy src
```
