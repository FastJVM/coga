---
name: coga-dev/codebase/gotchas
description: Module seams and code-level hazards to respect when editing Coga's own Python (operator resolution, activation seam, blackboard writers, prospective validation, create guards, Typer calls, branch probes, resource packages, prompt resources, native Windows imports and writes).
---

# Editing gotchas in Coga's source

Each item names a real seam a new caller must keep. Environment and test
pitfalls live in [coga-dev/testing](../../testing/SKILL.md); checkout hazards in
[coga/git](../../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/git/SKILL.md).

## Seams

- **One operator resolver.** `bump.resolve_operator` is the single pure
  resolver that launch, transitions, script handoffs, status/show,
  notifications, and sweep eligibility read. Nothing stores or caches an
  assignment; a new consumer calls the resolver.
- **Activation splits at `prepare_active` / `mark_active`.** `prepare_active`
  validates, freezes the workflow ref, selects the main agent, re-derives the
  operator, and mutates an in-memory copy without writing. `mark_active`
  validates that copy, writes it, and audits it. `coga_edge.megalaunch` imports
  `mark.PREPARE_ACTIVE_ERRORS`, which
  encodes the division: `WorkflowMissing`, `WorkflowError`,
  `RequiredExtensionMissing`, `BlackboardNeedsSynthesis`,
  `MainAgentUnavailable`, and `RepoResourceUnreadable` refuse before any
  byte is written;
  `TaskValidationError` comes from `mark_active`'s `assert_task_valid`, which
  checks the prospective ticket before anything is written.
  Megalaunch prepares on a throwaway copy (`_prepare_for_launch`), preflights
  prompt, env, and agent there, commits only after every refusal passes, and
  refuses if the ticket bytes moved. The dependency-drain call site activates
  before resolving blockers on purpose; see
  [coga/megalaunch](../../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/megalaunch/SKILL.md).
- **Blackboard writers are fence-aware.** Persist state below
  `<!-- coga:blackboard -->` only through `taskfile.read_blackboard` /
  `replace_blackboard` or `blackboard.append_blackboard_report` /
  `append_to_section`, from a `ticket.py`, recipe, or helper alike. A raw
  append onto a file ending at the fence line glues text to the marker,
  `fence_count` drops to zero, and every reader raises `TaskFileError`. A
  whole-file marker search mistakes body prose for state. Pass captured
  `expected_bytes` to `read_blackboard` / `replace_blackboard` /
  `append_to_section`; `append_blackboard_report(cfg, ticket_path, report)`
  checks its own bytes and holds the state-publication barrier. Known gap:
  `replace_blackboard` splices directly after the marker, so when the file
  ends at the fence with no newline, start your content with a newline.
- **`create_task` validates after it writes and logs.** It calls
  `git.write_ticket`, then `append_log`, then `assert_task_valid`, so a failed
  validation leaves the ticket and a `created` log line on disk. For the
  `description` argument, `create.description_structure_problem` rejects a
  `##` line outside a code fence and an own-line blackboard fence before
  anything is written, for every caller; generated text such as the autofix
  analyst's body must be fitted first (`recurring_autofix.demote_headings`).
  The verbatim `body` argument has no such guard: an extra `##` there only
  earns validate's `uncomposed-section` warning.
- **Validate a prospective ticket before a config-dependent write.**
  `validate.assert_task_valid` leaves a bad written ticket on disk for the
  operator to fix, which is safe only for checks keyed off ticket content. A
  check that can fail on configuration (such as `unresolvable-step-assignee`)
  must run against a prospective copy before writing: copy the `Ticket`,
  apply the change, pass `ticket_override=...`, then write and log.
  `mark_done`, `mark_canceled`, `mark_active`, `mark_in_progress`,
  `mark_blocked`, `mark_paused`, bump's step advance, the assist freeze, and
  `coga owner` do this; `create_task` does not. The shared finalizers live
  in `src/coga/mark.py`; `bump.REWINDABLE_STATUSES` holds the rewind set.
- **Recipes report to the repo under test.** Pass the discovered root to
  `task_env.blackboard_from_env(coga_os_root)`; it refuses a blackboard
  outside that root's `tasks/` tree and fails closed to stdout.
