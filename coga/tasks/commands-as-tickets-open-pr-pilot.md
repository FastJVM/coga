---
slug: commands-as-tickets-open-pr-pilot
title: 'Commands as tickets: open-pr pilot'
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- coga/architecture
- coga/principles
- coga/codebase
- dev/code
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
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 5 (review)
---

## Description

Pilot the "commands as tickets" direction using `coga open-pr` as the worked
example, then generalize. The owner's thesis (2026-07-21): everything but
`launch` could in principle be a ticket — the microkernel should shrink to
launch + the ticket state machine, with verbs living as launchable
ticket/skill work. open-pr is deliberately chosen as the *hardest* case: if
it works as a ticket, the pattern generalizes; where it can't, the failure is
the finding.

Two deliverables:

1. **The pilot** — make open-pr runnable as a ticket (or stateless launch
   target), solving the structural problems listed in Context, with the
   `requires: pr` bump gate still enforced.
2. **The generalization** — from what the pilot proves, write the rules for
   which remaining commands follow (including whether read-only surfaces —
   `status`, `show`, `validate`, `usage` — become stateless launch targets),
   and amend the microkernel policy text accordingly.

This is a co-design ticket: the owner launches it attended and shapes the
design in-session with the agent.

**Settled thesis (owner, in-session 2026-07-21):** "commands as tickets" means
the ticket file is the command's *definition* — body as docs, `script:` as
implementation, `secrets:` as capability grant — launched in place each time.
No per-invocation task instance is ever created. Extensibility is the point:
anyone mints a new `coga <verb>` by dropping a stateless command ticket in
their repo plus an `[aliases]` line, with zero core-Python change.

## Acceptance Criteria

- [ ] `coga launch bootstrap/open-pr <slug>` runs the full open-pr recipe end
  to end from the control checkout: reads `branch:`/`worktree:` from the
  target ticket's `## Dev`, enforces control checkout, pushes with the
  lease-safe retry, opens/readies the PR, writes `pr:` back, prints the URL;
  exits non-zero (nothing advanced) on any `OpenPrError`.
- [ ] `coga open-pr <slug>` still works, now as a default alias for
  `launch bootstrap/open-pr <slug>`; `open-pr` is no longer a registered
  Typer command and is removed from `BUILTIN_COMMANDS`.
- [ ] `src/coga/open_pr.py` and `src/coga/commands/open_pr.py` are deleted;
  the recipe lives beside the command ticket in package
  `bootstrap/open-pr/` (`ticket.md` + `run.py` + `recipe.py`); its tests are
  repointed to load the packaged copy and still cover control-checkout
  refusal, no-commits-ahead refusal, lease retry, and the byte-spliced
  `pr:` write-back.
- [ ] Trailing-args channel: `coga launch <target> [ARGS...]` injects
  `COGA_ARG_1..N` and `COGA_ARGC` into every *script* launch's env; an
  *agent* launch given trailing args fails loud (no silent drop). Secrets
  named `COGA_*` remain rejected; the new variables are launch-owned.
- [ ] Local-first resolution: a repo-local `coga/bootstrap/<name>/ticket.md`
  resolves over the package resource for `coga launch bootstrap/<name>`.
  A test mints a toy verb (local command ticket + `[aliases]` entry, zero
  Python) and runs it end to end.
- [ ] The `requires: pr` bump gate is untouched: `coga bump` off the open-pr
  step still refuses until `pr:` is recorded, and its remediation string
  still names a working `coga open-pr {slug}` spelling.
