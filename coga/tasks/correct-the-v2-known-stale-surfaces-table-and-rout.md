---
title: Correct the v2 known-stale-surfaces table and route future Dream gap findings
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
step: 4 (review)
---

## Description

The `coga/tasks/v2/README.md` known-stale-surfaces table has a defect that misroutes readers, and
the parking area has no recorded answer for where future Dream `gap` findings should go. This is the
PR-shaped half of the v2 triage: file edits only, no lifecycle writes, no cancels.

Three deliverables:

- **Fix the `relay-os/… -> coga/…` rename row.** As written it sends readers to `workflows/code/*`
  paths that do not exist in the repo.
- **Decide whether `script:` warrants a row at all**, and if so write it accurately (see Context —
  the obvious version of this row would be false).
- **Record where future Dream `gap` findings go** instead of decaying in this directory.

Also clears 2 of the 4 `coga validate` errors via the two blackboard syntheses named in Context.

## Context

### Shared background (all three v2 triage tickets)

This ticket is one of three split out of `triage-the-v2-parking-area-empty-descriptions-prem`
(canceled 2026-09-02). Siblings: `correct-the-v2-known-stale-surfaces-table-and-rout`,
`adjudicate-the-eight-premise-dead-v2-drafts`, `interview-the-owner-on-the-17-title-only-v2-stubs`.

Origin: Dream 2026-08-24, Phase 2 knowledge scan (shards 06, 09, 11, 12), classified `gap`.
Re-verified against `main` 2026-09-02 plus an independent cold review. **Where these notes and the
original Dream findings disagree, these notes win.**

**The contract for this directory is `coga/tasks/v2/README.md`.** Read it first — it defines the
two-question premise check (does the subject still exist? do the surfaces it names still resolve?)
and records the `decide-the-fate-of-two-premise-dead-v2-drafts-whos` cancellation precedent.

**Counting `v2/` correctly.** `coga status v2 --all` reports **81 tasks**. Do not count with
`ls coga/tasks/v2/*.md` — that returns 76, counting the `cleanup-core-commands/` directory as one
entry and missing its six children. The Dream scan's "~75" and "18" are both this artifact.

**`coga validate` state.** 4 ERRORs repo-wide, all `unsynthesized-draft-blackboard`, all under
`v2/`. The rule fires only on `status == "draft"` (`src/coga/validate.py:447`), so each clears by
cancelling or synthesizing. Everything else `coga validate` prints is a WARN. Two errors clear in
`correct-the-v2-known-stale-surfaces-table-and-rout`, two in
`adjudicate-the-eight-premise-dead-v2-drafts`. **A green validate is never a reason to cancel a
draft** — it is a consequence of correct verdicts, never an input to them.

### The table defect that is real and unqualified

The `relay-os/…`, `relay-os/contexts/…` row maps to `coga/`, `coga/contexts/…`. That is correct for
contexts but misleading for workflow refs: **`coga/workflows/code/` does not exist.** The `code/*`
workflows resolve only from `src/coga/resources/templates/coga/bootstrap/workflows/code/`.
`coga/workflows/` itself does exist and holds repo-local workflows (autoclose-merged, branch-sweep,
digest, skill-update, build, direct), so the row cannot simply be deleted — it needs to distinguish
repo-local from packaged.

### The `script:` field — do not write the obvious row

15 drafts in `v2/` carry `script:`, all of them `script: null`. An earlier version of this work
claimed core "has no reader" for the field. **That is wrong and would have put false prose into the
contract file.** `src/coga/ticket.py:74-80` is a bounded migration that pops `script` when its value
is `None`, so all 15 are already handled and self-heal on the next write through core.

If a row is added at all, the accurate text is: "`script:` — Gone; a bounded migration in
`src/coga/ticket.py:74` strips `script: null` on next write." Confirm with the owner whether that
earns a row — the honest answer may be no, since the field is inert and self-clearing. Note this is
a *different* surface from the `mode: script` row the table already carries.

### The two blackboard syntheses

`measure-relay-prompt-scope-and-agent-precision` (4,215-char blackboard) and
`use-worktree-when-starting-a-dev-task` both fail `coga validate` with
`unsynthesized-draft-blackboard`. Synthesize both. "Synthesize" is defined in
`coga/contexts/coga/architecture/SKILL.md` (~lines 720-730): fold durable content from the
blackboard up into the ticket body, or move deliberate launch notes under a `## Production notes`
heading, which the validator accepts as the alternative. Read that passage before starting — it is
not attached as a context because the file is 59 KB.

