---
title: Adjudicate parked and active tickets whose premises have moved
status: done
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
---

## Description

Dream's knowledge scan found eleven tickets whose stated premise no longer
matches the repo. Each needs a verdict — rewrite, narrow, cancel with a reason,
or close as done-by-other-means — and none of them is a context edit, which is
why they are collected here rather than in a proposal PR.

**Premise-dead parked drafts** (the subject or surface no longer exists):
- `v2/pass-secrets-to-skills-with-per-skill-scope` — the `[secrets]`
  bulk-inject model it is entirely about now fails loud in `src/coga/config.py`
  ("no longer supported. Secrets are now declared inline on each ticket's
  `secrets:` frontmatter"). The residue worth preserving in a cancellation is
  the finer ask: per-*skill* rather than per-ticket scope, and the
  agent-versus-script-mode asymmetry.
- `v2/audit-rules-md-usage-across-relay-and-decide-wheth` — audits a "Global
  rules" prompt layer, `coga/rules.md`, a `rules_path()` and a `compose.py`
  rules layer, none of which exist anywhere in the repo. Its "Known facts
  (verified — do not re-derive)" block is now confidently wrong.
- `v2/file-locking-for-concurrent-task-mutation` — its central evidence is that
  "no mutual-exclusion primitive exists" and that `fcntl` appears once, for an
  ioctl. `src/coga/git.py` now takes a real `fcntl.flock(LOCK_EX)` / `LOCK_UN`
  pair, and the architecture context describes the worktree branch checkout as
  doubling as the concurrency lock.
- `v2/debug-surface-for-recurring-tasks-streamed-output` — built entirely on the
  template `mode:` field, which appears zero times in the recurring context
  (determinism is now selected by the reserved `ticket.py` sibling), and depends
  on a ticket `enforce-mode-auto-for-recurring-templates` that does not exist.
- `v2/wire-recurring-sweep-into-system-cron` — asserts "the cron entry point
  already ships — `relay-os/scripts/cron.sh`"; no `cron.sh` exists anywhere.

The last two are **not** in the cohort of `adjudicate-the-eight-premise-dead-v2-drafts`,
so nothing currently routes them.

**Parked drafts whose deliverable already shipped:**
- `v2/document-workflow-less-concept-capture-drafts-as-s` — asks for
  architecture prose that `coga/contexts/coga/architecture/SKILL.md` now
  carries; the sibling it names is gone from `coga/tasks/` entirely.
- `v2/overload-ticket-locally-easily` — both halves landed in architecture and
  extension-model. Residue is one sentence: `coga ticket` injects a hardcoded
  `bootstrap/ticket` ref that an alias cannot redirect, so dropping a local
  `coga/skills/bootstrap/ticket/SKILL.md` substitutes your own interview.
- `v2/split-context-to-doc-user-accessible-and-editable` — the larger question
  it fences off as out of scope is live and past its design step in
  `redo-documentation-dir-and-merge-it-with-context-b`. Leaving it armed invites
  a narrow move against a design the owner is about to gate.
- `v2/docs-and-contt-block-should-be-merged` — empty description, empty context,
  no workflow; its title duplicates that same live ticket, which already
  classifies it as such.
- `v2/implement-accepted-ticket-interview-improvements` — routes the implementer
  to the "Ranked changes" section of a blackboard whose ticket no longer exists
  on disk, so the wording it defers to is reachable only through git history.

**An active ticket that is nearly discharged:**
- `vendored-skills-carry-no-coga-source-json-so-coga` (`status: active`, step 1)
  — its premise has moved from three directions. `.coga-source.json` now exists
  (`coga/skills/clarity/`); the skill-update template was rewritten with `gh`
  delegation in PR #743 *after* the ticket's last edit; and its "the twin is not
  in `IDENTICAL_LIVE_PACKAGED_PAIRS`" warning is false since twins are derived.
  Its only outstanding requirement is naming `ATTRIBUTION.md` / `NOTICE.txt` as
  the hand-vendored provenance substitute. Leaving it active advertises merged
  work.

## Context

Per `coga/tasks/v2/README.md`, the outcome for a premise-dead draft is a
cancellation **with a recorded reason** naming what replaced it, not a silent
delete and not a rewrite that preserves a dead frame.

**Guard, and it matters here:** a green `coga validate` is never a reason to
cancel a draft — it is a consequence of correct verdicts, never an input to
them. Two of the four standing `unsynthesized-draft-blackboard` errors sit on
drafts in this list, so ruling them dead is the cheapest route to a green gate.
Do not take it.

Re-verify each premise before ruling on it; these were checked on 2026-09-08 by
a scan shard, not by the person who will act.

Overlaps to reconcile rather than duplicate: `adjudicate-the-eight-premise-dead-v2-drafts`
(existing cohort — add the two strays rather than ruling them here if that
ticket is live), `interview-the-owner-on-the-17-title-only-v2-stubs`,
`correct-the-v2-known-stale-surfaces-table-and-rout`, and the sibling
`the-v2-parking-area-premise-check-has-four-holes`, which fixes the contract
that would have caught most of these earlier.

<!-- coga:blackboard -->

## Adjudication session 2026-09-16 (megalaunch queue, unattended)

Every premise below was re-verified against `main` in this session before any
verdict; the 2026-09-08 scan held on all eleven. Overlaps reconciled first:
`adjudicate-the-eight-premise-dead-v2-drafts` is still `draft` (not live), so
the two strays were ruled here rather than added to it, and its three
overlapping cohort members are ruled here too with a note left in its body;
`docs-and-contt` is left to `interview-the-owner-on-the-17-title-only-v2-stubs`,
which already carries it (row 5) at its owner gate. Lifecycle verdicts were
applied with `coga mark` on `main` from this checkout (irreversible; the
ticket's stated outcome for premise-dead drafts, same mechanics as
`four-parked-tickets-carry-premises-that-have-since`); prose verdicts ride the
PR. No draft was cancelled for the validate gate — `split-context` is the
proof: it sat on one of the four errors and was kept.

### Verdict table

| ticket | before | verdict | evidence | applied |
| --- | --- | --- | --- | --- |
| `v2/pass-secrets-to-skills-with-per-skill-scope` | draft | **cancel** | `config.py` refuses `[secrets]` with the "declare inline" error; `coga/secrets` is per-ticket `secrets:`; `ticket.py` and agent phases get the same declared set (architecture). Residue named: per-skill scope. | `mark canceled` on main |
| `v2/audit-rules-md-usage-across-relay-and-decide-wheth` | draft | **cancel** | `rules_path`, `rules.md`, "Global rules" absent from `src/`, `coga/`, `docs/`; only hit is the stale-artifact fixture in `tests/test_init.py`. | `mark canceled` |
| `v2/file-locking-for-concurrent-task-mutation` | draft | **cancel** | `git.state_publication_barrier` takes `fcntl.flock(LOCK_EX)`/`LOCK_UN` (tests in `test_git.py`); architecture: `git worktree add` doubles as the concurrency lock; residual window recorded in `coga/blackboard`; paired `atomic-writes-…` draft absent. | `mark canceled` |
| `v2/debug-surface-for-recurring-tasks-streamed-output` | draft | **cancel** | zero `mode:` in the recurring context; `enforce-mode-auto-…` absent from tasks and log; reqs 1–2 shipped by the REPL supervisor + `recurring launch --interactive`. Residue named: phase step-through. | `mark canceled` |
| `v2/wire-recurring-sweep-into-system-cron` | draft | **cancel** | no `cron.sh` anywhere; `docs/operations.md` "Point a single cron entry at `coga recurring`"; recurring context "operator-owned scheduler outside Coga"; `nightly-auto-drain` canceled. | `mark canceled` |
| `v2/document-workflow-less-concept-capture-drafts-as-s` | draft | **done by other means** | architecture "Workflow gated at activation, not draft time"; validator emits `active-no-workflow` only, no `missing-workflow`; sibling `resolve-missing-workflow-…` absent. | `mark active` → `mark done` |
| `v2/overload-ticket-locally-easily` | paused | **done by other means + residue** | architecture: local skills override bundled by ref, `coga ticket` injects `bootstrap/ticket`; extension-model: local-first override without core change. Residue sentence added to architecture (both twins) in this PR. | `mark active` → `mark done`; PR |
| `v2/split-context-to-doc-user-accessible-and-editable` | draft | **keep — rewrite + guard** | subject unbuilt: `paths.repo_context_path` still hardcodes `coga/context.md`, `compose.py` still emits the layer; #704 knob covers the contexts dir only; `redo-documentation` (step 3, owner gate) explicitly leaves it deferred. Body rewritten to current surfaces, blackboard synthesized to `## Production notes`, pull-forward guarded on that gate. | PR |
| `v2/docs-and-contt-block-should-be-merged` | draft | **defer execution to sibling** | title-only stub; README says only the author rules. The owner confirmed row 5's cancellation as a duplicate on 2026-09-13 in `interview-the-owner-on-the-17-title-only-v2-stubs`; that ticket is still at `review-design` and owns execution. No second ask or cancellation belongs here. | none |
| `v2/implement-accepted-ticket-interview-improvements` | paused | **rewrite pointer** | source ticket retired in `ffb0a383`; "Ranked changes" reachable via `git show ffb0a383^:…`; changes 2–4 still absent from the packaged skill, 5 shipped, 6 partly (name confirmation + Proposals present, the "needs that exact body" gate absent); `the-ticket-interview-never-asks-…` keeps only change 1. | PR |
| `vendored-skills-carry-no-coga-source-json-so-coga` | active, step 1 | **narrow** | `coga/skills/clarity/.coga-source.json` exists; template rewritten in #743/#776/#796/#804 (twins identical); `IDENTICAL_LIVE_PACKAGED_PAIRS` is derived, not a registry. Body narrowed to the one residue (name `ATTRIBUTION.md` / `NOTICE.txt`). Stays active for its own run. | PR |

### Decisions and notes for the reviewer

- Cancel reasons are in `coga/log.md` (2026-09-16), each naming what replaced
  the draft and any residue not carried forward.
- `overload-ticket` was marked done before its residue sentence merges; the
  closing log line names this PR as where the sentence lands. If the PR is
  rejected, that sentence is the only thing lost.
- `adjudicate-the-eight-premise-dead-v2-drafts` now expects to clear at most
  one validate error; its `unfrozen-workflow` warning is pre-existing.
- Repo-wide `coga validate` after this work: three `unsynthesized-draft-blackboard`
  errors remain (`autotrigger-ticket-type`, `measure-relay-prompt-scope…`,
  `use-worktree-when-starting-a-dev-task`), all owned by sibling tickets.
- Nothing here was decided from the slug alone or from the validate gate.

## Dev

pr: https://github.com/FastJVM/coga/pull/826
branch: adjudicate-moved-premises
worktree: /home/n/Code/claude/coga-adjudicate-moved-premises

One commit (`c3805432`, "Adjudicate parked tickets whose premises moved") on
top of `origin/main` `a6e54ba4`, which carries the nine lifecycle commits.
Peer review rebased the original `0da8ac09` with no conflicts; `git range-diff`
confirms the patch is unchanged. The feature worktree is clean and one commit
ahead of `origin/main`.

## Peer review

2026-09-16: `codex review --base main` **returned** (exit 0) from the recorded
feature worktree with no must-fix findings. Its focused suite passed all 220
tests. No review-fix commit was needed. Independently checked the local-first
authoring-skill resolution, the retired proposal's git-history pointer, the
repo-context relocation guard, and hand-vendored attribution. The explicit
skip instructions in the interview-improvements ticket preserve the original
numbered proposal's mapping without reopening change 1 or redoing change 5.
Corrected the `docs-and-contt` verdict row: the sibling already has the
owner's cancellation decision (2026-09-13), rather than an unanswered ask;
deferring its execution to that sibling is unchanged.
This diff changes ticket/context prose only; no terminal, pager, or rendered
notification surface requires an interaction check.

`git fetch origin main` and `git rebase FETCH_HEAD` completed successfully.
Post-rebase checks: all four edited tickets pass scoped validation (the
feature checkout's `missing-user` warning and the cohort draft's pre-existing
`unfrozen-workflow` warning remain); `git diff --check main...HEAD` is clean;
the architecture twins are byte-identical. Repo-wide `coga validate --json`
still reports only the three unrelated `unsynthesized-draft-blackboard`
errors named above. The full post-rebase suite,
`/home/n/Code/claude/coga/.venv/bin/python -m pytest`, **passed all 2561 tests**
in 173.21 seconds.

## PR

Refresh the surviving tickets after auditing eleven moved premises. Keep the
repo-context relocation deferred behind the documentation design review,
recover the accepted interview prompts from git history and identify shipped
changes, and narrow the active skill-update ticket to human-readable provenance.

Exclude already-ruled members from the sibling adjudication cohort's remaining
work and document the local `bootstrap/ticket` override in both architecture
copies. Five cancellations and two done-by-other-means verdicts are already
recorded on `main`; the title-only duplicate stays with the sibling ticket
that holds its owner's cancellation decision.

Test plan: `/home/n/Code/claude/coga/.venv/bin/python -m pytest` (2561 passed);
`coga validate --json` (three pre-existing draft-blackboard errors; all four
edited tickets also pass scoped validation); `git diff --check main...HEAD`
(clean). The live and packaged architecture copies are byte-identical.
