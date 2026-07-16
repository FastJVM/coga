---
slug: ticket-must-merge-blackblaord
title: ticket must merge blackblaord
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- coga/codebase
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
# --- extensions ---
mode: agent
---

## Description

The `bootstrap/ticket` flow writes authoring notes into a draft's blackboard
(`## Evaluator review`, `## Proposals`, `## Ticket authoring notes`) but nothing
clears them, so drafts are handed back carrying that cruft — and `coga mark
active` then *refuses* to activate until it's synthesized. Two changes:

1. **Bootstrap synthesizes, then clears its own blackboard.** As its **final
   action, after** the human has confirmed the step-7 summary, make the
   `bootstrap/ticket` skill **fold the evaluator review (and any other authoring
   notes) into the ticket body** — synthesize the durable substance into
   `## Context` (or an appropriate body section) — and **then** reset the
   blackboard to the stock placeholder. Nothing is lost: the review survives in
   the body (and the human edits from there), not only in git history. Update
   the step-7 summary line accordingly — it must no longer point at a
   `## Evaluator review` blackboard section that no longer exists.
2. **`validate.py` flags a non-empty blackboard.** Add a `coga validate` finding
   that surfaces a draft whose blackboard still holds prelaunch authoring notes.
   **Flag only** — no `--fix` mutation; it just makes the condition visible
   outside the `mark active` boundary. **Critical:** gate the finding to
   `status == "draft"` only. `prelaunch_blackboard_synthesis_reason` is
   status-agnostic, so reusing it unguarded would false-flag nearly every
   active/in_progress ticket (working blackboards routinely carry headings or
   >600 chars). Honor the existing `## Production notes` opt-out the helper
   already respects.

## Context

- **Blackboard helpers** live in `src/coga/blackboard.py`:
  `render_blackboard()` (stock template from `src/coga/resources/blackboard.md`),
  `_is_stock_blackboard()`, and `prelaunch_blackboard_synthesis_reason()` /
  `_text()` — the heuristic that decides whether a draft blackboard still holds
  authoring content (the `## Evaluator review` / `## Proposals` /
  `## Ticket authoring notes` headings, or >600 chars of non-placeholder text,
  unless a `## Production notes` section marks it intentional). "Empty" means
  reset to the stock placeholder, which `_is_stock_blackboard` treats as clean —
  not literally zero bytes.
- **Existing enforcement:** `src/coga/mark.py:240`
  `_refuse_unsynthesized_draft_blackboard()` calls that helper at the
  draft→active boundary and raises `BlackboardNeedsSynthesis`. The new validate
  check should **reuse the same helper** (single source of truth) rather than
  reimplement the heuristic. Do **not** change the mark.py refusal — validate is
  additive.
- **The skill to edit** is `bootstrap/ticket`. Two copies must stay in sync
  (see CLAUDE.md): the live repo copy
  `coga/bootstrap/skills/bootstrap/ticket/SKILL.md` and the packaged copy
  `src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md`.
  The relevant region is step 6 ("Run the evaluator review") through step 7
  ("Show the summary…"); the clear happens after the human confirms. **Note:
  the two copies already differ on disk today** (`diff -q` reports them
  non-identical) — diff and reconcile both deliberately before editing, don't
  assume they start in lockstep.
- **Tests:** `tests/test_validate.py` (new finding), `tests/test_mark.py`
  (existing refusal must stay intact), `tests/test_blackboard.py` (helper).
- **validate finding infra:** `src/coga/validate.py` already emits blackboard
  findings (e.g. `kind="large-blackboard"` at line 318) and has a `--fix` path;
  add the new finding as flag-only, consistent with the size-warning finding.
- **Resolved design decision (fold-then-clear):** the skill currently keeps the
  evaluator review in the blackboard so the human can re-read it. The decision
  for this ticket is to **synthesize the review into the ticket body before
  clearing** (not accept git-only retention, not skip the clear). So the
  ordering is: human confirms step-7 summary → skill folds review substance into
  `## Context`/body → skill resets blackboard to stock → human then edits the
  body as desired. The synthesis should be a faithful fold, not a verbatim dump
  of the whole review. Note this partly neuters the `mark.py` synthesis refusal
  for the bootstrap path (the draft now hands back already-synthesized) — that
  is intended; leave the mark.py backstop in place for non-bootstrap tickets.

**Out of scope:** changing mark.py's refusal; adding `--fix` auto-clear to
validate; the deferred "every ticket resets its blackboard at `done`" idea
(this ticket is bootstrap-flow-only cleanup).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: codex/ticket-blackboard-fold
worktree: /tmp/coga-ticket-blackboard-fold
commit: 999ccf48 Flag unsynthesized draft blackboards
pr: https://github.com/FastJVM/coga/pull/524

## Implementation

- `bootstrap/ticket` now tells the authoring agent to summarize durable evaluator findings in the step-7 summary, wait for confirmation, fold evaluator/proposal/authoring notes into the ticket body, and reset the blackboard to stock before printing the closing line.
- `coga validate` now emits warn-only `unsynthesized-draft-blackboard` findings for `status: draft` tickets whose blackboard trips `prelaunch_blackboard_synthesis_reason()`. It skips non-draft tickets and preserves the existing `## Production notes` opt-out. No `--fix` mutation was added.
- Existing live/package `bootstrap/ticket` copy differences around package bootstrap discovery were preserved; the new cleanup text was added to both copies.

## Verification

- `PYTHONPATH=/tmp/coga-ticket-blackboard-fold/src python3.12 -m pytest tests/test_validate.py tests/test_mark.py tests/test_blackboard.py` -> 78 passed.
- `PYTHONPATH=/tmp/coga-ticket-blackboard-fold/src python3.12 -m pytest` -> 1075 passed, 1 skipped.
- `PYTHONPATH=/tmp/coga-ticket-blackboard-fold/src python3.12 -m coga.cli validate --json` from `example/coga` -> ok_count 1, no issues.

## Peer review

- Codex review found one must-fix: the cleanup wording could reset useful blackboard state when editing non-draft tickets. Fixed in feature commit dcf7e00c by making full stock reset draft-only, preserving unrelated non-draft blackboard content, and adding a packaged-template regression assertion.
- Verification after the peer-review fix: `PYTHONPATH=/tmp/coga-ticket-blackboard-fold/src python3.12 -m pytest tests/test_bootstrap_ticket_skill_template.py tests/test_validate.py tests/test_mark.py tests/test_blackboard.py` -> 82 passed; `PYTHONPATH=/tmp/coga-ticket-blackboard-fold/src python3.12 -m pytest` -> 1076 passed, 1 skipped; `PYTHONPATH=/tmp/coga-ticket-blackboard-fold/src python3.12 -m coga.cli validate --task ticket-must-merge-blackblaord --json` -> ok_count 1, no issues.

## Open PR

- PR: https://github.com/FastJVM/coga/pull/524
- Preflight: `coga validate --check-github` succeeded for GitHub/auth freshness after unsandboxing (no GitHub/freshness errors), but raw repo-wide validation still exits nonzero on pre-existing unrelated task drift; `--check-github` cannot be combined with `--task`.
- CI: `gh pr checks 524` reported no checks on the branch yet.
