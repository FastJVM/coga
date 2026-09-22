---
name: coga/script-tickets
description: The deterministic `ticket.py` launch phase — its exact classifier, environment, reloads, chaining into and out of agent steps, completion attribution, and the `COGA_TASK_*` metadata contract it shares with agents and recipes.
---

# Script tickets (`ticket.py`)

A ticket owns deterministic work by carrying one file named exactly
`ticket.py` beside `ticket.md`. There is no execution-mode field, no plugin
scan, no import of ticket code, and no frontmatter switch; workflow skills
stay prompt contracts. Registered `coga run` recipes remain the
repository-independent command surface (`coga/extension-model`); a script may
call them through `runner.run_recipe`.

## Classifier

`launch_script.script_entry_point` returns `<task_dir>/ticket.py` when it is
a regular file. File-form tasks have no task directory and never qualify.
Directory tasks and bootstrap tickets use the same name. Executable bits and
other filenames never participate: a `run.py`, test, or other executable
attachment is untouched by the classifier and runs only when agent
instructions invoke it explicitly. A user repo may keep script tests beside
the ticket, but Coga neither discovers nor runs them. A recurring template's
`ticket.py` is copied into each period task (`coga/recurring/templates`). Classification is a point-in-time stat:
launch repeats it after every moving sync, and a vanished file becomes an
agent-only handoff instead of a failed run of a stale path.

## One deterministic phase

`run_script_phase` runs before any agent setup: no prompt composition, CLI
lookup, skill refresh, or push probe.

1. Declared secrets resolve (`build_launch_env`) before any lifecycle write.
2. An `active` ticket becomes `in_progress` (actor `system`, `▶️ script
   started`); draft/paused/blocked were activated just before. A
   `launched as a script (ticket.py)` log line is published before user code.
3. Those syncs can move a control checkout, so config, target, ticket,
   secrets, and the entry stat are reloaded. If the task vanished, its status
   is no longer `in_progress`, or its routing identity (status, step, owner,
   main agent, step roles) changed, the script does not run and the fresh
   state is reclassified.
4. The child runs as `[sys.executable, ticket.py]` from the host repository
   root with no operands. Its environment gets fresh `COGA_TASK_*`,
   `COGA_SCRIPT_TASK=<absolute target path>`, and loses `COGA_SUPERVISED`,
   `COGA_DONE_SENTINEL`, `COGA_EXPECTED_TASK`, and `COGA_EXPECTED_STEP`, so a
   child completion cannot finish an outer agent session.
5. `script exited with code N` is logged even if the script deleted or broke
   its ticket. A non-zero exit posts `💥 script failed` (non-fatal to the
   post) and launch exits with that code. On success config, target, and
   ticket are re-derived again. A bootstrap script keeps framing on stderr so
   `$(coga <verb>)` sees only its stdout.

## Chaining

`run_script_chain` runs at most once per step per launch:

- Step unchanged and still `in_progress`: the agent continues the same open
  step. That needs a TTY, a derivable agent operator (or the override), and
  its CLI; otherwise launch refuses and keeps the deterministic work.
- Step advanced to another agent step: that step's script phase runs first.
- Next step owner-held or unroutable, or status terminal, paused, or other:
  return to the caller.

After an agent step advances, the supervisor runs `ticket.py` again for the
new step before spawning. `--prompt-report` refuses a script target, and the
agent-only in-process delegation seam rejects one.

## Completion attribution

`coga bump` and `coga mark done` credit `system` when `task_env.is_script_task`
matches the target they act on; a marker naming another target has no effect.
The marker grants no owner-gate, assist, launch, or rewind authority and
bypasses no completion gate, validation, or publication. A script inside a
verified recorded assist still credits `system`, using the assist's
publication checks ([human assist](../internals/human-assist/SKILL.md)).
An assist agent keeps its verified identity; a supervised agent completion
uses the derived agent only when `COGA_EXPECTED_TASK` matches. Otherwise the
local human is credited. Ticket metadata and configured agents never prove an
agent ran. A later agent spawn clears the marker.

## `COGA_TASK_*` contract

`task_env.TASK_ENV_KEYS` is the whole namespace: `COGA_TASK_SLUG`,
`COGA_TASK_DIR`, `COGA_TASK_TICKET`, `COGA_TASK_BLACKBOARD`,
`COGA_TASK_STEP`, `COGA_COGA_OS_ROOT`, `COGA_REPO_ROOT`, `COGA_SCRIPT_TASK`,
`COGA_ASSIST_AGENT`, `COGA_ASSIST_BRANCH`, and `COGA_ASSIST_PR`. There is no
`COGA_TASK_LOG`. `apply_task_env` clears every key, then `build_task_env`
sets the slug, task directory, ticket path, Coga root, and host repo root,
plus, for tasks under `tasks/` only, `COGA_TASK_BLACKBOARD` and, when a step
exists, `COGA_TASK_STEP` (`<index> (<name>)`). The script marker and assist
values are re-minted only at their launch boundaries. Nothing survives by
inheritance, so a stateless bootstrap target never exposes a packaged
`ticket.md` as a blackboard. `blackboard_from_env` refuses an inherited
blackboard outside the discovered root's `tasks/` tree and reports to stdout.
