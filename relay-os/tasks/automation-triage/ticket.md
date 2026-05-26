---
title: Automation-triage meta-skill — sort a task into one of three workflows
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

Before we automate a task, someone has to decide *how much* to automate
it. Today that judgment lives in our heads and gets re-litigated every
time. This ticket proposes a single meta-skill that interviews the human
about a candidate task and emits a follow-up automation ticket with the
right workflow already attached.

Triage turns on two questions — *how costly is a wrong result?* and *can
a human reliably tell a right result from a wrong one?* — which sort the
task into one of three workflows: **human-only**, **human-verify**, or
**fully-automated**. The driver is the cost of being wrong, not whether
an irreversible action exists.

This ticket is the explanation only. It defines the triage questions, the
rules each classification must abide by, and the list of skills and
contexts the follow-up build work would create. Nothing is built here —
it's a proposal to review before any of it lands.

## Triage questions

The meta-skill walks the human through these in order:

1. **Cost of being wrong.** If a wrong result slipped through, how costly
   and reversible is it? (Cheap to correct → leans automated. High-cost
   or hard to reverse → leans human.)
2. **Recognizability.** Can a human reliably look at the output and tell a
   correct result from a wrong one?
3. **Irreversible action.** Is there a final submit/send? This decides
   *who fires it*, not which classification the task lands in.

## Classifications

Each follow-up ticket is assigned exactly one. The rules each must abide
by:

- **human-only** — High cost of being wrong **and** the human cannot
  reliably recognize a correct result. No trustworthy success signal
  exists, so the human does the task end to end. (e.g. KP Recert sign-off
  is not something we'd let run unattended — coverage could be dropped.)
- **human-verify** — High cost of being wrong **but** the human *can*
  clearly tell right from wrong. The agent does the task end to end and
  stops before the irreversible step; the human reviews the output and
  fires the submit/send themselves.
- **fully-automated** — Low cost of being wrong; errors are cheaply
  correctable. The agent does the task and the final action with no human
  gate. (e.g. RxDC report — a wrong amount just gets a correction notice.)

## Repeatable process (applies to every follow-up)

- Run the triage questions above before assigning a classification.
- **Dry-run before live.** Every automation build is dry-run and confirmed
  before it's allowed to run live.
- **Easy downgrade.** If a task aligned to an automated workflow proves too
  hard to automate, switching it to **human-only** must be cheap — the
  meta-skill owns that escape hatch.
- **Always-on contexts.** Every automation ticket carries two standing
  contexts: search for an API first (APIs are less brittle than browser
  automation), and all browser automation is DOM-backed.

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
- Where do these live long-term — seeded by the CLI into every workspace,
  or per-workspace? This ticket assumes CLI-seeded primitives.
