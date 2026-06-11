---
title: relay-crm
status: draft
mode: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
skills: []
workflow: null
---

## Description

Add visibility into external adoption by creating a tracker for: who said
they would use it, who actually used it, who's still using it. Target is
a Google Sheet (changed from a Doc, 2026-06-11 — tabular adoption data
fits a sheet better).

## Context

- The existing `docs/create-google-doc` workflow is Doc-oriented; it may
  inform the shape but wasn't built for Sheets. One known path to create
  a Sheet via the Google Drive MCP: upload CSV content, which Drive can
  auto-convert to a Sheet (only text/plain and text/csv auto-convert;
  HTML→Doc conversion notably does not work).
- Doc edits were decided to be manual (2026-06-06, no edit-google-doc
  workflow exists). The interview should settle how recurring updates to
  the tracker happen: manual edits by Zach, or regenerate/re-upload.
