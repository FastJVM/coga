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
call them through `runner.run_recipe`, or run edge code through
`runner.run_entry`.

A repo script can be a thin import of a wheel-owned edge implementation or a
full local fork; distribution and adoption are in
[coga/edge-code](../edge-code/SKILL.md). Classification below is unchanged.

## Classifier

The current workflow step's `run: <skill-ref>` names a directory containing
`run.py`. It resolves local-first, then to a packaged skill. A selected
directory with a missing or unreadable script is an error. A script step
requires an agent-held role. A step without `run:` uses its task's
`ticket.py` when the task has a companion directory. Stateless bootstrap
targets continue to use `ticket.py`.

## One deterministic phase

The script runs with the current Python interpreter and ticket environment.
A stateful script receives no trailing arguments. A stateless command may
declare its own arguments. The launcher checks secrets before executing code
and records the local outcome. A nonzero exit ends the phase and reports
failure. A blocked ticket requires `coga unblock --answer` before running its
script.

## Stateless command help and interrupts

A bootstrap script receives trailing argv after launch's `--`. Its own `--`
ends option parsing: only exact `--help` before that separator requests help.
Launch detects this before ordinary configuration and session setup. Help
works without a user, agent or repository; a valid workspace resolves local
overrides first, while missing or invalid configuration uses the package.
The child runs from the host repo root, or the invocation cwd outside a repo.
Help resolves no secrets and performs no refresh, audit, publication or sweep.
Its inherited environment loses task and supervision identity and gains
`COGA_SCRIPT_HELP=1`. Each command script must check this at its command body
and exit 2 before effects: a value-taking option can consume `--help` as its
value rather than displaying help. Normal execution clears the help marker.

While a stateless child runs, the parent installs no-op Python SIGINT and
(on Windows) SIGBREAK handlers, which reset to default in the child. It never
uses inherited ignore dispositions. Console interrupts reach the foreground
child directly; the parent waits without killing it. Parent SIGTERM forwards
once, including when received during spawn. Handlers are restored after wait.
Negative signal return codes map to `128 - code`; other statuses pass through,
including exit 75's retained-state boundary. Native Windows/macOS verification
is performed at release.

## Chaining

The script phase runs at most once per step per launch:

- Step unchanged and still `in_progress`: the agent continues the same open
  step. That needs a TTY, a derivable agent operator (or the override), and
  its CLI; otherwise launch refuses and keeps the deterministic work.
- Step advanced to another agent step: that step's script phase runs first.
- Next step owner-held or unroutable, or status terminal, paused, or other:
  return to the caller.

After an agent step advances, the supervisor runs `ticket.py` again for the
new step before spawning. `--prompt-report` refuses a script target, and the
agent-only in-process delegation seam rejects one.

On native Windows the deterministic phase still runs. Python child processes
receive `PYTHONIOENCODING=utf-8` so their standard streams match the
[CLI encoding](../cli/SKILL.md), including redirected script output. This
does not enable Python UTF-8 mode or change locale-default file decoding.

## Completion attribution

`coga bump` and `coga mark done` credit `system` when `COGA_SCRIPT_TASK`
names the target they act on; a marker naming another target has no effect.
The marker grants no owner-gate, assist, launch, or rewind authority and
bypasses no completion gate, validation, or publication. A script inside a
verified recorded assist still credits `system`, using the assist's
publication checks ([human assist](../human-assist/SKILL.md)).
An assist agent keeps its verified identity; a supervised agent completion
uses the derived agent only when `COGA_EXPECTED_TASK` matches. Otherwise the
local human is credited. Ticket metadata and configured agents never prove an
agent ran. A later agent spawn clears the marker.

A script child cannot end an outer agent session: it has no done sentinel or
expected identity. A stateless agent-backed command ends its own session from
the agent with `coga mark done bootstrap/<name>`
([coga/cli](../cli/SKILL.md#stateless-command-completion)); the `bootstrap/slack`
FYI script never completes anything.

## `COGA_TASK_*` contract

The namespace is exactly `COGA_TASK_SLUG`,
`COGA_TASK_DIR`, `COGA_TASK_TICKET`, `COGA_TASK_BLACKBOARD`,
`COGA_TASK_STEP`, `COGA_COGA_OS_ROOT`, `COGA_REPO_ROOT`, `COGA_SCRIPT_TASK`,
`COGA_ASSIST_AGENT`, `COGA_ASSIST_BRANCH`, `COGA_ASSIST_PR`, and the
parser-only `COGA_SCRIPT_HELP`. There is no
`COGA_TASK_LOG`. Each launch clears every key, then sets the slug, task directory, ticket path, Coga root, and host repo root,
plus, for tasks under `tasks/` only, `COGA_TASK_BLACKBOARD` and, when a step
exists, `COGA_TASK_STEP` (`<index> (<name>)`). The script marker and assist
values are re-minted only at their launch boundaries. Nothing survives by
inheritance, so a stateless bootstrap target never exposes a packaged
`ticket.md` as a blackboard. `blackboard_from_env` refuses an inherited
blackboard outside the discovered root's `tasks/` tree and reports to stdout.

The design rationale for this shape and its source map are in
[coga-dev/microkernel](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/microkernel/SKILL.md#the-ticketpy-script-phase).
