---
title: relay-crm
status: in_progress
mode: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts:
- docs/gdrive-mcp
skills: []
workflow:
  name: autonomy/human-only
  steps:
  - name: brief-and-hand-off
    skills: []
    assignee: agent
  - name: human-executes
    skills: []
    assignee: human
  - name: verify-read-only
    skills: []
    assignee: agent
step: 2 (human-executes)
---

## Description

Add visibility into external adoption by creating a Google Sheet tracker
for: who said they would use relay, who actually used it, who's still
using it. Zach builds the sheet by hand from the spec in Context; the
agent briefs him on the structure and verifies the result read-only via
the Google Drive MCP. All updates after creation are manual too (decided
2026-06-11) — relay has no telemetry, so "still using" is conversational
evidence Zach maintains, not something an agent can observe.

## Context

Sheet structure (settled in the 2026-06-11 interview):

- Tab 1 "Tracker" — one row per person:
  `Name | Email | Source | Status | Committed | First used | Last confirmed use | Notes`.
  Status is a dropdown: `Committed / Tried / Active / Churned`. The date
  columns are the evidence behind Status: blank "First used" = said but
  never followed through; recent "Last confirmed use" = still using.
- Tab 2 "Touchpoints" — one row per interaction:
  `Date | Person | Channel | What we learned`. "Last confirmed use" on
  Tab 1 is a manual rollup of the latest relevant touchpoint.
- The sheet is named "Relay CRM"; Drive location is Zach's choice (no
  required folder).
- Zach has an existing list of people and fills the rows in by hand
  after the sheet exists; the agent does not seed data.
- Why human-built: per the attached `docs/gdrive-mcp` context, the
  Drive MCP cannot create a two-tab sheet with a dropdown, edit files
  in place, or read past the first tab. Expect verify-read-only to
  confirm Tab 1's columns only; Tab 2 and the dropdown rest on Zach's
  report (the workflow allows this: "if the result can't be observed,
  the human's report stands").
