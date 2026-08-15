---
slug: reconcile-recurring-wrapper-tty-admission-guidance
title: Reconcile recurring wrapper TTY-admission guidance with resolve-conflicts template
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
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
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

A recurring template whose work is "launch another agent" currently has to
fake a terminal to do it, and two shipped documents disagree about whether
that is sanctioned. Remove the need for the fake terminal.

`recurring/resolve-conflicts` owns only a schedule; its body tells the period
task's wrapper agent to run `coga resolve-conflicts --agent <type>`, which is
an alias for `coga launch bootstrap/resolve-conflicts` (`src/coga/aliases.py:67`).
That is a **double hop**: the recurring supervisor launches an agent, and that
agent shells out to launch a second agent. `coga launch` refuses an agent
launch unless stdin *and* stdout are terminals
(`_interactive_stdio_has_tty`, `src/coga/commands/launch.py:2361`), and an
agent's own Bash tool subprocess has neither — so the inner launch exits 2.

**Owner decision (2026-08-14): fix this structurally, not by wording.** The
wrapper agent must stop shelling out to a nested agent launch. The component
that already owns a real pty — the recurring REPL supervisor — should perform
the delegated launch itself, so a delegating template declares its delegation
rather than improvising it in prose. Two candidate mechanisms, implementer's
choice with the reasoning recorded in the PR:

1. A declarative delegation field on the recurring template's frontmatter
   (sibling to the existing `recipe:`), which `recurring_runner` honours by
   launching the delegated ticket directly under its supervisor — one agent
   session for the period, not two.
2. A fixed entry in `runner.RECIPES` that performs the supervised launch as
   deterministic plumbing (`recurring-scan` is already a recipe that launches
   agents), with the template naming it via `recipe:`.

Whichever lands, the `script -qec` pty recipe must stop being the sanctioned
pattern, and both documents must end up saying the same thing.

**Blast radius: all delegating wrappers, not just this one.** Audit every
recurring template for the double-hop shape and convert each. Today
`resolve-conflicts` is the only instance (see Context), but the context's
gotcha is written as generic guidance for *any* future wrapper, which is how
the pattern would spread.

## Context

### The two documents that disagree

- `coga/contexts/coga/recurring/SKILL.md:440-455` (under `## Gotchas`) —
  prescribes the workaround: run the delegation under a fake pty,
  `timeout 900 script -qec 'coga resolve-conflicts --agent claude' /dev/null`,
  and confirm success by reading the `bootstrap/resolve-conflicts` `slack:`
  line in `coga/log.md` rather than the captured stream (ANSI noise, plus the
  delegated session is torn down by the done sentinel seconds after its
  roll-up posts).
- `coga/recurring/resolve-conflicts/ticket.md:31` — "Recurring's outer agent
  supervisor remains responsible for TTY admission and the idle/max-session
  liveness bounds over the whole process tree." Also the frontmatter comment
  at line 5: "This template stays agent-backed so recurring's TTY admission
  … govern the whole delegated command."

**The template's sentence is true one level up and false one level down.**
The supervisor genuinely does own TTY admission for the *wrapper* session —
that is why `coga recurring` itself refuses to create an agent-backed period
task without a TTY (`src/coga/recurring.py:430,462`). It does not extend to a
nested launch the wrapper makes from inside its own tool shell. Preserve that
distinction in whatever replaces these passages; a reader who conflates the
two levels reproduces the original bug.

### Why this is a real defect, not a documentation nit

- 2026-08-13: the W33 run followed the template's framing, verified its tool
  shell has no TTY, judged the pty a design bypass, and terminally blocked
  (blocker `20260813T094004`, `coga/log.md:3287`). The sweep never ran.
- 2026-08-14: a rerun found the context section, ruled the pty sanctioned,
  and proceeded — then hit a *different* wall: the agent harness's own
  permission classifier refused to execute `script -qec` (`coga/log.md:3428`).
  W33 still has not swept.

So the wording fix alone would not make this job run unattended; only removing
the shell-out does. That second blocker is evidence for the structural
direction, not separate work — it should be moot once the supervisor performs
the launch.

### Recurring template taxonomy (what "audit all delegating wrappers" means)

Templates come in two shapes (`coga/contexts/coga/recurring/SKILL.md:118-135`):
a known `recipe:` selects deterministic headless execution; without one the
task is agent-backed and runs under the REPL supervisor.

- `recipe:` — `digest`, `branch-sweep`, `autoclose-merged`,
  `blocker-reminders`, `skill-update`. No agent, no TTY, unaffected.
- agent-backed — `dream` (does its work in-session; fine) and
  `resolve-conflicts` (the only double-hop).

Confirm that inventory still holds at implementation time rather than trusting
it; the deliverable is that the double-hop shape is unavailable or unnecessary
going forward, not just that one template changed.

### Files to touch, and the packaged twin rule

- `coga/recurring/resolve-conflicts/ticket.md` — **has an identical packaged
  twin** at `src/coga/resources/templates/coga/recurring/resolve-conflicts/ticket.md`
  (verified byte-identical). Both must change together, per CLAUDE.md.
- `coga/contexts/coga/recurring/SKILL.md` — repo-local only; there is **no**
  packaged twin (packaged `coga/` contexts live under
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/` and that set
  does not include `recurring`). Do not create one as a side effect.
- Code: `src/coga/recurring.py`, `src/coga/recurring_runner.py`, and
  `src/coga/runner.py` / `src/coga/aliases.py` depending on which mechanism is
  chosen. Add tests under `tests/` named for the module changed, and run
  `coga validate --json` — it statically resolves recurring templates,
  including `recipe:` names against the fixed registry.
- The microkernel rule in CLAUDE.md constrains option 2: a recipe is a fixed
  name in `runner.RECIPES`, not a plugin, and skills describe how to invoke
  commands rather than supplying launch plugins.

### Out of scope

- Adding a harness permission rule for `script -qec` to work around the
  2026-08-14 blocker. The structural fix should remove the need; do not ship
  both.
- Running the W33 sweep itself. That is `recurring/resolve-conflicts`'s work,
  currently paused, and it should be re-run by the owner after this lands.
- `coga/period-task` guidance and the `resolve-conflicts` command runbook
  under `bootstrap/resolve-conflicts` — the operation itself is not changing,
  only how it gets launched.

### Provenance

Dream 2026-W33 stale finding F5 (`coga/tasks/recurring/dream/ticket.md:307,374`).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
