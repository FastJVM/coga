---
title: Move retire to a command ticket
status: done
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
contexts:
- coga-dev/principles
- coga-dev/microkernel
- coga/script-tickets
- coga/launch
- coga/checkout-cleanup
- coga/recurring/scheduling
- coga/cli
- coga-dev/codebase
- coga-dev/testing
- coga-dev/packaging
agent: claude
---

## Description

`coga retire` is a single-consumer Typer head in `src/coga/commands/retire.py`
with no `runner.RECIPES` entry and no co-versioning proof, so it sits in the
"Open command placements" table of `coga-dev/microkernel`. Move it to the
edge as a stateless script command ticket, `bootstrap/retire`, reached by a
default alias, without changing what it does. Then let each of the three
cleanup tickets (`bootstrap/retire`, `recurring/autoclose-merged`,
`recurring/branch-sweep`) own the description of its own job in `ticket.md`,
so `coga/checkout-cleanup` keeps only the rules they share.

Three parts in order, one PR: (1) script command tickets receive trailing
argv, (2) move retire, (3) split the docs. Part 1 is required because a
`ticket.py` runs with no operands today: `launch_script.run_script_phase`
spawns `[sys.executable, ticket.py]` and the invocation's `launch_args` are
silently dropped for every script target. That is a fail-loud defect
even before retire depends on it.

Design decisions (owner, 2026-10-16, design step): process argv rather than
an env var; all of retire's code in the packaged `bootstrap/retire/ticket.py`
(no `coga_edge` module); the canceled path launches its retire task through
a `coga launch` subprocess.

### Acceptance criteria

Part 1 — argv for script command tickets

- [ ] Launching a **stateless** (`bootstrap/<name>`) target whose
      `ticket.py` exists runs `[sys.executable, ticket.py, *args]`, where
      `args` are the launch's trailing positionals in order, each a separate
      argv element (no shell, no joining). The script reads `sys.argv[1:]`.
