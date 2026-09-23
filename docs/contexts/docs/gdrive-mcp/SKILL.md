---
name: docs/gdrive-mcp
description: Dated (2026-06) capability observations for the Google Drive MCP server used by Docs and Sheets tasks — what creation converts, why revisions are re-uploads, and read-side gotchas; re-verify before relying on them.
---

# Google Drive MCP capability contract (observed 2026-06)

**Scope and date.** These are observations of the particular Google Drive MCP
server connected in June 2026 (conductor-report, 2026-06; coga-crm,
2026-06-11). They describe that server's tools at that time, not Google Docs
or Drive in general. The tool set may have changed since: before relying on a
limit below, check the tools the current session actually exposes, and update
this page when a fact no longer holds. Do not rediscover still-valid facts by
trial uploads.

## Creation and conversion

- `create_file` auto-converted **only** `text/plain` → Google Doc and
  `text/csv` → Google Sheet. The CSV path yields a **single-tab** sheet.
- `text/html` was **not** converted; it landed as a raw HTML file. The
  HTML → Doc conversion is the human's click ("Open with → Google Docs"),
  which creates a **new** Doc beside the HTML file. Each click mints another
  duplicate, so click once.
- Do **not** force `contentMimeType: application/vnd.google-apps.document`
  on HTML or docx content: the result is a native Doc containing the literal
  markup (or binary garbage) as text.
- Uploads could not create multi-tab spreadsheets, dropdowns, or any data
  validation. Anything beyond flat single-tab values is finished by hand.

## Updates, deletes, reads

- `update_file` edited **metadata only** — title and parent folder (a move).
  With no content-update tool, revising a Doc/Sheet means uploading a **new**
  file.
- `trash_file` exists. Once the replacement is confirmed, trash the superseded
  file yourself and name it in the report. It is recoverable from trash; there
  was no permanent-delete tool.
- Spreadsheet reads/exports returned only the first tab, and data validation
  never appears in an export. Verification of multi-tab structure rests on
  the human's report.
- A cheap read-only call (for example, listing recent files) is the connection
  preflight before any content work.

## Not covered

Authoring process lives in the package workflow
`src/coga/resources/templates/coga/bootstrap/workflows/docs/create-google-doc.md`
(`docs/create-google-doc`). The Google Sheets API and Apps Script were not
available through this server.