Phase 1 `validate-drift` originally proposed synthesis for four drafts. Only these two keep that
route; the other two (`autotrigger-ticket-type`, `split-context-to-doc-user-accessible-and-editable`)
are adjudicated in `adjudicate-the-eight-premise-dead-v2-drafts` and must not be synthesized here.

### Where future `gap` findings go

The v2 README records that two drafts it cancelled as premise-dead "were themselves Dream `gap`
findings originally." Findings parked here decay — that is the standing pattern this ticket names.
The decision is durable routing policy, so it lands in a file, not in a ticket: write it into
`coga/tasks/v2/README.md`, and if it changes Dream's own behavior, also the roadmap's "Deferred
work" section. **Confirm the target and the policy with the owner before writing** — this is the one
judgment call in an otherwise mechanical ticket.

### Out of scope

Any `coga mark canceled` call, and any verdict on the 8-draft premise cohort or the 17 stubs. Those
are the two sibling tickets. If triaging the table surfaces a draft you believe is premise-dead,
note it for the sibling ticket rather than acting on it.

**Dream 2026-W38 evidence (finding F-20).** Re-verified: the known-stale-surfaces row `relay-os/…` → `coga/…` still misroutes workflow refs — `coga/tasks/v2/dev-loop-git-hygiene-lift-sync-with-main-into-code.md` (now deleted by Retro) and `coga/tasks/v2/automerge-ticket.md` cite `relay-os/workflows/code/with-self-review.md` / `with-review.md` / `design-then-implement.md`, and `coga/workflows/code/` does not exist; `code/*` workflows resolve only through `src/coga/paths.py::bootstrap_workflow_path` from the packaged bootstrap tree. Split the row: `relay-os/contexts/…` → `coga/contexts/…`; `relay-os/workflows/<name>` → repo-local `coga/workflows/<name>` if present, otherwise the packaged bootstrap tree (`code/*` is packaged-only). The second deliverable (a `script:` row) is now moot: `grep -rl '^script:' coga/tasks/v2/` returns nothing and the `script: null` migration was removed by #784 (`grep -n script src/coga/ticket.py` is empty) — drop it from this ticket's scope.

<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/845
branch: v2-stale-surfaces
worktree: /tmp/coga-v2-stale-surfaces

Separate linked feature checkout. Primary stays on `main` and owns this
blackboard and the workflow transition. Implementation commit: `c6a56e83`
(`Clarify v2 workflow paths and Dream gap routing`). No push or PR.

## Decisions and implementation (2026-09-17)

- README splits context renames from workflow resolution, matching
  `src/coga/paths.py::resolve_workflow_path` and `bootstrap_workflow_path`.
  Local workflows take precedence; this repo's `code/*` workflows are packaged.
- No `script:` row, per the ticket's W38 scope correction. The v2 drafts have
  no such field and `ticket.py` no longer has the old migration reader.
- The owner already settled routing in PR #799:
  https://github.com/FastJVM/coga/pull/799. GitHub records `nicktoper` merging it
  on 2026-09-15 UTC as `8816fa5315ed069de2d7e7be4afa8435a830c668`. Its Phase 6
  rules explicitly cover the question: reconcile with open owners, file new
  Dream drafts at the task root, and leave parking in `v2/` to humans after
  triage. This satisfies the ticket's owner-confirmation requirement without
  asking again or choosing a new policy. README summarizes and links to the
  owning Dream template and the roadmap's existing deferral rule. Dream behavior
  did not change, so no roadmap/template edit was needed. No packaged twin
  exists for this repo's v2 README.
- Prompt-scope draft: folded implementation provenance, historical measurements
  and verification, and the owner's context-selection correction into the body.
  Old `## Dev` pointers are historical provenance, no longer launch state.
  Remaining on-disk signals and the cut A/B scope remain as authored.
- Worktree draft: folded interview decisions and open cleanup, optional branch
  deletion, and sequencing questions into the body. Existing safety requirements
  remain intact; synthesis does not approve a new checkout contract.
- Both drafts retain their original frontmatter bytes and prior body text.
  Body syntheses were appended; authoring blackboards were replaced through
  `taskfile.replace_blackboard` with the stock placeholder. No lifecycle
  changes, cancellations, or sibling-cohort adjudications were made.

