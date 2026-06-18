---
title: relay init must ship reusable workflows + code skills into new repos
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/architecture
- relay/codebase
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 2 (review-design)
---

## Description

When you add Relay to a new directory, `relay init` does not bring over the
reusable **workflows** or the **`skills/code`** set they depend on. The
canonical contexts and most skills already ship — they're vendored under the
gitignored `bootstrap/` umbrella and refreshed on every `--update` — but the
packaged template tree carries only the `_template`/`browser` examples for
`workflows/` and `skills/`, and `bootstrap/` has no workflows at all. So a
fresh repo can't run `code/with-review` or `code/design-then-implement` out of
the box; all that process machinery has to be hand-copied. Make `relay init`
ship the reusable workflows (`code/`, `dev/`, …) and their `skills/code`
dependencies (implement, open-pr, self-qa, design) into new repos, and lock it
so the packaged tree can't drift back out of sync with the live `relay-os/`.

## Context

**What already ships (don't re-derive this).** A fresh `init` copies the
packaged tree at `src/relay/resources/templates/relay-os/`, which includes the
`bootstrap/` umbrella. So new repos already get the canonical contexts
(`bootstrap/contexts/relay/{architecture,cli,patterns,period-task,principles,sync}`,
`bootstrap/contexts/dev/code`) and several skills
(`bootstrap/skills/{bootstrap,eval,relay,retro,google-agents-cli-*}`).
`OBSOLETE_PATHS` in `update.py` prunes the old top-level `contexts/relay/*` so
runtime resolution falls through to the `bootstrap/` copy.

**The actual gap.** Nothing ships the reusable **workflows** —
`src/relay/resources/templates/relay-os/workflows/` has only `_template.md` and
`browser/`, and `bootstrap/` has no `workflows/` at all. And **`skills/code`**
(design, implement, implement-and-pr, open-pr, self-qa) is not under
`bootstrap/skills`, so it doesn't ship either. The rich set
(`workflows/{code,dev,dev-update,digest,docs,dream,test}`, `skills/code`) lives
only in this repo's git-tracked live `relay-os/`.

**Correctly out of scope.** Some contexts are source/repo-specific and should
*not* ship: `relay/{codebase,current-direction,project-stage,recurring}` and
`marketing/`. The curation question is therefore about workflows + `skills/code`
and how to handle the `browser` examples — not about the contexts.

**Existing mechanism to evaluate first.** `bootstrap/` is wholesale-vendored by
`_copy_vendored_bootstrap` (`src/relay/commands/update.py`): wiped and copied
fresh from package resources, gitignored in the source checkout, and refreshed
on every `relay init --update`. That already gives drift-proof, update-carried
delivery for contexts and most skills. Extending that channel to cover the
reusable workflows and `skills/code` is the most likely fix; the design step
should weigh it against a separate curation manifest + parity test.

Key code: `src/relay/commands/init.py` (`_do_init`, `copy_fresh_templates`),
`src/relay/commands/update.py` (`_copy_vendored_bootstrap`,
`refresh_gitignored_mirrors`, `OBSOLETE_PATHS`, `refresh_templates` vs
`copy_fresh_templates`). Per the repo `CLAUDE.md`, the packaged tree and live
`relay-os/` must stay in sync — the fix should fail loud on future drift.

## Design findings (settle these before implementing)

Two facts from the codebase pin the shape of the fix:

1. **Workflows have no `bootstrap/` fallback.** `paths.py:workflow_path`
   resolves a workflow from exactly one place: `relay-os/workflows/<name>.md`.
   Skills and contexts resolve local-first *then* bootstrap
   (`resolve_skill_path`, `resolve_context_path`), but workflows do not. So a
   workflow can only ship by landing a file under `relay-os/workflows/` in the
   target repo — putting it under `bootstrap/workflows/` would require new
   resolution code (and changes to freeze/validate paths). Skills, by contrast,
   *can* ship through the existing bootstrap channel with zero new resolution
   code.

2. **Fresh init already copies the whole packaged tree.**
   `copy_fresh_templates` → `_copy_resource_tree` copies all of
   `src/relay/resources/templates/relay-os/` into a new repo. So any file added
   under the packaged `workflows/` or `bootstrap/` ships to new repos
   automatically. The `VENDORED_WORKFLOW_TEMPLATES` / `VENDORED_SKILL_TEMPLATES`
   lists are only consulted on `--update` of an existing non-source repo (where
   the tree is *not* re-copied wholesale), and they overwrite wholesale — which
   would clobber a user's edited playbook, the reason the existing code
   deliberately keeps them narrow ("most named workflows are repo-owned
   playbooks").

**Curation (settled by reference-tracing, not guesswork).** The reusable set
that ships is:

- `workflows/code/design-then-implement.md`
- `workflows/code/with-review.md`
- `workflows/dev/with-self-review.md`
- `skills/code/` (all five: `design`, `implement`, `open-pr`, `self-qa`, and
  the adjacent `implement-and-pr`)

Excluded as repo-specific / relay-self-dev / domain-specific, confirmed by
who references them:

- `workflows/digest/post.md` — referenced only by relay's own
  `recurring/digest/` (not a vendored battery; `recurring/digest/` does not
  ship).
- `workflows/dream/{validate-drift,skill-update,cleanup-orphan-markers}.md` —
  the shipped Dream template launches child `mode: script` tasks against the
  `bootstrap/dream/tasks/*` skills directly; nothing references these workflow
  files, so they are vestigial and not needed in fresh repos.
- `workflows/build/dry-run.md`, `workflows/test/relaunch-chain.md` —
  self-described relay-internal fixtures (an onboarding-flow dry run and a
  launch-chain probe), not delivery workflows.
- `workflows/docs/create-google-doc.md` — Google-Drive-MCP domain workflow;
  excluded as domain-specific (see Open Question 3).

## Acceptance Criteria

- [ ] A fresh `relay init` into an empty dir produces a repo where
      `relay create "<t>" --workflow code/with-review`,
      `--workflow code/design-then-implement`, and
      `--workflow dev/with-self-review` all activate and bump without
      "workflow not found" or "skill not found" errors.
- [ ] The three curated workflow files exist under the packaged tree at
      `src/relay/resources/templates/relay-os/workflows/{code,dev}/` and are
      byte-identical to their live `relay-os/workflows/{code,dev}/`
      counterparts.
- [ ] `skills/code/` ships and resolves in a fresh repo: every `skills:` ref in
      the three curated workflows (`code/design`, `code/implement`,
      `code/open-pr`, `code/self-qa`) resolves via `resolve_skill_path`.
- [ ] A drift lock exists and fails loud: if a file under
      `relay-os/workflows/code/` or `relay-os/workflows/dev/` is added, removed,
      or edited without mirroring the packaged tree (or vice versa), a test
      fails. The lock is namespace-scoped (globs both sides), not a hardcoded
      filename list, so a *new* `code/*` workflow can't silently skip shipping.
- [ ] A closure test fails loud if any shipped curated workflow references a
      `skills:` ref that does not resolve to a shipped skill (bootstrap or
      packaged `skills/`).
- [ ] `python -m pytest` passes, including `tests/test_packaging.py`
      (run with a build backend so the wheel test does not skip — see
      `relay/codebase` packaging notes).
- [ ] `relay validate --json` is clean on the relay source checkout after the
      change.

## Proposed Shape

Recommended approach — **skills via bootstrap, workflows as plain templates,
both locked by a parity + closure test**:

1. **Move `skills/code/` into the bootstrap channel.**
   - Author the five skills under
     `src/relay/resources/templates/relay-os/bootstrap/skills/code/<name>/SKILL.md`
     (byte copies of the current live `relay-os/skills/code/*`). This makes the
     packaged tree the *single* source of truth — no dual copy to drift.
   - `git add -f` them: the template tree's own `.gitignore` ignores
     `bootstrap/` (see `relay/codebase` "Force-add new battery files"), so
     without `-f` they ship nothing despite green tests.
   - Delete the git-tracked live `relay-os/skills/code/` (it becomes a
     gitignored bootstrap mirror, materialized by
     `refresh_gitignored_mirrors` → `_copy_vendored_bootstrap`). Run
     `relay init --update` (source-checkout path) so the live
     `relay-os/bootstrap/skills/code/` is materialized and relay's own tasks
     keep resolving `code/*`.
   - Add `"skills/code"` to `OBSOLETE_PATHS` in `update.py` so existing user
     repos prune their stale top-level copy and fall through to bootstrap —
     mirroring the existing `contexts/relay/*`, `skills/retro/done-ticket`
     entries.
   - No resolution change needed: `resolve_skill_path` already does
     local-then-bootstrap.

2. **Ship the curated workflows as plain packaged template files.**
   - Copy `workflows/code/design-then-implement.md`,
     `workflows/code/with-review.md`, `workflows/dev/with-self-review.md` into
     `src/relay/resources/templates/relay-os/workflows/{code,dev}/` (byte
     copies of live). These are *not* under `bootstrap/`, so they commit
     normally and `copy_fresh_templates` ships them on fresh init.
   - Do **not** add them to `VENDORED_WORKFLOW_TEMPLATES` (that overwrites
     wholesale on `--update` and would clobber a user's edited playbook;
     workflows are user-owned). Fresh repos get them; that is the task's target
     ("new repos"). See Open Question 2.

3. **Lock against drift — new `tests/test_template_parity.py`.**
   - **Parity (namespace-scoped):** glob `relay-os/workflows/code/**` and
     `relay-os/workflows/dev/**` and the matching packaged paths; assert the
     two file *sets* are equal and each pair is byte-identical. This is the
     "can't drift back out of sync" lock and it catches a brand-new `code/*`
     file added on only one side.
   - **Closure:** parse each shipped curated workflow's `skills:` refs; assert
     each resolves to a shipped skill under the packaged tree
     (`bootstrap/skills/<ref>/SKILL.md` or `skills/<ref>/SKILL.md`). Catches
     "shipped the workflow, forgot the skill."
   - Extend `EXPECTED_BOOTSTRAP_RESOURCES` in `tests/test_packaging.py` with
     the `bootstrap/skills/code/*/SKILL.md` paths so the wheel-contents guard
     also asserts skills/code ships.

4. **Verify** with a real fresh `init` into a temp dir (offline:
   `[notification.slack] enabled = false`, set `user`) and exercise the three
   `relay create --workflow ...` paths, plus the full `pytest` run with a build
   backend installed.

Alternative considered and deferred (Open Question 1): give workflows a
`bootstrap/workflows/` resolution fallback so they ride the same wholesale
vendoring as skills/contexts. Cleaner long-term (single source for workflows
too, uniform local-override model) but a larger change — it touches
`workflow_path`, the workflow freeze in `retrofit.py`, and the
workflow-existence checks in `create.py`/`mark.py`. Out of proportion to "ship
+ lock," so recommended for a later ticket.

## Out of Scope

- Adding `bootstrap/workflows/` resolution (the deferred alternative above).
- Shipping `digest/`, `dream/`, `build/`, `test/`, `docs/` workflows or their
  skills (curated out above).
- Shipping repo-specific contexts (`relay/{codebase,current-direction,
  project-stage,recurring}`, `marketing/`) — already correctly excluded and
  unaffected by this task.
- Force-carrying the workflows onto existing repos via `--update`
  (`VENDORED_WORKFLOW_TEMPLATES`) — see Open Question 2.
- Changing `relay build` / onboarding flows or the managed-skills mechanism.
