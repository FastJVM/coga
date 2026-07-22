---
slug: build-an-order-for-megqlaunch
title: "megalaunch: drain blocked tickets whose dependency landed in the same run"
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- dev/code
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

`coga megalaunch` runs its queue oldest-first with no notion of ordering
between tickets. When ticket B needs ticket A to land first, B's agent
discovers the missing dependency mid-step and ends the session with
`coga block` — and that is terminal for the run. B stays parked even when A
completes minutes later in the *same* sweep, so the operator has to notice and
re-run megalaunch by hand. The same is true of a ticket that was already
`blocked` when the sweep started: it is skipped outright
(`skipped-unresolved-blocker`), even if this run lands the very thing it was
waiting for.

Add a **drain loop**. After the main sweep finishes, megalaunch re-examines
blocked tickets; for each one whose blocker is now satisfied it **resolves the
open blocker and then launches the ticket normally**; if any launched, it
restarts the walk from the top (an earlier drain may satisfy a later ticket).
A full pass that launches nothing is terminal — report and exit.

Deliberately *no* dependency model: no `depends_on:` frontmatter, no
topological sort, no new CLI flag. Satisfaction is decided by reading the open
blocker text off the blackboard, scanning it for a known task slug, and
checking whether that ticket has since finished.

## Context

### Decisions taken during ticket authoring (and why)

1. **Dependencies are discovered at run time, not declared.** A declared
   `depends_on:` / `after:` field plus a topological sort was considered and
   rejected — it is only as good as what someone remembers to declare, and the
   agent doing the work already discovers the real dependency for free.
2. **The agent blocks; megalaunch decides when to retry.** `coga block` keeps
   its current signature. No `--waiting-on` flag, no new ticket field.
3. **The satisfaction check must be pure Python — never spawn an agent to ask
   "are you still blocked?"** Before relaunching a blocked ticket, megalaunch
   reads its open blocker text, scans for known task slugs, and proceeds only
   if a named ticket has since finished.
4. **Satisfaction resolves the blocker, then launches — it is a one-way
   transition.** On a satisfied dependency megalaunch calls
   `resolve_open_blockers(...)` with an explanatory answer *before* launching,
   so the ticket enters the launch path as an ordinary reactivated task with no
   open asks. This is what makes the loop terminate: a drained ticket leaves the
   eligible set by construction, so it cannot be picked up again on the next
   pass regardless of how its session ends. A heuristic "did it make progress?"
   rule was considered and rejected — see the termination risk below for why it
   does not terminate.
5. **Fixed-point loop, not a single retry pass.** Walk all blocked tickets;
   drain any that are satisfied; if any launched, **restart the walk from the
   top** (an earlier drain may satisfy a later ticket). A full pass that
   launches nothing ends the run.
6. **Retry scope is every blocked ticket in scope**, not only the ones this run
   blocked. Chosen for simplicity and flexibility. Accepted cost: a
   human-parked blocker whose reason incidentally names a finished slug gets
   drained and relaunched once — and because draining resolves the blocker,
   that is not self-correcting. The answer text written by
   `resolve_open_blockers` must therefore say plainly that megalaunch resolved
   it automatically and name the dependency it matched.
7. **Convention, not schema.** Add one line to the queue directive telling
   agents to name the blocking ticket's slug in `--reason`. This is what makes
   the scan fire; without it a blocker phrased as "waiting on the schema
   migration" parses to nothing.
8. **Drain relaunches count against `--max-tasks`** like any other launch. The
   loop must not be able to exceed the operator's stated budget.

### Codebase pointers

*Line numbers were verified at authoring time; treat them as starting points,
not gospel.*

- `src/coga/megalaunch.py` — module docstring (`:38`) states today's order:
  oldest-first by first `coga/log.md` line, via `first_activity_map` (imported
  at `:70`, implemented in `src/coga/logfile.py`) and `_tasks_oldest_first`
  (`:538`). `run_megalaunch` is at `:140`.
- Blocked tickets are skipped today with outcome `skipped-unresolved-blocker`
  (`:581`, `:587`). The `MegalaunchOutcome` literal (`:97`) and the counts dict
  in `MegalaunchRun.counts` (`:126–134`) both need updating for whatever the
  drain loop reports.
