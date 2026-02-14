# TODO

## 2026-02-13

- [x] Audit current CLI surface and relevant XDK endpoints.
- [x] Expand `.tasks/backlog.md` into a detailed roadmap (phases, endpoint mapping, sequencing).
- [x] Implement `xcli posts mine` and `xcli posts get --id <tweet_id>`.
- [x] Implement `xcli timeline --user <handle>`.
- [x] Implement auth UX improvements: `xcli auth status` and `xcli auth logout`.
- [x] Implement media upload + attachment support in post/reply flows.
- [x] Investigate tweet scheduling endpoint availability in public XDK/OpenAPI.
- [x] Add tests for new functionality and run validation (`pytest`, `ruff`, `mypy`).
- [x] Fix OAuth callback handling for WSL/manual browser flows (avoid immediate 0s timeout).
- [x] Add `--exclude-replies` filter support for `posts mine` and `timeline` lookups.

### Notes

- Existing commands are currently `compose`, `post`, `reply`, `quote`, and `auth` (`login`, `whoami`).
- XDK supports required read endpoints: `users.get_posts`, `posts.get_by_id`, `users.get_timeline`, and `users.get_by_username`.
- XDK OpenAPI includes Spaces `scheduled` state but no tweet scheduling field/path in post create APIs.
- Media upload endpoint requires OAuth scope `media.write`; existing tokens without it must re-login.
- `xcli auth login` now defaults to manual URL open; use `--open-browser` to attempt auto-open.

## 2026-02-14

- [completed] Agree requirement: keep download/upload separation and add video+subtitle posting to `xcli` only.
- [completed] Finalize CLI shape: `xcli post --video <file> --srt <file>` (no separate command).
- [completed] Implement media upload flow for video + subtitle sidecar association in `xcli` core client.
- [completed] Wire `xcli post` command to support `--video` and `--srt`, including validation and preview output.
- [completed] Add/update tests and run verification checklist (`pytest`, `ruff`, `mypy`).
- [completed] User validation of live video+subtitle posting flow.
- [pending] Commit on approval.

### Notes

- Testing checklist: `.tasks/notes/2026-02-14-testing-checklist.md`.

### Testing checklist

- See `.tasks/notes/2026-02-13-testing-checklist.md` for the detailed checklist and live command validations.