## Verification and handoff

- `PYTHONPATH=/tmp/coga-v2-stale-surfaces/src /home/n/Code/claude/coga/.venv/bin/python -m pytest`
  — **2654 passed** in 199.95 seconds. The initial ambient-Python attempt
  could not collect because `tomlkit` was absent; the existing test venv has
  the dependencies and was verified to import this feature checkout.
- Primary baseline: `coga validate --json` — 3 errors (the ticket's count of
  4 was dated), 48 warnings. Feature check:
  `PYTHONPATH=/tmp/coga-v2-stale-surfaces/src /home/n/Code/claude/coga/.venv/bin/python -m coga.cli validate --json`
  — exactly the two requested synthesis errors cleared. The remaining error
  is `v2/autotrigger-ticket-type`, owned by sibling
  `adjudicate-the-eight-premise-dead-v2-drafts`; it stays out of scope.
  Feature validation adds only the expected `missing-user` warning because
  this checkout has no ignored local config. Exit 1 is that known remaining
  error, not a new regression. JSON evidence is in
  `/tmp/coga-v2-validate-before.json` and `/tmp/coga-v2-validate-after.json`.
- Read-only checks verified all three `code/*` workflow paths, local
  `build/onboarding` and `direct/body`, README relative links, unchanged draft
  frontmatter/prior bodies, and the synthesis gate failing on each original
  blackboard and passing on each edited one.
- `git diff --check origin/main...HEAD` passed. After the commit,
  `git fetch origin main` and `git rebase FETCH_HEAD` confirmed freshness;
  `git merge-base --is-ancestor origin/main HEAD` passed against
  `c85725aaefda0618b6336f338d960150eb485c6c`. Feature checkout is clean.

Ready for peer review; no unresolved implementation blocker.


## Peer review

- `codex review --base main` **returned** successfully with no findings.
  It confirmed that the documentation preserves substantive requirements and
  historical evidence, and that routing and workflow paths match the repo.
  Initial sandbox initialization failed before review; the approved retry
  completed. Review transcript: `/tmp/coga-v2-peer-review.txt`.
- `git fetch origin main && git rebase FETCH_HEAD` completed without conflicts
  before review and tests. Current implementation commit: `fd8997a8d`, on
  `dd5415699` (`origin/main`). No review fixes or additional feature commit
  were needed; the feature checkout is clean and one commit ahead.
- Post-rebase verification:
  `PYTHONPATH=/tmp/coga-v2-stale-surfaces/src /home/n/Code/claude/coga/.venv/bin/python -m pytest`
  — **2657 passed** in 184.88 seconds.
  `git diff --check origin/main...HEAD` passed.
- `coga validate --json` on primary versus
  `PYTHONPATH=/tmp/coga-v2-stale-surfaces/src /home/n/Code/claude/coga/.venv/bin/python -m coga.cli validate --json`
  on feature confirms exactly the two requested errors clear (4 → 2).
  Remaining errors: `clean-up-all-the-working-trees` and
  `v2/autotrigger-ticket-type`, both pre-existing and outside scope.
  Warnings are 53 → 54, with the expected missing local user config warning.
  Evidence: `/tmp/coga-v2-peer-baseline.json`,
  `/tmp/coga-v2-peer-validate.json`, `/tmp/coga-v2-peer-pytest.txt`.
- Read the changed Markdown and verified the linked Dream Phase 6 / roadmap
  rules and workflow resolver. No terminal, pager, prompt, or Slack-rendered
  surface changes are present, so no interactive surface exercise applies.

## PR

Correct the v2 stale-surface table so Relay-era workflow references resolve
through repo-local workflows first, then packaged bootstrap workflows; this
repo's `code/*` workflows are packaged-only. Link future Dream gap findings to
the existing Phase 6 routing policy: reconcile with open owners, file new
drafts at the task root, and leave v2 parking to human triage.

Synthesize the prompt-scope and worktree drafts' authoring blackboards into
their bodies, preserving requirements, historical evidence, and open design
questions. No lifecycle changes or new Dream policy; the obsolete `script:`
row is omitted per the corrected scope.

Test plan: full `python -m pytest` with feature `PYTHONPATH` and the existing
test venv (2657 passed); `coga validate --json` comparison confirms exactly
the two targeted errors clear, with two unrelated baseline errors remaining;
`git diff --check origin/main...HEAD` passes.