- [ ] Launching a **stateful** task (or recurring period) whose `ticket.py`
      would run, with any trailing positional, is refused with exit 2 before
      any lifecycle write, secret resolution or log line, naming the target and
      saying a stateful script takes no launch arguments (they would be
      hidden mutable input: `coga/extension-model`, "Parameters and trust
      boundaries"). Today those args are dropped silently.
- [ ] Agent-backed command tickets and agent tasks are unchanged: they still
      get the `## Launch arguments` JSON block (`_agent_args_prompt_suffix`);
      the delegated-period refusal is unchanged.
- [ ] A bootstrap target with both `ticket.py` and an agent phase is not a
      shape that exists (`_classify_script_handoff` returns for stateless);
      argv goes to the script only.
- [ ] `coga/script-tickets` (live `docs/contexts/` + packaged
      `bootstrap/contexts/` twin) documents the contract under "One
      deterministic phase" step 4 and replaces "no operands"; `coga/launch`
      "Targets" and `coga/extension-model` "Command ticket" bullet and the
      `launch` command's `args` help text in `src/coga/commands/launch.py`
      say the same. Tests in `tests/test_launch_script.py`: argv reaches a
      bootstrap script with boundaries preserved (an arg with spaces, one
      starting with `--`), no args gives `sys.argv == [path]`, a stateful
      script target with args exits 2 with the ticket unchanged and no log line.

Part 2 — retire as a command ticket

- [ ] `aliases.DEFAULT_ALIASES` gains
      `"retire": "launch bootstrap/retire --"`. The trailing `--` is required:
      without it, launch's own Typer command would consume `--agent <type>`
      and reject `--no-launch`. `"retire"` leaves `aliases.BUILTIN_COMMANDS`
      and `cli._SWEEPING_COMMANDS` (the `launch` it expands to already
      sweeps); `cli.py` drops `app.command("retire")` and the import.
- [ ] `src/coga/commands/retire.py` is deleted. Its whole body moves, logic
      unchanged ("No inversion"), into the packaged
      `src/coga/resources/templates/coga/bootstrap/retire/ticket.py`: a Typer
      app with the same `retire` command (same argument, `--agent`,
      `--no-launch`, help text) invoked as
      `if __name__ == "__main__": app(prog_name="coga retire")`, so loading
      the file as a module for tests has no side effects.
- [ ] The one deliberate behavior change: the canceled path's in-process
      `coga.launch.launch(slug, ...)` becomes
      `subprocess.run([sys.executable, "-m", "coga.cli", "launch", slug])`,
      and retire exits with its return code. Reason: the script runs in a
      child of the outer launch, outside `cli.main`'s `checkout_guard_scope`
      and end-of-command sweep, which the old in-process call ran inside.
      The new task launch keeps that CLI boundary.
- [ ] Unchanged observable behavior: `coga retire <slug>`,
      `coga retire <slug> --no-launch`, `coga retire <slug> --agent <type>`
      and `coga retire --help` all work. Same refusals and exit codes
      (2 for unknown slug, non-terminal status, kept checkout, config errors;
      the launched task's exit propagates). The same stdout `Retire: ...`
      lines, commit messages (`Ticket: <slug> — deleted (retire)`,
      `— created (retire)`), blocked-task path, and `retires.md` discharge.
      Allowed differences: launch's stderr framing
      (`→ coga launch bootstrap/retire -- ...`, `→ running bootstrap/retire
      ticket.py`, `bootstrap/retire: script ran successfully`) and the exempt
      bootstrap launch's exit-time `git.refresh` of a control checkout.
- [ ] Retire still works from a checkout off the control branch (bootstrap
      targets are exempt from checkout preparation per
      `coga/checkouts/launch-boundary`) and still prints
      `Retire: checkout cleanup skipped ...` there.
- [ ] A packaged `bootstrap/retire/ticket.md` exists with no `status:` or
      `workflow:` (a stateless command ticket), plus the body in Part 3. No
      live `coga/bootstrap/retire/` copy is created (`coga-dev/packaging`: don't
      mirror); this repo resolves the packaged one.
- [ ] The wheel ships it: add `bootstrap/retire/ticket.md` and `ticket.py`
      to `tests/test_packaging.py::EXPECTED_BOOTSTRAP_RESOURCES`.
- [ ] `tests/test_retire.py` keeps every existing case. They now load the
      packaged `ticket.py` with `importlib.util.spec_from_file_location` (one
      helper/fixture) and `CliRunner().invoke(module.app, [slug, ...])`. The
      launch test patches `subprocess.run` in that module instead of
      `launch`. Add end-to-end cases through the real alias
      (`sys.executable -m coga.cli retire <slug> --no-launch` with an
      absolute `PYTHONPATH`, per `coga-dev/testing`): a done ticket is
      deleted, `--no-launch` creates `retire-<slug>`, and an unknown slug
      exits 2 with its message.
- [ ] Shared core stays and keeps serving retire, autoclose and branch-sweep:
      `checkout_disposal.py`, `branchcleanup.py`, `retire_worklist.py`,
      `autoclose` parsers (`parse_branch_name`, `parse_branch_names`,
      `parse_pr_url`, `parse_worktree_path`), `delete_task.run_delete_task`,
      `create.create_task`, `mark.mark_blocked`, `paths.load_resource`, and
      `src/coga/resources/retire.md`. Production `src/coga/` imports nothing
      from the bootstrap directory.

Part 3 — descriptions own their job

- [ ] Pre-step: re-sync live `coga/recurring/autoclose-merged/ticket.md`,
      `ticket.py` and `coga/recurring/branch-sweep/ticket.md`, `ticket.py` to
      their packaged copies (the `scope: clone` versions #1033 shipped;
      commit 28cba8f70 rolled the live copies back and the merge kept that).
      `test_live_and_packaged_copies_stay_identical` fails on main today.
      Check `coga/recurring/upstream-coga` against #1033 the same way.
- [ ] `bootstrap/retire/ticket.md` describes retire step by step: refusal
      unless done/canceled; checkout disposal from `## Dev` (only on the
      control branch); a kept worktree/branch is a bug and exits 2 (done:
      nothing deleted; canceled: task created `blocked`); worklist
      discharge; done → delete + sync; canceled → `retire-<slug>` task via
      `direct/body` running `retro/done-ticket`, launched unless
      `--no-launch`; `--agent` only affects that task. It carries the
      2026-10-13 owner decision and links (`context:` links) to
      `coga/checkout-cleanup/proofs`, `coga/checkout-cleanup` (primary
      checkouts) and `coga/checkout-cleanup/terminal-owners` instead of
      restating the proofs. This is the old `## coga retire` section of
      `coga/checkout-cleanup`, moved.
- [ ] `recurring/autoclose-merged/ticket.md` and
      `recurring/branch-sweep/ticket.md` (live + packaged) keep their
      step-by-step job descriptions but replace inline restatements of the
      shared proofs (for example autoclose step 6's parenthesized proof list,
      branch-sweep's references to "the same landing policy `coga retire`
      uses") with links to `coga/checkout-cleanup/proofs` /
      `coga/checkout-cleanup/branch-sweep`. Text that says retire runs "daily"
      or is "best-effort" is corrected to match the current retire contract.
- [ ] `coga/checkout-cleanup` (live + packaged) loses its
      `## coga retire <slug> ...` section and keeps: intro, Leaves, Primary
      checkouts and other clones, Accepted disappearance policy, `/tmp`
      recovery, and `## coga delete <slug>`. `coga delete` stays because it's a
      kernel command with no ticket to move to. The intro says the
      retire procedure lives in `bootstrap/retire/ticket.md` and the
      autoclose/branch-sweep procedures in their templates.
- [ ] Inbound pointers follow: `coga/cli` splits the `delete`, `retire`
      row: `delete` stays → `coga/checkout-cleanup`, and
      `retire` → `launch bootstrap/retire --` points at
      `bootstrap/retire/ticket.md`, in the alias-row style;
      `coga-dev/microkernel` drops `retire` from the Open command placements
      row (it becomes `megalaunch`, `slack`), counts ten default aliases and
      names `retire` in the list, and cites `bootstrap/retire` as a shipped
      script command-ticket example beside `resolve-conflicts` /
      `address-pr-comments`; `coga-dev/codebase` source map if it names
      `commands/retire.py`; `docs/archive/cli-extension-audit.md` row for
      `retire` is updated to "moved to `bootstrap/retire` (alias)";
      `microkernel/work-orchestration-commands-to-tickets` ticks retire's
      table exit. All context edits land in both twins.
- [ ] Verification: `PYTHONPATH=$PWD/src python3.12 -m pytest` (full suite,
      counts in the PR), a Python 3.11 run or a stated gap,
      `coga validate --json`, `env -u SLACK_WEBHOOK_URL coga validate --json`
      on `tests/fixtures/seeded-repo/coga`, and a manual
      `coga retire <done-slug>` / `coga retire --help` smoke in a scratch clone.

### Proposed shape

1. **Launch argv (kernel).** `launch_script.run_script_phase` and
   `run_script_chain` gain an `args: Sequence[str] = ()` parameter; the
   subprocess argv becomes `[sys.executable, str(entry), *args]` and a
   phase forwards `args` only when `stateless` (a defensive `ValueError`
   if a stateful phase ever receives them). `launch._LaunchInvocation` passes
   `self.launch_args` at the `run_script_chain` call(s) in the
   script-execution phase (the one in initial script execution and the one
   in step supervision after an agent step). Refuse the stateful case in the
   invocation before the first `run_script_chain`, alongside the existing
   delegated-period `launch_args` refusal, so nothing is written. Scripts run
   by the supervisor after an agent step on a stateful task never get args
   (already refused at entry).
2. **Alias + CLI.** Edit `aliases.DEFAULT_ALIASES`, `BUILTIN_COMMANDS`, the
   comment above `DEFAULT_ALIASES`; `cli.py` registration, import,
   `_SWEEPING_COMMANDS`. `tests/test_aliases.py` already asserts
   `BUILTIN_COMMANDS` matches Typer's registry; add an assertion that
   `retire` is a default alias expanding to `launch bootstrap/retire --`.
3. **Move the code.** `git mv src/coga/commands/retire.py
   src/coga/resources/templates/coga/bootstrap/retire/ticket.py`, add the
   `app = typer.Typer(add_completion=False)` / `app.command()(retire)` /
   `__main__` guard, swap the in-process launch for the subprocess, keep
   `_bail` → `sys.exit(2)`. Write `bootstrap/retire/ticket.md`.
4. **Tests.** Port `tests/test_retire.py` to the loaded module; add the
   alias end-to-end cases and the Part 1 launch-script tests; update
   `EXPECTED_BOOTSTRAP_RESOURCES`.
5. **Docs.** Re-sync the drifted recurring twins, then the Part 3 edits,
   then run the packaging twin test.

### Out of scope

- `megalaunch` and `slack` (stay with
  `microkernel/work-orchestration-commands-to-tickets`).
- Moving `coga delete` or the `delete-task` recipe; growing
  `runner.RECIPES` (no `coga run retire`).
- Moving `src/coga/resources/retire.md` beside the ticket, or changing its
  `{slug}` override semantics.
- Passing argv to stateful script tickets, an env-var form of argv, or
  giving bootstrap scripts the `## Launch arguments` block.
- Changing the shared proofs, autoclose, or branch-sweep behavior; Part 3
  is a docs reorganization plus the twin re-sync.
- Reworking the `coga/autoclose/sweep` and `coga/branch-sweep/sweep` step
  skills beyond fixing links that pointed at the moved retire section.

## Context

Group: `microkernel/README.md`. Split out of
`microkernel/work-orchestration-commands-to-tickets` on 2026-10-16 (owner
decision in an orient chat), which keeps `megalaunch` and `slack`. One
ticket rather than three because the parts depend on each other in order.

Shape to follow: the `resolve-conflicts` and `address-pr-comments` command
tickets reached by aliases, and the `recurring/autoclose-merged` and
`recurring/branch-sweep` script tickets.

Alternatives considered and rejected:
an agent-backed `bootstrap/retire` (every done-ticket retire would cost an
agent session, undoing the 2026-10-13 decision that a done retire needs no
agent); a new `coga run retire` recipe (grows the fixed kernel recipe
registry, which `gigantic-refactor-move-recurring-recipes-out-of-co` owns);
argv via a `COGA_LAUNCH_ARGS` JSON env var (inherits into grandchildren,
needs decoding); a `src/coga_edge/retire.py` module with a shim (owner chose
one file).

Codebase facts the implementer relies on:

- `src/coga/launch_script.py`, `run_script_phase()`: builds the child env
  (`apply_task_env`, pops supervisor witnesses, sets `COGA_SCRIPT_TASK`) and
  calls `subprocess.run([sys.executable, str(entry)], cwd=host_repo_root(cfg))`;
  `run_script_chain()` derives `stateless = isinstance(ref, BootstrapRef)`
  and is the only caller. `_classify_script_handoff()` returns immediately
  for stateless targets, so a bootstrap script never chains to an agent.
  `_echo_script_iteration()` prints framing to stderr for stateless targets,
  and the success line goes to stderr too, so a script's stdout is clean.
- `src/coga/launch.py`, `_LaunchInvocation`: `self.launch_args` is set from
  `args` in `__init__`; it reaches agents only through
  `_agent_args_prompt_suffix()` at the spawn; the existing refusal
  "Cannot pass trailing arguments to delegated period" is the model for the
  new stateful-script refusal. `run_script_chain` is called from the script
  phase and again inside step supervision.
- `src/coga/commands/launch.py`, `launch()`: `args` is a variadic
  `typer.Argument`; `--agent` is launch's own option, so it collides with
  retire's `--agent` unless the alias ends with `--`.
- `src/coga/cli.py`, `main()`: alias expansion is
  `shlex.split(expansion) + sys.argv[2:]`, echoed as `→ coga ...` on
  stderr; `aliases.validate_aliases()` only checks the first token, so a
  trailing `--` is legal.
- `src/coga/commands/retire.py`: imports only shared core (`git`,
  `blackboard.append_blocker`, `autoclose` parsers, `checkout_disposal`,
  `create.create_task`, `delete_task`, `mark.mark_blocked`,
  `paths.load_resource`, `retire_worklist.discharge_slug`, `tasks`), plus a
  lazy `from coga.launch import LaunchBail, launch` used only in the
  canceled path. `_bail()` exits 2.
- `autoclose.ClosedTicket.retire_command` and the remedies in
  `autoclose.py` print `coga retire <slug>`; they keep working through the
  alias and need no change.
- `tests/test_retire.py` drives `CliRunner().invoke(app, ["retire", ...])`
  and imports `_checkout_cleanup_section` from `coga.commands.retire`.
- Recurring script precedent for completing via the CLI rather than
  in-process: `coga/recurring/autoclose-merged/ticket.py` runs
  `[sys.executable, "-m", "coga.cli", "bump", ...]`.
- Prior work: #1041 folded `coga/checkout-cleanup/foreign-ownership` into
  `coga/checkout-cleanup`. #1033 (clone-scoped recurring) shipped the
  packaged recurring templates that the live ones must be re-synced to.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design (2026-10-16, design step)

Spec written above. Owner choices in the attended design chat: process argv
(`sys.argv[1:]`) for stateless script targets only, stateful + args refused;
all retire code in packaged `bootstrap/retire/ticket.py`; canceled path
launches via `coga launch` subprocess.

Findings:
- Trailing args to any script target are silently dropped today.
- `retire = "launch bootstrap/retire"` would lose `--agent`/`--no-launch` to
  launch's own parser; the alias must end in `--`.
- `test_packaging.py::test_live_and_packaged_copies_stay_identical` fails on
  main: live `coga/recurring/{autoclose-merged,branch-sweep}` were rolled
  back by 28cba8f70 and #1033's merge kept that. Re-sync first in implement.

## Open Questions

- Should `coga delete` move out of `coga/checkout-cleanup` too? Spec keeps it
  (kernel command, no ticket to own it), which departs from the original
  keep-list.
- Is changing the canceled path from in-process `launch()` to a subprocess
  acceptable under "moves unchanged"? Owner picked it; evaluator should
  confirm no test or caller depends on `LaunchBail` reason text from retire.

## Evaluator review

2026-10-16. Reviewed cold against fetched `origin/main` / HEAD
`4f5b0d028`, with a clean control checkout. **Needs revision before
implementation.** The three-part scope, edge placement, literal argv, alias
separator, shared-helper boundary and packaging approach are coherent. The
Description subsections compose correctly, and the frozen workflow matches
`code/design-then-implement`. The following compatibility gaps need owner
disposition; this is not design approval.

### Must fix before implementation

1. **P1 — A child CLI boundary does not preserve the outer no-publication
   decision.** In `src/coga/launch.py`, `_CheckoutBoundary.settle` / `_stop`
   set the process-local `git.state_sweep_withheld`; `_supervise_steps` keeps
   the agent's exit code, including success, when checkout return refuses.
   `src/coga/cli.py::main` / `_sweep_coga_state` honor that flag only in the
   same process. Today's in-process retire launch shares it. With the proposed
   subprocess, a child can withhold publication and exit 0, after which the
   outer `bootstrap/retire` launch calls `refresh_after_script` and its CLI
   sweeps again. Forwarding `returncode` alone loses the refusal. Existing
   tests `test_launch_teardown_refusal_preserves_work_result_and_stops_chaining`
   (`tests/test_launch.py`) and
   `test_withheld_launch_return_skips_the_sweep_and_keeps_the_exit`
   (`tests/test_cli.py`) establish this contract. A scratch process-boundary
   probe using `_CheckoutBoundary._stop` confirmed child "state sweep
   withheld", outer exit 0, then both outer refresh and outer sweep.
   Define how the retained-state decision crosses both subprocess boundaries
   and suppresses the outer refresh/publication, and add an integration case
   for a refused return after a successful agent session. The current
   successful-launch mock and exit-code criteria do not cover this.

2. **P2 — Moving onto bootstrap launch adds an agent-configuration
   requirement to done-ticket retirement.**
   `src/coga/commands/retire.py::retire` deletes a done ticket before
   `_default_agent` / `cfg.agent_type` are consulted. In contrast,
   `src/coga/launch.py::_LaunchInvocation._align_and_classify` calls
   `_target_operator` before `_run_initial_script`; for a bootstrap target it
   calls `bump.resolve_main_agent`, which refuses an empty agents table.
   In an isolated configured workspace with no `[agents.*]`, today's
   `coga retire finished` exits 0 and deletes the done ticket, while an
   otherwise valid bootstrap script exits 2 without running. Add the needed
   script-only routing change to Proposed shape and an alias end-to-end
   done-ticket test without configured agents. Agent resolution should remain
   required for the canceled task that actually needs it.

3. **P2 — The promised unchanged `retire --help` behavior needs an explicit
   design.** `src/coga/cli.py::main` deliberately loads configuration with
   `require_user=False`, and the current Typer help exits before `retire`
   loads strict configuration. After the proposed rewrite, `--help` is a
   script operand, so `_LaunchInvocation._prepare_target` first calls strict
   `load_config()`. A fresh clone without `coga.local.toml` therefore cannot
   display it; outside a Coga workspace bootstrap resolution fails as well.
   Scratch verification: current `retire --help` without a configured user
   exits 0; `launch bootstrap/probe -- --help` exits 2 for the missing user
   before executing its script. Specify how setup-independent help is
   preserved, or explicitly accept and document the narrower help contract
   instead of claiming unchanged behavior. Test this through `cli.main`,
   since direct invocation of the moved Typer app bypasses the new preflight.

### Recommendations

- Make the new durable ownership rule explicit in `coga/knowledge` and its
  twin: its ownership table and "Narrative links, never restates" currently
  put behavior contracts and command semantics in topics, while Part 3 moves
  retire's contract into a permanent command ticket. Also allow small factual
  corrections beyond link edits in the excluded sweep skills:
  `coga/skills/coga/branch-sweep/sweep/SKILL.md` still calls retire best-effort,
  and the packaged `code/design-then-implement` workflow's `review` section
  still says done retirement creates a Retro task. Point these summaries at
  the new owner rather than preserving contrary descriptions.
- Strengthen Part 1's refusal tests with draft/paused and recorded-assist
  paths plus a secret-resolution spy. `_run_initial_script` resolves secrets
  and may activate before calling `run_script_chain`, and assist alignment
  can change script classification after `_prepare_target`. Put the guard
  before those effects using the authoritative classification. The proposed
  unchanged-ticket/no-log test alone does not prove secrets were untouched.
  Also qualify the `_classify_script_handoff` claim: its stateless return has
  `needs_agent=True` when the script vanished before running; a successfully
  executed bootstrap script returns without an agent in `run_script_chain`.

### Checked premises and open-question answers

- `run_script_phase` currently spawns only the interpreter and script path;
  the CLI has nine default aliases, retire is still registered as a built-in,
  and the fixed recipe registry contains no retire entry. The proposed `--`
  separates retire's options from launch's parser without an alias extension.
- The recurring rollback is real. The twin test fails on autoclose's Markdown;
  both named recurring jobs' Markdown and scripts differ from the packaged
  versions. `git diff c1d8227d7 HEAD -- coga/recurring/upstream-coga/ticket.md
  coga/recurring/upstream-coga/ticket.py` also confirms the clone-scope and
  conditional-bump changes were rolled back there. Preserve later work when
  restoring this behavior.
- Keeping `coga delete` in the shared topic is consistent with the explicit
  scope. No retire test depends on `LaunchBail` exception identity or its
  reason text; both the current retire handler and the launch CLI adapter
  render a nonempty reason and preserve the code. Finding 1, rather than
  exception formatting, is the substantive subprocess issue.

### Verification receipts

- `PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest -q
  tests/test_retire.py tests/test_launch_script.py tests/test_aliases.py
  tests/test_packaging.py::test_live_and_packaged_copies_stay_identical`
  → **95 passed, 1 failed** (the already identified autoclose twin drift).
- `PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest -q
  tests/test_cli.py::test_withheld_launch_return_skips_the_sweep_and_keeps_the_exit
  tests/test_launch.py::test_launch_teardown_refusal_preserves_work_result_and_stops_chaining`
  → **4 passed**.
- Interpreter: Python 3.12.12. The initial focused command using
  `python3.12` instead of `.venv/bin/python` stopped with **3 collection
  errors** because that ambient environment lacks `tomlkit`; the receipts
  above use the working checkout venv. These are design-review baseline
  checks, not the implementation's full-suite or Python 3.11 verification.
- Scratch probes exercised the existing launch/CLI paths with notifications
  and Git publication disabled or mocked, and launch-owned environment
  variables removed. No agent or production cleanup was launched. No ticket
  body, code, branch or PR was changed by this review.
- Handoff checks: `git fetch origin main` left control at `4f5b0d028`;
  `git diff --check` passed. `PYTHONPATH=/home/n/Code/claude/coga/src
  .venv/bin/python -m coga.cli validate --task
  microkernel/move-retire-to-a-command-ticket --json` reported **1 OK,
  no issues**. The diff contains only this appended blackboard review.

## Owner disposition of evaluator review (2026-10-16, implement step, attended)

- P1: back out the subprocess. `bootstrap/retire/ticket.py` calls
  `coga.launch.launch()` in-process inside `checkout_guard_scope()` (as the
  old command did under `cli.main`); if `git.state_sweep_withheld` is set
  afterwards it exits `git.RETRY_WITHOUT_SWEEP_EXIT_CODE` (75). Kernel: a
  stateless script exiting 75 makes the outer launch skip its teardown
  refresh and propagate 75, so `cli.main` skips the sweep.
- P2: a bootstrap target with `ticket.py` does not fail on operator
  resolution before its script runs; agents are still required for the
  canceled path's retire task. Add a no-agents done-retire e2e test.
- P3: accept narrower help: `coga retire --help` needs a configured
  workspace; document it rather than claim it is unchanged.
- Recommendations accepted: `coga/knowledge` ownership rule for command
  tickets; fix stale summaries (branch-sweep sweep skill, design-then-
  implement review text); stronger stateful-args refusal tests
  (draft/paused/assist + secret spy, guard before any effect).

## Dev

pr: https://github.com/FastJVM/coga/pull/1042
branch: retire-command-ticket

## Implement handoff (2026-10-16, claude, attended)

Branch `retire-command-ticket` pushed at `3df99d642d6a409ab8c51ae0d5028850969f56fa`, on top of `origin/main`
`c77870f36aee5fa6cc808508073cc81c730f4b8c`. Four commits: kernel argv + retire move; recurring twin re-sync;
docs split; workflow-summary test update.

What changed, by owner disposition above:
- Part 1: `launch_script.run_script_phase` / `run_script_chain` take
  `args`; argv is `[sys.executable, ticket.py, *args]` for stateless only
  (`ValueError` otherwise). `launch._LaunchInvocation._align_and_classify`
  refuses trailing args to a stateful `ticket.py` target right after
  classification (after assist alignment, before secrets/activation/log),
  exit 2. Tests cover active/draft/paused/human-assist with a secret spy.
- P2: same method tolerates `OperatorResolutionError` for a bootstrap
  target with `ticket.py` (operator `None`); the post-script handoff still
  refuses if the script vanished and an agent is needed.
- P1: a bootstrap script exiting 75 sets `git.state_sweep_withheld` and
  `script_retained_state`, so `refresh_after_script` skips the teardown
  refresh and `cli.main` skips the sweep (it already does for 75).
  `bootstrap/retire/ticket.py::_launch_retire_task` launches in-process
  inside `checkout_guard_scope()` and returns 75 when the nested launch
  withheld the sweep (warns on stderr if that masks a non-zero launch code).
- P3: `coga retire --help` works in a configured workspace; documented in
  `bootstrap/retire/ticket.md`. Not special-cased.
- Part 2: alias `retire = "launch bootstrap/retire --"`; built-in, import,
  `_SWEEPING_COMMANDS` entry removed; `git mv` of the module; packaged
  `ticket.md`; `EXPECTED_BOOTSTRAP_RESOURCES` updated. Tests load the
  script via `spec_from_file_location`; e2e alias cases added (done
  delete, no-agents done delete, `--no-launch`, unknown slug, `--help`).
- Part 3: recurring live templates restored to packaged bytes and the
  upstream-coga rollback of 28cba8f70 reversed (no later edits to preserve);
  retire section moved out of `coga/checkout-cleanup`; autoclose and
  branch-sweep templates link the proofs; `coga/knowledge` gains the
  command-ticket ownership row; stale summaries fixed (branch-sweep sweep
  skill, four packaged workflow review sections, and the test that pinned
  the stale `retro/done-ticket` claim); `coga/cli`, extension-model,
  script-tickets, launch, archive audit updated. The orchestration ticket
  notes retire's pending table exit.

Adjacent, not fixed here:
- `tests/test_compose.py::test_coga_repo_instructions_carry_the_minimal_core_boundary[CLAUDE.md]`
  fails on main too: the repo has no root `CLAUDE.md` (by design per
  `coga-dev/packaging`), so the parametrization is stale. No follow-up ticket
  found.
- `tests/test_clean_install_harness.py::test_release_check_requires_completed_logged_clean_task`
  fails under a fresh 3.11 venv with `No module named 'yaml'`: the harness
  needs PyYAML, which the `test` extra does not declare. Environment gap,
  passes in the checkout venv.
- `coga validate --json` repo-wide reports 2 errors on
  `marketing/demo-hackability-ask-claude-to-add-a-command-live` (missing
  `marketing/plan`, `marketing/positioning` contexts), untouched here.

## PR

```yaml
title: Move coga retire to the bootstrap/retire script command ticket
author: claude
author_evidence: Attended implement session ran as Claude Opus 5.5 (claude-opus-5-5), launch 8ad060b6-b354-4d86-9fca-f03a6c7fb7f5.
head: a93a674acec6615e314397c47a3dd924d11324a8
base: 5d6a7737d15fa4efb7cd53974824e5739f5875a8
depth: deep
rationale: Changes launch's script dispatch (argv, a new stateful refusal, operator tolerance, and an exit-75 retained-state contract) and moves a destructive command out of core; no code review yet.
implementation: Bootstrap ticket.py targets receive trailing launch args as argv; stateful script targets refuse them before any effect; a script-only bootstrap target needs no agent; a bootstrap script exiting 75 skips launch's teardown refresh and the CLI sweep. coga retire becomes the default alias "launch bootstrap/retire --" whose packaged ticket.py holds the unchanged command body, launching a canceled ticket's retire task in-process and exiting 75 when that launch withheld the sweep. Docs move retire's procedure into bootstrap/retire/ticket.md and leave shared rules in coga/checkout-cleanup.
deviations: Per the owner's implement-step disposition of the evaluator review, the canceled path stays in-process (not the designed subprocess), with the exit-75 channel; help needs a configured workspace. The live recurring templates are re-synced to their packaged clone-scoped versions.
limitations: coga retire --help no longer works without coga.local.toml. Launch framing now appears on stderr. The nested-launch withheld path is covered by unit tests (fake launch setting the flag) and a subprocess exit-75 launch test, not by a real refused checkout return under retire.
files:
  coga/recurring/autoclose-merged/ticket.md: Re-sync to packaged clone-scope version; link the shared proofs instead of restating them.
  coga/recurring/autoclose-merged/ticket.py: Re-sync to packaged version (28cba8f70 rollback).
  coga/recurring/branch-sweep/ticket.md: Re-sync to packaged clone-scope version; link proofs; correct the best-effort retire claim.
  coga/recurring/branch-sweep/ticket.py: Re-sync to packaged version (28cba8f70 rollback).
  coga/recurring/upstream-coga/ticket.md: Reverse the 28cba8f70 rollback (clone scope).
  coga/recurring/upstream-coga/ticket.py: Reverse the 28cba8f70 rollback (conditional bump).
  coga/skills/coga/branch-sweep/sweep/SKILL.md: Correct the stale best-effort retire summary.
  docs/archive/cli-extension-audit.md: Record retire moved to bootstrap/retire (ticket-requested archive edit).
  docs/contexts/coga/cli/SKILL.md: Split the delete/retire row; retire points at its command ticket.
  docs/contexts/coga/extension-model/SKILL.md: Drop retire from open placements; ten aliases; script command-ticket example and argv.
  docs/contexts/coga/knowledge/SKILL.md: A command ticket's ticket.md owns its verb's contract.
  docs/contexts/coga/launch/SKILL.md: Targets section documents bootstrap argv and the stateful refusal.
  docs/contexts/coga/script-tickets/SKILL.md: Step 4 argv contract, no-agent bootstrap scripts, exit-75 retained state.
  docs/contexts/coga/checkout-cleanup/SKILL.md: Remove the retire section; keep shared rules and point to job owners.
  src/coga/aliases.py: Add the retire default alias; drop retire from built-ins.
  src/coga/cli.py: Unregister the retire command and its sweeping entry.
  src/coga/commands/launch.py: args help text describes bootstrap argv and stateful refusal.
  src/coga/launch.py: Stateful-args refusal, bootstrap script operator tolerance, exit-75 retained state, args passed to the script chain.
  src/coga/launch_script.py: Forward args to stateless ticket.py argv; reject them for stateful phases.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md: Twin of docs/contexts/coga/cli.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/extension-model/SKILL.md: Twin of docs/contexts/coga/extension-model.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/knowledge/SKILL.md: Twin of docs/contexts/coga/knowledge.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md: Twin of docs/contexts/coga/launch.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md: Twin of docs/contexts/coga/script-tickets.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/SKILL.md: Twin of docs/contexts/coga/checkout-cleanup.
  src/coga/resources/templates/coga/bootstrap/retire/ticket.md: New stateless command ticket owning retire's procedure.
  src/coga/commands/retire.py: Removed; moved to the packaged bootstrap/retire/ticket.py.
  src/coga/resources/templates/coga/bootstrap/retire/ticket.py: Retire body moved unchanged plus Typer app, in-process launch with exit-75 handoff, __main__ guard.
  src/coga/resources/templates/coga/bootstrap/skills/coga/branch-sweep/sweep/SKILL.md: Twin of the live branch-sweep sweep skill.
  src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md: Done retire deletes with no agent; point at bootstrap/retire/ticket.md.
  src/coga/resources/templates/coga/bootstrap/workflows/code/with-review.md: Same correction.
  src/coga/resources/templates/coga/bootstrap/workflows/code/with-self-review.md: Same correction.
  src/coga/resources/templates/coga/bootstrap/workflows/docs/with-review.md: Same correction.
  src/coga/resources/templates/coga/recurring/autoclose-merged/ticket.md: Link the shared proofs (twin).
  src/coga/resources/templates/coga/recurring/branch-sweep/ticket.md: Link proofs; correct the retire claim (twin).
  tests/test_aliases.py: Assert the retire alias and that its options survive rewriting.
  tests/test_bootstrap_workflow_review_sections.py: Expect the command-ticket pointer instead of the stale retro claim.
  tests/test_launch_script.py: Bootstrap argv, no-arg argv, no-agent bootstrap, exit-75 retained state, stateful refusal before effects.
  tests/test_packaging.py: Ship bootstrap/retire ticket.md and ticket.py.
  tests/test_retire.py: Load the packaged script; withheld-launch exit 75; end-to-end alias cases.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Code review belongs to the later self-qa/review steps; design approval is not code review.
checks:
  - command: PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q -p no:cacheprovider -x --deselect 'tests/test_compose.py::test_coga_repo_instructions_carry_the_minimal_core_boundary[CLAUDE.md]'
    status: passed
    head: a93a674acec6615e314397c47a3dd924d11324a8
    base: 5d6a7737d15fa4efb7cd53974824e5739f5875a8
    detail: Python 3.12.12 — 3801 passed, 7 skipped, 1 deselected (the main-wide CLAUDE.md parametrization). Run on a rebase whose tree is byte-identical to the pushed merge a93a674ac (same tree hash).
  - command: PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q -p no:cacheprovider
    status: failed
    head: 3df99d642d6a409ab8c51ae0d5028850969f56fa
    base: c77870f36aee5fa6cc808508073cc81c730f4b8c
    detail: Python 3.12.12 — 3801 passed, 1 failed, 7 skipped. The failure (test_compose CLAUDE.md parametrization) also fails on main; the repo has no root CLAUDE.md.
  - command: PYTHONPATH=$PWD/src <scratch venv311>/bin/python -m pytest -q -p no:cacheprovider
    status: failed
    head: a232a5d53ed0c5bbb13aba7ca10ca1c66cb95a4c
    base: c77870f36aee5fa6cc808508073cc81c730f4b8c
    detail: Python 3.11.15 fresh venv, before the final test-only commit — 3796 passed, 6 failed, 7 skipped. 4 failures are the workflow-summary test fixed in the next commit (re-verified on 3.12); 1 is the main-wide CLAUDE.md test; 1 is a clean-install harness needing PyYAML, absent from the test extra.
  - command: PYTHONPATH=$PWD/src .venv/bin/python -m coga.cli validate --task microkernel/move-retire-to-a-command-ticket --json
    status: passed
    head: 3df99d642d6a409ab8c51ae0d5028850969f56fa
    base: c77870f36aee5fa6cc808508073cc81c730f4b8c
    detail: 1 OK, no issues. Repo-wide validate reports 2 errors on an untouched marketing ticket.
  - command: cd tests/fixtures/seeded-repo/coga && env -u SLACK_WEBHOOK_URL coga validate --json
    status: passed
    head: 3df99d642d6a409ab8c51ae0d5028850969f56fa
    base: c77870f36aee5fa6cc808508073cc81c730f4b8c
    detail: 4 OK, no issues.
  - command: scratch clone smoke — coga retire --help / coga retire <done-slug> / coga retire nope-xyz
    status: passed
    head: 3df99d642d6a409ab8c51ae0d5028850969f56fa
    base: c77870f36aee5fa6cc808508073cc81c730f4b8c
    detail: 'Help printed the script usage; a done ticket was deleted with commit "Ticket: smoke-two — deleted (retire)" on main and "checkout cleanup skipped" off control; the unknown slug exited 2.'
```

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `microkernel/move-retire-to-a-command-ticket`
Recorded: 2026-10-17T05:30:54+00:00

    Branch 'retire-command-ticket' is not safe to publish. refs/heads/retire-command-ticket does not contain latest origin/main. Rebase or merge before opening a PR, e.g. `git fetch origin main` then `git rebase origin/main`. Overlapping paths: coga/recurring/autoclose-merged/ticket.md, coga/recurring/autoclose-merged/ticket.py, coga/recurring/branch-sweep/ticket.md, coga/recurring/branch-sweep/ticket.py, coga/recurring/upstream-coga/ticket.md, coga/recurring/upstream-coga/ticket.py. Reconcile it and relaunch, or `coga block --task microkernel/move-retire-to-a-command-ticket`.

## Open-PR handoff (2026-10-17, claude, attended)

`coga open-pr` first refused: the checkout-return sweep `39123119e` had
published this branch's recurring-template re-sync onto `main`, so the branch
was stale with overlapping (identical) paths. Owner chose a merge over a
force-pushed rebase: `retire-command-ticket` now has `origin/main`
(`5d6a7737d`) merged in at `a93a674ac`, pushed without force. The full suite
ran on a rebased tree with the same tree hash: 3801 passed, 7 skipped,
1 deselected (the known `CLAUDE.md` case). The workflow
(`code/design-then-implement`) orders no code review, so none ran before the PR.
