---
title: 'Installer-managed skills: the local-adaptation guard misses github-backed
  packs'
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

Two facts about the seven installer-managed `google-agents-cli-*` packs that
no context records, both of which change how a reader should treat those trees.

**1. The local-adaptation guard covers url-sourced skills only.** In
`src/coga/skill_manager.py`, `installed_digest` is computed only when
`metadata.get("source_type") == "url"`, so the `dirty_existing_skill` refusal on
install ("has local adaptations; rerun with --force to overwrite") and the
update-side `skipped-local-adaptation` / `conflict` results in
`_update_url_skill_dir` apply to url-sourced skills alone. Every entry in
`src/coga/resources/managed-skills.toml` is `source_type = "github"`, and
`_update_gh_backed_skills` simply delegates `gh skill update --dir <root> --all`
with no digest comparison and no Coga-side guard. So a local edit to any
`google-agents-cli-*` file is silently overwritable by the weekly skill-update
job, while the identical edit to a url-sourced skill raises a conflict. Neither
`coga/contexts/coga/codebase/SKILL.md` nor `coga/contexts/coga/extension-model/SKILL.md`
records the asymmetry.

**2. Nothing records why those packs are in this repo at all.** They are ~250 KB
of Google Cloud / ADK agent-development guidance, all seven materialized into
`coga/.agent-skills/` — the view Claude Code and Codex are pointed at — so every
session in this repo carries their descriptions, one of which
(`google-agents-cli-workflow`) self-describes as "Always active". Yet no ticket,
context, recurring job or workflow in the repo does ADK work: a case-insensitive
sweep of `coga/tasks`, `coga/contexts`, `coga/recurring` and `docs` for ADK or
agents-cli turns up only provenance and cleanup tickets about managing the packs
themselves. The presumable reason — dogfooding `coga skill install` / `update`
against a real remote source — is a good one and is written down nowhere, so a
future cleanup pass could read them as dead weight and delete the only
end-to-end exercise of that path.

## Context

Both belong in the installer-managed bullet of
`coga/contexts/coga/codebase/SKILL.md` (with its enforced packaged twin):

- state that installer-managed github-backed skills are read-only in-repo —
  fix them upstream or convert to a hand-vendored namespaced copy with
  attribution — because Coga's local-adaptation guard does not cover that path;
- state why the packs are kept, so their purpose survives a cleanup sweep.

A third, closely related item is already routed into a Dream proposal PR this
run (the counter-instruction that a pack's own `uvx google-agents-cli setup`
refresh instructions are inert in a Coga repo). Check that PR before editing the
same bullet, and fold rather than conflict.

Verify the `skill_manager.py` behavior yourself before writing — describe what
the code does, not this summary.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Findings (verified against `src/coga/skill_manager.py` at 6210db59)

- `install_github_skill` runs `gh skill install <source> [skill] --dir <root>`
  and writes no Coga metadata: no `.coga-source.json`, no digest. The only
  record is what `gh` injects into `SKILL.md` frontmatter (`metadata.github-repo`,
  `github-ref`, `github-tree-sha`) — an *upstream* tree SHA, not a hash of the
  files on disk.
- `install_url_skill` reads `installed_tree_digest` only when the existing
  target's `.coga-source.json` says `source_type == "url"`;
  `dirty_existing_skill` (`hash_skill_tree(target) != installed_digest`)
  refuses without `--force`. A gh-backed target has no such metadata, so the
  digest is `None` and the guard is inert for it.
- `_update_url_skill_dir` compares `hash_skill_tree` to `installed_tree_digest`
  and reports `skipped-local-adaptation` (upstream unchanged) or `conflict`
  (upstream changed) instead of overwriting.