- Reactivating a blocked ticket for launch exists today only on the *selection*
  path (`_activate_for_launch`); the sweep path has no such step. The drain loop
  needs one.
- `_launch_until_stop` (`:751–759`) calls `_reblock_unresolved`, which returns a
  ticket to `blocked` when the session exits `in_progress` with any ask still
  open. Decision 4 exists to keep the drain path out of that trap.
- `open_blockers(ticket_path) -> list[Blocker]` lives in
  `src/coga/blackboard.py:285` and is **already imported** by megalaunch
  (`:52`) — the read side exists. Its sibling `resolve_open_blockers`
  (`blackboard.py:290`) is the write side decision 4 needs.
- `coga block` (`src/coga/commands/block.py`) appends the free-text reason via
  `append_blocker` (`:48`) and sets `status: blocked` (`:54`). `--reason` is
  required and non-empty (`:26–28`), so there is always text to scan. Note
  megalaunch itself writes **no** blocker record today — `_reblock_unresolved`
  calls `mark_blocked`, which flips `status:` and does not touch `## Blockers`.
- `--max-tasks` already exists (`src/coga/commands/megalaunch.py:73`) and is the
  natural budget for decision 8.
- Queue directive to amend: `src/coga/resources/prompt-megalaunch.md`.
- Tests: `tests/test_megalaunch.py`.
- Per `CLAUDE.md`, behavior changes update the matching context in the same PR.
  Megalaunch behavior is described in `coga/contexts/coga/architecture/SKILL.md`
  (megalaunch at `:302`, `:347`, `:387`). Keep the live copy under `coga/` and
  the packaged copy under `src/coga/resources/templates/coga/` in sync.

### Risks the implementer must handle

- **Termination is the whole design.** A "did it make progress?" rule was
  considered and does **not** work: a drained ticket that does real work and
  bumps, but never runs `coga unblock`, is returned to `blocked` by
  `_reblock_unresolved` with the same blocker still naming the same finished
  slug. It is then eligible again *and* it made progress, so the loop restarts
  and relaunches it forever. Decision 4 (resolve the blocker before launching)
  is the structural fix — do not replace it with a progress heuristic.
- **A drained relaunch must not inherit the blocker-resolution preamble.**
  `compose.py:156–176` injects it whenever open asks exist, and
  `prompt-blocker-resolution.md` tells the agent to *discuss the asks with the
  human* — wrong in an unattended queue. Decision 4 avoids this by construction
  (no open asks at launch time). Any alternative design must handle it another
  way. The `prompt-megalaunch.md` amendment in decision 7 is for a different
  purpose and does not cover this.
- **"Finished" has three states, not two.** A dependency may be `done`, or it
  may be *gone*: a session earlier in the same sweep can legitimately retire a
  finished task and delete its directory (`megalaunch.py:261–266`,
  `bootstrap/delete-task`). A naive `status == "done"` check raises
  `TicketNotFoundError` on the most completely finished case and treats it as
  unsatisfied. Handle both.
- **Slug scanning is lossier than it looks.** `append_blocker` writes the
  blocker as a **single line** and the parse regex captures the reason as the
  rest of that line — so a multi-line `--reason` silently loses everything after
  the first line, including a slug on line 2. Slugs are also truncated to ~50
  chars and nested tickets carry a `dir/slug` id, so an agent paraphrasing from
  memory will often not produce an exact match. False negative = ticket stays
  blocked (status quo, acceptable). False positive = an unwanted drain that
  decision 6 says must be legible in the resolution text.
- **Result accounting.** Each drain appends a second `MegalaunchResult` for a
  slug already in `run.results`, so `counts` double-counts and
  `render_run_summary` lists the slug twice. Decide whether a drain supersedes
  the earlier result or is reported as its own line.
- **Sweep scope is narrower than "every blocked ticket" implies.** `_run_sweep`
  (`:279`) skips tickets whose `owner != cfg.current_user`, and the queue is a
  snapshot taken before the first launch — so a ticket blocked *and created*
  mid-run is invisible to the drain loop unless it re-lists.
