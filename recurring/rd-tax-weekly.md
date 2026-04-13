---
schedule: "7 9 * * 1"
schedule_comment: "Every Monday at 9:07am (matches the current launchd job)"
project: rd-tax
title: "Weekly R&D tax scrape and classify"
mode: auto
workflow: admin/script
assignee: claude1
owner: zach
contexts:
  - admin/tax-automation
---

## Description

Run the weekly R&D tax credit scrape. Fetches the last week of daily
updates from the FastJVM Slack workspace, sends them to Claude for
classification against IRC §41 rules, and appends qualifying bullets
to the correct project sections in `rd_tax_<year>.md`.

Today this lives at `~/RD_Tax_Automation/run_weekly.sh` and runs under
its own launchd job. Migration path for this recurring template:

1. Create a script-mode skill `skills/admin/rd-tax-scrape/` with a
   bundled `run.sh` that `exec`s the existing `run_weekly.sh`.
2. Clone `workflows/admin/script.md` to `workflows/admin/rd-tax.md`
   pointing at the new skill.
3. Update this recurring template to use the new workflow.
4. Disable the existing launchd job; let `relay create --check-recurring`
   create the task, and run `relay launch` on it.

## Context

Qualifying projects and exclusions are documented in the
`admin/tax-automation` context attached above. If the set of qualifying
projects changes mid-year, update that context file first, then the
classification prompt in the scraper will need a matching update on
the next migration pass.
