---
title: Document how packaged contexts reach a repo, and settle the packaged-only cli
  context
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

Two related packaging facts that no context records, one of which has already
shipped a defect.

**1. The two packaged-context trees are consumed by different mechanisms.**
`coga/contexts/coga/codebase/SKILL.md` documents packaged contexts only as a
byte-identity twin rule over two path mappings (`templates/coga/<path>` and
`templates/coga/bootstrap/{contexts,skills,workflows}/<path>`). Nothing records
that `paths.resolve_context_path` falls back to `bootstrap/contexts/` **only**,
while `templates/coga/contexts/**` is init-seeded into a new repo by
`commands/update.py::copy_fresh_templates` and is never a runtime fallback.
Verified in-tree: `src/coga/resources/templates/coga/bootstrap/contexts/` holds
only `coga/` and `dev/`, whereas `browser/api-first` and `browser/dom-backed`
exist only under `src/coga/resources/templates/coga/contexts/browser/`.

That undocumented distinction has already shipped a defect:
`src/coga/resources/templates/coga/bootstrap/browser-automation/ticket.md`
attaches `browser/api-first`, and `bootstrap/skills/browser/build-automation/SKILL.md`
tells the agent to apply it — so that bootstrap ticket cannot compose from
bundled resources alone. Both the design agent and the independent evaluator on
`redo-documentation-dir-and-merge-it-with-context-b` had to rediscover this by
probing the package.

**2. `coga/cli` is the one shipped context with no live copy.** Of the eleven
bootstrap contexts under `src/coga/resources/templates/coga/bootstrap/contexts/coga/`,
ten have a live counterpart under `coga/contexts/coga/`; `coga/cli` does not.
Because `tests/test_packaging.py` derives twins from the packaged tree and a
packaged file with no live counterpart is simply not a pair, that context sits
outside byte-parity enforcement entirely and is invisible to anyone treating
`coga/contexts/` as the canonical tree — yet three live contexts route readers
to it (`launch-internals`, `architecture`, `extension-model`) and tickets edit
it (`migrate-recurring-templates-to-ticket-py-shims-and` records correcting
"active stale launch text in the packaged `coga/cli` context"). The done ticket
`packaged-repos-ship-recurring-templates-without-th` flagged this exact case as
an adjacent finding — "worth deciding whether that packaged-only context is
intentional" — and the decision was never made or written down.

## Context

Part 1 wants a short "how packaged contexts reach a repo" section in
`coga/contexts/coga/codebase/SKILL.md` (and its enforced twin) naming the three
states — init-seeded, bootstrap-fallback, local-only — and stating the rule an
author needs: an attachment in a bundled bootstrap ticket must resolve from
`bootstrap/contexts/`. Fixing the shipped `browser-automation` defect is a
separate, smaller change; decide whether it rides along.

Part 2 is a decision, not a documentation task: either state in the twin-rule
paragraph that a packaged-only context is a deliberate unenforced shape, name
`coga/cli` as the only current instance and why, and say where its edits are
reviewed — or give it a live copy so the derived parity test covers it.

Verify each claim against `src/coga/paths.py` and `src/coga/commands/update.py`
before writing; this Dream run read them but did not re-verify every path.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Verified facts (implement session, 2026-09-19)

- `paths.resolve_context_path`: local `contexts_root/<ref>/SKILL.md`, then
  `packaged_template_path("bootstrap", "contexts", ...)`, else `None`.
  `compose.py` raises `ComposeError` on `None`; `validate.py` and `create.py`
  reject the ref statically. Only `bootstrap/contexts/` is a runtime fallback.
- `commands/update.py::copy_fresh_templates` → `_copy_resource_tree(src,
  dst, skip_top={"bootstrap"})`, called once from `commands/init.py::_do_init`.
  So `templates/coga/contexts/**` is seeded once into a new repo and then
  repo-owned; nothing reads it afterwards.
- Packaged tree today: `templates/coga/contexts/` = `_template`,
  `browser/api-first`, `browser/dom-backed`. `templates/coga/bootstrap/contexts/`
  = `coga/*` (12 entries) + `dev/code`.
- Ticket count correction: 12 bootstrap `coga/*` contexts, 11 with live twins
  under `coga/contexts/coga/`; `coga/cli` is the only packaged-only one.
- `coga/architecture` ("Where a fact lives") already says a package-only
  context such as `coga/cli` is still a single owner — but neither it nor the
  codebase twin-rule bullet says the shape is deliberate, why, or where edits
  are reviewed. `docs/reference.md` links the packaged path directly.
- `browser-automation` defect: bites only a repo that predates the seeded
  browser contexts or deleted them (e.g. a non-browser project pruning
  `coga/contexts/browser/`). Fresh `coga init` works because the seed copy
  exists. `update.py::_LEGACY_COGA_GITIGNORE_ENTRIES` shows `contexts/coga/cli`
  was once a gitignored init copy — historical, not current behaviour.

## Dev

pr: https://github.com/FastJVM/coga/pull/843
branch: packaged-context-states
worktree: /home/n/Code/coga-packaged-context-states

## Decisions (human confirmed, attended session)

- **Part 2: keep `coga/cli` packaged-only and document the shape.** It is the
  command-behaviour contract, co-versioned with the package and reviewed in
  the PR that changes the command; this repo resolves it through the
  bootstrap fallback, so a live copy would exist only to be identical.
  Recorded in the codebase twin-rule bullet (both copies). Rejected: a live
  copy for parity coverage alone — 1369 duplicated lines, two edits per CLI
  change, no behavioural gain.