- **Every drain relaunch is a real interactive REPL** under the same TTY and
  the same idle-timeout / max-session backstops as the main sweep. The loop
  must not defeat those backstops.

### Open questions for the implement step

- Does the drain loop run for the default sweep only, or also for explicit
  `--pick` / `--relaunch` selections?
- Should the terminal pass report still-blocked tickets distinctly from ones
  that were never eligible?

### Out of scope

Declared dependency fields; topological reordering of the main sweep;
persisting dependency information across runs; changing `coga block`'s CLI
signature.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

---

## Evaluator review

*Independent cold read by a fresh session that did not see the authoring interview. Verbatim.*

### 1. Description clarity

Good enough to start, and unusually well-scoped for a cold read. Three short paragraphs give the problem (B blocks on A, A lands in the same sweep, B stays parked), the fix (post-sweep drain loop, fixed-point, terminal when a full pass launches nothing), and the explicit non-goals (no `depends_on:`, no topo sort, no new flag). An agent picking this up cold knows what to build in the first 30 seconds.

Two things the Description asserts that the code doesn't quite support:

- **"ends the session with `coga block` — and that is terminal for the run."** Accurate for the ticket, but understated: in the default sweep a blocked ticket is *never launched in the first place* (`megalaunch.py:562-581` returns `skipped-unresolved-blocker`). So the drain loop has two distinct populations — tickets this run blocked, and tickets that were already blocked at sweep start and got skipped. The Description reads as if only the first exists; decision 5 says both. Worth reconciling before launch.
- **"repeats from the top until a full pass launches nothing."** See §6 — as written this rule does not terminate in the most likely case.

### 2. Workflow fit (`code/with-review`)

Fits. This is a real code change in `src/coga/` with test surface, doc/context sync obligations, and non-obvious design judgment (termination, blocker record shape, prompt interaction) — exactly the case for a peer-review pass before the PR. `implement → peer-review (other-agent) → open-pr (requires: pr) → review (owner)` is the repo's default for this class; the adjacent megalaunch tickets (`bug-if-not-on-megalaunch-don-t-block-ask`, `add-a-status-canceled-for-ticket`) use the same workflow.

The one mismatch worth naming: the ticket carries three unresolved **Open questions for the design/implement step** plus a "exact shape is a design-step decision" (decision 6). `code/with-review` has no design step — the implement agent will answer all four unilaterally and the human first sees them at step 4 (`review`), after the PR is open. `code/design-then-implement` exists in this repo and is used by at least one other ticket. Given that decision 6 as written is factually wrong about the code (see §6), a design step would likely pay for itself here. That said, the Context section is opinionated enough that a competent implementer can pick sane defaults; this is a judgment call, not a blocker.

### 3. Contexts

`dev/code` is the right and standard attachment — `code/open-pr` reads `branch:`/`worktree:` from `## Dev` and the step declares `requires: pr`, so the convention is load-bearing.

**But it is largely redundant at the step where it costs the most.** `src/coga/resources/templates/coga/bootstrap/skills/code/implement/SKILL.md:33-36` already tells the agent to write `branch:` and `worktree:` under `## Dev`, with the same escaping rules, and explicitly says "See the `dev/code` context." The step skill isn't in your prompt-report breakdown (the ticket is unfrozen, so no step skill is composed yet); once step 1 freezes, `code/implement` adds ~8 KiB and the total goes to roughly 28 KiB, at which point `dev/code`'s 1253 tokens are buying very little marginal information. If you want a trim, this is the honest candidate — not because it's irrelevant, but because it's duplicated downstream. I'd keep it anyway for the `open-pr` step and consistency with the repo's other code tickets; it is not worth copying facts out of it into `## Context`.

**Missing:** nothing critical, but note the Context section itself says the PR must update `coga/contexts/coga/architecture/SKILL.md` (36 KiB) and keep the live/packaged copies in sync. Attaching `coga/architecture` would more than double the prompt for a doc edit the implementer can do by reading the file at three named line numbers — correctly left as a pointer. `coga/codebase` (16 KiB, defines source layout and test expectations) is the other plausible add and is paired with `dev/code` on several sibling tickets; I'd skip it here since the ticket already names every file to touch including the test file.

