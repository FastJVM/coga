---
slug: update-contewt-bloxk-for-ordering-megalunach-uncle
title: Document megalaunch drain order and the numbered-task convention where launchers actually read
status: draft
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow: docs/with-review
secrets: null
script: null
---

## Description

`coga megalaunch` has real ordering capability — tasks drain oldest-first by
first `coga/log.md` line, and a sub-directory whose tasks carry `1-`/`2-`/`3-`
prefixes runs as one contiguous block in number order, anchored where its
oldest task would have run. This shipped with the tool, but the docs never
caught up: the behavior is written down only in `docs/reference.md` and in
Python docstrings. Neither surface is what a person or agent about to run
`coga megalaunch` actually reads.

The consequence is that the numbering convention is effectively invisible.
Someone sequencing a multi-step pipeline has no way to discover that naming
tasks `1-schema`, `2-migrate`, `3-cutover` is how you express order — there is
no flag to stumble onto, because it is a naming convention. They either
serialize by hand or assume ordering isn't supported.

Close the gap at the surfaces that get read: the operator-facing coga contexts,
the megalaunch prompt/skill layer, and the CLI help text itself.

## Context

### What the behavior actually is (verified, don't re-derive)

Source of truth is `coga.service_order`. The two authoritative prose
statements already exist and are accurate — reuse their wording rather than
inventing new phrasing:

- `src/coga/megalaunch.py:38-42` (module docstring): "Tasks are serviced
  oldest-first (first `coga/log.md` line per ref — committed content, so the
  order survives clones where file mtimes don't), except that a sub-directory
  holding `1-`/`2-`/`3-` prefixed tasks runs as one contiguous block in number
  order, anchored where its oldest task would have run."
- `docs/reference.md:122-128` — the fullest existing writeup. Adds the edge
  cases: unnumbered siblings follow the numbered ones; a sub-tree with no
  numbered task (or a top-level `1-foo`) is unaffected; `--pick` lists in the
  same order; `coga status --order-by created` matches; `coga validate` warns
  when two tasks in one directory claim the same position.
- `src/coga/megalaunch.py:723-727` — picker docstring, confirms the picker
  lists in drain order.

### Where the gap is (verified by grep, 2026-07-30)

- `coga/contexts/coga/usage/SKILL.md` — mentions megalaunch once (line 56),
  only in a list of interview-capable commands. **No ordering, no numbering.**
  This is the highest-value fix: it is the operator-facing usage context.
- `coga/contexts/coga/architecture/SKILL.md` — megalaunch at lines 350, 431-432,
  578 (blocked re-listing, prompt composition, core-command status). **No
  ordering, no numbering.**
- `coga megalaunch --help` — documents `DIR`, `--pick`, `--relaunch`,
  `--max-tasks`, `--agent`. **Says nothing about drain order.** A launcher
  reading `--help` cannot learn the convention exists.
- `src/coga/resources/prompt-megalaunch.md` (32 lines) — zero hits for
  order/numbered.
- `src/coga/resources/templates/coga/bootstrap/skills/coga/megalaunch/run/` —
  zero hits for order/numbered.
- `README.md:11,57` and `AGENTS.md`/`CLAUDE.md:19` mention megalaunch but in
  scheduling/microkernel framing; ordering is out of place there. Probably
  leave alone — decide, don't reflexively edit.

### Scope boundary — read this before widening

This is a **docs ticket with a narrow code allowance**. The permitted code
change is the CLI help/docstring text on `coga megalaunch` (and `coga pick` if
it needs the same line) so `--help` states the drain order and points at the
numbering convention.

**Do not change ordering logic, `coga.service_order`, or any behavior.** The
convention is correct as built; this ticket only makes it discoverable. If you
conclude the convention itself is wrong, stop and raise it — that is a
different ticket.

`docs/with-review` was chosen deliberately over `code/with-review`, with the
tradeoff understood: the peer-review step reviews prose, accuracy, and
repo↔packaged sync rather than running `/code-review` and `python -m pytest`.
That is the right bar for a markdown-dominant diff. It stops being the right
bar if the code side grows past help-text strings — so if it does, escalate to
the owner rather than continuing under a workflow that won't test the change.

### Repo ↔ packaged sync

Per `CLAUDE.md`, shipped contexts and templates exist twice: the live repo copy
under `coga/` and the packaged copy under `src/coga/resources/templates/coga/`.
Any edit to a shipped context or skill must land in **both**, or the difference
must be intentional and documented. The peer-review step of `docs/with-review`
checks exactly this — don't make it find a missed copy.

### Done looks like

Someone who has never used megalaunch can learn, from `coga megalaunch --help`
and the coga usage context alone, that (a) tasks drain oldest-first, (b)
numbering a sub-directory's tasks `1-`/`2-`/`3-` sequences them, and (c) it is
a naming convention, not a flag.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