- **Defect fix rides along.** `templates/coga/contexts/browser/{api-first,
  dom-backed}` move to `templates/coga/bootstrap/contexts/browser/`, so the
  bundled `browser-automation` ticket and `browser/build-automation` skill
  resolve from bundled resources alone. Live `coga/contexts/browser/*` stay
  twins via the bootstrap mapping in `tests/test_packaging.py`. New repos get
  the bundled copy (overridable locally) instead of a seeded editable copy;
  already-inited repos keep their seed, which shadows the identical bundle.
- Regression test: every bundled bootstrap ticket's `contexts:` must resolve
  from `bootstrap/contexts/` (the authoring rule, enforced).

## Implemented (branch `packaged-context-states`, 2 commits, rebased on origin/main)

1. `Move browser contexts into the bootstrap fallback tree` —
   `git mv templates/coga/contexts/browser → templates/coga/bootstrap/contexts/browser`
   (live `coga/contexts/browser/*` unchanged, still byte-identical twins via
   the bootstrap mapping). New
   `tests/test_packaging.py::test_bundled_bootstrap_tickets_attach_only_bootstrap_contexts`
   walks every `bootstrap/*/ticket.md` and requires each `contexts:` ref to
   exist under `bootstrap/contexts/`; verified it fails against the pre-fix
   tree. `tests/test_browser_automation_bootstrap.py` path assertions moved;
   `tests/test_init.py` (empty- and filled-repo init) now assert the browser
   contexts are *not* seeded and resolve via `bootstrap_context_path`.
2. `Document how packaged contexts reach a repo and settle coga/cli` — new
   `### How packaged contexts reach a repo` subsection in `coga/codebase`
   (three states + authoring rule + the shipped instance); twin-rule bullet
   gains the deliberate packaged-only paragraph naming `coga/cli`, why, and
   where edits are reviewed; one-line pointer added to `coga/architecture`
   "Where a fact lives". Packaged twins synced (cmp-verified after rebase).

Verification: scratch 3.12 venv (`uv venv` + `-e ".[test]"` + pip, in the
session scratchpad — no `.venv` in any checkout), `PYTHONPATH=$PWD/src python
-m pytest` → 2658 passed, before and after rebase onto `fcbd9897`. Docs
surface checked: `docs/development.md` sync-rule prose is a summary and stays
consistent; `docs/reference.md` already links the packaged `coga/cli` path.
No push, no PR.

Adjacent, not fixed here: `update.py::_LEGACY_COGA_GITIGNORE_ENTRIES` still
lists `contexts/coga/{architecture,principles,cli}` from an era when init
copied and gitignored them; harmless dedupe data, but a reader may infer the
old behaviour from it.

## Peer review

- Ran `codex review --base main` in the recorded feature worktree. The review
  **returned** successfully: no actionable regressions or must-fix findings.
  Initial sandbox startup failed; the approved outside-sandbox retry returned.
  Review transcript: `/tmp/packaged-context-review.log`.
- Independently checked the diff against `paths.resolve_context_path` and
  `commands/update.py::copy_fresh_templates`, documentation ownership, and
  browser resource references. No additional findings; no fix commit needed.
- Ran `git fetch origin main && git rebase FETCH_HEAD` unconditionally; clean
  rebase onto `c8218398863a53194bdfb33bcb2d3db680f21b06`. Feature branch remains
  clean with two commits: `b2c48a28` and `04ad5876`.
- Post-rebase verification:
  `PYTHONPATH=src /tmp/coga-dispose-review-venv/bin/python -m pytest` —
  **2658 passed**, two sandbox cache-write warnings, 186.24 seconds.
  The default Python and review subprocess lacked `tomlkit`; the complete
  suite above used an existing dependency-equipped venv with imports forced
  to this feature worktree. Log: `/tmp/packaged-context-pytest.log`.
  `git diff --check` also passed.
- No terminal, pager, prompt, or rendered notification surface changed; no
  additional interactive surface check applies. No push or PR in this step.

## PR

Document how contexts reach a repository: init-seeded copies, package-backed
bootstrap fallbacks, and local-only contexts. Record why `coga/cli` deliberately
remains packaged-only and where its command-contract edits are reviewed; keep
the live and packaged documentation twins synchronized.

Move the browser contexts into the bootstrap fallback tree so the bundled
`browser-automation` ticket can resolve them even when a repository never had
or deleted the old seeded copies. New repositories use the bundled contexts;
existing local copies continue to override them. Add a regression check for
bundled tickets' context attachments and update the init/browser fixtures.

Test plan: `PYTHONPATH=src /tmp/coga-dispose-review-venv/bin/python -m pytest`
(2658 passed); `git diff --check`; `codex review --base main` returned with no
actionable findings.

## Open PR

- Confirmed `## Peer review` records the review returned with no must-fix
  findings before publishing. `origin/main` was 5 generated task/log commits
  ahead of the rebase point (`c8218398`); none overlap the feature diff, and
  `coga open-pr` reported the branch safe to publish.
- Ran `coga open-pr` from the primary control checkout (separate-worktree
  layout). Pushed `packaged-context-states`, opened PR #843 (non-draft),
  `pr:` recorded under `## Dev`. Next step is the owner's merge decision.
