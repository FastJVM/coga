---
title: relay init must ship reusable workflows + code skills into new repos
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
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
step: 1 (design)
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
