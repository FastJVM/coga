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
workflow: code/with-review
secrets: null
script: null
---

## Description

`coga megalaunch` has real ordering capability — tasks drain oldest-first by
first `coga/log.md` line, and a sub-directory whose tasks carry `1-`/`2-`/`3-`
prefixes runs as one contiguous block in number order, anchored where its
oldest task would have run. The numbering convention is effectively invisible
to whoever is about to run a megalaunch: there is no flag to stumble onto,
because it is a naming convention. They serialize by hand, or assume ordering
isn't supported at all.

The surprise is that this is **not** a case of nobody writing it down. A full,
accurate writeup exists in the *packaged* `bootstrap/contexts/coga/cli`
context. It just isn't reachable from the surfaces a launcher reads — and in
this repo specifically it isn't reachable at all, because there is no repo-side
copy of that context. Bootstrapped repos get the drain-order rules; coga's own
repo does not.

So the work is two-part: decide how the existing writeup reaches this repo's
launchers, and close the surfaces that are silent regardless — `coga megalaunch
--help`, the queued-agent prompt directive, and the missing megalaunch skill.

## Context

### What the behavior actually is (verified — do not re-derive)

Source of truth is `src/coga/service_order.py`. Reuse the existing accurate
prose rather than inventing new phrasing:

- **Rule 1 — age.** Oldest-first by the earliest `coga/log.md` line per ref
  (`first_activity_map`, `src/coga/logfile.py:99-129`). Committed content, so
  order survives clones where mtimes collapse. Tasks with no parseable log line
  sort **last** (`_NO_TIMESTAMP`, `service_order.py:44`), then by `id_slug`.
- **Rule 2 — numeric prefix on the slug leaf.** `_NUMBERED =
  re.compile(r"^(\d+)-")` (`service_order.py:37-40`), deliberately strict:
  `02-` == `2-`, `10-` sorts after `9-`, and `2fa-login` / `schema-1` are
  **not** numbered.
- A sub-directory **opts in** by having at least one `<n>-` task; it then runs
  as one contiguous block **anchored at its oldest member**, so it never jumps
  the queue. Inside the block: numbered by number, then unnumbered siblings by
  age. Top-level `1-foo` is ignored — `tasks/` itself is not a pipeline.
- **`--pick` does not order anything.** The selection is a *set filter* applied
  over the already-service-ordered queue (`megalaunch.py:213-218`), and the
  saved `.coga/megalaunch-selection.json` is a membership list, not a queue.
  Pick order is discarded. This is a genuine gotcha and worth stating.
- **No parallelism.** Strictly serial interactive PTY launches; requires a TTY.
- Dependency drain (`megalaunch.py:330-495`) is **separate from numbering** and
  text-based: a blocker `--reason` naming an exact path-qualified slug is
  retried when that task finishes. Don't conflate the two mechanisms.
- `coga validate` warns `duplicate-task-number` when two tasks in one directory
  claim the same position (`src/coga/validate.py:809-848`). Gaps (`1-`, `2-`,
  `5-`) are deliberately fine.

Existing prose to reuse: `docs/reference.md:122-128`,
`src/coga/megalaunch.py:38-42`, `service_order.py:1-27`, and — the fullest
version — packaged `bootstrap/contexts/coga/cli/SKILL.md:652-678`.
Tests that pin the behavior: `tests/test_service_order.py` (9 tests),
`tests/test_megalaunch.py:1709,1757`, `tests/test_validate.py:1619-1662`.

### Where the gap is (verified by grep, 2026-07-30)

**The root cause — a packaged-only context.**
`src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md:652-678`
has a dedicated "**Drain order.**" section covering the whole rule set. There
is **no `coga/contexts/coga/cli/` directory in this repo**, so it is the one
shipped context with no repo-side copy. Bootstrapped repos load it; coga's own
agents get only the one-line pointer at
`coga/contexts/coga/codebase/SKILL.md:35-36` ("the drain order (age plus
numbered sub-directories) in `service_order.py`"), and `codebase` is itself
repo-only and never ships. **Decide how to resolve this** — add the repo-side
`cli` context copy, or lift the drain-order facts into a context this repo
already loads. Don't silently pick one; say which and why in the blackboard.

**Surfaces that are silent everywhere:**

- `coga megalaunch --help` — documents `DIR`, `--pick`, `--relaunch`,
  `--max-tasks`, `--agent` and **says nothing about drain order**. Highest-value
  fix: it is where a launcher actually looks.
