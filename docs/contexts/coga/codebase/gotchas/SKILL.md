---
name: coga/codebase/gotchas
description: Module seams and code-level hazards to respect when editing Coga's own Python (operator resolution, activation seam, blackboard writers, create guards, Typer calls, branch probes, prompt resources).
---

# Editing gotchas in Coga's source

Each item names a real seam a new caller must keep. Environment and test
pitfalls live in [coga/testing](../../testing/SKILL.md); checkout hazards in
[dev/checkouts](../../../dev/checkouts/SKILL.md).

## Seams

- **One operator resolver.** `bump.resolve_operator` is the single pure
  resolver that launch, transitions, script handoffs, status/show,
  notifications, and sweep eligibility read. Nothing stores or caches an
  assignment; a new consumer calls the resolver.
- **Activation splits at `prepare_active` / `mark_active`.** `prepare_active`
  validates, freezes the workflow ref, selects the main agent, re-derives the
  operator, and mutates an in-memory copy without writing. `mark_active`
  writes, validates, audits, and optionally syncs. `megalaunch._PREPARE_ACTIVE_ERRORS`
  encodes the division: `WorkflowMissing`, `WorkflowError`,
  `RequiredExtensionMissing`, `BlackboardNeedsSynthesis`, and
  `MainAgentUnavailable` refuse before any byte is written;
  `TaskValidationError` comes from the post-write `assert_task_valid`.
  Megalaunch prepares on a throwaway copy (`_prepare_for_launch`), preflights
  prompt, env, and agent there, commits only after every refusal passes, and
  refuses if the ticket bytes moved. The dependency-drain call site activates
  before resolving blockers on purpose, so both land in one publication; see
  [coga/megalaunch](../../megalaunch/SKILL.md).
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
  validation leaves the ticket and a `created` log line on disk. A `## ` line
  in a description passes validation but truncates the composed Description.
  Only `commands/create.py`'s `_description_structure_problem` rejects both
  hazards, before `load_config`. Any caller forwarding agent- or user-authored
  text (for example `recurring_autofix.py`'s `analysis.body`) must apply the
  same guard or accept the failure modes.
- **Recipes report to the repo under test.** Pass the discovered root to
  `task_env.blackboard_from_env(coga_os_root)`; it refuses a blackboard
  outside that root's `tasks/` tree and fails closed to stdout.
- **Shipped `ticket.py` shims go through the runner.** They call
  `run_recipe(load_config(), "<name>", [])` rather than importing the recipe
  function, so the recipe failure report applies;
  `tests/test_recurring_shims.py` pins that shape.
- **`reminders.py` is only `run()` plus `SweepResult`** for downstream sweep
  scripts: it parses `--today` / `--tasks-dir` / `--dry-run`, prints the
  report, and posts alerts through `coga slack` by default (a `ticket.py` gets
  no operands). Date math, frontmatter reads, and acks (blackboard
  `key: value` lines read with `period_state.parse_keys`) stay in each script;
  `tests/fixtures/reminders/` holds worked examples.
- **`checkout_disposal.py` is imported lazily by `autoclose.py`**, because
  `branchcleanup` imports `autoclose`'s `## Dev` parsers at load time.

## Code-level hazards

- **Calling a Typer command from Python passes `OptionInfo` sentinels** for
  every omitted option, not defaults (this crashed `repl_supervisor`'s timeout
  comparison once). Pass every parameter, or better call a non-Typer helper.
  An alias avoids it because it goes through real CLI parsing.
- **Use `git branch --show-current`, never `rev-parse --abbrev-ref HEAD`.** A
  tag with the branch's name makes the latter return `heads/<name>`. Fail
  closed when the probe errors instead of treating it as "not control".
  `branchcleanup._current_branch` is correct; `branchsweep._current_branch`
  and two call sites in `open_pr.py` still use the shadowable form and map a
  failed probe to `""`.
- **Prompt resources are the only copy of a rule most agents see.**
  `src/coga/resources/prompt*.md` compose into every launch, while contexts
  attach per ticket. Restate a rule there completely or point at the topic,
  never halfway (an abridgement once dropped the `runner.RECIPES` exception).
  When a guard spans two resources, pin both halves in
  `tests/test_compose.py` and grep the other resources before calling a
  sentence redundant.
- **A recorded "rebases clean" expires.** Re-measure drift at implement time;
  never let an inherited note stand in for running the rebase.
