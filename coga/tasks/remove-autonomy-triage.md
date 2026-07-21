---
slug: remove-autonomy-triage
title: remove autonomy triage
status: draft
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/with-self-review
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

Why (usage audit, 2026-07-20): the 3-question test never changed a real
decision — the one recorded disagreement (`clean-up-workflows-…` triaged
fully-automated) was overridden in favor of `code/with-review`. The patents
repo never installed the mechanism; its high-stakes work is gated by
`patent/*` workflow design directly. `autonomy/assist-only` is the exception
with real mileage: 4 tickets, all agent-drafts-human-owns taste work — hence
the rename rather than deletion.

Evaluator (2026-07-21) verified every path on the checklist and greps found
no misses; `src/coga/config.py:463` mentions "autonomy rework" only in a
historical comment — leave it. Two taste calls left to the implementer, for
the human to check at PR review: `draft-for-human` sits unnamespaced at
workflows/ top level, and the exact wording of the human-gate sentence in
the interview is open (gist in ## Description).

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

- `bootstrap/skills/bootstrap/ticket/SKILL.md` — remove interview question 3
  (autonomy triage) and the tier→workflow mapping from `## Step 3 — Interview
  the human`, renumber the following questions, remove the "do not infer from
  the autonomy tier" clauses in the script question, and remove the
  `Autonomy tier` block from the Step 7 summary template. Add the one-line
  human-gate sentence to the workflow question (currently question 4).
- `bootstrap/skills/browser/build-automation/SKILL.md` — its "Choose the
  autonomy workflow" section routes to `autonomy/*` refs; rewrite the routing
  to real surviving workflows (all-agent workflow / owner-gated workflow /
  human performs it, agent read-only) without the tier names. Also fix the
  frontmatter `description:` (line 3), which mentions selecting an autonomy
  workflow.
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
contexts' "autonomy" positioning language. Also unrelated "human-only"
phrasings: `contexts/coga/principles/SKILL.md` ("a human-only operation",
live + packaged), `src/coga/resources/prompt.md` ("a human-only field"), and
`bootstrap/skills/bootstrap/dream/tasks/validate-drift/run.py` ("Lifecycle
correction is human-only"). Leave all of those alone.

Downstream repos already seeded with `autonomy/*` workflows (magicator,
xpref, worktree clones) are not cleaned by this ticket — accepted; they pick
up the change whenever they re-seed.

Tickets already on `autonomy/*` workflows keep working: their workflow
snapshots are frozen in frontmatter and are not rewritten.

Verify with `python -m pytest` and `coga validate --json`; grep for
`autonomy/` afterward to confirm only frozen ticket snapshots and
out-of-scope mentions remain.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
