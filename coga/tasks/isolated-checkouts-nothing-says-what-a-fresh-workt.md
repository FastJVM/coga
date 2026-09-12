---
title: 'Isolated checkouts: nothing says what a fresh worktree lacks'
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

Record, in the contexts agents actually read, what a fresh linked worktree or
`/tmp` clone does **not** have — so that creating one stops being a trial-and-error
step that fails on the first mutating command.

Two related gaps, found by Dream 2026-W36 Phase 2 (shards `ks-01` and `ks-04`) from
five independent tickets.

**a. The `coga.local.toml` step is missing from both documents that tell an agent to
create a checkout.** `coga/contexts/dev/code/SKILL.md` ("Checkout boundary") and
`coga/skills/code/implement/SKILL.md` (step 3 and the `/tmp` fallback) each instruct
the agent to create a linked worktree or an independent `git clone --no-hardlinks`.
Neither mentions that `coga/coga.local.toml` is gitignored and therefore absent in
the new checkout, so the next mutating Coga command fails with exit 2 before doing
anything.

**b. Nothing states what else a fresh worktree lacks**, so every design in the
"run recurring from somewhere other than the operator's checkout" family re-derives
the same facts.

Deliverable: a short subsection under `dev/code`'s "Checkout boundary" (mirrored to
the packaged copy and to `code/implement`) giving the config-copy rule the three
existing precedents already follow — ordinary-copy the primary checkout's
`coga.local.toml` to the same repo-relative path, mode 0600, never symlink, stage or
commit it, and remove it with a disposable checkout — plus a "what a linked worktree
does not have" block in `coga/contexts/coga/codebase/SKILL.md`'s existing
`### Which checkout you invoke coga from` section.

Deciding *where* each half lands, and whether the codebase block belongs there or in
`dev/code`, is the design judgment this ticket exists for.

## Context

Citations name symbols and files, not line numbers.

**Evidence for (a).** Two tickets hit it as a live dead end:

- `coga/tasks/v2/auto-persist-dirty-launch-worktrees-to-pushed-bran.md` records in
  its blackboard that "task-scoped validation, `coga bump ...`, and `coga block ...`
  all failed before running because this launch checkout has no
  `coga/coga.local.toml` user configured".
- `coga/tasks/v2/propagate-local-coga-config-into-worktrees.md` names the same defect
  and lists three places that already work around it ad hoc: the live and packaged
  `recurring/dream/ticket.md`, the packaged `skills/retro/done-ticket/SKILL.md`, and
  `src/coga/resources/retire.md` — each of which requires an ordinary copy.

Grep confirms no context under `coga/contexts/` outside `secrets`, `codebase`, `sync`,
`architecture` and `recurring` mentions `coga.local.toml` at all, and neither of the
two checkout-creating documents does.

`v2/propagate-local-coga-config-into-worktrees` covers the **command-side**
enforcement (making Coga propagate the config itself). This ticket is the missing
**written convention** agents read today; the two are complements, and whoever picks
this up should check whether the other has landed first.

**Evidence for (b).** Three tickets re-derive the same worktree facts:

- `coga/tasks/service-recurring-from-a-temp-control-worktree-ins.md` records under its
  design notes that `coga.local.toml` is gitignored so any fresh worktree has no
  `user` and `load_config` raises before the scan starts — "seeding the copy is not a
  nicety, the feature does not run without it".
- `coga/tasks/reuse-the-existing-control-worktree-for-recurring.md` filed the identical
  fact later as `### Blocker found: the relayed child cannot load machine-local
  config`, verified against this repo's own linked worktrees (none carries the file),
  and had to escalate to the human for a resolution (a `COGA_LOCAL_CONFIG` env
  handoff).
- `coga/tasks/run-recurring-agent-templates-off-the-control-bran.md` restates it a
  third time under `### Worktree hygiene facts`, extends it to `.coga/` and
  `.agent-skills/`, and explicitly voids the second ticket's reasoning about
  `.agent-skills/` not being needed.

Two further facts are re-derived across the same tickets with no home:

- git refuses to check one branch out twice — simultaneously the concurrency lock in
  the temp-worktree design and the reason a create-only design cannot serve the layout
  Coga recommends;
