The blackboard is a notepad to be written to often as the human and agent works through a task.

## Preflight (2026-06-14) — PASS

Google MCP connection verified live and `create_file` capability confirmed.

- Read-only check: `Google_Drive.list_recent_files` returned real data — connection is live.
- `Google_Drive.create_file` tool is exposed and callable — this is the upload path for the HTML draft.
- Reminder of the known MCP Drive contract (from conductor-report; do not rediscover): `create_file` auto-converts only `text/plain`→Doc and `text/csv`→Sheet. `text/html` lands as a raw HTML file (the expected `draft` artifact). HTML→Doc is the human's "Open with → Google Docs" click, which mints a NEW Doc of the same title (verify by listing for a new `application/vnd.google-apps.document`, don't re-click). No update/delete tools server-side.

### Useful context for content steps
- Superseded doc: "Getting Started with Relay — Your First Five Commands", id `1bZyF0D2_FJsf-NCCWm6rlewSkyOmVl6Q9QOLwtamnf0` (too many steps, documents removed commands `relay project` and double `relay setup`). New doc title: "Relay Onboarding".
- Drive root parentId observed on recent files: `0AI38XlSataDrUk9PVA`.

Bumping past preflight into content work.
