The blackboard is a notepad to be written to often as the human and agent works through a task.

## Preflight (2026-06-13) — PASSED

Google Drive MCP connection verified live:

- Read-only probe `list_recent_files` returned real Drive files (e.g. "Relay
  Marketing Plan", "Relay CRM") — connection is authenticated and working.
- `create_file` capability confirmed present:
  `mcp__claude_ai_Google_Drive__create_file`.
- Contract matches the conductor-report learnings: `text/html` is NOT
  auto-converted (lands as a raw HTML file — the correct `draft` artifact);
  only `text/plain`→Doc and `text/csv`→Sheet auto-convert. No update/delete
  tools; HTML→Doc is the human's "Open with → Google Docs" click.

Bumping forward to the content steps.
