---
slug: trim-blackboard-eval-once-processed
title: trim blackboard eval once processed
status: in_progress
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- coga/codebase
skills: []
workflow:
  name: dev/with-self-review
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
  - name: review
    skills: []
    assignee: owner
secrets: null
step: 3 (pr)
---

## Description

When a ticket is marked active ("ready for launch"), mechanically strip
one-time scratch sections from its blackboard region so they stop being
composed into every future launch prompt. The primary target is the
`## Evaluator review` section that `bootstrap/ticket` writes during
authoring — verbatim evaluator prose the human reads once at approval and
never needs again, yet it currently rides along in every launch prompt and
counts against the blackboard size budget.

The trim is a deterministic section-delete of a known heading list, not an
agent judgment pass. It fires at the `draft → active` transition, which is
exactly the "once processed / ready for launch" boundary. Git history is
the recovery backstop for anything removed.

## Context

**Design decision (settled in the bootstrap interview):** mechanical strip
at `mark_active`, not agent judgment. `coga mark active` is pure Python with
no agent in the loop, so judgment can't live there; and putting judgment
inside a state-transition command would cut against coga's split (mechanical
CLI owns state transitions, agents do judgment). A judgment-based pass over
arbitrary stale notes, if ever wanted, is a separate bootstrap-step ticket.

**Where to hook it:** `src/coga/mark.py` `mark_active` (~mark.py:219-250).
It already freezes the workflow, validates extensions, rewrites the ticket,
and git-syncs — adding the trim there covers both `coga mark active`
(`commands/mark.py:active`) and `coga launch`'s `_auto_activate`
(`launch.py:498`) in one place. An already-active/in_progress ticket
launched directly bypasses `_auto_activate` and so is not re-trimmed — that
matches the "once, at the readiness transition" semantics.

**Primitives to use** (all in `src/coga/`):
- `taskfile.read_blackboard` / `replace_blackboard` (`taskfile.py:122`,
  `taskfile.py:147`) — read the region below the `<!-- coga:blackboard -->`
  fence and byte-splice a replacement, preserving frontmatter + body
  verbatim. Operate ONLY on the region below the fence.
- `blackboard.py` already has section-aware machinery (`_SECTION_RE`,
  `append_to_section_text` at `blackboard.py:29-60`). Add a section-DELETE
  helper here (parallel to the existing append helpers) and unit-test it
  directly. Nothing in the codebase trims/section-deletes the blackboard
  today — this is net-new.

**Heading list to strip:** start with `## Evaluator review`. Consider also
dropping a resolved `## Proposals` section if present — confirm scope in the
implement step; default to just `## Evaluator review` if unsure, and make the
list easy to extend (a module-level constant, not scattered literals).

**Safety / no-op behavior:** when none of the target headings are present
(ticket never went through bootstrap, recurring/period templates, etc.) the
trim must be a clean no-op — do not alter the blackboard, do not reformat
surrounding sections, and round-trip cleanly with `replace_blackboard`.
Two correctness traps the evaluator flagged (handle both, with tests):
- **Fence-less tickets throw.** `read_blackboard` defaults to
  `blackboard_required=True` and raises `TaskFileError` on a ticket with no
  `<!-- coga:blackboard -->` fence. Guard the trim the same way
  `blackboard_size_warning` does — `try/except (FileNotFoundError,
  TaskFileError)` and treat as no-op — or pass `blackboard_required=False`.
- **Orphan separators.** Deleting a mid-blackboard section must not leave a
  dangling `---` divider; mirror the separator handling
  `append_to_section_text` already does (`blackboard.py:48-52`). Cover the
  "section between two others" case in tests.

Note `mark_active` fires on `draft→active` *and* `paused→active`, so the trim
is "idempotent no-op after first run," not literally once — fine, but design
it to be safely re-runnable. And the recurring/period parent `ticket.md` is
itself a blackboard holding `state_keys` high-water marks: keep the strip
list scoped to authoring artifacts (`## Evaluator review`) so it can never
touch state-bearing headings.

**Where the eval section comes from:** authored by the bootstrap skill, not
code — `src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md`
Step 6 (~line 278): "Write the evaluator's response ... under a top-level
`## Evaluator review` section, verbatim."

**Prior art to mirror:** the existing `blackboard.blackboard_size_warning`
(`blackboard.py:87`, 32 KiB warn) is the same "blackboard region is included
in launch prompts" concern this ticket reduces — a useful reference for tone
and the size budget being protected.

**Tests:** add `tests/` coverage for the new section-delete helper and for
`mark_active` stripping `## Evaluator review` on the active transition (and
no-op when absent). Run `python -m pytest` and `coga validate --json`.

**Out of scope:** agent-judgment trimming of arbitrary notes; trimming at
launch-time of already-active tickets; changing the size-warning threshold.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

