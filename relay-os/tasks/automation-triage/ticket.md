---
title: Automation-triage-skill — sort a task into one of three workflows
status: draft
mode: interactive
owner: zach
human: zach
agent: claude1
assignee: claude1
contexts: []
skills: []
workflow: null
---

## Description

Browser automations should always start with a decision of *how much* to automate the task. Today that judgment lives in our heads and gets re-litigated every time. This ticket proposes a skill that interviews the human
about a candidate task and emits a follow-up browser automation ticket with the
right workflow already attached.

Triage turns on two factors — failure radius (*If this task went out wrong and no one caught it, what's the worst that happens--can we fix it?*) and machine feasibility (*Can a machine do this reliably, or is a human needed to perform it?*) — which sort the
task into one of three workflows: **human-only**, **human-verify**, or
**fully-automated**.

This ticket is the explanation only. It defines the triage questions, the
rules each classification must abide by, and the list of skills and
contexts the follow-up build work would create. Nothing is built here —
it's a proposal to review before any of it lands.

## Triage questions

The skill walks the human through these in order:

1. **Worst-case.** If a wrong result slipped through, what's the worst that can happen? (Low-cost failures → leans automated; High-cost failures → leans human.)
2. **Reversibility.** If a wrong result is shipped, can it be undone? (Question 1 and question 2 together make up the failure radius)
3. **Machine feasibility.** Can a machine do this reliably, or does a human have to perform it?

## Classifications

Each follow-up ticket is assigned exactly one workflow. The rules each browser automation ticket must abide
by:

- **human-only** — A machine can't do this reliably; a human performs it end to end. (Clicking "OK" on Xero)
- **human-verify** — A machine can do it, but the failure radius is high, so the agent runs end to end, stops before the irreversible step, and the human reviews and fires it. (KP Recert)
- **fully-automated** — A machine can do it and the failure radius is low, so it runs unattended. (RxDC Report)

## Build rules

Two rules should be part of the automation workflows (human-verify and fully-automated). They aren't standalone. 

- **Dry-run before live.** Every automation build is dry-run and confirmed
  before it's allowed to run live.
- **Easy downgrade.** The `human-verify` and `fully-automated` workflows fail
    loud at the dry-run/build step if the task can't be automated reliably (per
    `dom-backed`'s blocker process); the documented resolution is a cheap
    re-assign to `human-only`.

## Skills & contexts to create (list only — not built here)

Skills:

- `automation-triage` — the interview + follow-up-ticket scaffolder
  described above.
- `dochub-form-fill` — DocHub form completion. Fill-out is fully
  automatable via Playwright **except** signature-box placement. First
  dry-run: the human positions the signature box and tells Claude to save
  the coordinates; dry-run again to confirm; live runs replay the saved
  coords. (This is a deliberate coordinate-based exception to the
  DOM-backed rule, and the skill must document it as such.)

Contexts (always-on for automation tickets):

- `api-first` — require a "why not the API?" answer before any browser
  automation.
- `dom-backed` — browser control is DOM-backed (Playwright snapshots /
  accessibility refs), not coordinate clicks.

Workflows (one per classification):

- `human-only`
- `human-verify`
- `fully-automated`

## Open questions

- Is there a fourth classification we should define? (One was floated but
  not pinned down.)