- **Shipped recurring `ticket.py` shims are edge shims, not registry shims.**
  Each imports its `coga_edge` module's `main` and calls it; none calls
  `run_recipe`, and none has a `runner.RECIPES` entry. blackboard-size,
  blocker-reminders and skill-update reach `runner.run_entry`, which reports
  the run and then bumps a launched script task once. phone-home and trim-log
  call `runner.run_reported` and bump their own step. Do not turn a shim into a
  registry entry ([coga/edge-code](../../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/SKILL.md#wheel-owned-edge-implementations)).
  `tests/test_recurring_shims.py` pins the import-and-call shape only for the
  templates in `EDGE_SHIMMED_TEMPLATES` (blocker-reminders and skill-update)
  and tests phone-home's failure report separately.
- **`reminders.py` is only `run()` plus `SweepResult`** for downstream sweep
  scripts: it parses `--today` / `--tasks-dir` / `--dry-run`, prints the
  report, and posts alerts through `coga slack` by default (a `ticket.py` gets
  no operands). Date math, frontmatter reads, and acks (blackboard
  `key: value` lines read with `period_state.parse_keys`) stay in each script;
  `tests/fixtures/reminders/` holds worked examples.

## Code-level hazards

- **Patch a name where it is used.** `commands/init.py` imports `AGENT_CLIS`
  and `packaged_template_root` by name, so monkeypatching
  `coga.dependencies.AGENT_CLIS` or `coga.commands.update.packaged_template_root`
  does not reach init: patch `coga.commands.init.AGENT_CLIS` /
  `init_cmd.packaged_template_root`. `tests/test_init.py`'s `fake_vendor`
  patches only `update_cmd`, so `_do_init` still copies the real packaged
  template; tests comparing against the packaged `coga.toml` use
  `_PACKAGED_COGA_TOML`.
- **`coga validate` does not check bootstrap tickets' pinned `agent:`.** Its
  `unknown-agent` / `missing-main-agent` check (`validate._check_main_agent`)
  runs only on refs from `list_tasks(cfg)`, which walks `coga/tasks/`, so a
  `bootstrap/ticket` or `bootstrap/orient` whose `agent: claude` names an
  undeclared type (a Codex-only repo) validates clean and fails only when
  `coga ticket` or `coga chat` resolves the operator. A delivered onboarding
  ticket such as `coga-build` lives under `tasks/` and is checked. Separately,
  validate's success line prints `All good (1 tasks checked).` with no
  singular form (`validate.py`, cosmetic, no ticket).
- **Calling a Typer command from Python passes `OptionInfo` sentinels** for
  every omitted option, not defaults (this crashed `repl_supervisor`'s timeout
  comparison once). Pass every parameter, or better call a non-Typer helper.
  An alias avoids it because it goes through real CLI parsing.
- **Use `git branch --show-current`, never `rev-parse --abbrev-ref HEAD`.** A
  tag with the branch's name makes the latter return `heads/<name>`. Fail
  closed when the probe errors instead of treating it as "not control".
  `branchcleanup._current_branch` is correct. The shared `git.current_branch`
  still uses the shadowable form and has the widest reach (refresh, launch,
  `bump`, `retire`, autoclose); `branchsweep._current_branch` and two call
  sites in `open_pr.py` also use that form and map a failed probe to `""`.
- **Prompt resources are the only copy of a rule most agents see.**
  `src/coga/resources/prompt*.md` compose into every launch, while contexts
  attach per ticket. Restate a rule there completely or point at the topic,
  never halfway (an abridgement once dropped the `runner.RECIPES` exception).
  When a guard spans two resources, pin both halves in
  `tests/test_compose.py` and grep the other resources before calling a
  sentence redundant. They compose into every repo's launches, not only
  this one's, so a rule about Coga's own source tree (`src/coga/`, the
  microkernel boundary) belongs in the `coga-dev/microkernel` topic, which
  owns it; this repo's root `AGENTS.md` carries only a summary and pointer
  (`coga/context.md` only describes the repo and names `coga-dev/principles`);
  `test_packaged_prompt_layers_carry_no_coga_source_rules` pins that.
- **Every `files("coga.<pkg>")` anchor must be a regular package.** On a
  directory without `__init__.py`, `importlib.resources.files` returns a
  `MultiplexedPath`; before 3.12 its `joinpath` takes one segment and it has
  no `__fspath__`, so a multi-segment lookup raises `TypeError` (it broke
  `coga init` on 3.11, #831). Keep `src/coga/resources/__init__.py`;
  `test_coga_resources_is_a_regular_package` pins it. A green
  3.12 run says nothing about the declared 3.11 floor: run resource-lookup or
  version-sensitive stdlib changes on a real 3.11 too.
- **A blackboard section heading does not run to EOF.** A recurring digest
  writer once treated its `### State` heading as running to the end of the
  parent blackboard and swallowed the scheduler's `last_serviced_period`
  appended after it; the two writers then alternated, and every sweep re-fired
  the same period while the scan table showed an ordinary `ready` / `→ launch`.
  Bound each writer's region explicitly and test both orderings and repeated
  alternating writes ([coga/period-task](../../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/period-task/SKILL.md)).
- **A recorded "rebases clean" expires.** Re-measure drift at implement time;
  never let an inherited note stand in for running the rebase.
- **Native Windows imports and writes.** `cli.py` eagerly imports every
  command module, so a single top-level `fcntl`, `pty`, `termios`, `tty` or
  `select` import anywhere on that path breaks the whole CLI on Windows. A
  deliberate probe of that kind failed collection with 35
  `ModuleNotFoundError`s. Guard those imports with `if os.name == "posix":`,
  as `repl_supervisor` and `megalaunch` do, or import them inside the
  function that runs the PTY. Use `oscompat` for locks and process-tree
  ownership, not `fcntl` or process groups directly. Keep that module to
  locks, liveness and process trees; it is not a home for one-off platform
  checks. Text-mode writes turn `\n` into `\r\n` on Windows and break the
  `expect=` byte comparisons in `git.publish` and `write_ticket`. Write any
  file Coga or Git reads back through `atomicio.atomic_write_text`, or with
  `encoding="utf-8", newline="\n"`, and read it with `encoding="utf-8"`.
  Coga's own `.gitattributes` checks every text file out as LF, because Git
  for Windows' default `core.autocrlf=true` would otherwise give a CRLF
  source checkout that breaks byte pins and guarded audit rewrites in tests
  and would ship CRLF templates in a wheel built there. Renormalize an older
  Windows checkout once with `git rm --cached -r -q . && git reset --hard`.
  On Windows `git._git_env` also sets `gc.autoDetach` and
  `maintenance.autoDetach` to false: a detached auto-maintenance there keeps
  the captured pipes of the Git call that started it, so a Coga read would wait
  for the whole background gc.
  A new agent-session entry point must run `launch.agent_command_refusal()`
  before any checkout, publication or draft write, so a Windows command line
  that cannot be represented refuses before effects, with the sweep withheld.
- **Retired-ticket searches span two trees.** Tasks lived under
  `relay-os/tasks/` before the relay → coga rename (`d0645a197`, #454); add
  `':(glob)relay-os/tasks/**/<slug>.md' ':(glob)relay-os/tasks/**/<slug>/**'`
  to the [discovery](../../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/discovery/SKILL.md) pathspecs, or a
  `coga/tasks/`-only search misses earlier deletions.
- **Git workflows require a branch where the task records one.** Git
  workflow scripts check the recorded branch before pushing or merging.
  Preserve local work when a Git operation fails.
- **The deferred done marker has known limits.** `completion_pending` treats
  any pending file whose PID `oscompat.process_is_running` reports alive as
  live, so on POSIX a SIGKILLed Coga command left as an unreaped zombie holds
  off the terminal-status backstop until it is reaped (the idle and
  max-session backstops still apply).
- **Blocker ids are not unique.** `blackboard._blocker_id` formats only whole
  seconds (`%Y%m%dT%H%M%S`), so two asks appended in the same second (for
  example back-to-back `coga block` calls) share an `id=`. Never key
  resolution, deduplication or lookup on `Blocker.id` alone:
  `resolve_blockers_text` takes `dict[Blocker, str]` and matches whole frozen
  `Blocker` records, and `blocker_reminders` fingerprints id, stamp, actor and
  reason together. ID generation is unchanged and no follow-up ticket exists;
  a consumer that must address blockers by id first has to make ids unique
  (for example with a sub-second or counter suffix).