**Cold-read critique — trim-blackboard-eval-once-processed**

- **Clarity: strong.** A no-context agent could start immediately. Hook point, primitives, heading list, no-op contract, test targets, and out-of-scope are all spelled out. Rare for a draft.
- **Workflow fit: good.** `dev/with-self-review` suits a small mechanical helper + unit tests; no mismatch.
- **Hook point: correct.** Both `commands/mark.py:active` (line 41) and `_auto_activate` (`commands/launch.py:498`) route through the core `mark_active` (`mark.py:219`), so trimming there covers both, as claimed. Confirmed.
- **Line pointers: mostly accurate**, two nits: `launch.py:498` is really `src/coga/commands/launch.py:498` (path omits `commands/`); bootstrap Step 6 is line 279, not ~278. Harmless.
- **Real gap in the no-op claim.** The ticket frames no-op purely around *heading absence*, but `read_blackboard` (default `blackboard_required=True`) **raises `TaskFileError` on a fence-less ticket** — and bootstrap tickets have no fence. If `mark_active` ever runs on one, the trim throws. Mirror `blackboard_size_warning`'s `try/except (FileNotFoundError, TaskFileError)` guard; the ticket doesn't mention this.
- **"Once at the transition" is loose.** `mark_active` fires on every `draft→active` *and* `paused→active`; the trim runs each time (idempotent no-op after first). Fine, but it's "idempotent," not literally once.
- **Separator handling underspecified.** Deleting a mid-blackboard section risks leaving an orphan `---` divider — the existing `append_to_section_text` already wrestles with these separators (`blackboard.py:48-52`); the delete helper must too. Call this out as a test case.
- **Question before launch:** the `## Proposals` ambiguity is the only scope-creep vector; defaulting to just `## Evaluator review` is the right call. Also note the recurring parent `ticket.md` is itself a blackboard holding `state_keys` high-water marks — confirm the trim never names a heading that could touch that.

## Dev

branch: trim-blackboard-eval
worktree: /tmp/coga-trim-blackboard-eval

Decision: trim only `## Evaluator review` at activation. Durable launch data belongs in the ticket body; the blackboard can still hold transient operational handoff notes like this `## Dev` section.

Implemented in commit `3eaf167b` (`Trim processed blackboard eval on activation`).

Changed:
- Added `blackboard.delete_sections_text` / `delete_sections` for top-level `##` blackboard section deletion with separator cleanup and fence-less no-op support.
- Hooked `mark_active` to remove processed activation scratch after the frontmatter write and before validation/git sync.
- Updated live + packaged `coga/architecture` context to document activation cleanup.

Verification:
- `python -m pytest tests/test_blackboard.py tests/test_mark.py` passed: 33 passed.
- `python -m pytest` passed: 919 passed, 1 skipped.
- `PYTHONPATH=/tmp/coga-trim-blackboard-eval/src python -m coga.cli validate --task trim-blackboard-eval-once-processed --json` passed.
- Repo-wide `PYTHONPATH=/tmp/coga-trim-blackboard-eval/src python -m coga.cli validate --json` still fails on pre-existing unrelated task issues (`install/*`, `marketing/*`, `v2/*`, plus stale in-progress warnings); not changed by this branch.

## Self-QA

No findings — both passes came back clean against `trim-blackboard-eval` vs `main`.

- `/code-review` (high effort): no confirmed bugs. Verified the trim is committed (`mark_active` runs the trim at `mark.py:263` before `git.sync_task_state` at `mark.py:268`), no stale in-memory rewrite, separator handling round-trips (middle/orphan/absent cases), fence-less no-op guard holds, and `Iterable` is consumed once. The one candidate considered — deletion stopping at a `## ` line embedded in verbatim evaluator prose — was refuted: it's governed by the same pre-existing `_SECTION_RE` section model, so the diff introduces no new failure mode.
- `/simplify`: code already clean. Reuse (net-new section delete, reuses `_SECTION_RE`), simplification (no derivable/dead state), efficiency (runs once off any hot path), and altitude (generic `delete_sections` + module constant, not a buried literal) all pass. No edits applied.
- Tests re-run with 3.12: focused `test_blackboard.py`+`test_mark.py` 33 passed; full suite 919 passed, 1 skipped; `validate --task` clean. Working tree clean — no QA commit needed.

## Usage

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":3169792,"cli":"codex","input_tokens":324657,"model":"gpt-5.5","output_tokens":25263,"provider":"openai","schema":1,"session_id":"019f16f3-ca68-74e3-94bf-302f47bc13ab","slug":"trim-blackboard-eval-once-processed","step":"implement","title":"trim blackboard eval once processed","ts":"2026-06-30T18:18:48.444170Z","usage_status":"ok"}