- `src/coga/resources/prompt-megalaunch.md` (32 lines) — the directive injected
  into every queued session. Zero mentions of ordering. Agents running *under*
  megalaunch are never told the convention exists.
- `src/coga/resources/templates/coga/bootstrap/skills/coga/megalaunch/` —
  contains **only** a stale untracked `run/__pycache__/*.pyc` and **no
  `SKILL.md`**, while every sibling recipe skill (`autoclose/sweep`,
  `blockers/remind`, `branch-sweep/sweep`) has one. Also delete the stray
  `.pyc`.
- `coga/contexts/coga/usage/SKILL.md:56` — megalaunch mentioned once, about
  usage capture. No ordering.
- `coga/contexts/coga/architecture/SKILL.md:350,431-432,578` — documents the
  dependency drain and prompt composition; zero hits for numbering.
- `README.md:11,57` and `AGENTS.md`/`CLAUDE.md:19` — scheduling/microkernel
  framing. Ordering is arguably out of place there; README:11 "schedules the
  queue" is unexplained and could take a clause. Decide, don't reflexively edit.

### Tests — cover discoverability, not the ordering logic

Megalaunch is an important command and this ticket ships tests. Aim them
correctly:

**The ordering logic is already well covered — do not add more there.**
`tests/test_service_order.py` has 9 focused tests including every edge case
(`2fa-login` is not numbered, top-level numbering ignored, no-log-line sorts
last, block anchoring, per-directory numbering, nested groups), plus
`tests/test_megalaunch.py:1757` end-to-end. Duplicating that is waste.

**What is untested is the thing that actually failed: discoverability.**
Nothing asserts that any human- or agent-facing surface states the convention,
which is why it could go missing without a red test. Add regression tests that
would have caught this:

- `coga megalaunch --help` output mentions the drain order and the numbered-task
  convention. Assert on substance (oldest-first, `1-`/`2-`/`3-` sequencing), not
  exact prose, so wording can be edited without breaking the test.
- The packaged megalaunch skill `SKILL.md` exists and is non-empty — a template
  completeness check, ideally generalized so every packaged recipe skill
  directory must contain a `SKILL.md`. That would have caught the empty
  directory too.
- If a context ends up duplicated repo↔packaged, a test that the two copies
  match, following whatever existing sync-test pattern the suite already uses.

Prefer extending existing test modules over inventing new ones. Run
`python -m pytest` and report the exact command in the PR.

### Scope boundary — read this before widening

This is a **documentation and discoverability ticket**. Permitted changes:
markdown surfaces, the CLI help/docstring text on `coga megalaunch` (and `coga
pick` if it needs the same line), the missing packaged skill, and the tests
above.

**Do not change ordering logic, `coga.service_order`, or any runtime
behavior.** The convention is correct as built; this ticket only makes it
discoverable. If you conclude the convention itself is wrong, stop and raise it
— that is a different ticket.

Workflow note: this started as `docs/with-review` and was moved to
`code/with-review` deliberately, because the ticket now ships tests and
`docs/with-review` runs none. The peer-review step must run `python -m pytest`
and `/code-review` on the diff, and must *also* check repo↔packaged sync, which
is the failure mode a code-focused review is most likely to skim past.

### Repo ↔ packaged sync

Per `CLAUDE.md`, shipped contexts and templates exist twice: the live repo copy
under `coga/` and the packaged copy under `src/coga/resources/templates/coga/`.
Any edit to a shipped context or skill must land in **both**, or the difference
must be intentional and documented. The peer-review step of `docs/with-review`
checks exactly this — don't make it find a missed copy.

Current drift, already surveyed (`diff -q` per context):

- **Byte-identical both sides:** `architecture`, `important`, `patterns`,
  `period-task`, `principles`, `sync`. Edit these in both places.
- **Repo-only, never packaged:** `codebase`, `current-direction`,
  `extension-model`, `project-stage`, `recurring`, `roadmap`, `secrets`,
  `usage`. Editing these does *not* need a packaged counterpart.
- **Packaged-only, no repo copy:** `cli`. This is the asymmetry the ticket
  turns on — see the root-cause note above.

Existing drift is out of scope to fix wholesale. Touch only what the ordering
docs require.

### Done looks like

Someone who has never used megalaunch can learn, without reading source, that
(a) tasks drain oldest-first, (b) numbering a sub-directory's tasks
`1-`/`2-`/`3-` sequences them, and (c) it is a naming convention, not a flag —
reaching that from `coga megalaunch --help` plus a context this repo actually
loads. The packaged megalaunch skill exists. The `cli`-context asymmetry is
resolved one way or the other, with the choice recorded.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
