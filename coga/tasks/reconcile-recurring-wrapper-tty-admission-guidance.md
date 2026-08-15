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
wrapper agent must stop shelling out to a nested agent launch. Nothing needs
to manufacture a terminal: `recurring_runner` already runs in the operator's
own terminal and already calls `launch` in-process
(`src/coga/recurring_runner.py:684,709`), so it can launch the delegated
ticket directly instead of launching a wrapper that re-launches it. A
delegating template should *declare* its delegation rather than improvise it
in prose. Candidate mechanisms are in Context; pick one, record the reasoning
in the PR, and see the note there on when that choice has to be made.

Whichever lands, the `script -qec` pty recipe must stop being the sanctioned
pattern, and every document describing the shape must end up saying the same
thing.

**Blast radius: all delegating wrappers.** `resolve-conflicts` is the only
current instance — the inventory in Context was taken for this ticket and
re-verified, so re-confirming it is a few minutes, not a work item. The point
of the wider framing is that the context's gotcha is written as generic
guidance for *any* future wrapper: the deliverable is that the double-hop
shape becomes unnecessary or unavailable going forward, not merely that one
template changed.

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

### Candidate mechanisms, and the design question nobody has answered

These are not equally sound. Weigh them against the taxonomy facts below
before writing code.

**When to decide, and when to stop.** This choice is made before the first
line of code, but `code/with-review` only exposes it to a reviewer after the
implementation exists — so a wrong pick is discovered late and rewritten.
Owner's instruction (2026-08-14): the implement step picks and justifies the
choice in the PR, but if option 1's "who marks the period task done" question
has no clean answer, `coga block` with the specific ask rather than guessing.
All three options stay live; none is pre-rejected.

1. **Declarative delegation field** on the template frontmatter, sibling to
   `recipe:`, honoured by `recurring_runner`'s existing in-process
   `launch_cmd` call. The delegating template stays agent-backed, so the
   pre-create TTY refusals at `src/coga/recurring.py:430,462` keep guarding a
   headless sweep — correct behaviour preserved.
   **Its unanswered question:** every piece of period-task bookkeeping in the
   runner is written against the period `TaskRef` — `mark_in_progress`,
   `_stop_if_unfinished_after_launch`, `_advance_serviced_period`, the log and
   Slack lines. Launching `bootstrap/resolve-conflicts` instead means one
   session on a *bootstrap* ref, with the period task's transitions happening
   around it and no session inside to run `coga mark done`. Settle this before
   committing to the option; it is the actual design work in this ticket.
2. **A fixed `runner.RECIPES` entry** named by the template's `recipe:`.
   **Carries a specific defect — do not choose it without answering this.**
   The recipe/agent split *is* the mechanism of the TTY gate: both raises read
   `if not allow_agent and not template.recipe`. Giving this template a
   `recipe:` moves it into the class explicitly exempt from TTY admission, so
   a headless sweep would create the period task, run the recipe, and only
   then hit the agent-launch refusal at `src/coga/commands/launch.py:546` —
   relocating a clean pre-create refusal into a mid-run failure, which is
   strictly worse for an unattended job. It also contradicts two shipped
   documents (see files to touch). The tempting precedent — "`recurring-scan`
   is already a recipe that launches agents" — does not transfer:
   `recurring-scan` launches agents only because `coga recurring` invoked it
   from the operator's shell, and it re-checks `_interactive_stdio_has_tty()`
   and filters on the result. It is not evidence that recipes have terminals.
3. **No second session at all.** Templates may name a `workflow:`, and `dream`
   already does its work in-session. The delegated work is a stateless prose
   runbook at `coga/bootstrap/resolve-conflicts/ticket.md`; carrying it into
   the period task's own session by context or skill attachment removes the
   double hop with no code change and no new frontmatter field.
   **Its tension:** that runbook explicitly says "do not create a task per run
   … do not run `coga bump` / `coga mark`", which fights the period-task
   lifecycle, and the human-facing `coga resolve-conflicts` alias must keep
   working for on-demand use either way. Ruling this out is fine; ruling it
   out silently is not — record the reason.

### Recurring template taxonomy (what "audit all delegating wrappers" means)

Templates come in two shapes (`coga/contexts/coga/recurring/SKILL.md:121-126`):
a known `recipe:` selects deterministic headless execution; without one the
task is agent-backed and runs under the REPL supervisor.

- `recipe:` — `digest`, `branch-sweep`, `autoclose-merged` (its recipe name is
  `autoclose`, not the template name — grepping `runner.RECIPES` for
  `autoclose-merged` finds nothing), `blocker-reminders`, `skill-update`. No
  agent, no TTY, unaffected.
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
- `coga/contexts/coga/architecture/SKILL.md:525-527` — states the taxonomy
  this change alters, verbatim: "A recurring template selects this path with
  `recipe:`; without one, its period task is an agent launch and therefore
  needs a TTY." Any mechanism makes that incomplete. **Has a byte-identical
  packaged twin** at
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md`;
  both move together.
- `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md:307`
  — enumerates the recipe registry by name; option 2 makes it stale. **This
  one is packaged-only: there is no `coga/contexts/coga/cli/`.** The usual
  "check the live copy and the packaged copy" habit misses it precisely
  because there is no live copy to start from.
- Code: `src/coga/recurring.py`, `src/coga/recurring_runner.py`, and
  `src/coga/runner.py` / `src/coga/aliases.py` depending on which mechanism is
  chosen. The human-facing `coga resolve-conflicts` alias
  (`src/coga/aliases.py:67`) must keep working unchanged for on-demand use —
  do not repurpose it as part of the fix.
- The microkernel rule in CLAUDE.md constrains option 2: a recipe is a fixed
  name in `runner.RECIPES`, not a plugin, and skills describe how to invoke
  commands rather than supplying launch plugins.

### Acceptance

- **The test that distinguishes a correct fix from a relocated bug:** a
  headless (no-TTY) sweep must still refuse the delegating template at
  *admission* — before the period task is created — and not fail mid-run.
  Name it explicitly in `tests/`.
- An attended sweep runs the delegated conflict work end to end with no
  `script`/pty invocation anywhere in the path.
- `coga validate --json` clean — it statically resolves recurring templates,
  including `recipe:` names against the fixed registry.
- Add tests under `tests/` named for the module changed, per CLAUDE.md.

### Out of scope

- Adding a harness permission rule for `script -qec` to work around the
  2026-08-14 blocker. The structural fix should remove the need; do not ship
  both.
- Running the W33 sweep itself. That is `recurring/resolve-conflicts`'s work,
  currently paused, and it should be re-run by the owner after this lands.
- The conflict-resolution *operation* itself. What the sweep does — which PRs
  it selects, how it rebases, verifies, force-pushes, and rolls up — is not
  changing; only how it gets launched. The runbook at
  `coga/bootstrap/resolve-conflicts/ticket.md` (packaged twin under
  `src/coga/resources/templates/coga/bootstrap/resolve-conflicts/`) is
  therefore edited only if the chosen mechanism forces it — option 3 would,
  and its sentence describing the `coga resolve-conflicts` alias sits in the
  blast radius if the alias path moves.
- `coga/period-task` guidance.

### Provenance

Dream 2026-W33 stale finding F5 (`coga/tasks/recurring/dream/ticket.md:307,374`).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