**Size flag:** no layer exceeds 40%. Largest is `base_prompt` at 1800 tok (35.5%), which is package-owned and not yours to trim. `ticket_context` is 24.7% and `task_context` 22.2% — the two ticket-authored layers together are 47%, which is high but defensible: the `## Context` is decision rationale a cold agent genuinely needs, not padding.

### 4. Scope

Reasonable — one coherent behavior change. The out-of-scope list does real work (declared dependency fields, topological reordering, cross-run persistence, `coga block` CLI changes are all excluded).

The hidden scope creep is in the *implicit* surface, not the stated one. Landing this touches: a new drain phase in `run_megalaunch`, blocked→active reactivation in the sweep path (which today only exists in the selection path, `_activate_for_launch`), the `MegalaunchOutcome` literal and `counts` dict, `render_run_summary`, `prompt-megalaunch.md`, `tests/test_megalaunch.py`, and two copies of `architecture/SKILL.md`. That's still one PR, but it's a bigger one than the three-paragraph Description implies.

### 5. File:line pointer accuracy

I verified every one. Summary: **substantively correct, several off by one or pointing at an import rather than a definition.** None will send an agent to the wrong file; a couple will send it to a blank line.

| Ticket claim | Actual | Verdict |
|---|---|---|
| docstring order statement `:39` | statement starts at `:38`; `:39` is its second line | off by one, harmless |
| `first_activity_map` `:70` | `:70` is `from coga.logfile import first_activity_map` | correct as an *import* pointer; the implementation is in `src/coga/logfile.py`, which the ticket doesn't say. Mildly misleading |
| "ordering helper around `:543`" | `_tasks_oldest_first` is defined at `:538`; `:543` is inside its docstring | "around" saves it |
| `run_megalaunch` `:140` | `def run_megalaunch(` at `:140` | exact |
| `skipped-unresolved-blocker` `:581`, `:587` | both exact `_result(...)` calls | exact |
| `MegalaunchOutcome` literal `:96` | `:96` is blank; the literal is at `:97` | off by one |
| counts dict `:131` | dict spans `:126–134`; `:131` is the `"skipped-unresolved-blocker": 0` key. Property is at `:124-125` | points inside the right structure, arguably at the most relevant line |
| `open_blockers` at `blackboard.py:285` | `def open_blockers` at `:285` | exact |
| already imported by megalaunch `:52` | `from coga.blackboard import open_blockers` at `:52` | exact |
| `coga block` appends via `append_blocker`, sets `status: blocked`, `--reason` required/non-empty | `block.py:26-28` rejects empty, `:48` `append_blocker`, `:54` `mark_blocked` | fully accurate |
| architecture `:302`, `:347`, `:387` | all three lines contain "megalaunch" | accurate, though `:302` is a one-clause passing mention, not a section the drain loop would edit |

### 6. Assumptions to question before launch

This is where the ticket is weakest. Four concrete problems.

**a) Decision 6 is factually wrong about the code.** "Megalaunch normalizes the blocker record **it writes** when a supervised session ends in `coga block`." Megalaunch writes no blocker record. `coga block` runs *inside the agent REPL* and calls `append_blocker` (`block.py:48`); megalaunch only observes the resulting status via `read_ticket`. Its own `_reblock_unresolved` calls `mark_blocked`, which flips `status:` and writes nothing to `## Blockers` (`mark.py:383-386`). So "normalize the record it writes" would have to become a new post-session rewrite of someone else's blackboard line. The implementer needs to know that seam does not exist today.

**b) The reason-scanning approach is workable but has a specific silent failure.** `append_blocker` writes a **single line**: `- [ ] [ts] [actor] id=<id> <reason>`, and `_CHECKBOX_BLOCKER_RE` captures `reason` as the rest of *that line*. `--reason` is free text and nothing strips newlines, so a multi-line reason produces trailing lines that match no regex and are simply dropped from `Blocker.reason`. A slug on line 2 is invisible to the scan. Also: `id_slug` is the path under `tasks/`, so nested tickets are `dir/slug`, and slugs are truncated to ~50 chars (`clean-up-workflows-and-make-sure-they-re-in-bootst` is a live example). Decision 7's convention asks agents to type an exact truncated, possibly slash-qualified slug into prose — a substring scan over prose will miss more often than the ticket's "accepted, mitigated by decision 7" implies. Worth deciding up front whether the scan matches the *title* too, or whether decision 6's normalized record should carry an explicit `waiting-on=<slug>` token that the agent is told to emit.

