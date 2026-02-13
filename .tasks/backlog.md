# xcli backlog

## Roadmap

### Endpoint inventory (XDK 0.8.x)

Confirmed in the installed XDK client:

- `client.users.get_me` -> authenticated user lookup.
- `client.users.get_posts` -> user-authored posts (paginated iterator).
- `client.posts.get_by_id` -> single post lookup.
- `client.users.get_by_username` -> resolve `@handle` -> user id.
- `client.users.get_timeline` -> reverse-chronological home timeline for a user id (paginated iterator).
- `client.posts.create` -> create post/reply/quote.

Scheduling note:

- No native "scheduled post at timestamp" endpoint is exposed for posts in this XDK version.
- `schedule/scheduled` terms currently appear in Spaces search state, not tweet create/update.
- Treat tweet scheduling as API-capability investigation (possible private/limited-scope endpoint), not local queue emulation.

### Phase 1: read + auth UX (active)

1. Pull own recent tweets: `xcli posts mine`.
2. Fetch a single tweet by id: `xcli posts get --id <tweet_id>`.
3. Timeline lookup for a handle: `xcli timeline --user <handle>`.
4. Better auth UX: `xcli auth logout` and `xcli auth status`.

Done when:

- Commands support both human output and `--json`.
- Errors map to friendly messages (bad id, auth missing/expired, API errors).
- Timeline and post-list commands respect a limit (`--limit`, sane defaults).

### Phase 2: publish enhancements (active)

1. Media upload + attach media to posts/replies.
2. Validate media constraints and produce clear error messages.
3. Keep `--dry-run` behavior useful when media is provided.

Done when:

- `xcli post ... --media <path> [--media <path>]` works for supported media.
- Upload + create flow is atomic enough for CLI usage and surfaces upload failures.
- Reply flow supports media attachment with same behavior.

### Phase 3: stretch features

1. Notifications/inbox command (investigate API support and tier access limits).
2. Tweet scheduling command if/when API support is confirmed.
3. Thread composer (`xcli thread create ...`).
4. Shell completion + richer TUI-style previews.

### OSS/release chores

1. Add CI workflow for `ruff`, `mypy`, and `pytest`.
2. Add changelog and release checklist.
3. Add issue templates for bugs and feature requests.

## Implementation notes

- Keep command names lowercase and concise.
- Reuse existing auth refresh and output helpers where possible.
- Prefer atomic tasks with clean commit boundaries:
  - `phase-1` command surface
  - `phase-2` media upload + publish integration
  - tests + docs updates
