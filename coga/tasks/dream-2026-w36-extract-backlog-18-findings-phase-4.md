---
title: 'Dream 2026-W36 extract backlog: 18 findings Phase 4 could not consume'
status: in_progress
owner: nicktoper
agent: claude
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 3 (open-pr)
launch_generation: 62a7c2ba-1860-4177-99cd-f0c0ea643102
---

## Description

Carrier ticket. Dream 2026-W36's Phase 2 knowledge scan classified 18 findings as
`extract` — durable knowledge sitting in a done ticket that belongs in a context or skill.
Phase 6 routes `extract` findings to Phase 4, which opens the knowledge PRs.

**Phase 4 could not consume any of them.** Every one names a source ticket that either
carries a real `## Dev` branch and worktree (retirement debt, deliberately left on disk so
the human-typed `coga retire <slug>` stays valid) or is `status: canceled` (which
`retro/done-ticket` refuses). Phase 4's seven eligible tickets were all period tickets
carrying nothing durable, and were direct-deleted.

The source tickets are all still on disk, so the *knowledge* is safe. This ticket exists
because the *findings* were not — Dream's blackboard is deleted at the next firing.

**This is a backlog, not a single change.** The right first move is triage: decide which of
the 18 are worth landing, group them into coherent knowledge PRs by target context, and
split into sibling tickets if that is cleaner than one pass. Several may be better handled
by the `coga retire` flow for their source ticket, which would consume the evidence
naturally.

The routing hole that produced this is ticketed separately as
`dream-findings-have-three-routing-holes-that-lose`.

## Context

Citations name symbols and files, not line numbers. Each item gives the source ticket and
the target area; the full finding paragraphs are in the Dream 2026-W36 blackboard
(`coga/tasks/recurring/dream/ticket.md`, `## Findings`) **until that task is retired at the
next firing** — copy anything you need from it before then, or recover it from git history.

**Target `coga/codebase` (5)**

1. `autoclose-should-name-the-retire-follow-up` — peer review's microkernel refinement: do
   not promote a helper to core while its duplicate consumers stay unmigrated.
   `append_report` exists as three byte-identical private copies in `skill_update.py`,
   `dream_validate_drift.py`, and `dream_cleanup_orphan_markers.py`; the rule is
   "consolidate the real consumers, don't add a fifth". The naive reading of the current
   context ("three consumers, therefore promote") gives the opposite answer.
2. `bumppy-requires-exactly-two-agents` — validate-before-write for lifecycle mutations:
   build a prospective `Ticket`, validate via `assert_task_valid(..., ticket_override=...)`,
   then commit. Three writers converted (in `mark.py` and `bump.py`); `mark_active`,
   `mark_in_progress`, `mark_blocked` and `mark_paused` still write-then-validate.
3. `select-session-conduct-instead-of-appending-a-cont` — `coga launch --prompt-report`
   reads as a report but runs under the mutating `launch` command and is swept, so it
   published three working-tree doc edits to `origin/main`. The codebase context's
   "read-only commands are safe" list invites exactly the wrong inference.
4. `megalaunch-only-shows-one-page` — inside a feature worktree a bare `python -m pytest`
   imports the *primary* checkout's source via the editable-install `.pth`.
   `PYTHONPATH=$PWD/src` is the default invocation, not a repair for a broken install.
5. `rewrite-coga-base-prompt-and-agent-mode-block` — authoring rules for
   `src/coga/resources/prompt*.md`: an abridged restatement inside a prompt resource is
   often the only version an agent sees, and a guard split across two resources can be
   deleted wholesale in one commit with tests still green.

**Target `coga/recurring` (3)**

6. `recurring-last-serviced-period-compares-as-a-strin` — how to suppress a new template's
   first firing.
7. `migrate-recurring-templates-to-ticket-py-shims-and` — why a `ticket.py`-backed step
   keeps `assignee: agent`.
8. `fix-the-autofix-analyst` — **two of that ticket's three specified defects are still
   live** in `src/coga/recurring_autofix.py`: the failure detail is built as
   `(result.stderr or result.stdout or "")`, so a benign stderr warning hides the real
   cause on stdout; and the analyst subprocess passes no `stdin`, so piped bytes are
   grafted onto the analysis prompt. This one is a **bug carrier**, not just knowledge —
   it likely deserves its own ticket.

**Target `dev/code` (2)** — both from `launch-ignores-the-recorded-worktree-stranding-bla`

9. `coga launch` never chooses the agent's working directory: `run_with_done_marker` takes
   no `cwd` and there is no `os.chdir` in `src/coga/`. `worktree:` authorizes the
   single-checkout assist; it does not place anything.
