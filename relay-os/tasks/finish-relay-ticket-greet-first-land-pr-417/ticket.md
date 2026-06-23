---
title: Consolidate agent-triggering into one launch mechanism (greet-first as an option)
status: active
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/architecture
- relay/codebase
- relay/extension-model
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
  - name: review
    skills: []
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

`relay launch` is the real mechanism that triggers an agent: compose the
prompt → write the prompt file → build the agent command → spawn the REPL (under
a PTY watcher) → log. But `relay ticket` (authoring) and `relay project` each
hand-roll their **own copy** of that sequence inline instead of going through
it. The greet-first work (PR #417) bolted a `cmd.append("Begin")` onto the
`ticket.py` copy — i.e. it patched a *fork* of the launch mechanism rather than
the mechanism itself.

This ticket makes agent-triggering **one common mechanism** that every command
routes through, with the per-command differences (greet-first kickoff, secrets
policy, discussion mode, no supervisor chain) expressed as **explicit options**
on that one path. Greet-first stops being a special-case append in `ticket.py`
and becomes one of those options. The payoff: a single spawn path to test and
dogfood — testing the mechanism tests every command that uses it — and no
quietly-diverging copies. This **supersedes PR #417**.

## Context

**This supersedes PR #417** (`greet-first-ticket`, open). #417's earlier
revisions (a `discussion_kickoff` toml key, a `kickoff=True` flag threaded
through `build_agent_command`) were already rejected in review as touching
shared core / "the antipattern"; its current head is the minimal local
`cmd.append("Begin")` in `ticket.py`. All of that is the wrong altitude — it
operates on the *forked* spawn copy. Close #417 as superseded and reuse the
`greet-first-ticket` branch (or branch fresh) for this consolidation. The
validated greeting *text* from #417's `bootstrap/ticket` Step 1 rewrite is still
good and should carry over — only the trigger plumbing changes.

**Reconcile branch state first.** The `cmd.append("Begin")` lives only on the
`greet-first-ticket` PR branch — it is **not** on `main` (a `grep` for "Begin"
in `ticket.py`/`project.py` on `main` finds nothing). So on a fresh branch off
`main` there is no append to "convert into an option" — the greet-first trigger
is being built here, not migrated. Decide the branch base before starting, and
don't assume the append is present in your checkout.

**The duplication (the thing to kill).** Both `ticket.py:_run_authoring_session`
(~`src/relay/commands/ticket.py:159-199`) and `project.py` (~`:93`) reimplement
the `relay launch` spawn sequence found at `commands/launch.py:~400-520`:

| step    | `launch.py` (real)               | `ticket.py` / `project.py` (copy) |
|---------|----------------------------------|-----------------------------------|
| compose | `compose_prompt(...)`            | `compose_prompt(...)`             |
| write   | `write_prompt_file(...)`         | `write_prompt_file(...)`          |
| build   | `build_agent_command(...)`       | `build_agent_command(...)`        |
| spawn   | PTY watcher (REPL exit/sentinel) | **bare `subprocess.run`** (drift) |
| log     | `append_log(...)`                | `append_log(...)`                 |

The copy has already drifted: the real path runs a PTY watcher so an interactive
REPL releases on the done-sentinel, while the `ticket.py` copy uses a plain
`subprocess.run`. Consolidation fixes this drift for free.

**The options the common mechanism must carry** — these are *why* the commands
forked, so they must survive as parameters, not be flattened away:
- **secrets** — `relay launch` flows secrets to task work; ticket/project
  authoring deliberately get **none** (least privilege — there is an explicit
  comment about this at the `ticket.py` spawn site). Secrets must stay a
  parameter, default-none for authoring.
- **greet-first kickoff** — append a positional kickoff token (`"Begin"`) as the
  agent's first user turn. On for `relay ticket` (and `relay project` if wanted);
  off for `relay chat` / general `relay launch`.
- **discussion mode** — already a `build_agent_command(..., discussion=True)`
  flag; preserve.
- **no supervisor chain** — this is a **structural boundary, not a flag**.
  `launch.py`'s spawn is not a clean sequence: it lives inside a `while True`
  supervisor chain (~`launch.py:358`) doing per-step CLI re-resolution, agent
  rotation (claude↔codex), `RELAY_SUPERVISED`, sentinel logic, and respawn.
  Authoring wants none of that. The honest shared unit is **"spawn one agent
  once"** — the inner single-shot body — and the chain stays **launch-only**,
  wrapping the shared call. So the extraction is "lift the single-shot body out
  from under the chain loop," not "add a chain on/off flag."

**Codebase rules** (`relay/codebase`): keep `commands/*` thin; the shared spawn
helper is testable logic, so it belongs in a module (e.g. alongside
`build_agent_command` in `launch.py`, or a small `agent_session.py`), not in a
command file. Update the `example/` fixture and keep the packaged-template /
live `relay-os/` copies in sync where touched (CLAUDE.md). `python -m pytest`
must stay green.

## Acceptance Criteria

- [ ] One shared **single-shot** spawn entry point exists (e.g.
      `spawn_agent_session(...)`) — "spawn one agent once" — carrying compose →
      write prompt → build command → spawn-under-PTY-watcher → log → cleanup.
      `relay launch`'s `while True` supervisor chain stays launch-only and wraps
      this call; the chain is NOT pushed into the shared unit.
- [ ] `relay ticket` (authoring) and `relay project` route through it; their
      hand-rolled spawn copies are deleted. No command file reimplements the
      sequence.
- [ ] Per-command differences are explicit options on the shared single-shot
      path: `secrets` (default none for authoring), greet-first `kickoff` token,
      and `discussion`.
- [ ] Greet-first is an **option** on the mechanism, not a hardcoded append in
      `ticket.py`. `relay ticket` opts in; it works for **both** `claude` and
      `codex`. `relay chat` / general launch stay silent.
- [ ] The PTY-watcher drift is gone — authoring sessions spawn through the same
      watcher as `relay launch` (interactive REPLs release on the
      done/panic sentinel).
- [ ] Least privilege preserved: ticket/project authoring sessions still
      receive **no** secrets.
- [ ] The validated greet-first greeting text from PR #417's `bootstrap/ticket`
      Step 1 rewrite is carried over (shape-specific opening line per launch
      shape; `relay create`, not `relay draft`).
- [ ] Tests cover the shared path and the greet-first option (claude + codex
      append the kickoff via `relay ticket`; `relay chat` does not); `example/`
      fixture updated if behavior shape changed; `python -m pytest` green.
- [ ] PR #417 closed as superseded; this change ships as its own PR.

## Proposed Shape

1. **Lift the single-shot body** out from under `launch.py`'s `while True`
   supervisor chain into one shared entry (`spawn_agent_session(...)` or
   equivalent) with parameters for `secrets`, `kickoff`, and `discussion`. The
   chain (per-step re-resolution, agent rotation, sentinel, respawn) stays in
   `relay launch` and now wraps the shared single-shot call; it is not a flag on
   the shared unit. `relay launch` calls the shared unit per step with its
   current behavior (secrets on, no kickoff).
2. **Route** `relay ticket` and `relay project` through it — delete their inline
   copies — passing `secrets=none`, `discussion=True`, no chain, and (for
   `relay ticket`) `kickoff="Begin"`.
3. **Carry over** the `bootstrap/ticket` Step 1 greet-first text from PR #417.
4. **Test + dogfood**: unit-test the shared path and options; then launch
   `relay ticket` for real to confirm it greets first (claude and codex) and
   `relay chat` stays silent.

## Out of Scope

- The broader external-script / `relay-os/scripts/` extension surface
  (`relay/extension-model` tier 3 / `docs/cli-extension-external-surface.md`) —
  this ticket only unifies the *in-kernel* spawn path the existing commands
  already fork. Wiring brand-new commands onto the mechanism comes later.
- Removing the `relay draft` command (sibling ticket
  `marketing/remove-relay-draft`).
- Configurable kickoff tokens — `"Begin"` stays hardcoded at the `relay ticket`
  call site; making it configurable was explicitly rejected in #417 review.
