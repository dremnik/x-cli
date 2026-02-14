# Testing checklist (2026-02-14)

## Automated checks

- [x] `uv run python -m pytest` (29 tests passing)
- [x] `uv run python -m ruff check`
- [x] `uv run python -m mypy src`

## CLI surface checks

- [x] `uv run python -m xcli.cli post --help`
- [x] `uv run python -m xcli.cli post --video clip.mp4 --srt clip.srt --dry-run --json`

## Live API checks

- [x] `xcli post --video clip.mp4 --srt clip.srt --yes --json`

### Notes

- `xcli post` now supports media-only payloads when using `--video` and `--srt`.
- `--video` and `--srt` must be provided together.
- `--video`/`--srt` cannot be combined with image `--media` attachments.
- Initial subtitle one-shot upload returned HTTP 400; switched subtitle upload to initialize/append/finalize.
- End-to-end validation succeeded with clip from `n1E9IZfvGMA` (`15:00-15:35`) and sidecar SRT.
