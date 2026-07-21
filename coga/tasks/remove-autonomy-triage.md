---
slug: remove-autonomy-triage
title: remove autonomy triage
status: draft
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

Remove the autonomy-triage apparatus: the three-question tier test in the
`bootstrap/ticket` interview, the `autonomy/triage` context, and the unused
`autonomy/*` tier workflows. A usage audit (2026-07-20, see `## Context`)
showed the test never changed a real decision — workflow choice already
carries the "does a human gate this?" judgment. Keep the one piece with real
mileage: the `autonomy/assist-only` workflow (agent drafts → human owns and
finishes → report), renamed to `draft-for-human` and scrubbed of tier
vocabulary. Replace the interview step with one sentence in the
workflow-selection question: if the task has an irreversible or
outward-facing step, pick a workflow with a human gate before it.

## Context

Every shipped Coga OS file has a live copy under `coga/` and a packaged copy
under `src/coga/resources/templates/coga/` (some under its `bootstrap/`
subtree); per CLAUDE.md, change both.

Delete (live + packaged):

- `contexts/autonomy/triage/` (whole namespace dir if empty after)
- `workflows/autonomy/fully-automated.md`, `human-verify.md`, `human-only.md`
  — zero tickets ever used fully-automated or human-verify; human-only was
  used once (`tasks/marketing/relay-discord`, paused, snapshot frozen)

Rename (live + packaged): `workflows/autonomy/assist-only.md` →
`workflows/draft-for-human.md` with `name: draft-for-human`; drop the
"automated-tier downgrade ladder" sentence and any tier framing from its
body. Remove the then-empty `workflows/autonomy/` dirs.

Edit (packaged bootstrap unless noted):

- `bootstrap/skills/bootstrap/ticket/SKILL.md` — remove interview step 3
  (autonomy triage) and the tier→workflow mapping, renumber the following
  steps, remove the "do not infer from the autonomy tier" clauses in the
  script question, and remove the `Autonomy tier` block from the step-7
  summary template. Add the one-line human-gate sentence to the workflow
  question (step 4).
- `bootstrap/skills/browser/build-automation/SKILL.md` — its "Choose the
  autonomy workflow" section routes to `autonomy/*` refs; rewrite the routing
  to real surviving workflows (all-agent workflow / owner-gated workflow /
  human performs it, agent read-only) without the tier names.
- `bootstrap/browser-automation/ticket.md` — "autonomy workflow" wording.
- `bootstrap/contexts/coga/cli/SKILL.md` ~line 230 — "autonomy-tier ticket"
  wording.
- Live `coga/tasks/v2/autotrigger-ticket-type.md` (draft) — references
  `autonomy/assist-only`; repoint to `draft-for-human`.
- Live `coga/tasks/nightly-auto-drain-run-for-ready-tickets.md`
  (in_progress) — defines drain-ready as "`autonomy/fully-automated`-shaped";
  reword to "workflow whose steps are all agent-assigned (no human/owner
  gate)". Touch only the wording, not that ticket's state.

Out of scope — unrelated senses of the words: `coga slack --important`
triage owner, `coga status` triage view, "P0/P1/P2 triage tier" example in
the architecture context, patents-repo patentability triage, and marketing
contexts' "autonomy" positioning language. Leave all of those alone.

Tickets already on `autonomy/*` workflows keep working: their workflow
snapshots are frozen in frontmatter and are not rewritten.

Verify with `python -m pytest` and `coga validate --json`; grep for
`autonomy/` afterward to confirm only frozen ticket snapshots and
out-of-scope mentions remain.

<!-- coga:blackboard -->

## Ticket authoring notes

Usage audit of autonomy triage across all repos (2026-07-20):

- **The 3-question test itself never changed a decision.** The only recorded
  disagreement with intuition was overridden: `clean-up-workflows-…` blackboard
  says "triaged fully-automated, but the chosen `code/with-review`" won anyway.
  Evaluator reviews repeatedly spent lines debating tier fit ("assist-only vs
  human-verify, mild semantic stretch, not worth blocking") with no downstream
  effect.
- **`autonomy/assist-only` is the one workflow with real usage** — 4 tickets,
  all "agent drafts, nick owns the wording" taste tasks:
  `launch-prompt/review-and-edit-the-relay-launch-prompt-editorial` (paused),
  `why-browser-autoamtion-as-a-ticket` (done), `improve-prompt-for-relay-ticket`
  (in_progress), `v2/autotrigger-ticket-type` (draft).
- **`autonomy/human-only`**: 1 ticket (`marketing/relay-discord`, paused).
  **`autonomy/fully-automated` and `autonomy/human-verify`: zero tickets ever.**
- **Patents repo** (`/home/n/Code/patents`) never used it: no `autonomy/*`
  workflows installed, no tier mentions. Its "triage" hits are patentability
  triage (unrelated). High-stakes fee work is gated by `patent/*` workflow
  design directly. Its tickets carry an older `autonomy: interactive|auto`
  frontmatter field — a predecessor mechanism, not this triage.
- **Magicator/xpref repos**: autonomy workflows present only as seeded
  batteries; zero tickets use them. The `coga-*` siblings are worktree clones
  (duplicate hits).
- `nightly-auto-drain-run-for-ready-tickets` (in_progress) uses
  "fully-automated-shaped workflow" as its *definition* of drain-ready — but
  reads that off workflow shape (no human/owner gate), not a stored tier.
  Removal must keep that wording coherent.
- Tickets already on `autonomy/*` workflows keep working after deletion —
  their workflow snapshots are frozen in frontmatter.
