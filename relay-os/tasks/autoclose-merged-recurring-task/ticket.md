---
title: Add a daily recurring task that auto-closes merged tickets (port the automerge
  sweep)
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/recurring
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
---

## Description

Tickets routinely get stuck `in_progress` at their final `review` step after
their PR has already merged on GitHub — the owner just forgot to run
`relay mark done`. The merged→done logic already exists in
`src/relay/automerge.py` (`auto_bump_merged`): it scans active/in-progress
tickets, reads the `pr:` link under the blackboard's `## Dev` section, checks
the PR's merge state via `gh`, and — only when the ticket is on its **final**
workflow step (or workflow-less) — runs `relay mark done`. The gap is that
nothing runs it on a schedule, so a GitHub-merged ticket that is never
relaunched sits stuck until a human notices.

This ticket closes the gap **additively**: add a **daily recurring task** that
runs the existing sweep. It does **not** remove or rename anything yet — the
existing `relay automerge` command and the launch-freshness check keep working
alongside the new scheduled run. Retiring those other triggers so the recurring
sweep is the *sole* trigger is the follow-up ticket
`retire-standalone-relay-automerge-triggers-recurri`, which depends on this one
landing first.

Concretely:

1. **Create a new daily recurring task** under `relay-os/recurring/` (proposed
   name `autoclose-merged/`) that runs the merged→done sweep once a day,
   `mode: script`, mirroring how `relay-os/recurring/digest/` runs `relay
   digest`. Schedule it slightly before the 9am digest (e.g. `0 8 * * *`) so
   the `mark done` events it produces are spooled into the **same** day's
   digest. Behavior stays **auto-mark-done** — the sweep closes confidently-
   merged final-step tickets directly; the resulting state-change broadcasts
   are spooled into the digest, so the closures are still visible.
2. **Factor the sweep into a reusable function the script skill can call.**
   Mirror `relay/digest/flush`: a `script: run.py` skill that imports the
   sweep function from `relay.automerge` and calls it directly (no dependency
   on `relay` being on `PATH`). Add the matching one-step workflow (mirror
   `digest/post.md`). Do **not** rename `automerge.py` in this ticket — the
   existing CLI command still imports it; the rename rides with the removal
   follow-up. Extract/share, don't break the current callers.

## Context

- **Source of the existing logic:** `src/relay/automerge.py`. Read its module
  docstring first — it documents the exact scope (final-step only; `pr:` line
  under `## Dev`; mid-workflow merges are deliberately left alone as
  "suspicious"). Preserve that scope; we are only changing *when* the sweep
  runs, not *what* it closes. `auto_bump_merged(quiet=...)` is the function to
  reuse.
- **Pattern to mirror** (script-mode recurring task): the trio
  `relay-os/recurring/digest/ticket.md`, the skill
  `relay-os/skills/relay/digest/flush/` (`SKILL.md` + `run.py`), and the
  workflow `relay-os/workflows/digest/post.md`. Copy this shape for the new
  recurring task. Open question for the implementer: create a dedicated
  `autoclose-merged/sweep.md` workflow + `relay/autoclose/sweep` skill (clean)
  rather than reusing digest's.
- **PR-link convention** is owned by the `dev/code` context (a `pr:` line
  under `## Dev` on the blackboard). The sweep parses it as plain text on
  purpose — do not change the convention; just keep parsing it.
- **Mode note:** like `digest`, this is `mode: script`. Unlike digest (which
  only drains a local spool), this sweep calls `gh pr view` per candidate
  ticket — but that is exactly what `relay automerge` already does today, so
  network-in-script is established, not new. The "temporary mode=auto recurring
  freeze" is about agent buffering (no `claude -p` / `codex exec`), which a
  script step sidesteps.
- **Keep both `relay-os/` copies in sync:** the live tree and the packaged
  `src/relay/resources/templates/relay-os/` copy.
- **Tests:** add coverage for the new recurring sweep path (script skill calls
  the shared sweep; idempotent per period). Run `python -m pytest` and
  `relay validate --json` before opening the PR.
- **Out of scope (→ follow-up ticket):** removing the `relay automerge`
  command, removing the launch-freshness check, renaming the module, doc
  updates for the changed trigger surface, and reconciling the
  `drift-…-auto-bump-merged` draft. All of that lives in
  `retire-standalone-relay-automerge-triggers-recurri`.

## Done when

- [ ] New recurring task `relay-os/recurring/autoclose-merged/` fires daily
      (`mode: script`) and runs the merged→done sweep via a script skill +
      one-step workflow (mirrors the digest trio).
- [ ] Sweep logic is shared (script skill and the existing `relay automerge`
      command both call one function); no existing caller broken.
- [ ] Live + packaged `relay-os/` copies in sync.
- [ ] `python -m pytest` green and `relay validate --json` clean; tests cover
      the new sweep path.
