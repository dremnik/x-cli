# Testing checklist (2026-02-13)

## Automated checks

- [x] `ruff check .`
- [x] `python -m mypy src` (run via `.venv/bin/python -m mypy src`)
- [x] `python -m pytest` (18 tests passing)

## CLI surface checks

- [x] `python -m xcli.cli --help`
- [x] `python -m xcli.cli post --help`
- [x] `python -m xcli.cli posts --help`
- [x] `python -m xcli.cli auth --help`

## Live API checks

- [x] `xcli auth status --json`
- [x] `xcli auth whoami --json`
- [x] `xcli posts mine --limit 3 --json`
- [x] `xcli posts get --id <id_from_mine> --json`
- [x] `xcli timeline --user dremnik --limit 3 --json`

## Optional follow-up checks

- [ ] `xcli post "test" --media <image.png> --yes --json`
- [ ] `xcli reply "test" --to <tweet_id> --media <image.png> --yes --json`
- [ ] `xcli auth logout --json` then `xcli auth status --json`

### Notes

- Previous token scopes were missing `media.write` (`tweet.write users.read tweet.read offline.access`).
- Added default scope `media.write` in config and CLI now returns a clear error if scope is missing.
- After re-login, token includes `media.write`.
- Media upload flow updated to use multipart form upload directly against `/2/media/upload`.
- To complete media live checks: rerun the two media commands above with a normal local image file.