- `git.sync_log` plus `_sync_recurring_create_paths` refuse to publish from a detached
  HEAD, which is what forces a worktree to have control checked *out* rather than
  `--detach`.

Which gitignored paths self-heal matters: `.agent-skills/` is rebuilt by launch, while
`coga.local.toml`'s absence hard-errors `load_config(require_user=True)`.

`coga/contexts/coga/codebase/SKILL.md`'s `### Which checkout you invoke coga from`
section already covers the inverse hazards (a feature worktree sweeping `coga/` edits
onto control; launch composing from the invoking checkout) but says nothing about what
a fresh or linked worktree is *missing*.

Candidate contexts to attach at design time: `coga/codebase`, `dev/code`. Both are
large; copy the needed facts rather than attaching wholesale if prompt size matters.

Filed by Dream 2026-W36, Phase 2 knowledge scan (shards `ks-01`, `ks-04`), classified
`gap`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: fresh-checkout-lacks
worktree: /home/n/Code/claude/coga-fresh-checkout-lacks

## Implement — 2026-09-11

**Design decision (the split the ticket asked for).** "What you must *do*"
lives in `dev/code` (a bootstrap context attached to every code ticket in any
repo); "what you must *know*" lives in `coga/codebase` (where the
recurring-from-a-worktree designers already read). Putting `git.sync_log`
internals in `dev/code` would bloat a generic context; putting the copy rule
only in `coga/codebase` would hide it from the agents that create checkouts.

**Landed (commit `bdc1534e`, six files, all packaged twins byte-identical):**

- `coga/contexts/dev/code/SKILL.md` — new `### Seed the machine-local config`
  subsection under "Checkout boundary", between the `/tmp` fallback paragraph
  and "Keep the feature checkout durable": exit-2 symptom, when the copy is
  needed at all (never in the two standard layouts), the copy rule, and the
  retire consequence.
- `coga/skills/code/implement/SKILL.md` — one paragraph at the end of step 3's
  fallback block pointing at that rule; no second copy of it.
- `coga/contexts/coga/codebase/SKILL.md` — new bullet block closing
  `### Which checkout you invoke coga from`: per-path failure mode
  (`coga.local.toml` hard error / `.agent-skills/` self-heals / `.coga/` on
  demand / `.venv`, `.env*`, `.secrets/` not needed), one-branch-one-checkout,
  detached-HEAD sync refusal.

**Facts verified in source before writing (symbols, not line numbers):**

- `config.load_config(require_user=True)` raises `ConfigError`; `cli` exits 2.
  Read-only surfaces per the comment in `load_config`: `status`, `show`,
  `validate`, `usage`, `skill status`, `recurring list`, `secret get`.
- No `COGA_LOCAL_CONFIG` / `COGA_USER` env override exists in `src/coga/` —
  the env handoff the reuse-the-existing-control-worktree ticket asked for
  never landed. `v2/propagate-local-coga-config-into-worktrees` is `draft`
  (v2 is off the execution path), so the written convention is the only
  mechanism today.
- Fourth precedent, in code: `recurring_runner`'s temporary control worktree
  does `shutil.copyfile` + `chmod(0o600)` into the mirrored Coga OS dir. That
  is the source for the 0600 rule.
- `branchcleanup.REGENERABLE_IGNORED_DIRS` = `__pycache__`, `.pytest_cache`,
  `.ruff_cache`, `.mypy_cache` only → a copied `coga.local.toml` or a
  launch-rebuilt `.agent-skills/` left in a feature worktree makes
  `coga retire` refuse. Documented as a consequence in both contexts.
- `.agent-skills/`: `commands.init` builds, `launch._refresh_agent_skills_for_launch`
  rebuilds. `.coga/`: `recurring-runs/` (`recurring_autofix`, `recurring_runner`),
  `megalaunch-selection.json` (`megalaunch`); `_persist_control_worktree_run_logs`
  moves temp-worktree ledgers back.
- `git.sync_log` docstring: detached HEAD → skip local commit, still land
  task dir on control. `recurring_runner` docstring: that is why the temp
  worktree checks control *out* and why `git worktree add` doubles as the
  concurrency lock.

