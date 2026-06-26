---
name: docs/gdrive-mcp
description: Capability contract of the Google Drive MCP server — what file creation can and cannot convert, the no-update/no-delete limits, and read-side gotchas for Docs and Sheets tasks.
---

# Google Drive MCP capability contract

Facts learned across tasks (conductor-report 2026-06, coga-crm
2026-06-11). Do not rediscover these by trial uploads.

## Creation and conversion

- `create_file` auto-converts **only** `text/plain` → Google Doc and
  `text/csv` → Google Sheet. The CSV path yields a **single-tab** sheet.
- `text/html` is **not** converted — it lands as a raw HTML file. The
  HTML→Doc conversion is the human's click ("Open with → Google Docs"
  in Drive), which creates a **new** Doc next to the HTML file rather
  than converting in place. One click only — each click mints another
  duplicate Doc.
- Do **not** force `contentMimeType: application/vnd.google-apps.document`
  on HTML or docx content: you get a native Doc containing the literal
  markup (or binary garbage) as text.
- Uploads cannot create multi-tab spreadsheets, dropdowns, or any data
  validation. Anything beyond flat single-tab values is hand-finished
  by the human.

## Updates, deletes, reads

- The server has **no update or delete tools**. Revising a Doc/Sheet
  means uploading a new file; superseded files are trashed by the human.
- Read side: spreadsheet content reads/exports return only the first
  tab, and data validation (dropdowns) never shows in an export.
  Verification of multi-tab structure rests on the human's report.
- A cheap read-only call (e.g. list recent files) is the right
  connection preflight before any content work.

## What this context does NOT cover

Workflow process for authoring documents — that's
`coga-os/workflows/docs/create-google-doc.md`. Google Sheets API or
Apps Script (not available via this MCP server).
