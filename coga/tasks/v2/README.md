# `coga/tasks/v2/` — the parking area

Drafts for work that is real but not on the current execution path. `coga
status v2` is the authoritative list; this file is the contract for reading
what is in here. The pull-forward rule itself lives in `coga/roadmap`
("Deferred work").

## Read every draft in here as a dated artifact, not as instructions

A parked draft is a **record of what someone wanted at the time it was
written**. It is not a maintained spec, and nothing re-validates it while it
sits. Its problem statement usually survives; its proposed implementation
often does not, because the surfaces it names keep moving underneath it.

The failure mode this file exists to prevent: an agent or a person picks up a
v2 draft, follows its steps literally, and writes code or prose against a repo
that no longer exists — or, worse, "modernizes" the draft's dead commands into
live-looking ones and buries the fact that the premise died.

## Title-only drafts: a capture, not a ticket

A draft whose `## Description` is empty is a **title-only draft**: a thought
that was written down as far as its title and no further. It is a different
shape from a workflow-less draft — that is a decision deferred; this is a
thought never recorded — and it is the weaker of the two, because nothing in
the repo can reconstruct what the author meant. The premise check below cannot
run on it: there is no premise to check.

This directory is the **only** place a title-only draft may sit. `coga create
"v2/<title>"` is the supported spelling for capturing a bare thought; a ticket
anywhere else carries its description from the moment it exists (`coga create
--description`, or `coga ticket` for guided authoring). The rule itself lives
in `coga/roadmap` ("Deferred work"); this section is how to read a stub once
it is here.

`coga validate` reports every live title-only ticket as `empty-description`
(a warning, wherever the ticket sits). That report is the stub's **expiry**:
the first sweep that names it is when the author's verdict is due, and only
the author can give it —

- **describe**: fill `## Description` in the author's own words, and put
  what the codebase says about it under `## Context`; or
- **cancel**: `coga mark canceled v2/<slug> --message "<reason>"` when the
  author confirms the intent is lost or already shipped.

Nothing in either verdict may be inferred from the slug alone, and a green
`coga validate` is never a reason to cancel a draft — it is a consequence of
correct verdicts, never an input to them. Precedent for the batch form of this
verdict is `interview-the-owner-on-the-17-title-only-v2-stubs`.

## Before pulling anything forward, check the premise

Two questions, in this order:

1. **Does the subject still exist?** If the thing the draft asks you to build,
   document, or remove is already gone, the draft is *premise-dead* — cancel
   it with a reason (`coga mark canceled v2/<slug> --message "…"`) rather than
   writing prose about a removed design. A draft that sits long enough can
   outlive its own subject; two already did (see "Precedent" below).
2. **Do the surfaces it names still resolve?** Grep the draft for the dead
   surfaces below and check each against current `main` before trusting any
   step in it.

Only then decide: pull forward, rewrite against the current shape, or cancel.

## Known-stale surfaces (the pre-rename cohort)

Most of this directory predates the `relay` → `coga` rename, and 46 of its
drafts still say `relay`. **The rename is not a find-and-replace.** Some names
carried over, some changed meaning, and some were deleted outright — so
mechanically rewriting `relay` to `coga` produces confident, wrong
instructions. Check each occurrence against this table:

| As written in a draft | Status today |
| --- | --- |
| `src/relay/` | Renamed — now `src/coga/`. |
| `relay-os/…`, `relay-os/contexts/…` | Renamed — now `coga/`, `coga/contexts/…`. |
| `relay launch`, `relay recurring`, `relay status`, `relay bump` | Renamed — the `coga` equivalents exist. |
| `relay draft` | **Gone.** Ticket creation is `coga create` (raw draft) or `coga ticket` (authoring skill). |
| `relay panic` | **Replaced.** Use `coga block --task <slug> --reason "…"` for unresolved input; it records the ask, marks the task blocked, notifies the owner, and ends the session. |
| `mode:` ticket frontmatter (`script` / `auto` / `interactive`) | **Gone.** There is no `mode` or `recipe:` field. A directory-form ticket's exact sibling `ticket.py` is its headless deterministic half; without that file, launch selects the agent path. See `coga/architecture`. |
| Child `mode: script` tasks driven by a parent task | **Gone.** Put a ticket-owned deterministic phase in that selected ticket's exact sibling `ticket.py`, or invoke a stable package command explicitly through `coga run`; do not rebuild child-task mode orchestration. |
| `[secrets]` bulk-inject config block | **Gone.** Secrets are per-ticket `secrets:` frontmatter holding `op://vault/item/field` refs; see `coga/secrets`. |

This table is a starting point, not a guarantee of completeness — it was built
from the surfaces actually present in these drafts as of 2026-08-13. Treat any
other `relay`-era name the same way: verify it against `main` before acting on
it.

## Precedent

`decide-the-fate-of-two-premise-dead-v2-drafts-whos` cancelled two drafts whose
subjects had been deleted out from under them —
`document-parent-orchestrates-child-script-tasks-pa` (asked to canonize the
child-`mode: script` shape) and
`document-interactive-recurring-sweep-hazard-in-rel` (entirely about the `mode`
field). Both were themselves Dream `gap` findings originally. Cancelling a
parked draft with a recorded reason is a normal, healthy outcome; leaving a
premise-dead draft in place so someone later implements it is not.
