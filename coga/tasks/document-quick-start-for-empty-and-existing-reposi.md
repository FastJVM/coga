---
title: Document Quick Start for empty and existing repositories
status: blocked
owner: nicktoper
workflow:
  name: docs/with-review
  steps:
  - name: implement
    skills: []
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills: []
    assignee: agent
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
agent: claude
---

## Description

Give the README two complete Quick Start paths: a new empty repository eligible for coga build onboarding, and an existing repository where init says coga build is unavailable. Follow current init behavior instead of routing both users into an empty-repository-only command.

Done when each path states its prerequisites and gives valid commands through to a first launched task: the new-repo path ends at `coga build` → `coga launch <starter ticket>`, the existing-repo path ends at `coga ticket "<title>"` → `coga launch <ticket>`. Each path says when `coga build` is available (empty repo only). Verify every command against current `--help` and by running `coga init` in a temporary empty git repo and a temporary non-empty one, quoting what init prints in the PR. Keep this change focused on onboarding instructions; a broader README rewrite is outside scope.

If the code and the init messages turn out to disagree with each other or the tests, stop and flag it on the blackboard rather than changing `init` messages — this ticket is docs-only.

## Context

**On hold (2026-10-08):** the owner is rewriting README.md. Do not start until that rewrite lands. Then re-check the scope boundaries below against the new README, and confirm with the owner whether the draft build prose and the old Install block should be moved into Quick Start or left in place.

### Report relayed by the owner — 2026-10-07

Another AI reports that coga init in an existing repository says “coga build is unavailable here,” while the README sends readers to build. Intake confirms the corresponding init message and empty-repo-only packaged onboarding contract. README currently has empty Existing repo and New repo subsections; complete those paths rather than adding another competing Quick Start.

Read coga/init (`docs/contexts/coga/init/SKILL.md`), cited rather than attached; inspect empty/filled repository detection and handoff messages. Start with `src/coga/commands/init.py`, its tests, README.md, and `src/coga/resources/templates/coga/workflows/build/onboarding.md`. Coordinate the missing vision publication fix in publish-build-vision-before-handing-off-starter-ti; do not promise clone-ready generated contexts until that path is verified.

### README is mid-rewrite by the owner — scope boundaries

The owner is restructuring README.md. Everything through `## Example` (the top of the file) is considered done: do not edit it. Everything after it is work in progress. This ticket owns only the new skeleton's `## Install` (currently empty, the first one) and `## Quick Start` → `### Existing repo` / `### New repo` subsections.

Raw material already in the WIP region, to reuse rather than reinvent (keep the owner's wording where it is correct):
- the owner's draft `coga build` / `coga status` / `coga ticket` / `coga launch` prose sitting under the misspelled `## Licnence` heading (it has an unclosed code fence) — this is draft content for the New repo path;
- the older, complete second `## Install` section (Python 3.11+, Git, authenticated Claude Code or Codex CLI; `uv tool install coga`; `coga init --user <name>`; links to the install and first-task topics).

Move that material into the skeleton sections it belongs to and remove the moved copies so the README has one Install and one Quick Start. Leave the other WIP sections (Why, Development & Community, Donors and Sponsors, the Licnence heading itself, Who it is for, Learn more, Weekly telemetry) for the owner. Before starting, check `git log -- README.md` and the working tree for owner edits in progress to avoid conflicts.

### Owning topics — summarize and link, don't restate

Per `coga/knowledge`'s one-owner rule, setup facts belong to `coga/install` (`docs/contexts/coga/install/SKILL.md`) and the first-ticket walkthrough to `coga/first-task` (`docs/contexts/coga/first-task/SKILL.md`); both are cited, not attached. The README summarizes and links them. If writing the Quick Start exposes a gap or contradiction in either topic, fix the topic in the same PR.

Verified at authoring time (2026-10-08): `init.init` prints "Skipped the onboarding ticket… `coga build` is unavailable here — create tasks with `coga ticket`" for a filled repo, and its next-steps text branches on the repo being empty (`coga build`) or filled (`coga ticket "<title>"`); `tests/test_init.py` covers both branches. The sibling vision-publication ticket does not block this one — the local `build` → `launch` path works now — but don't promise clone-ready generated contexts.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

- 2026-10-08 implement: not started — no branch created, no README edits. The
  ticket's hold note says do not start until the owner's README rewrite lands
  and to confirm the scope with the owner. README on `main` is still mid-rewrite:
  latest README commit is f5da579ac/db830202c (2026-10-07). It still has the
  empty skeleton `## Install` and `## Quick Start` (`### Existing repo` / `### New repo`),
  the `## Licnence` heading holding draft build/status/ticket/launch prose with
  an unclosed fence, and the older complete second `## Install`.
- Asked the owner, via block: (1) has the rewrite landed, or should this proceed
  against the current WIP skeleton? (2) Should the draft build prose under `Licnence`
  and the old `## Install` block move into the skeleton Install/Quick Start (and
  be removed from their old places), or stay where they are?
- Once unblocked: follow the plan in the ticket context. Run init in temporary
  empty and non-empty git repos, check each command against `--help`, and summarize
  and link coga/install and coga/first-task.

---

## Blockers

- [ ] [2026-10-08 12:08] [agent:claude] id=20261008T120827 Ticket is on hold until your README rewrite lands. README on main is still mid-rewrite: the skeleton Install/Quick Start is empty, draft build prose sits under 'Licnence' with an unclosed fence, and there is a duplicate old Install. Please confirm: (1) is the rewrite done, or should I write Quick Start into the current WIP skeleton now? (2) Should I move the draft build prose and the old Install block into the skeleton Install/Quick Start and delete the old copies, or leave them where they are?

---

## Blocker reminders

- 015376f4e624 last_reminded: 2026-10-09 13:48
