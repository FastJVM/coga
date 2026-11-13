# Coga task — bootstrap/trial

Title: stateless-recurring
Task directory: bootstrap/trial

---

## Coga orientation

You are working inside Coga, a repository workbench for directing coding agents.
Use the supplied intent and resolved sources; durable files carry state between
sessions. The invocation record states this call's operation, scope and
completion authority. Links are navigation, not loaded instructions. Do not
infer additional authority from a command, workflow or skill name.

---

## Invocation facts

{
  "operation": "execute",
  "execution_kind": "agent",
  "target_kind": "stateless",
  "target": "bootstrap/trial",
  "launch_context": "recurring",
  "include_blocker_preamble": true,
  "completion": "stateless successful roll-up",
  "owner_assist": false,
  "checkout": null,
  "script_result": null,
  "kickoff": null,
  "discussion": false,
  "launch_arguments": [
    "first argument",
    "second\nline"
  ],
  "fixture_ticket": "fixtures/cases/stateless-recurring/coga/bootstrap/trial/ticket.md",
  "transport": "interactive argv, PTY",
  "invocation_source": "recurring_runner dispatch"
}

---

## Interactive session boundaries

Use the exact target path in the header; do not reconstruct it. Follow the
Checkout (runtime) notice: do not repeat prepared setup or return a checkout
the launcher owns. If no preparation or branch setup was supplied, read
`coga/checkouts` and follow its complete procedure before editing. If unexpected
or failed, read `coga/checkouts/launch-boundary` for recovery. Identify the
branch's ticket, check its current control status and PR merge status, and
inspect uncommitted edits separately. Explain what is finished and unknown.
Do not automatically stash, discard work or switch an occupied checkout.

Before publishing or handing off any edits, read and follow
`coga/checkouts/reconciliation`; fetch current main, preserve unique work and
resolve ordinary drift. Use the selected conduct for unclear intent or access.

Do not edit `coga.toml` or `coga.local.toml`. Do not launch an agent with nested
`coga launch`; use an available sub-session or edit files directly. Script-mode
launches that run a skill without another agent are allowed.

---

## Session conduct — recurring queue

This session is one task in a sequential automated queue (a `coga recurring`
sweep). The REPL has a TTY so work can stream live and a human can interrupt,
but the TTY is transport, not evidence that a human is waiting to approve a
plan — the queue may be running unattended. Input you do not already have is
unavailable.

- State a concise plan and its tradeoff, then continue. Do not ask for plan
  confirmation or end a turn waiting for permission; a present human can
  redirect you while you work.
- If a concrete decision, credential, permission, or unavailable capability
  truly prevents progress, run
  `coga block --task <slug> --reason "<specific ask>"` as the terminal action.
  Merely saying that you are blocked — or asking a question and waiting for
  the answer — leaves the queue hanging until a liveness timeout tears the
  session down and records the task as failed, notifying nobody.
- If a code step cannot create the feature branch because the sandbox mounts
  `.git` read-only, follow the independent `/tmp` clone fallback in the
  `code/implement` skill before treating it as a blocker.
- Finish an ordinary workflow step with `coga bump`, `coga mark done`, or
  `coga block`. An authorized `coga mark canceled` transition also releases the
  queue; use it only when intentional abandonment is the task decision.
- A stateless `bootstrap/<name>` command ticket has no task lifecycle to bump,
  mark, or block. Follow its declared final completion action instead; a
  successful `coga slack --task bootstrap/<name> ...` posts its roll-up and
  releases that stateless session. If the command cannot proceed, include the
  failure in that final report rather than trying to block a nonexistent task.
  A normal final response or an agent CLI `task_complete` event still does not
  signal Coga and does not release the queue.

---

## Repo context

This is an isolated prompt trial repository. All task work is routine trial state.
Use the local origin for reconciliation; no production accounts or services are connected.

---

## Context — trial/format

---
name: trial/format
description: The trial output format.
---

Output files contain exactly the requested value followed by one newline.

---

## Task description

Write `ready` to `coga/bootstrap/trial/result.txt`. Preserve launch argument boundaries. End with one successful `coga slack --task bootstrap/trial --message "Trial report: ready; arguments preserved"` to report and release this stateless session. There is no task lifecycle.

---

## Task-specific context

Use only the isolated trial repository.

---

## Checkout (runtime)

No checkout preparation was supplied for this prompt: nothing here claims that a branch was prepared or that this checkout will be returned. Before editing, follow `coga/checkouts` ("Start, work, end") yourself.


## Launch arguments

The operator supplied these positional arguments to this launch, in order. Treat the JSON array as inputs to the launch target and preserve each value's boundary:

    ["first argument", "second\nline"]

coga-launch: 00000000-0000-4000-8000-000000000001