**Testing.** `PYTHONPATH=$PWD/src .venv/bin/python -m pytest` from the feature
worktree: 2435 passed. (`python3` on this machine is 3.9 and the uv-tool
interpreter lacks pytest — the primary checkout's `.venv` is the one that works;
`coga/codebase` "Daily commands" already warns about the interpreter.)
`test_packaging.py` twin check passes with the three bootstrap copies synced.

**Adjacent observation, not fixed here.** `coga/codebase` "Daily commands" says
`python -m pytest` from a feature worktree imports the primary checkout's
package via the editable `.pth`. `pyproject.toml` sets
`[tool.pytest.ini_options] pythonpath = ["src"]`, which prepends the
worktree's own `src` — so the plain command may already resolve correctly and
the `PYTHONPATH` advice may be belt-and-braces rather than required. Not
verified end-to-end (would need a deliberate divergence between checkouts);
left the existing text alone and used the explicit `PYTHONPATH` spelling.

## Peer review

2026-09-11 — **`codex review --base main` returned, exit 0**, from the recorded
feature worktree. The sandboxed invocation could not initialize its app-server
(read-only filesystem); the unsandboxed retry completed. It reported two P2
findings:

- Missing local config refuses the requested action but is not a no-write
  guarantee. `cli.main` still calls `_sweep_coga_state` after ordinary failures,
  loading with `require_user=False`. The reviewer reproduced `coga bump missing`
  exiting 2 while publishing a dirty context onto a temporary repository's
  `origin/main`. Keep the pre-command commit requirement in the copy guidance.
- Detached HEAD is not a blanket publication refusal. `git.sync_log` refuses
  its narrow log publication, but `sync_task_state` and `sync_coga_state` can
  publish state and union-merge logs; strict lifecycle publishers can create
  scoped detached commits. Recurring admission requires control checked out.
  `_sync_recurring_create_paths` skips its detached local commit, while
  `_land_recurring_create_on_control_branch` still lands the task and period
  ledger. The implementation note's broader detached-HEAD inference is stale.

Source checks confirm the config-copy and retire rules; the propagation
companion remains draft. The attending human approved both corrections. Applied
them in `dev/code` and `coga/codebase`, preserving the original documentation
split, and synchronized their packaged twins. The `code/implement` pointer
continues to use the corrected `dev/code` rule. All three pairs are byte-identical.
Committed as `d4f754ee` (`peer-review: correct checkout publication guidance`).

**Freshness.** Ran `git fetch origin main` followed by `git rebase FETCH_HEAD`
unconditionally in the feature worktree. Rebase completed without conflicts on
`525fa025`; implementation commit is now `8a60bbcc`. Repeated fetch/rebase after
the approved fix commit: already up to date. The feature worktree is clean,
with two commits ahead of `origin/main` and no remaining must-fix findings.

**Validation.** The full post-fix suite passed: **2435 passed in 171.02s**,
including packaging/twin checks, using the feature checkout's source and the
primary checkout's Python 3.12 interpreter (exact command under `## PR`).
`git diff --check main...HEAD` passed in the feature worktree.
`coga validate --task isolated-checkouts-nothing-says-what-a-fresh-workt`
passed from the primary checkout: `All good (1 tasks checked).`

Peer review is complete. The next action is the single workflow bump from the
primary checkout; the PR body below is ready for the mechanical open-pr step.

## PR

Fresh linked worktrees and fallback clones omit gitignored Coga config and
generated state. Document the ordinary-copy, mode 0600, and cleanup rule in
`dev/code`, reference it from `code/implement`, and explain omitted state and Git
checkout constraints in `coga/codebase`. The guidance accounts for the exit
sweep after missing-config failures and distinguishes recurring admission from
detached publication; all packaged twins are synchronized.

Test plan: `PYTHONPATH=/home/n/Code/claude/coga-fresh-checkout-lacks/src /home/n/Code/claude/coga/.venv/bin/python -m pytest` (2435 passed); `git diff --check main...HEAD` (passed); `coga validate --task isolated-checkouts-nothing-says-what-a-fresh-workt` (1 task passed).