- [ ] Docs updated, live + packaged copies in sync: `code/open-pr` SKILL.md
  (command spelling unchanged, mechanism note updated), `coga/architecture`
  (bootstrap section: local-first + arg channel + command-ticket definition),
  `coga/codebase` (rescope the "don't copy into `coga/bootstrap/`" warning to
  "don't *repair* bundled resources by copying — authoring a local command
  ticket or deliberate override is sanctioned"), and the microkernel policy
  text (see Generalization below).
- [ ] `python -m pytest` green; `coga validate --task <this>` clean.

## Proposed Shape

**1. Argument channel (kernel, generic).** `launch()` in
`src/coga/commands/launch.py` gains a variadic trailing
`args: list[str]` Typer argument. `run_script_mode` /
`build_task_env` (in `commands/launch_script.py`) inject them as
`COGA_ARG_1..N` plus `COGA_ARGC` for every script launch (stateless or not).
An agent launch with trailing args bails fail-loud — composing args into
agent prompts is deliberately deferred until a second use case exists.
Aliases already rewrite argv through real CLI parsing, so
`coga open-pr <slug>` → `launch bootstrap/open-pr <slug>` carries the
trailing arg for free (verify in `test_aliases.py`).

**2. Local-first bootstrap resolution (kernel, generic).**
`bootstrap_path` in `src/coga/paths.py` (and `resolve_bootstrap` in
`tasks.py`) check `<coga-root>/bootstrap/<name>/ticket.md` before the package
resource — the same local-first rule skills, contexts, and workflows follow.
This is the seam that makes command tickets user-authorable.

**3. open-pr as the first shipped command ticket.** New package resource dir
`src/coga/resources/templates/coga/bootstrap/open-pr/`:
- `ticket.md` — stateless bootstrap shape (no status/workflow), body
  documents the verb, frontmatter `script: run.py`, `secrets: null`.
- `recipe.py` — `src/coga/open_pr.py` moved wholesale (git rename so history
  follows): `OpenPrError`, `open_pr()`, `set_dev_pr()`. It keeps importing
  shared core infra (`coga.autoclose` parsers, `coga.github_preflight`,
  `coga.taskfile`, `coga.compose._extract_section`, `coga.config`) — skills
  and command tickets import core freely; the parsers stay core per the
  sibling ticket's settled move list.
- `run.py` — the old `commands/open_pr.py` seam as a script: read the target
  from `COGA_ARG_1` (usage message when absent), `load_config()`,
  `_require_control_checkout`, `resolve_task`, `read_ticket`, run the recipe,
  print the URL, exit 2 on `OpenPrError`.
Delete `src/coga/open_pr.py`, `src/coga/commands/open_pr.py`, and the
`cli.py` registration. In `aliases.py`: drop `"open-pr"` from
`BUILTIN_COMMANDS`, add `DEFAULT_ALIASES["open-pr"] = "launch
bootstrap/open-pr"`.

**4. Why this won't oscillate back (the #517 → #585 test).** Every invariant
#585 settled is preserved untouched: `code/open-pr` remains an ordinary agent
step; the completion gate remains a *data check in `bump`*
(`requires: pr` reading the recorded artifact — never an exit code); the
recipe keeps control-checkout enforcement and the observed-OID
force-with-lease retry. #517 failed because it changed *gating semantics*
(exit-code gate, all-script step); this change moves only the recipe's home
and the dispatch seam, and the alias keeps the operator-facing spelling
byte-identical. The step's UX, the gate, and the failure modes are the same
before and after.

**5. Kernel-residue accounting (honest).** Leaves core: ~430 lines of
verb-specific code (`open_pr.py`, `commands/open_pr.py`). Stays core:
`step_gate.py` (`requires: pr`), the `autoclose` parsers,
`github_preflight`, `taskfile.replace_blackboard`, secrets/config. Newly
*added* to core: the arg channel and local-first bootstrap resolution — both
generic extension seams, not verb code. Net: the kernel trades a verb
implementation for the machinery that lets any verb live outside it.

**6. Generalization (deliverable 2, lands as policy-text amendment).** Amend
the microkernel policy text (CLAUDE.md / AGENTS.md / `coga/codebase`, as
landed by `agree-the-core-vs-skills-move-list-then-execute` — coordinate if
that PR is still in flight) with the command-ticket rule:

> A core command migrates to a command ticket when it is a deterministic
> verb: script-shaped, parameterized by trailing args + env, owning no
> control/data-plane state transition. Its completion gate, if any, stays a
> declarative `requires:` data check in `bump`. State-machine commands
> (`create`, `mark`, `bump`, `block`, `unblock`, `launch`, `megalaunch`) are
> the kernel. Shared parsers/preflights stay core once ≥2 consumers exist.
> Read-only surfaces (`status`, `show`, `validate`, `usage`) are explicitly
> *unruled* — deferred until a driving case (owner, 2026-07-21).

**Order of work:** seams first (1, 2 — each independently testable), then the
migration (3), then docs/policy (6). One PR, commits split along those lines.

## Out of Scope

- Migrating any other command (`digest`, `megalaunch`, the read-only
  surfaces) — this ticket only writes the *rules* for them.
- Composing trailing args into agent prompts (deferred; agent launches
  fail loud on args instead).
- Changing `bump`'s ownership of step gates, the `requires:` mechanism, or
  the `## Dev` blackboard convention.
- The three recipe moves and the initial policy-doc landing (owned by
  `agree-the-core-vs-skills-move-list-then-execute`).
- Per-invocation task instances for commands (rejected in-session: the
  ticket is the definition, not the run).

## Context

Origin: review-design discussion on
`agree-the-core-vs-skills-move-list-then-execute` (2026-07-21). That ticket
lands the three recipe moves + microkernel policy docs and rules open-pr
stays-core *pending this pilot* — this ticket may amend the policy text that
ticket lands.

History that must inform the design (the #517 → #585 oscillation):

- PR #517 moved `open_pr.py` into the `code/open-pr` skill.
- PR #585 reversed it: `code/open-pr` became an *agent step* that calls a
  deterministic core `coga open-pr` command; the completion gate moved into
  `coga bump` as declarative `requires: pr`; the command owns
  control-checkout enforcement and lease-safe rebase retries. Read that PR
  before proposing a third shape — the design must say explicitly why the new
  shape won't oscillate back.

Structural problems the design must solve (identified 2026-07-21):

1. **Argument channel** — open-pr operates *on another ticket* (reads its
   blackboard `branch:`/`worktree:`, writes `pr:` back). Launch targets take
   no arguments today; the alternatives are parameterized launches (new
   design) or a machine-authored ticket per invocation (sprawl for a
   30-second verb).
2. **Nested launch** — the `code/open-pr` step runs mid-workflow, inside a
   supervised session; "don't `coga launch` from inside a launch" is
   currently a hard prohibition. Possible wedge: script-mode nested launches
   are already sanctioned (a script step's launch releases its session via
   the slug-scoped sentinel).
3. **Write ownership** — a separate open-pr ticket's session and the code
   ticket's session would both write the code ticket's `ticket.md`; the
   divergent-writers mode "status is the signal" tolerates would become the
   normal path for every PR.
4. **Kernel residue** — the `requires: pr` gate (in `bump`) and the
   branch/PR parsers (shared infra in `autoclose.py`) stay core regardless;
   be honest in the design about how much actually leaves.

Out of scope: the three recipe moves and policy-doc landing (owned by
`agree-the-core-vs-skills-move-list-then-execute`); changing `bump`'s
ownership of step gates.

<!-- coga:blackboard -->

## Dev
pr: https://github.com/FastJVM/coga/pull/625
branch: commands-as-tickets-open-pr
worktree: /home/n/Code/claude/coga-commands-as-tickets

## Implement step (2026-07-21)

Landed on the branch as four commits (seams → migration → docs), exactly the
ticket's Proposed Shape:

1. **Arg channel** (`0b977e5b`): `launch()` takes variadic trailing args;
   `run_script_mode` injects `COGA_ARG_1..N` + always-present `COGA_ARGC`
   via `build_arg_env` (launch_script.py); agent launch with args fails loud
   *before* the TTY gate so the refusal is testable headless. Sentinel
   normalization up front (`isinstance` check) covers in-process callers
   (recurring/retire) that omit the new param — the coga/codebase
   OptionInfo gotcha.
2. **Local-first bootstrap** (`0378918d`): `resolve_bootstrap` checks
   `coga/bootstrap/<name>/ticket.md` before the package resource
   (`bootstrap_resolution_paths` in paths.py); not-found names both paths.
3. **Migration** (`745eb273`): `src/coga/open_pr.py` → packaged
   `bootstrap/open-pr/recipe.py` (git rename, R092 detected);
   `commands/open_pr.py` deleted, replaced by `bootstrap/open-pr/run.py`
   (reads `COGA_ARG_1`, own `_control_checkout_refusal` copy — chosen over a
   shared helper since core no longer has one); `ticket.md` documents the
   verb; `open-pr` left `BUILTIN_COMMANDS`, added to `DEFAULT_ALIASES` →
   `launch bootstrap/open-pr`. run.py mirrors the sibling branch's
   sys.path.insert + sibling-import pattern; tests load the recipe via new
   `conftest.load_bootstrap_recipe` (named to merge cleanly beside the
   sibling's `load_skill_recipe`).
4. **Docs** (`d514e9cc`): architecture context (live+packaged) — local-first
   bootstrap bullet incl. command-ticket definition + arg channel, alias
   mechanism in the `requires: pr` paragraph, and the generalization rule as
   "Commands as tickets — the migration rule" under Command Surface;
   codebase context warning rescoped to *repairs* (deliberate authoring
   sanctioned); code/open-pr SKILL.md mechanism note (live+packaged in
   sync); docs/reference.md (launch args, open-pr alias, alias table).

Implementation-level picks (left open by design): `COGA_ARGC` spelling;
run.py carries its own control-checkout helper. Wheel packaging needs no
change — the whole `bootstrap/` tree is already exclude+force-included.

Verification: full suite green in the worktree (1393 passed, 1 skipped;
`PYTHONPATH=$PWD/src python3.12 -m pytest`); `coga validate --task
commands-as-tickets-open-pr-pilot` clean; `coga launch --help` shows the
args channel and `--help` lists the open-pr alias; branch rebased-checked
against origin/main (already up to date). Coverage preserved per acceptance:
control-checkout refusal, no-commits-ahead, lease retry, byte-spliced `pr:`
write-back all still tested against the packaged copy; new end-to-end tests
for the alias spelling, stateless launch path, arg env, local override, and
a zero-Python toy verb (`coga hello`).

**Coordination note:** the sibling
`agree-the-core-vs-skills-move-list-then-execute` PR (microkernel policy in
CLAUDE.md/codebase context) has not landed yet — its branch
`microkernel-move-recipes` is still in flight. The command-ticket rule
therefore lands here in the architecture context only; whichever PR merges
second should reconcile CLAUDE.md's policy paragraph with this rule (both
texts were written to compose — different sections, no overlapping edits
except `coga/contexts/coga/codebase/SKILL.md`, where the sibling adds a new
section and this ticket edits the existing bootstrap-repair gotcha).

## Design-step investigation (2026-07-21)

Facts an implementer/designer should not re-derive:

- **Current shape (post-#585):** `src/coga/open_pr.py` (recipe, ~336 lines,
  `OpenPrError` fail-loud) + `src/coga/commands/open_pr.py` (~91-line CLI seam:
  `load_config` → `_require_control_checkout` → `resolve_task` → recipe).
  The `code/open-pr` step is an ordinary agent step; `requires: pr` is checked
  by `bump` via `step_gate.py` (generic token registry, reads `parse_pr_url`
  from `coga.autoclose`). The recipe writes `pr:` back with a byte-spliced
  `replace_blackboard` after a re-read, so the write is safe against the
  launcher's step advance.
- **What #585 actually settled** (read `move-open-pr-gate-from-launch-into-bump-*`):
  the oscillation was about *gating semantics*, not code location. #517's sin =
  gating on a script's exit code and forcing open-pr to be all-script; #585's
  invariants = (a) open-pr is an agent step, (b) the gate is a *data check in
  bump* (`requires: pr`), (c) the recipe keeps control-checkout enforcement +
  lease-safe force-with-lease retries. None of those pin where the recipe
  *lives* or whether the CLI seam is a registered command vs a launch dispatch.
- **Stateless launch path exists:** `BootstrapRef` targets
  (`coga launch bootstrap/<name>`) run `run_script_mode(..., stateless=True)` —
  no status flips, no log writes, no step advance, no done-marker emission
  (`launch_script.py:194-214`), secrets still injected, `COGA_TASK_*` env still
  built. Nested script launches are already sanctioned; a *stateless* nested
  launch can't even collide with the outer session's slug-scoped sentinel.
- **No argument channel today:** `launch()` takes exactly one positional
  (`task`) plus options; scripts receive context only via `COGA_*` env vars.
  `COGA_` env namespace is reserved for launch metadata (secrets named
  `COGA_*` are rejected), so an env-based arg channel fits the existing
  contract (e.g. `COGA_LAUNCH_ARGS` / `COGA_ARG_*`).
- **Alias seam:** `open-pr` is currently in `BUILTIN_COMMANDS`
  (`aliases.py`); default aliases (e.g. `autoclose = "recurring launch
  autoclose-merged"`) are the established pattern for skill-fronted command
  spellings. An alias is an argv rewrite through real CLI parsing.
- **Precedent for recipe-in-skill:** the sibling ticket
  (`agree-the-core-vs-skills-move-list-then-execute`, in implement) lands
  three single-consumer recipes as skill-local `recipe.py` + `run.py`, with
  shared parsers deliberately staying in core `coga.autoclose`. Skills import
  core freely.
- **Write-ownership insight:** today's `coga open-pr` is a synchronous
  subprocess run *inside* the code ticket's own step/session. A stateless
  launch target invoked the same way keeps single-writer semantics — the
  divergent-writers problem (structural problem 3) only materializes in the
  "real machine-authored ticket per invocation" variant, where a *second
  session* owns the write.

## Decisions (owner, in-session 2026-07-21)

1. **Thesis = definition, not instance.** The command ticket is the verb's
   durable definition, launched in place; no per-invocation task is created.
   Extensibility is the goal: ticket + alias = new verb, zero core Python.
2. **Resolution: local-first `bootstrap/`.** `coga launch bootstrap/<name>`
   checks `coga/bootstrap/<name>/ticket.md` before the package resource,
   mirroring skills/contexts/workflows. Codebase-context warning gets
   rescoped (don't *repair* by copying; deliberate authoring is sanctioned).
3. **Arg channel: trailing args → env**, script launches only
   (`COGA_ARG_1..N` + `COGA_ARGC`); agent launch with args fails loud.
4. **`coga open-pr` survives as a default alias** for
   `launch bootstrap/open-pr`.
5. **Read-only surfaces: explicitly unruled** in the generalization text —
   deferred until a driving case.

## Open Questions

None pending — all shaping questions were resolved in-session (see
Decisions). Implementation-level choices left open deliberately: exact env
var spelling (`COGA_ARGC` vs `COGA_ARG_COUNT`) and whether run.py shares a
`_require_control_checkout` helper with core or carries its own copy — the
implementer picks whichever reads cleaner.

## Dream Skill: validate-drift

Generated: 2026-07-21T22:20:26+00:00
Command: `coga validate --json --fix`
Task: `commands-as-tickets-open-pr-pilot`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-21T22:24:49+00:00
Command: `coga validate --json --fix`
Task: `commands-as-tickets-open-pr-pilot`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

## Dream Skill: validate-drift

Generated: 2026-07-21T22:28:03+00:00
Command: `coga validate --json --fix`
Task: `commands-as-tickets-open-pr-pilot`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.
