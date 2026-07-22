---
slug: remove-autonomy-triage
title: remove autonomy triage
status: in_progress
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 3 (pr)
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

## Dev
branch: remove-autonomy-triage
worktree: /tmp/coga-remove-autonomy-triage

## Implement notes

- 2026-07-21: Started from `main` at `fee62763`. The primary checkout already
  has unrelated control-plane edits; implementation is isolated in the
  recorded worktree.
- Scope decision: keep `draft-for-human` at the top-level workflow namespace,
  matching the evaluated ticket direction; frozen `autonomy/*` workflow
  snapshots and explicitly out-of-scope uses remain untouched.
- Implemented the live + packaged removals/rename, simplified the ticket
  interview, rerouted browser authoring by real workflow handoff shape, and
  updated the two named live tickets. Added focused template/init assertions.
- Verification: targeted template/init tests passed; after rebasing, the full
  suite passed (1,383 passed, 1 skipped). Repo-wide `coga validate --json`
  still exits 1 on the same pre-existing draft-ticket errors as untouched
  `main`; task-scoped validation has no errors (only the isolated worktree's
  expected missing `coga.local.toml` user warning).
- Final commit: `a069a6e3` (`Remove autonomy triage workflows`), rebased onto
  fetched `origin/main` at `b6dcc7d4`; feature worktree is clean and one
  material commit ahead.
- Final reference audit: live and packaged `draft-for-human` copies are
  byte-identical; both `autonomy/` context/workflow directories are absent;
  changed shipped surfaces and the two named live tickets contain no stale
  workflow refs. Remaining repo-wide matches are frozen/historical tickets,
  the removal ticket itself, and explicitly out-of-scope wording.
- Note: the inherited test environment twice appended synthetic
  `## Dream Skill: validate-drift` fixture output to this live blackboard;
  those test-only sections were removed before handoff.

## Self-QA

Commit `ad2c91b1`. `/code-review` is user-invocable only, so the review pass
ran in-loop; `/simplify` ran its four-agent fan-out. Applied:

- **Missed scope (3).** `docs/reference.md:77` still said the browser bootstrap
  "selects the appropriate autonomy workflow" — same wording the ticket had us
  fix in two sibling files, but that file was never listed. Also
  `nightly-auto-drain:227` ("`ready` = fully-automated-tier") and a whole
  `## Autonomy triage` section in `v2/use-worktree-when-starting-a-dev-task`
  (its one concrete detail folded into the workflow rationale two lines above).
- **`browser/build-automation`.** Removed prose that only parsed if you
  remembered the deleted tiers; fixed §2's dangling promise of a
  "prerequisites step" no surviving workflow has (it contradicted §4); aligned
  the "nothing fits" escape hatch with `bootstrap/ticket` — surface it to the
  human instead of authoring a workflow mid-flow.
- **`draft-for-human`.** Restored a "when to pick this" cue; the new
  description had replaced it with a restatement of its own step body, and the
  description is now the selection surface (`ls coga/workflows/`).
- **`bootstrap/ticket`.** Refolded "never override a workflow the human picks",
  which lost its referent when the tier advisory it qualified was deleted.
- **Tests.** Registered the live/packaged pair in `test_packaging.py`'s
  `IDENTICAL_LIVE_PACKAGED_PAIRS` + `EXPECTED_BOOTSTRAP_RESOURCES` (the real
  owners, with wheel-inclusion coverage) instead of a weaker re-implementation
  in the browser test; split the removal asserts into their own test; scoped
  the vocabulary bans to `autonomy/` so they can't fire on the live
  `autonomy: auto` execution axis.

Verification: `python3.12 -m pytest` → 1384 passed, 1 skipped.
`coga validate --json` → 8 errors, **byte-identical to the set on untouched
`origin/main`** (verified against a pristine clone at `b6dcc7d4`); all are
pre-existing `v2/*` + `op-service-account` draft-ticket errors. Zero
introduced.

The synthetic `## Dream Skill: validate-drift` fixture output appended itself to
this blackboard twice more during this step (same as implement saw); removed
again. It references a `coga/tasks/x/` and a `repair-branch` that don't exist —
nothing real was written.

## For PR review — four judgment calls left to the human

Not applied: each reverses or extends a decision the ticket states explicitly.

1. **The strongest finding — the usage audit may have measured too early.**
   "Zero tickets ever used fully-automated or human-verify" is true but those
   two were never author-picked; they were the *output set* of
   `browser/build-automation`, which shipped 2026-07-19 (PR #607). The audit
   ran 2026-07-20 — one day later. A fresh install now seeds no all-agent
   browser-shaped workflow, no workflow with a gate before an irreversible
   action, and no human-performs/agent-read-only workflow, so the router's §3
   routes to an empty set and every user hand-authors what was deleted. The
   audit disproved the *rubric*; it says nothing about the *handoff shapes*,
   which are separable. Worth deciding before merge whether `human-verify` /
   `human-only` should survive as domain-generic shapes under non-tier names.
2. **Deleting a workflow degrades in-flight tickets.** Freezing covers step
   names/assignees/skills, not the step's instruction prose —
   `src/coga/compose.py:355` re-reads the workflow file each launch and falls
   back to `*Workflow definition not found; using frozen snapshot only.*`. So
   `marketing/relay-discord` (paused, step 1) and `improve-prompt-for-relay-
   ticket` (in_progress, step 3) now resume with a placeholder where their step
   instructions were. They don't error — they just lose the instructions, which
   is quieter than the ticket's "keep working" implies, and
   `contexts/coga/architecture/SKILL.md:59-60` ("in-flight tickets are
   unaffected by later workflow edits") is imprecise as written.
3. **Namespacing.** `workflows/_template.md:3` instructs
   `workflows/<namespace>/<your-workflow>.md`, and `draft-for-human` is now the
   only unnamespaced workflow in either tree (`_template.md` is
   underscore-prefixed precisely because it isn't one). `draft/for-human` would
   restore that invariant and read like `code/with-review`. Left as-is because
   the ticket prescribes the literal name; flagging since the ticket already
   marked this a PR-review taste call.
4. **Where the human-gate rule lives.** It now exists only as skill prose, in
   two independently-worded copies (`bootstrap/ticket` q3 and
   `browser/build-automation` §3), where before it had one home in the deleted
   triage context. Reviewers argued it belongs in
   `contexts/coga/principles/SKILL.md` §2 with both skills pointing at it. Not
   applied — the ticket's stated design is the one sentence in the interview
   question.