- `_update_gh_backed_skill` (singular — one `gh skill update --dir <root>
  --all <ref>` call per skill; the ticket's "`_update_gh_backed_skills` ...
  `--all`" wording is slightly off) runs gh and classifies its printed line
  via `classify_gh_update_output`. There is no digest comparison anywhere on
  that path; whether the tree is rewritten is gh's stored-tree-SHA decision.
- Every entry in `src/coga/resources/managed-skills.toml` is
  `source_type = "github"`; the seven `google-agents-cli-*` packs carry
  `github-tree-sha`, no `.coga-source.json`.
- `coga/recurring/skill-update/ticket.md` already says "Do not keep local
  adaptations in those directories" — but that is a job template, not a
  composed context. `coga/contexts/coga/codebase/SKILL.md` does not say it.
- Why the packs exist: commit 321e6231 (2026-05-13, "Vendor google/agents-cli
  skills v0.1.3") installed them via `gh skill install` explicitly "so the
  install is self-describing and `relay skill update --all` can later refresh
  them"; #334 then moved them into `managed-skills.toml` as init's optional
  refs. The repo does no ADK work (sweep of `coga/tasks`, `coga/contexts`,
  `coga/recurring`, `docs` for adk/agents-cli hits only pack-management and
  provenance tickets). They are the checked-in exercise of the GitHub-backed
  install/update path and the weekly job — not presumed, stated in history.
- The "third item" (the `uvx google-agents-cli setup` counter-instruction)
  already landed on `main` in #773; no open PR carries it. Open PRs #834 and
  #835 touch `codebase/SKILL.md` at lines ~620 and ~903 — far from the
  installer-managed bullet (~207-234) and the refresh paragraph (~311-320),
  so no fold/conflict.
- Live context and packaged twin are byte-identical today.

## Dev

branch: gh-backed-readonly-context
worktree: /home/n/Code/coga
Single-checkout layout: branch created in place from `main`.

## Implement — what changed

- Docs-only. Extended the **Installer-managed, flat and GitHub-backed** bullet
  in `coga/contexts/coga/codebase/SKILL.md` with two bold-led statements:
  "Treat these directories as read-only in-repo" (names the three code facts
  above — `install_github_skill`, `install_url_skill`'s url-only digest read,
  `_update_gh_backed_skill`'s absent comparison — and the two sanctioned
  routes: fix upstream or hand-vendor under a namespace with attribution) and
  "The packs are kept on purpose" (cites commit `321e6231`, names the three
  functions that would lose their only live target). Packaged twin copied
  byte-for-byte. No source, test, or fixture change: the ticket scopes the
  fix to the context, and the behavior being documented already exists.
- Decision: did not extend the guard in code. Doing so would mean writing a
  Coga digest at `install_github_skill` time and checking it before
  `gh skill update` — a second provenance record beside gh's frontmatter.
  Reasonable follow-up if the read-only rule proves insufficient; out of
  scope here.
- Did not touch `extension-model/SKILL.md`: its `gh skill` mention is about
  the acquire primitive, not skill shapes; the shape facts live in codebase.

## Verification

- `python -m pytest` (scratch venv, Python 3.12): 2656 passed, 1 failed.
  The failure, `tests/test_open_pr_command.py::test_open_pr_ships_as_a_registered_recipe`,
  is pre-existing and environmental — a stale gitignored `__pycache__` at
  `src/coga/resources/templates/coga/bootstrap/open-pr/` left over from
  before #667 deleted that tree makes `.exists()` true. Fails identically
  with my change stashed. Remedy on this machine: delete that directory.
- `tests/test_packaging.py`: 13 passed (twin parity holds).
- Rebased onto `origin/main` (68ad9cd8; incoming commits were task/log state
  only).

## Peer review

- `codex review --base main` ran in `/home/n/Code/coga` on
  `gh-backed-readonly-context` and **returned** (exit 0): no actionable
  regressions; the documented installer/update behavior matches the source,
  and the live context and packaged twin are byte-identical. No must-fix
  findings or design changes.
- The review's targeted tests could not collect under the default Python
  because `tomlkit` was missing. Verified the existing Python 3.12 test venv
  `/tmp/coga-skill-attribution-venv` has the declared test dependencies;
  final validation used it with this checkout's absolute `PYTHONPATH`.
- Independently checked the GitHub/URL install and update paths, managed
  manifest, upstream-install commit `321e6231`, and subsequent pack refresh
  commits. PR #773 is merged and its counter-instruction remains intact.
- No terminal, pager, prompt, or rendered-message behavior changes in this
  docs-only diff; no interactive-surface exercise is applicable.
- Ran `git fetch origin main` then `git rebase FETCH_HEAD` unconditionally;
  rebased cleanly onto `ca52f488`. Git dropped two state commits already
  upstream; the context changes are unchanged.
- Moved the stale, ignored `bootstrap/open-pr/` directory (only
  `__pycache__/recipe.cpython-312.pyc`) to
  `/tmp/coga-gh-backed-readonly-stale-cache-_gs420bl/open-pr`. No tracked
  files changed.
- After rebasing, ran
  `PATH=/tmp/coga-skill-attribution-venv/bin:$PATH PYTHONPATH=/home/n/Code/coga/src python -m pytest`:
  **2657 passed** in 185.63 seconds, including the previously failing
  open-PR test and all 13 packaging checks.
- `git diff --check origin/main...HEAD` and `cmp` of the live and packaged
  codebase contexts both passed.

## PR

GitHub-backed managed skills have no Coga digest guard, so upstream refreshes
can overwrite local adaptations. Document their read-only handling and the
options to fix them upstream or hand-vendor attributed copies in the codebase
context and its packaged twin. Record why the seven Google packs are retained as the
repo's real GitHub install/update exercise, alongside the existing rule against
running their upstream installer.

Test plan: `PATH=/tmp/coga-skill-attribution-venv/bin:$PATH PYTHONPATH=/home/n/Code/coga/src python -m pytest` (2657 passed, including packaging parity); `git diff --check origin/main...HEAD`.

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `installer-managed-skills-the-local-adaptation-guar`
Recorded: 2026-09-19T00:59:14+00:00

    Recorded worktree '/home/n/Code/coga' has uncommitted changes. The implement/peer-review steps must commit implementation work before open-pr. This is the single-checkout layout: preserve live task/log edits here and commit them separately from implementation work. Then relaunch.