10. The `requires: branch` gate is cheaply satisfiable by hand-copying the lines, and
    `open-pr`'s "commit or stash them" remediation steers an agent into committing the
    stranded duplicate onto the feature branch, manufacturing a `ticket.md` merge conflict.

**One each**

11. `put-build-back` → `coga/architecture`: a `--agent` override propagates across directly
    consecutive frozen agent steps and stops at a role change or human assist.
12. `remove-legacy-config-compatibility-shims` → `coga/extension-model`: alias-validation
    failure modes, including the `coga init` / `coga recurring --all` recovery exemption.
13. `ship-a-shared-recurring-reminder-engine-battery` (canceled) → `coga/period-task` +
    `coga/codebase` gotchas: cross-run state writers must use the fence-aware
    `coga.blackboard` / `coga.taskfile` API; a bare append destroys a fence on a file that
    ends at one, breaking every blackboard reader at once.
14. `move-cogacontext-to-roodoc-so-its-easier-for-human` → `coga/sync`: an experiment that
    mutates tracked repo state and is exercised through Coga commands publishes itself on
    the first command; run it with `[git] enabled = false` or in a throwaway clone.
15. `put-build-back` → `coga/project-stage`: two more delete-then-restore cycles for the
    bias-toward-deletion precedent list, plus the partial-revert procedure both produced.
16. `dream-phases-2-3-cannot-complete-scan-subagents-re` → `retro/done-ticket`: Phase 4 is
    the one Dream phase with no on-disk progress contract, and it is the destructive one.
17. `reconcile-recurring-wrapper-tty-admission-guidance` → `code/with-review`: the workflow
    never says the peer review must have returned and been read before `coga bump`. PR #723
    merged while its review was still running; the review then returned six actionable
    regressions in merged code, two of them P1 lifecycle races.
18. `megalaunch-only-shows-one-page` → `code/self-qa`: no rule covers surfaces automated
    tests structurally cannot reach; a recorded manual sweep should be a gate and an
    undrivable terminal a blocker.

Filed by Dream 2026-W36, Phase 6 disposition.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: dream-w36-extract-backlog
worktree: /home/n/Code/claude/coga-dream-w36-extract-backlog

Separate-checkout layout, branched from `origin/main` (`329b8d0b`). The
primary checkout sits on the `cite-symbols-rule` control branch, which carries
unrelated in-flight edits, so the feature branch deliberately does not fork
from it.

## Triage (2026-09-12, implement)

Key fact the ticket predates: Dream's *next* firing (period 2026-09-08) routed
its `extract` findings into proposal PRs #763–#775 instead of Phase 4, and all
of them merged on 2026-09-09. That consumed a large share of this backlog.
Verified item by item against `origin/main`:

**Already covered or separately ticketed — no action (7):**

- 2 validate-before-write → `coga/architecture` (PR #769; `ticket_override`
  idiom, and the four still-write-then-validate writers named).
