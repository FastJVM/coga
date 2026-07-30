---
slug: update-contewt-bloxk-for-ordering-megalunach-uncle
title: Surface megalaunch drain order and the numbered-task convention in `--help`
status: draft
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

`coga megalaunch` orders the tasks it drains, and the ordering is expressive:
oldest-first by first `coga/log.md` line, except that a sub-directory whose
tasks carry `1-`/`2-`/`3-` prefixes runs as one contiguous block in number
order. That is how you sequence a pipeline — and because it is a naming
convention rather than a flag, there is nothing to stumble onto.

`coga megalaunch --help` never mentions it. Someone reading the help text sees
`DIR`, `--pick`, `--relaunch`, `--max-tasks`, `--agent` and concludes the
command has no ordering story. That is the whole bug: the behavior is correct
and the long-form docs are fine, but the surface people actually read is
silent.

Fix the help text, add regression tests so the surface can't go quiet again,
and decide whether the queued-session directive should mention it too.

## Context

### Where the facts live — read, don't re-derive

The behavior is well documented already. Read these rather than reconstructing
the rules from source:

- `docs/reference.md:122-128` — complete and accurate: age ordering, the
  `1-schema`/`2-migrate`/`3-cutover` convention, block anchoring, unnumbered
  siblings, top-level exemption, `--pick` parity, `status --order-by created`
  parity, the `coga validate` duplicate warning.
- Packaged `bootstrap/contexts/coga/cli/SKILL.md:662-688` — the fullest
  writeup, "**Drain order.**" section. Not attached to this ticket (58 KiB
  composed, ~15k tokens); open the file directly.
- `src/coga/service_order.py:1-27` — module docstring, the implementation's own
  statement of the rules.

Two details worth knowing because they are easy to get wrong in help text:

- The prefix match is strict — `^(\d+)-` (`service_order.py:37-40`). `02-` ==
  `2-`, `10-` sorts after `9-`, and `2fa-login` is **not** numbered.
- **`--pick` does not order anything.** The selection is a set filter applied
  over the already-service-ordered queue (`megalaunch.py:211-214`), so pick
  order is discarded. Worth a clause in the help text; it is a real trap.

### The gap

- **`src/coga/commands/megalaunch.py:48-93`** — the Typer help strings. Silent
  on ordering. This is the fix.
  Note `coga pick` is an argv alias (`pick = "megalaunch --pick"`), **not** a
  separate command — there is no second docstring to edit, and inventing a
  `pick` command would violate the microkernel rule in `CLAUDE.md`.
- **`src/coga/resources/prompt-megalaunch.md`** (32 lines) — the directive
  injected into every queued session; no ordering content. **Owner decision,
  see below** — do not edit without resolving it.

Deliberately out of scope, with reasons — do not "fix" these:

- **A megalaunch `SKILL.md`.** Its absence is not an oversight. Commit
  `2741d36f` (#550) removed it: megalaunch is on-demand only, unlike the
  recipe-backed `autoclose/sweep`, `blockers/remind`, `branch-sweep/sweep`.
  `paths.py:11-16` still carries the migration message. Re-adding it reverses a
  merged decision.
- **A repo-side `coga/contexts/coga/cli/` copy.** Context refs fall back to the
  packaged copy (`resolve_context_path`, `paths.py:133-142`), so `coga/cli`
  already resolves in this repo — `coga/tasks/nightly-auto-drain-run-for-ready-tickets.md:11`
  attaches it today. Adding a repo copy would create a 1,058-line sync burden
  that currently does not exist.
- **`docs/reference.md`.** Already correct. Leave it.
- **`README.md`, `AGENTS.md`, `CLAUDE.md`, the `usage`/`architecture`
  contexts.** Ordering is off-topic for their framing.

### Owner decision — `prompt-megalaunch.md`

Open question the implementer must resolve with the owner before touching it:
that file is a *behavioral directive to the running agent* (announce your plan,
don't ask-and-wait, use `coga block`), and its word budget is spent on every
queued session. A queued agent has already been selected and ordered, so drain
order is arguably not actionable for it.

The case *for* including it: an agent running under megalaunch may create
follow-up tasks, and knowing the convention lets it sequence them correctly.

Raise this in the blackboard and get an answer rather than deciding silently.

### Tests — cover discoverability, not the ordering logic

**The ordering logic is already well covered — do not add tests there.**
`tests/test_service_order.py` has 9 focused tests spanning every edge case
(`2fa-login` not numbered, top-level ignored, no-log-line sorts last, block
anchoring, per-directory numbering, nested groups), plus
`tests/test_megalaunch.py:1709,1757` end-to-end and
`tests/test_validate.py:1619-1662` for duplicate positions. Duplicating that is
waste.

What is untested is the thing that actually failed — **nothing asserts any
user-facing surface states the convention**, which is why it could go missing
with every test green. Add a regression test that `coga megalaunch --help`
mentions the drain order and the numbered-task convention. Assert on substance
(oldest-first, `1-`/`2-`/`3-` sequencing), not exact prose, so wording stays
editable. Extend an existing test module rather than adding one.

Run `python -m pytest` and put the exact command in the PR.

### Scope boundary

Permitted: the megalaunch help strings, the test above, and — if the owner
approves — `prompt-megalaunch.md`.

**Do not change ordering logic, `coga.service_order`, or any runtime
behavior.** The convention is correct as built; this ticket only makes it
discoverable. If you conclude the convention itself is wrong, stop and raise it
— that is a different ticket.

### Done looks like

Someone who runs `coga megalaunch --help` and reads nothing else learns that
tasks drain oldest-first, that naming a sub-directory's tasks `1-`/`2-`/`3-`
sequences them, and that it is a naming convention rather than a flag. A test
fails if that stops being true.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
