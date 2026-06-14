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

## Draft step (2026-06-14)

Human confirmed the content/tone before generation: warm-but-terse, one screen, "value in 30 seconds", nothing added beyond the ticket's three-step spec. Content follows the task-specific context exactly:

1. Install the CLI — `git clone https://github.com/FastJVM/relay && cd relay && pip install -e .` (note: clone alone isn't enough; `pip install -e .` puts `relay` on PATH).
2. Set up your repo — `relay setup` in a separate work folder; one run creates Relay OS, interviews, offers to plan first project into draft tickets; safe to re-run.
3. Start the work — `relay launch "<ticket>"`; auto-activates a draft.

Left out per ticket: no `relay project`, no `relay create`/`relay ticket`, no PyPI/`pip install relay-os`.

### HTML upload — DONE
- HTML draft uploaded as raw `text/html` (disableConversionToGoogleType=true), placed as sibling of the superseded doc in parent `0AI38XlSataDrUk9PVA`.
- HTML file id: `11C_rIJlWknKYoZ9zqS9UT7cLTALg4-Ih`
- HTML view link: https://drive.google.com/file/d/11C_rIJlWknKYoZ9zqS9UT7cLTALg4-Ih/view?usp=drivesdk
- Next: human does "Open with → Google Docs" to mint the converted Doc, then pastes the Doc link here. Once I have the Doc link, write it below and bump with `--message "draft Doc: <link>"`.

### Converted Doc link — DONE
- Converted Google Doc verified: mimeType `application/vnd.google-apps.document`, title "Relay Onboarding", parent `0AI38XlSataDrUk9PVA` (sibling of superseded doc).
- Doc id: `1eAdnxopeVC7jLGUfdo05R-h_a4jM-OwhracyUgYLtq0`
- Doc link: https://docs.google.com/document/d/1eAdnxopeVC7jLGUfdo05R-h_a4jM-OwhracyUgYLtq0/edit
- Bumping draft step with this Doc link.