**c) "Checking whether that ticket is now `done`" has an unhandled third state: gone.** `megalaunch.py:261-266` documents that a session earlier in the same sweep can legitimately reap a finished task ("retire deletes the source directory"), and `bootstrap/delete-task` exists. A dependency that landed and was retired raises `TicketNotFoundError` rather than reading `status: done`, so a naive `status == "done"` check treats the *most completely finished* case as unsatisfied. Not in the risks list.

**d) The termination/progress rule is not well specified, and the stated version probably doesn't terminate.** Three interacting facts the ticket doesn't connect:

- Relaunching a blocked ticket requires reactivating it, which sets `blocked_resume`-style semantics. `_launch_until_stop:751-759` then calls `_reblock_unresolved`, which returns the ticket to `blocked` if the session exits `in_progress` with any ask still open. A drain relaunch that does real work and bumps but never runs `coga unblock` therefore lands back in `blocked` **with the same open blocker still naming the same now-`done` slug**. On the next pass it is eligible again, and it *did* make progress by the ticket's own rule (the step advanced) — so the loop restarts from the top and relaunches it again. The stated progress rule permits exactly the spin it was written to prevent.
- The clean fix is the one the ticket doesn't name: megalaunch should call `resolve_open_blockers(ref.ticket_path, actor, "dependency <slug> landed in this run")` **before** relaunching. That makes satisfaction a one-way transition, removes the ticket from the eligible set by construction, and makes termination trivial. It also fixes (e) below.
- `--max-tasks` already exists (`commands/megalaunch.py:73`) and is the natural global budget, but the ticket never mentions whether drain relaunches count against it. They should.

**e) Bonus: the drain relaunch will inherit a human-attended prompt.** `compose.py:156-176` unconditionally injects the blocker-resolution preamble whenever open asks exist, and `prompt-blocker-resolution.md` says *"Discuss the open asks with the human and land on a resolution."* `prompt-megalaunch.md:16-21` frames that exception as valid only because "the human explicitly selected this task." An unattended drain relaunch with the blocker still open gets a prompt telling it to talk to a human who isn't there. Either auto-resolve the blocker before relaunching (per (d)) or add a drain-specific preamble variant. The ticket's amendment to `prompt-megalaunch.md` is for a different purpose entirely.

**f) Smaller ones.** Decision 5's "every blocked ticket in scope" is narrower than it sounds in sweep mode: `_run_sweep:279` skips any ticket whose `owner != cfg.current_user`, and the queue is a snapshot taken before the first launch, so a ticket blocked *and created* mid-run is invisible. And each drain relaunch appends a **second** `MegalaunchResult` for the same slug, so `counts` double-counts and `render_run_summary` lists the slug twice — the ticket says the counts dict "needs updating" but doesn't name this.

### 7. `script: null`

Correct. This is a design-and-code change across Python modules, a package prompt resource, tests, and two copies of a context doc — nothing deterministic to run. `is_script_launch` would be false regardless (`code/with-review` step 1 declares `code/implement`, which has no `script:`), so setting a ticket script would only conflict with the workflow.

### Verdict

Launchable, and better than most tickets I'd see cold. Before launch I'd (1) correct decision 6 to say megalaunch would need a *new* post-session write, since it writes no blocker record today; (2) replace the "progress = step advanced" rule with "resolve the open blocker before relaunching," which makes termination structural; (3) add "the dependency ticket may have been retired/deleted" to the satisfaction check; (4) say whether drain relaunches consume `--max-tasks`; and (5) note the blocker-resolution preamble conflict. Fix the two off-by-one line refs (`:96` → `:97`, `:39` → `:38`) while you're in there. Consider `code/design-then-implement` given four open design questions.
