# xcli

`xcli` is a command line tool for interacting with the X API.

It is designed for local-first usage, safe publishing defaults, and open-source packaging.

## Install

Install from PyPI:

```bash
pip install xcli-v2
```

## Quickstart

1. Set OAuth app credentials:

```bash
export TWITTER_CLIENT_ID="..."
export TWITTER_CLIENT_SECRET="..."
```

Set your app callback/redirect URL to `http://localhost:3000/callback`.
If needed, override in the CLI with `XCLI_REDIRECT_URI`.

2. Run login flow (prints an auth URL you can open manually):

```bash
xcli auth login
```

Optional: attempt auto-open in your default browser:

```bash
xcli auth login --open-browser
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

7. Attach media (repeat `--media` up to 4 files):

```bash
xcli post "launch day" --media image1.png --media image2.jpg
```

8. Post a video with subtitle sidecar:

```bash
xcli post --video clip.mp4 --srt clip.srt
```

Optional post text:

```bash
xcli post "launch clip" --video clip.mp4 --srt clip.srt
```

Currently supported media types are image uploads accepted by the X media upload endpoint (jpeg, png, webp, bmp, tiff).
Media upload requires OAuth scope `media.write`; if you logged in before this was added,
run `xcli auth login` again to refresh token scopes.

For `--video`, supported formats are `.mp4`, `.m4v`, `.mov`, `.webm`, and `.ts`.
For `--srt`, supported subtitle formats are `.srt` and `.vtt`.
`--video` and `--srt` must be used together and cannot be combined with `--media`.

## Commands

- `xcli auth login`
- `xcli auth whoami`
- `xcli auth status`
- `xcli auth logout`
- `xcli compose`
- `xcli post`
- `xcli post --video <file> --srt <file>`
- `xcli reply --to <tweet_id>`
- `xcli quote --to <tweet_id>`
- `xcli posts mine`
- `xcli posts mine --replies false`
- `xcli posts get --id <tweet_id>`
- `xcli timeline --user <handle>`
- `xcli timeline --user <handle> --replies false`

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
