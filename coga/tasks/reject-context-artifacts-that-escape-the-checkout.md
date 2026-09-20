---
title: Reject context artifacts that escape the checkout
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

Reject context artifacts whose symlink targets cannot be reproduced from the same checkout. The configured contexts root is already checked, but a tracked `<contexts-root>/team/style/SKILL.md` symlink can still resolve outside it into machine-local prose.

P2 fix from [the triage](triage-five-review-comments-that-merged-unanswered.md). Owner approved the narrower policy on 2026-09-19: reject all context artifact symlinks, including symlinked ancestor directories, for default and relocated roots.

### Evidence and source

Original [PR 704 comment](https://github.com/FastJVM/coga/pull/704#discussion_r3834289315); source ticket: [move-cogacontext-to-roodoc-so-its-easier-for-human](move-cogacontext-to-roodoc-so-its-easier-for-human.md). Assessed 2026-09-18 at `4d828256d28bf772d17aa8ffa1b47d6f436ca57b`.

A local-Git probe committed an external-target `SKILL.md` symlink under a configured relocated root. Config loading, task validation and composition accepted it and the external marker entered the prompt. Removing only the external file still allowed config loading, while context resolution disappeared and composition failed. Root-component rejection tests therefore do not cover the artifact concern.

### Expected behavior and scope

Inspect `config._require_trackable_context_entry`, `resolve_layout_contexts_path`, `paths.resolve_context_path`, `validate.validate_task`, and `compose.compose_prompt_report` in `src/coga/`. Enforce reproducible actual context resolution, including symlink chains and symlinked ancestor directories beneath a valid root. Invalid existing local artifacts must fail loudly before a bundled fallback can hide them.

Approved policy: reject all context artifact symlinks and symlinked ancestor directories, including internal, escaping, dangling, and cyclic links, with an actionable error. Also reject ignored or otherwise unpublishable actual context files. Internal-link publication proof is deliberately out of scope. Do not impose a new symlink policy on skills or ordinary attachments.

The original reproduction concerns relocated roots. Apply the artifact invariant to default roots too if they resolve the same unsafe file; keep the public behavior and test coverage explicit. Preserve ordinary local-first bundled resolution for genuinely absent local refs.

### Acceptance and focused verification

- A tracked external `SKILL.md` symlink and a chained escape fail clearly before prompt composition.
- A dangling or cyclic local artifact does not silently disappear into bundled fallback.
- Check ignored/unpublished in-checkout targets and a symlinked context ancestor directory. Cover rejection of internal links too.
- A second clone either composes the same approved context bytes or consistently rejects the invalid artifact; do not rely only on the root validator.
- Extend `tests/test_config.py`, `tests/test_layout_contexts.py`, and focused resolver/composer/validation coverage. Keep ordinary file, trackable marker, ignored scaffold and bundled-only cases working.
- Update the owning relocatable-context/artifact contract in `coga/contexts/coga/architecture/SKILL.md`, the PR 704 gotcha in `coga/codebase`, and their packaged twins; run packaging checks.

Tradeoff: repositories using context links, including internal links, will need real files under the contexts root. Out of scope: moving the contexts tree, the broader documentation redesign, or any live config edits during triage.

## Context

<!-- coga:blackboard -->

## Dev
pr: https://github.com/FastJVM/coga/pull/844
branch: fix/context-artifacts
worktree: /tmp/coga-context-artifacts

## Implementation plan

Owner approved rejecting internal links too, avoiding target-chain publication proof.
Use shared artifact checks at config loading and actual resolution, before bundled
fallback. Preserve ordinary files, ignored scaffolding, and genuinely absent refs.
Add regression coverage for config, resolver, composition, validation, and clones;
update architecture/codebase and packaged twins. Separate feature checkout; primary
checkout owns this blackboard and the final bump. Existing coga/log.md edit is the
launcher's state, not implementation work.


## Findings and verification

- `src/coga/config.py` + `require_context_artifact` is shared by configured-root
  admission and `src/coga/paths.py` + `resolve_context_path`. Actual resolution
  checks every lexical ancestor before following links or falling back, so default
  roots and changes made after config load are covered too.
- Config's scan does not follow directory symlinks. A dangling directory link
  cannot be distinguished from a dangling ordinary attachment during a global
  scan; actual context resolution rejects it if traversed. This preserves the
  agreed scope: ordinary attachments and skills keep their existing policy.
- `src/coga/compose.py` + `compose_prompt_report` turns artifact rejection into
  `ComposeError`; `src/coga/validate.py` + `_check_refs` reports `broken-context`.
- Regression-first run: 16 failures and 135 passes before implementation.
  Expanded focused suite: 336 passed. Full suite: 2688 passed in 185.32s,
  including packaging checks. Command from feature checkout:
  `/tmp/coga-context-test-env/bin/python -m pytest -q`.
- Test dependencies installed with the declared `[test]` extra in isolated
  `/tmp/coga-context-test-env` (system Python lacked tomlkit).
- Example fixture validation: `env -u SLACK_WEBHOOK_URL
  /tmp/coga-context-test-env/bin/coga validate --json` from feature checkout's
  `example/coga`: 4 valid tasks, no issues. Unsetting the inherited bare webhook
  avoids the existing removed-environment-key guard; no config files changed.


## Implement handoff

Committed as `818f47f42` (`Reject unpublishable context artifacts before resolution`).
Feature checkout is clean. `git fetch origin main` and `git rebase FETCH_HEAD`
completed after the commit; branch contains current `origin/main` (`0a31af566`).
`git diff --check` passed. No feature push or PR.
Architecture owns the artifact policy; its packaged twin and the codebase PR 704
pitfall note/twin are updated. Related end-to-end fixtures now exercise successful
state publication followed by fresh-clone composition, plus consistent rejection
of invalid links. No unresolved implementation blockers or adjacent bugs found.
Next transition: implement → peer-review via `coga bump` from the primary checkout.

## Peer review

- `codex review --base main` ran from `/tmp/coga-context-artifacts` and
  **returned** successfully: no actionable regressions or must-fix findings.
  The reviewer also ran 411 targeted tests, all passing. Review transcript:
  `/tmp/context-artifacts-review.log`. The initial sandbox-only invocation
  could not initialize its app-server state; the escalated retry completed.
- Ran `git fetch origin main` and `git rebase FETCH_HEAD` unconditionally.
  Rebase completed without conflicts onto `292bf811a`; the additional upstream
  commit was task bookkeeping. Feature commit is now `c6de5b7bc`.
- Post-rebase full suite: `/tmp/coga-context-test-env/bin/python -m pytest -q`
  — **2688 passed in 207.83s**, including packaging checks. `git diff --check`
  passed; feature checkout is clean and one commit ahead of `origin/main`.
- Example fixture: `env -u SLACK_WEBHOOK_URL
  /tmp/coga-context-test-env/bin/coga validate --json` from `example/coga`
  — 4 valid tasks, no issues. No config edits.
- No terminal, pager, TTY prompt, or rendered notification behavior changed;
  the changed surface is filesystem admission and context resolution, covered
  by resolver/composer/validation tests and fresh-clone regressions.
- No review fixes or additional implementation commit were necessary.
  Ready for peer-review → open-pr; PR creation belongs to the next session.

## PR

Context resolution could read machine-local prose through a tracked `SKILL.md`
symlink, or silently use bundled prose when that link became dangling. Reject
context artifact symlinks and symlinked ancestors before fallback for both
default and relocated roots, including internal, chained, dangling, and cyclic
links. Reject ignored files, nested-checkout artifacts, and non-regular files
with actionable errors surfaced through validation and composition.

Ordinary local files and genuinely absent refs retain local-first/bundled
resolution; skills and ordinary attachments keep their existing policy.
Repositories using context links must replace them with real files. Update the
owning architecture contract, codebase pitfall note, and packaged twins; extend
fixtures to verify rejection and successful publication in fresh clones.

Test plan: `/tmp/coga-context-test-env/bin/python -m pytest -q` (2688 passed,
including packaging); `env -u SLACK_WEBHOOK_URL /tmp/coga-context-test-env/bin/coga
validate --json` from `example/coga` (4 valid, no issues); `git diff --check`.

## Open-PR handoff

- Confirmed peer review **returned** (see `## Peer review`) before publishing.
- Ran `coga open-pr reject-context-artifacts-that-escape-the-checkout` from the
  primary control checkout; the feature branch was one generated `coga/log.md`
  commit behind `origin/main`, which the command classified as safe overlap.
- Pushed `fix/context-artifacts` (`c6de5b7bc`) and opened
  https://github.com/FastJVM/coga/pull/844 (non-draft, base `main`).
  `pr:` recorded under `## Dev`. Merge decision belongs to the next step.
