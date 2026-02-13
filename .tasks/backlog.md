# xcli backlog

## Next features

- Pull own recent tweets: `xcli posts mine`.
- Fetch a single tweet by id: `xcli posts get --id <tweet_id>`.
- Timeline lookup for a handle: `xcli timeline --user <handle>`.
- Better auth UX: `xcli auth logout` and `xcli auth status`.
- Draft workflow: save/list/send local drafts.

## Stretch features

- Notifications/inbox command (investigate API support and tier access limits).
- Media upload + attach media to posts.
- Thread composer (`xcli thread create ...`).
- Scheduled posting helper (local cron-friendly command).
- Shell completion + richer TUI-style previews.

## OSS/release chores

- Add CI workflow for `ruff`, `mypy`, and `pytest`.
- Add changelog and release checklist.
- Add issue templates for bugs and feature requests.
