---
title: Recurring context never mentions the packaged twin every template has
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
---

## Description

`coga/contexts/coga/recurring/SKILL.md` is what a recurring-template author reads, and
it never tells them the template they are editing has a packaged twin.

All seven templates under `coga/recurring/` have a counterpart under
`src/coga/resources/templates/coga/recurring/`, but grepping the recurring context for
`packaged`, `twin`, `mirror` or `resources/templates` returns nothing.

This matters more than an ordinary doc gap because **a recurring template body is
composed verbatim as the spawned task's `## Description`** — drift between the copies
changes the run prompt in every downstream repo after `coga init --update`.

Deliverable, two parts:

1. A twin-sync note in `coga/contexts/coga/recurring/SKILL.md` telling template authors
   the twin exists, where it is, and why drift is expensive.
2. A statement in `coga/contexts/coga/codebase/SKILL.md` of the principle governing
   **which** twins must be registered in `IDENTICAL_LIVE_PACKAGED_PAIRS` — that list
   currently covers only pairs someone remembered to add, and the context frames the
   hazard as rebase-specific.

Part 2 is the design judgment: deciding the registration rule (all twins? only those a
composed prompt depends on?) is what needs a human, and it determines whether this also
warrants extending the test.

## Context

Citations name symbols and files, not line numbers.

**Three tickets circle the same unenforced problem:**

- `coga/tasks/live-and-packaged-twin-pairs-are-edited-together-b.md` records that
  `IDENTICAL_LIVE_PACKAGED_PAIRS` enforces only a registered subset, and that two Dream
  Phase 6 PRs (#719, #721) each hit an unenforced pair in a single run.
- `coga/tasks/v2/document-recurring-template-live-vs-packaged-sync.md` asks specifically
  for a Gotchas bullet in the recurring context — this ticket supersedes it, and that
  draft should be folded in or canceled rather than worked separately.
- `coga/tasks/guard-the-browser-dochub-and-playwright-live-vs-pa.md` names one further
  unenforced pair.

**Verified on 2026-09-02:** `coga/recurring/` holds seven templates — `autoclose-merged`,
`blocker-reminders`, `branch-sweep`, `digest`, `dream`, `resolve-conflicts`,
`skill-update` — and each has a packaged twin under
`src/coga/resources/templates/coga/recurring/`. Of those, the enforced pair list
registers the five `ticket.py` files and `coga/recurring/dream/ticket.md`, but not the
other `ticket.md` bodies.

**Partial existing coverage:** `coga/contexts/coga/codebase/SKILL.md` carries a
rebase-hazard bullet that does state `IDENTICAL_LIVE_PACKAGED_PAIRS` "only covers pairs
someone remembered to register" — but it frames the hazard as rebase-specific and names
no rule for what must be registered.

Dream 2026-W36's own Phase 3 copy-divergence shard (`ca-06`) compared every registered
pair and the seven recurring template pairs and found **zero** divergence today, so this
is a preventive fix, not a repair.

`coga/contexts/coga/codebase/SKILL.md` is an enforced twin — edit both copies.
`coga/contexts/coga/recurring/SKILL.md` is 47 KB and has no packaged twin; check before
assuming.

Filed by Dream 2026-W36, Phase 2 knowledge scan (shard `ks-11`), classified `gap`.

<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/792
branch: recurring-twin-note
worktree: /home/n/Code/claude/coga-recurring-twin-note

## Implement (2026-09-12)

**Part 1 — done.** One Gotchas bullet added to `coga/contexts/coga/recurring/SKILL.md`
(bold lead, matching the neighbouring bullets): every `coga/recurring/<name>/` template
has a packaged twin under `src/coga/resources/templates/coga/recurring/<name>/`; the
packaged copy is what a fresh `coga init` ships and nothing refreshes it afterwards; the
`ticket.md` body is the run prompt, so drift changes what a downstream repo runs; the
same goes for `ticket.py`; `tests/test_packaging.py` enforces byte-identity; pointer to
`coga/codebase` for the rule and the rebase hazard. Commit `edc7e8af`.

The recurring context now *has* a packaged twin
(`src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md`) —
the ticket's "no packaged twin" note is stale — so the bullet went into both copies.

**Part 2 — already satisfied by other work; no edit.** The registration rule the ticket
asks for has been decided mechanically: `tests/test_packaging.py` derives
`IDENTICAL_LIVE_PACKAGED_PAIRS` from the packaged tree (every packaged file with a live
counterpart under `templates/coga/<path>` -> `coga/<path>` or
`templates/coga/bootstrap/{contexts,skills,workflows}/<path>` -> `coga/<area>/<path>`
must be byte-identical; only exceptions are registered, in
`INTENTIONALLY_DIVERGENT_TWINS`, and a stale exception fails the suite). The
`coga/codebase` context states exactly that in its rebase-hazard bullet ("a new twin is
covered the moment it exists and there is nothing to register") and CLAUDE.md repeats
it. Landed via `live-and-packaged-twin-pairs-are-edited-together-b` (status: done). So
"all twins" is the answer and no test extension is needed. Left the statement inside the
rebase bullet rather than lifting it into a standalone principle — agreed with the
operator as acceptable given CLAUDE.md carries it prominently.

**Superseded draft:** `v2/document-recurring-template-live-vs-packaged-sync` canceled
via `coga mark canceled` on `main` (commit `63185f0a`) with the reason recorded in
`coga/log.md`.

**Ticket facts that moved since filing:** six templates, not seven (`digest` removed);
`coga init --update` no longer exists (`docs/cli-extension-external-surface.md`), which
makes drift worse, not better — a repo initialized while the copies differ never gets a
refresh. The bullet is worded against the current shape.

**Verification:** `.venv/bin/python -m pytest` in the feature worktree — 2435 passed.
`diff -q` of the two recurring context copies — identical. Branch rebased on
`origin/main` (already up to date). No push, no PR.

## Peer review

`codex review --base main` ran from the recorded feature worktree and **returned**
on 2026-09-12 with no actionable findings. Both changed context copies remain
synchronized. The review's 10 non-wheel packaging checks passed; its wheel test
could not build because the default Python environment lacks `hatchling`.
No review-fix commit is needed.

Ran `git fetch origin main` then `git rebase FETCH_HEAD` in the feature worktree.
Rebase completed without conflicts onto `037f987d`; the branch's one commit is
now `c16e34cf`. The two reviewed files are unchanged by the rebase, `diff -q`
confirms the twins are identical, and `git diff --check origin/main...HEAD` passes.
The full suite **passed: 2435 tests in 171.30s**, including the wheel build, with
the primary checkout's Python 3.12 test environment (which has `hatchling`) and
an absolute `PYTHONPATH` naming the feature source. Exact command is in `## PR`.
The feature worktree is clean and committed, one commit ahead of fetched `main`;
no feature push or PR was opened in this step. Ready for the `open-pr` handoff.

## PR

Recurring-template authors lacked a reminder to update the packaged copy shipped
by `coga init`. Add the twin locations, explain how drift changes downstream run
instructions and scripts, and point to the existing all-twin packaging checks in
both copies of the recurring context.

Test plan: `PYTHONPATH=/home/n/Code/claude/coga-recurring-twin-note/src /home/n/Code/claude/coga/.venv/bin/python -m pytest` — 2435 passed, including wheel packaging.
