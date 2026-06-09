---
title: Add Dream skill-update maintenance phase
status: active
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/codebase
- relay/project-stage
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
step: 1 (implement)
---

## Description

Give Dream a maintenance phase that updates clean imported skills. This is the
fourth and largest gap from the `add-imported-skill-update-check` audit, split
out from the sibling ticket `close-imported-skill-provenance-conflict-and-dream`
(which handles the CLI/metadata/conflict gaps). The CLI building block already
exists — `relay skill update --all --pr` opens one PR of clean imported-skill
updates — but no Dream phase invokes it.

Add a script-worker phase `bootstrap/dream/tasks/skill-update` that:

- runs `relay skill update --all --pr`, producing one PR containing the clean
  imported-skill updates;
- writes a `## Dream Skill: skill-update` section to the child task's
  blackboard listing updated / conflict / skipped skills, so conflicts and
  skipped skills surface as follow-up work (matching the Dream contract's
  "let the worker write its own `## Dream Skill: <name>` section" rule);
- mirrors the shape of the two existing Dream script workers
  (`bootstrap/dream/tasks/validate-drift` and
  `bootstrap/dream/tasks/cleanup-orphan-markers`): a `SKILL.md` with a
  `## Known Skill Contract` declaring its reads/writes, plus a `run.py`.

Then wire the phase into the Dream dispatch contract (`dream/ticket.md`). It is
an execute-half script worker like `cleanup-orphan-markers`; pick its phase
slot and renumber accordingly.

## Context

Depends on nothing in the sibling ticket at the code level — the
`relay skill update --all --pr` flow it calls already shipped in #143
(`run_skill_update_pr_flow` / `render_update_pr_body` in
`src/relay/skill_manager.py`). It can land before, after, or alongside the
sibling. If the sibling's new `conflict` status (gap 3) has merged, the
worker's blackboard summary should bucket `conflict` separately from
`skipped-local-adaptation`; if not, it buckets whatever statuses the updater
currently emits.

Authoring gotchas (see `relay/codebase`, "Authoring bundled batteries"):

- Bundled Dream worker skills are authored in the **source** template tree
  `src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/dream/tasks/`,
  NOT the live `relay-os/bootstrap/` copy (gitignored, overwritten on
  `relay init --update`). New battery files must be `git add -f` — the template
  `.gitignore` ignores `bootstrap/`, so an un-forced add silently ships nothing.
- The Dream dispatch contract lives in BOTH
  `relay-os/recurring/dream/ticket.md` and its packaged counterpart
  `src/relay/resources/templates/relay-os/recurring/dream/ticket.md` — they are
  currently byte-identical; apply the new phase + renumber identically to both.
- The renumber is not just the disposition heading: update the phase-count
  framing sentences too (the "six phases" / "Phases 1-3 decide / Phases 4-6
  execute" prose around `dream/ticket.md:39-52`).
- Existing workers to mirror for shape:
  `relay-os/bootstrap/skills/bootstrap/dream/tasks/{validate-drift,cleanup-orphan-markers}/`.

Out of scope: the CLI/metadata/conflict gaps (sibling ticket); any change to
the `relay skill update` engine itself — this ticket only adds the Dream
worker + phase that calls it.

## Acceptance Criteria

- A `bootstrap/dream/tasks/skill-update` worker skill exists in the source
  template tree (force-added) with a `## Known Skill Contract`, mirrored to the
  live `relay-os/bootstrap/` copy.
- The worker runs `relay skill update --all --pr` and writes a
  `## Dream Skill: skill-update` blackboard section bucketing updated /
  conflict / skipped skills.
- A new Dream phase is wired into BOTH `dream/ticket.md` copies, with phase
  numbering and the phase-count framing sentences updated consistently; the two
  copies remain byte-identical.
- `example/relay-os/` / seeded fixtures updated if the new phase or worker skill
  affects the smoke path (per CLAUDE.md's fixture rule); state explicitly on the
  blackboard if no fixture change was needed.
- `python -m pytest` and `relay validate --json` are green.
