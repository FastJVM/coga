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
step: 1 (implement)
agent: claude
launch_generation: pending:91767d9b-b47a-4434-ae38-5d69f5e27786
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