- 3 `--prompt-report` is not read-only → `coga/codebase` (PR #773).
- 4 `PYTHONPATH=$PWD/src` as the default from a feature checkout →
  `coga/codebase` (PR #773).
- 11 `--agent` override propagation → `coga/architecture` (PR #769;
  `consecutive_agent_override` paragraph).
- 14 mutating experiments publish themselves; `[git] enabled = false` or a
  throwaway clone → `coga/sync` (PR #767).
- 17 wait for the ordered review before bumping → `code/with-review`
  peer-review section and `code/self-qa` step 7 (PR #771).
- 8 autofix analyst defects → already its own ticket:
  `the-autofix-analyst-ticket-closed-without-shipping` (draft) names all three
  defects, including the third this backlog never captured. Nothing to add.

**Landing here, grouped by target (11, including partially covered item 12):**

- `coga/codebase` (twin pair): 1 consumer-test refinement (`append_report` ×3
  private copies; consolidate, don't add a fifth), 5 prompt-resource authoring
  rules, 13 fence-aware blackboard writers (gotcha).
- `coga/recurring` (twin pair): 6 first-firing suppression — rewritten for the
  current ledger mechanism (`last_serviced_period:` no longer exists; the mark
  is a `coga/log.md` line written at period-task creation), 7 why a
  `ticket.py`-backed step keeps `assignee: agent`.
- `coga/extension-model` (twin pair): 12 alias-validation failure modes +
  cross-ref to the recurring escape hatch. PR #774 covered the recurring half
  already; the alias-owning context still needed this half.
- `dev/code` (twin pair) + `code/open-pr` skill (twin pair) +
  `open_pr.py` remediation string: 9 launch never places the agent, 10 the
  gate is presence-only and cheaply satisfiable; a stranded duplicate is
  discarded, never committed or stashed.
- `coga/period-task` (twin pair): 13 cross-run state writers use the
  fence-aware API.
- `coga/project-stage` (live only): 15 precedent list — `coga build` removed
  (#691) then restored (#701); watchers reintroduced then removed again
  (#784); partial-revert procedure. Also corrects the existing watcher bullet,
  which stopped being true at #784.
- `retro/done-ticket` (packaged only) + Dream template (twin pair): 16
  on-disk progress contract for the destructive phase.
- `code/self-qa` (twin pair) + `code/with-review` (packaged only): 18 manual
  sweep gate for surfaces automated tests structurally cannot reach.

**Decision: one PR, one commit per target area** rather than sibling tickets.
Eleven findings across eight target areas; five more `with-review`
tickets would cost more workflow overhead than the review of a commit-grouped
diff. `coga retire` on the source tickets is not used here: they stay on disk
as retirement debt, and this ticket only copies knowledge out of them.

## Implemented (2026-09-12)

Six commits on `dream-w36-extract-backlog`, one per target area, tip
`84cd9bcd`, 20 files, +400/−7. Every live/packaged twin was verified identical
at `origin/main` before editing and copied live → packaged after; the Dream
template pair was edited in both places.

- `45472c61` `coga/codebase` — items 1, 5, 13 (consumer-test refinement under
  the microkernel rule; two new gotchas).
- `e6818856` `coga/recurring` + `coga/extension-model` — items 6, 7, 12.
- `dd00fb90` `dev/code` + `code/open-pr` skill + `open_pr.py` — items 9, 10.
  The only code change: the "uncommitted changes" refusal no longer says
  "commit or stash them"; no test asserted on that string.
- `b6221cc9` `coga/period-task` + `coga/project-stage` — items 13, 15.
- `2123817f` `retro/done-ticket` (packaged-only) + Dream template — item 16.
- `84cd9bcd` `code/self-qa` + `code/with-review` (packaged-only) — item 18.

Decisions worth a reviewer's eye:

- **Item 6 rewritten for current reality, not transcribed.** The source
  ticket's lesson ("seed a real period key, not `none`") is about a template
  field that no longer exists; the mark is now a `coga/log.md` line written at
  period-task creation, and the bare sweep creates and launches in one pass
  with no create-only mode. The context therefore says: suppress by timing or
  by parking (`_` prefix), make the body tolerate an already-handled period,
  and never `coga mark canceled` a period task at the stable path — a canceled
  task is returned on the next period and refused (`recurring_runner`
  "left alone" gate), so the template sticks until deleted. Verified against
  `recurring.py` (`_last_firing`, `_advance_serviced_period`) and
  `recurring_runner.py`.
- **Item 15 corrects an existing bullet.** `project-stage` said watchers were
  "removed once and later reintroduced"; they were removed again in PR #784,
  which `current-direction` already records. The owner quote for the build
  restore is verbatim from `coga/log.md`.
- **Item 16 adds a contract, not just a note.** `retro/done-ticket` gains a
  `progress.md` beside the evidence snapshot (caller-owned directory, outside
  every diff) and the Dream template reads it and reports `partial` when the
  `complete` line is missing. Without the reader the contract would be dead.
- **Item 18 lands in both `code/self-qa` and the `with-review` peer-review
  section**: the incident's manual gate sat on peer-review, and this repo's
  tickets run `with-review`, so the skill alone would not reach them.
- **Item 12 landed in `extension-model` even though PR #774 covered the
  recurring side** — that context owns aliases and named no failure mode.

Verification, from the feature worktree with `PYTHONPATH=$PWD/src
python3.12 -m pytest -p no:cacheprovider`: 2434 passed, 1 failed —
`tests/test_packaging.py::test_wheel_includes_bootstrap_batteries`, "Cannot
import 'hatchling.build'", the environment gap Dream's blackboard records as
failing identically on unmodified `origin/main` (human-needed #5 there). All
twin-parity assertions pass. `git diff --check` clean. `coga validate --json`
reports the same 31 repo-wide baseline issues as before (none touch changed
files). Rebased onto `origin/main` `329b8d0b`; `origin/main` is an ancestor
of the tip. Not pushed; no PR.

## Peer review

`codex review --base origin/main` **returned** on 2026-09-12 (exit 0) from
`/home/n/Code/claude/coga-dream-w36-extract-backlog`, reviewing `84cd9bcd`
against the fork from `origin/main`. It found three P2 issues; all are fixed
in commit `901a9909` after the final rebase; final verification passed:

- The open-pr refusal and its context/skill twins treated every dirty task
  path as stranded and applied discard advice to single-checkout work. The
  hint now distinguishes layouts, preserves the live single-checkout ticket
  and intentional ticket/attachment implementation, and limits disposal to
  verified duplicate hunks. Regression coverage includes a dirty `ticket.py`
  and a single checkout carrying fresh review notes.
- Enabling a recurring template before its next firing still selected the
  previous firing. Verified a March 1 schedule on February 28 selects the
  previous year's March 1. Both twins now require parking until after the
  intended firing instant or an idempotent no-op body.
- Retro tried to append progress inside its read-only snapshot. Retro, Dream
  (both twins), and the Retire caller now use a unique writable run directory
  with read-only `evidence/` and a writable sibling `progress.md`; a `start`
  append verifies writability before remote mutation.

Additional local review corrections: progress receipts cannot prove that a
missing event never happened on the remote. The contract now treats that gap
as unknown disposition, checks fresh remote deletion/branch/PR evidence
before retrying, and retains recovery paths on incomplete runs. The new
blackboard guidance also overstated the APIs: `append_blackboard_report` has
no `expected_bytes` argument, and both it and `replace_blackboard` still glue
plain content to a fence at EOF with no newline. Reproduced both cases in an
isolated fixture; documented the required leading separator and the existing
API limitation in `coga/codebase` and `coga/period-task`, including both twins.
The underlying EOF-separator bug remains outside this knowledge PR; its
reproduction and workaround now survive source-ticket retirement.

No interactive terminal or Slack-rendering behavior changes here. Manual
contract review covered single vs separate checkouts, intentional ticket
attachments, readonly evidence with a writable sibling log, and termination
after a remote action but before its receipt.

Final verification (2026-09-12):

- `git fetch origin main` then `git rebase FETCH_HEAD` succeeded without
  conflicts onto `ce96f2af1086e457a8e71412522dbfcfd7887058`.
- From the feature worktree:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:/tmp/coga-dream-w36-review-deps" python3.12 -m pytest -p no:cacheprovider`
  — **2437 passed in 177.48s**, including the wheel-build test. `hatchling`
  and its dependencies were installed only into that temporary directory;
  the prior environment failure is resolved for this run. Confirmed that
  `import coga` resolves to this feature checkout's `src/coga/`.
- `git diff --check origin/main...HEAD` passed. All eight changed
  live/packaged pairs were separately compared after the rebase and are
  byte-identical.
- From the primary checkout:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src" python3.12 -m coga.cli validate --task dream-2026-w36-extract-backlog-18-findings-phase-4 --json`
  — one task OK, no issues.
- Focused checks covered both checkout layouts, dirty ticket attachments,
  packaged resources, and Dream/Retire callers. Two old literal snapshot
  assertions were updated to pin the writable-sibling contract; their rerun
  passed before the commit, and the final full suite includes them.
- A filesystem probe confirmed read-only `evidence/` rejects writes while
  sibling `progress.md` accepts the `start` receipt. Manual contract review
  also covered a remote action succeeding before its receipt is written.

Handoff: feature HEAD `901a9909a038902b42e0b904dbaa1636cec59213`, clean and
committed, seven commits ahead of fetched `origin/main`; final diff is 24
files, +575/−25. The branch is on the durable recorded sibling worktree and
has not been pushed; no PR exists yet. The next step only runs the
deterministic open-pr command and bumps. The review has returned and no
review process or test run is still in flight.

## PR

Dream 2026-W36 left durable findings on source tickets that its cleanup phase
could not consume. Preserve the remaining eleven findings in their owning
contexts and skills. Seven items are already covered or separately ticketed;
the carrier blackboard records the per-item disposition.

- Document the remaining microkernel, prompt-authoring, recurring, alias,
  period-state, and partial-revert lessons in the live and packaged contexts.
  Include the existing EOF-fence separator limitation and its workaround.
- Make open-pr recovery guidance respect checkout ownership: preserve the
  live ticket in a single checkout, retain intentional task attachments, and
  discard only verified duplicate task-state edits in a separate checkout.
- Give Retro, Dream, and Retire a shared progress contract: immutable
  evidence, writable event receipts, and remote reconciliation after an
  incomplete run. Preserve recovery paths when completion is unverified.
- Require recorded manual QA for changed surfaces automated tests cannot
  reach, in both self-QA and the peer-review workflow.

Source tickets remain available for explicit retirement. Native Codex review
returned; all three P2 findings were addressed before the final rebase.

Test plan: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:/tmp/coga-dream-w36-review-deps" python3.12 -m pytest -p no:cacheprovider` — **2437 passed**, including the wheel build; the temporary path contains the declared hatchling test dependency. Task validation and `git diff --check origin/main...HEAD` pass; all eight edited live/packaged pairs match.
