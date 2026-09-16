---
title: 'Dream 2026-W38 extract backlog: 4 findings Phase 4 could not consume'
status: in_progress
owner: nicktoper
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
agent: claude
---

## Description

Carrier ticket. Dream 2026-W38's knowledge scan classified four findings as extract, but every source ticket carries a real ## Dev branch and worktree (retirement debt, deliberately left on disk so the human-typed coga retire <slug> stays valid), so Phase 4 could not consume them. The full finding paragraphs are in this ticket's Context so they survive the Dream task's retirement.

## Context

Citations name symbols and files, not line numbers. Every source ticket below is
`status: done` and still on disk under `coga/tasks/` with a real `## Dev`
branch/worktree; `coga retire <slug>` would consume its evidence naturally, or
this ticket can land the knowledge in one or more knowledge PRs (group by
target: three items target `coga/codebase`, one targets `coga/sync`; keep live
and packaged twins byte-identical). A fifth W38 extract finding (Phase 4
progress receipts, source `dream-phases-2-3-cannot-complete-scan-subagents-re`)
is already implemented by open PR #795 item 16 and is not repeated here.

The routing hole that produces carrier tickets is tracked by
`dream-findings-have-three-routing-holes-that-lose` (PR #799).

### F-01 — target `coga/codebase` — source `live-and-packaged-twin-pairs-are-edited-together-b`

**CLAUDE.md/AGENTS.md are a hand-kept byte-identical twin with no test — record it beside the derived-twin rule.**

The done ticket `live-and-packaged-twin-pairs-are-edited-together-b` derived every live/packaged twin into `tests/test_packaging.py` and, under "Adjacent, not fixed here", recorded that `CLAUDE.md` and `AGENTS.md` are byte-identical twins with no test guarding them ("Same class of gap as this ticket, different root pair"). That is still repo reality: `cmp CLAUDE.md AGENTS.md` is identical today, no test under `tests/` names either file as a pair, and the in-progress ticket `the-human-doc-vs-agent-context-boundary-is-decided` independently had to check by hand that "`AGENTS.md`/`CLAUDE.md` still match byte-for-byte" after its rebase. `coga/contexts/coga/codebase/SKILL.md` (and its packaged twin) describes the derived twin discovery and `INTENTIONALLY_DIVERGENT_TWINS` in the "A rebase carries a fix through a rename" bullet but never mentions this root pair, so an agent editing one file has nothing telling it to edit the other. Add one sentence to that bullet: `CLAUDE.md` and `AGENTS.md` at the repo root are a third twin kept identical by hand — edit both and `cmp` them, since `test_packaging.py`'s discovery walks only the packaged template tree and never covers them.

### F-02 — target `coga/codebase` — source `cleanup/add-a-debug-mode-to-init-for-vendoring-from-source`

**Record the developer CLI install model: `coga` is a uv-tool editable install whose interpreter is not the ambient `python`.**

The done ticket `cleanup/add-a-debug-mode-to-init-for-vendoring-from-source` (PR #759, later re-scoped to delete the vendored venv outright) verified and recorded the install model every Coga developer actually runs, and nothing in `coga/contexts/coga/codebase/SKILL.md` carries it: neither dev checkout has a vendored venv; the `coga` on PATH is the global uv tool editable install (`~/.local/bin/coga` → `~/.local/share/uv/tools/coga/bin/coga`, with `direct_url.json` `{"url":"file:///home/n/Code/claude/coga","dir_info":{"editable":true}}` pointing at one checkout), so running `coga` from the *other* checkout executes the claude checkout's source — the silent wrong-bytes bug that started the ticket. The same fact bit the in-progress `make-sure-repo-clietn-don-t-edit-coga` design independently: its evaluator found the ticket's `python - <<'PY' ... from importlib.resources import files("coga.resources")` block fails with `ModuleNotFoundError` under the ambient `python` and only works under `/home/n/.local/share/uv/tools/coga/bin/python`. Re-verified now: that interpreter imports `/home/n/Code/claude/coga/src/coga/__init__.py` on Python 3.12, while ambient `python3` is 3.9. The codebase context's "Daily commands" already says "reinstall against the venv that backs your `coga` shim: `<that venv's python> -m pip install -e .`" but never says how to find that venv, and its "Installed-versus-source skew" section only hints that an editable install may come from a different checkout. Change: add a short "Which Python backs `coga`" note under **Daily commands** stating (a) the CLI is a uv tool editable install, its interpreter is `$(dirname "$(readlink -f "$(command -v coga)")")/python` (here `~/.local/share/uv/tools/coga/bin/python`), and `direct_url.json` in that env's `coga-*.dist-info` names the checkout it imports from; (b) any script that must `import coga` against the *active* CLI (Dream's owned-path derivation, ad-hoc probes) must run under that interpreter, not `python`/`python3`; (c) with two checkouts, the checkout named by `direct_url.json` is the one `coga` executes regardless of cwd. Also, since PR #759 `.coga/` is no longer an installation directory — it holds only machine-local run records (`.coga/recurring-runs/`) and the megalaunch selection — so the packaging-twin sentence "Discovery excludes local installation directories (`.coga/`, `.venv/`)" (and the matching CLAUDE.md line "Generated installation directories (`.coga/`, `.venv/`)") should call `.coga/` machine-local state, not an installation directory. Edit live and packaged codebase copies together.

### F-04 — target `coga/sync` — source `simplify-ticket-format`

**Shipping a stored-ticket schema conversion: the one-PR cutover procedure and the rebase rule for converted tickets.**

`coga/current-direction` records the *decision* from the done `simplify-ticket-format` ticket ("no compatibility reader, no migration tool, no dual-writer period — the whole stored population was converted in the same change"), but no context carries the *procedure* that made a code+data conversion of committed `coga/tasks/**` safe, and it will be needed again by any future frontmatter/format change (e.g. the parked playbook rename). Nothing under `coga/sync`, `coga/codebase`, or `dev/code` mentions a writer quiet window, a stale-writer inventory, or how to resolve rebase conflicts on tickets a feature branch has rewritten (grep for "quiet window|cutover|old writer|wholesale|re-apply" finds nothing relevant). Durable content to add to `coga/sync` (near "Design rule for new features"), with `dev/code` cross-referencing it: (1) keep code, converted data, fixtures, and context edits in **one PR** — a split merge leaves the running CLI and tickets disagreeing; (2) the state-regression guard compares lifecycle progress only and is *not* a schema barrier — an already-running older supervisor can restore removed fields at the same step, so before merge the owner stops recurring/megalaunch dispatchers, lets every old supervisor finish teardown and state sync, suspends scheduled entry points and writers on other machines, and inventories `git worktree list` plus independent clones and installed/editable entry points (ten worktrees were registered; that list proves nothing about live processes); (3) refresh the conversion commit from the *exact* control revision at the gate and re-verify the allowed field/token diff per ticket — control moved four times during one implement+open-pr pass, twice within ten minutes, so expect to repeat this; (4) the rebase rule for a converted ticket that control has since advanced: take control's version **wholesale** (lifecycle, body, blackboard), then re-apply only the mechanical conversion to it, never choose one side wholesale, and prove it with `git diff` against `git show origin/main:<path>` showing pure key deletions; (5) never run a mutating Coga command from the converting feature checkout (its exit sweep would publish converted `coga/` files before the code lands), verify with source-pinned `python -m coga.validate --json` and pure `compose_prompt_report`, and compare before/after validation reports by task/kind so the only removed findings are the intended ones (`unknown-assignee` went 5 → 0; no new kinds).

### F-03 — target `coga/codebase` — source `allow-description-and-owner-on-create`

**`create_task` writes and logs before it validates — only `coga create` guards a structure-breaking description.**

The done ticket `allow-description-and-owner-on-create` established (and its self-QA recorded as an explicit out-of-scope follow-up) that `create_task()` in `src/coga/create.py` calls `git.write_ticket_under_barrier(...)`, then `append_log(...)`, and only then `assert_task_valid(cfg, created_ref, action="create")` — so a description containing a `## ` heading line or the blackboard fence on its own line lands as a corrupt two-section/two-fence ticket on disk plus a `created` log line before validation fails (`tests/test_create.py::test_cli_create_reports_validation_failure_and_leaves_draft` pins the leave-on-disk behavior). The ticket therefore put the guard in `src/coga/commands/create.py` (`_description_structure_problem`: the `^##(?:\s|$)` line regex matching compose's `_SECTION_HEADING_RE`, plus `taskfile.fence_count`) and it runs on the *stripped* text before `load_config`/`create_task`. Verified today: the order in `create.py` is unchanged and `create_task` has four callers (`commands/create.py`, `commands/retire.py`, `recurring.py`, `recurring_autofix.py`), of which only the CLI command guards its description. Neither `coga/contexts/coga/codebase/SKILL.md` nor `coga/architecture` mentions `create_task` at all. Add a bullet under "Gotchas when editing coga's own code" in `coga/codebase` (and its packaged twin): `create_task` validates after writing, so any new caller that passes an agent- or user-authored description must reject level-2 headings and an own-line fence itself before calling it, or accept that a failed validation leaves the broken draft and its log line behind; the CLI guard in `commands/create.py` is the reference shape.

(ks-17 correction to the `create_task` finding above: `coga/architecture` does name `create_task` once, at its "Workflow gated at activation" section, in the sense of recurring/bootstrap callers bypassing draft state — nothing about write-before-validate order. The proposed change is unaffected.)

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/812
branch: dream-w38-extract-backlog
worktree: /home/n/Code/claude/coga-dream-w38-extract-backlog

Separate-checkout layout; worktree created from `origin/main` (`7b76b51a`).

## Plan (2026-09-15, implement)

One knowledge PR carrying all four findings. Facts re-verified in-session before
writing (see `## Findings` below). Files, grouped by target:

- `coga/contexts/coga/codebase/SKILL.md` + packaged bootstrap twin: F-01 (root
  `CLAUDE.md`/`AGENTS.md` hand-kept twin sentence in the rebase/twin bullet),
  F-02 ("Which Python backs `coga`" note under Daily commands; `.coga/` wording
  in the twin bullet), F-03 (`create_task` write-before-validate gotcha).
- `coga/contexts/coga/sync/SKILL.md` + twin: F-04 procedure section next to
  "Design rule for new features".
- `coga/contexts/dev/code/SKILL.md` + twin: one cross-reference to the F-04
  section.
- `CLAUDE.md` and `AGENTS.md` (both, byte-identical): F-02's `.coga/` wording.

Tradeoff: one PR instead of two (codebase vs sync) — the findings are all
doc-only, small, and share the packaging-twin test; splitting adds review
overhead with no isolation benefit.

## Findings

- F-01: `cmp CLAUDE.md AGENTS.md` identical; `grep -rn 'AGENTS.md' tests/`
  finds no pairing test. Twins live under
  `src/coga/resources/templates/coga/bootstrap/contexts/...` (not
  `templates/coga/contexts/...`), all three targets currently byte-identical.
- F-02: `command -v coga` -> `~/.local/bin/coga` -> readlink
  `~/.local/share/uv/tools/coga/bin/coga`; that env's `python` is 3.12.12 and
  imports `/home/n/Code/claude/coga/src/coga/__init__.py`; `direct_url.json`
  = `{"url":"file:///home/n/Code/claude/coga","dir_info":{"editable":true}}`;
  ambient `python3` is 3.9.12. `.coga/` here holds only `recurring-runs/` and
  `worktrees/`.
- F-03: `src/coga/create.py` `create_task` order unchanged:
  `git.write_ticket_under_barrier` -> `append_log` -> `assert_task_valid`.
  Four callers (`commands/create.py`, `commands/retire.py`, `recurring.py`,
  `recurring_autofix.py`); only `commands/create.py` runs
  `_description_structure_problem`.
- F-04: `grep -n 'quiet window|cutover|old writer|wholesale|re-apply'` over
  `coga/contexts/coga/sync`, `coga/codebase`, `dev/code` hits only the
  regression-guard "replaces the ticket wholesale" sentence — no procedure
  exists.

## Implement handoff (2026-09-15)

Commit `5bf988a0` on `dream-w38-extract-backlog` (worktree above), rebased on
`origin/main` `7b76b51a`, working tree clean, not pushed. Eight files: the three
live contexts, their three packaged bootstrap twins, `CLAUDE.md`, `AGENTS.md`.

What landed, by finding:

- F-01 → `coga/codebase` "A rebase carries a fix through a rename" bullet: root
  `CLAUDE.md`/`AGENTS.md` named as a hand-kept third twin; edit both + `cmp`.
- F-02 → `coga/codebase` Daily commands: new "Which Python backs `coga`"
  paragraph (uv tool editable install, interpreter path expression,
  `direct_url.json` names the checkout, ambient `python3` fails `import coga`,
  cwd is irrelevant with two checkouts). Same bullet + `CLAUDE.md`/`AGENTS.md`:
  `.coga/` reworded as machine-local state (run records, megalaunch
  selection), not an installation directory.
  Addition beyond the finding, verified in-session: the primary checkout *does*
  have a `.venv/` (editable coga + pytest 9.1.1 + tomlkit, created 2026-07-16)
  and the uv tool env has no `pytest`; recorded one sentence distinguishing the
  test venv from the CLI env, since "neither checkout has a vendored venv" is
  not literally true here and the distinction is exactly what tripped the
  test run (`python3.12` lacked tomlkit, tool env lacked pytest).
- F-03 → `coga/codebase` "Gotchas when editing coga's own code": new
  `create_task` write-before-validate bullet, naming the actual regex symbol
  `_SECTION_HEADING_LINE_RE` (the finding's "matching compose's
  `_SECTION_HEADING_RE`" softened to "mirroring the lines it splits on" — the
  two patterns differ: `^##(?:\s|$)` vs `^##\s+(.+?)\s*$`).
- F-04 → `coga/sync` new section "Shipping a stored-ticket schema conversion"
  placed directly after "Design rule for new features", five numbered steps as
  specified; step 4 reworded so "take control wholesale, then re-apply the
  conversion" and "never pick one side" do not read as contradictory.
  `dev/code` "What this context does not cover" gained a cross-reference item.

Verification:

- `PYTHONPATH=<worktree>/src /home/n/Code/claude/coga/.venv/bin/python -m
  pytest` → 2495 passed (170s). `tests/test_packaging.py` 11 passed.
- `cmp` on all three live/packaged pairs and on `CLAUDE.md`/`AGENTS.md`: identical.
- Source-pinned `python -m coga.validate --json` from the worktree: same
  finding set as `main` (pre-existing draft/stale warnings only).

Not done / for reviewers: no test added — doc-only change; the packaging twin
test already guards the six context files. `uv tool install -e <checkout>` in
the F-02 note is the reinstall spelling and was not executed in-session (the
install must not be repointed from a feature worktree).

## Peer review

2026-09-15: `codex review --base main` **returned**, exit 0, from the recorded
feature worktree. Its sandboxed attempt could not initialize the app-server;
the completed run used the existing unsandboxed command permission. Review
output: `/tmp/coga-dream-w38-peer-review.log`. It found two P2 issues, both
fixed in the live contexts and their packaged twins:

- F-04 lacked the post-merge gate from the source ticket: update and verify
  installed/editable writers, reconcile or bar stale checkouts while preserving
  local work, validate converted control, then resume with fresh processes.
- F-03 incorrectly promised validation failure for headings. A direct
  `create_task(description="Intro\n\n## Hidden\nBody")` succeeds and logs
  creation while compose extracts only `Intro`; an own-line fence fails after
  writing the ticket and log. Disposable `/tmp` probes confirmed both. The
  context now distinguishes these outcomes and accurately names recurring's
  `body=` interface and autofix's unguarded agent-authored description.

Also corrected the reinstall guidance: the active uv environment has neither
`pip` nor `pytest`, so pip instructions apply only to pip-managed installs;
uv uses `uv tool install --force -e <checkout>`. Verified the interpreter,
import path, `direct_url.json`, and local `uv tool install --help`; did not
repoint any installation.

Ran `git fetch origin main` and `git rebase FETCH_HEAD` unconditionally.
Rebased cleanly onto `9f0c30d8`; only task/log state had advanced from the
original base. All four twin pairs match, and `git diff --check` passes.
The eight-file diff is documentation-only; no terminal, pager, prompt UI, or
Slack rendering surface changed, so no interactive-surface gate applies.

Source-pinned `python -m coga.validate --json` reports the same 29 task findings
on primary and feature (4 pre-existing `unsynthesized-draft-blackboard` errors
and 25 warnings). Feature adds only `(config)/missing-user`, because its local
config is absent. This corrects the implement handoff's shorthand about only
warnings. Validation command, run from each checkout:
`PYTHONPATH="$PWD/src" /home/n/Code/claude/coga/.venv/bin/python -m coga.validate --json`.

Final verification from the feature worktree:

- `PYTHONPATH="$PWD/src" /home/n/Code/claude/coga/.venv/bin/python -m pytest`
  → **2495 passed in 173.92s**, including packaging tests. Two warnings only:
  pytest could not write its optional cache in the read-only feature checkout.
  Output: `/tmp/coga-dream-w38-peer-pytest.log`.
- `git diff --check origin/main` → clean.
- `cmp CLAUDE.md AGENTS.md` and `cmp` for each of the three context pairs
  (`coga/codebase`, `coga/sync`, `dev/code`) → identical.
- From primary, `PYTHONPATH="$PWD/src" /home/n/Code/claude/coga/.venv/bin/python -m coga.validate --task dream-2026-w38-extract-backlog-4-findings-phase-4 --json`
  → one valid task, no issues; blackboard diff also passes `git diff --check`.

Committed review fixes as `1d23cb4c` on top of rebased implementation
`18091d93`. `dream-w38-extract-backlog` is clean, two commits ahead of
`origin/main`, and unpushed. The recorded worktree remains correct. No open
review finding or design decision remains; ready for the mechanical open-pr
step.

## Open-pr (2026-09-15)

`coga open-pr` run from the primary control checkout on `main`: the branch was
safe to publish (origin/main had advanced only through non-overlapping task/log
state), pushed, and PR #812 opened; `pr:` recorded under `## Dev`. Both peer
review P2 fixes were already on the branch (`1d23cb4c`), no rebase needed.

## PR

Preserve four Dream W38 findings in durable contexts: the hand-kept root
instruction twin, the uv CLI interpreter and imported checkout, `create_task`
description hazards, and the atomic stored-ticket schema cutover through
verified writer restart. Add the `dev/code` cross-reference, describe `.coga/`
as machine-local state, and keep all live/packaged twins synchronized.

Test plan: `PYTHONPATH="$PWD/src" /home/n/Code/claude/coga/.venv/bin/python -m pytest` → 2495 passed; `cmp CLAUDE.md AGENTS.md` and three context-pair comparisons pass; `git diff --check origin/main` passes. Source-pinned `python -m coga.validate --json` has identical task findings to primary (four existing draft errors; feature adds only its missing-local-user warning).
