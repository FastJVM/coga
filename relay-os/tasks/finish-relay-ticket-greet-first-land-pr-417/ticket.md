---
slug: finish-relay-ticket-greet-first-land-pr-417
title: Consolidate agent-triggering into one launch mechanism (greet-first as an option)
status: in_progress
autonomy: interactive
owner: zach
human: zach
agent: claude
assignee: zach
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

<!-- relay:blackboard -->

# Bootstrap notes

## Scope pivot (2026-06-22, nick + claude)

Ticket reframed during authoring. Original framing was "finish/land PR #417
(greet-first `relay ticket`)". Nick redirected: the **real** problem is that
`relay ticket` and `relay project` hand-roll their own copy of the `relay launch`
agent-spawn sequence, and PR #417's `cmd.append("Begin")` patches that *fork*
rather than the real mechanism.

**Decision:** this ticket is now "turn agent-triggering into one common
mechanism." Commands route through a single spawn path; per-command differences
(greet-first kickoff, secrets policy, discussion mode, no supervisor chain)
become explicit options. Greet-first becomes one of those options.
Direction: route-through / one common path (nick: "it'll launch itself, we can
test it") rather than a diverging copy. **Supersedes PR #417.**

Key constraints captured in ## Context: secrets must stay a parameter
(authoring = none, least privilege); the `ticket.py` copy has already drifted
(bare `subprocess.run` vs launch.py's PTY watcher) — consolidation fixes that;
greet-first greeting *text* from #417 carries over, only the trigger plumbing
changes.

Workflow: `code/with-review`. Contexts: relay/architecture, relay/codebase,
relay/extension-model. Assignee → claude (agent implements).

## Autonomy triage (advisory)
- Q1 documented: yes — refactor target, options, and constraints are all written
  into the ticket body.
- Q2 conventional enough: a straight extract-and-route refactor is conventional,
  BUT it touches the launch chokepoint (secrets, PTY watcher) where a wrong move
  has real blast radius — wants a human eye before merge.
- Q3 verifiable/bounded: yes — `python -m pytest` + live dogfood (`relay ticket`
  greets, `relay chat` silent); bounded to the in-kernel spawn path.
→ Tier: **human-verify**. Satisfied by `code/with-review`'s owner review gate.

## Evaluator review

Clear enough to start cold. The Description states the actual mechanism (compose→write→build→spawn→log), names the three call sites with line ranges, and the table makes the duplication legible at a glance. A pickup agent could begin without the interview.

The central factual claims hold. `ticket.py:163-184` and `project.py:87-109` both reimplement the launch sequence and both fall back to bare `subprocess.run`, while `launch.py:461` alone runs `run_with_done_marker`. The identical "no secrets… least privilege" comment appears verbatim in both forks. So "duplicated sequence" and "PTY drift" are real, not rhetorical.

One claim is stale and should be flagged before launch: the ticket says #417's head is a `cmd.append("Begin")` in `ticket.py`. That append is **not** present on the current working copy — `grep` finds no "Begin" in either file. The greet-first trigger the ticket promises to "convert into an option" may not exist in the branch the agent checks out. The agent must reconcile branch state first, or AC item 4 ("stops being a hardcoded append") has nothing to remove.

Workflow `code/with-review` fits: this is a refactor with a real regression risk (secrets leaking into authoring) that warrants review. Good fit.

The skeptical question the ticket asks itself — "is full consolidation right?" — is the weak point, and it under-sells the gap. `launch.py`'s spawn isn't a clean sequence; it's wrapped in a `while True` supervisor chain (line 358) doing per-step CLI re-resolution, agent rotation (claude↔codex), `RELAY_SUPERVISED` env, sentinel logic, and respawn. Authoring wants *none* of that. So "extract one `spawn_agent_session`" really means extracting the **inner single-shot body** out from under the chain loop — a non-trivial untangling the Proposed Shape glosses as a step-1 "extract." Worth calling out: the honest shared unit is "spawn one agent once," and the chain stays launch-only. The ticket gestures at this ("no supervisor chain" option) but frames it as a flag rather than a structural boundary.

Context selection is right (`codebase` for the thin-command rule earns its place); `extension-model` is correctly fenced as out-of-scope. Scope is one ticket's worth — appropriately fenced against configurable kickoff and `relay draft` removal.

Net: strong, launch-ready ticket; fix the stale #417-head claim and sharpen the "extract from under the chain loop" framing first.

## POC — feasibility proven (2026-06-22)

Built a throwaway POC to test the evaluator's worry that lifting the single-shot
body out from under the `while True` chain would be a non-trivial untangling.
Worktree: `scratchpad/poc-wt` (branch `poc/spawn-agent-session`, off `main`,
uncommitted, disposable). Verdict: **clean — the untangling is easy because the
chain and the spawn body were already separable.**

What the POC did:
- Added `spawn_agent_session(agent, mode, prompt, ref, *, env, discussion,
  kickoff, ...)` to `launch.py` — the single-shot unit: write prompt → build cmd
  → append kickoff → spawn (PTY watcher for interactive, else subprocess.run) →
  cleanup. Returns `(exit_code, kind)`.
- Routed `relay ticket` authoring through it: `env=os.environ.copy()` (no
  secrets), `kickoff="Begin"`, `discussion=True`. Deleted ticket.py's inline
  write/build/subprocess/cleanup copy.
- Did NOT yet route launch.py's own loop or project.py — minimal POC, ticket.py
  alone proves the boundary.

Results:
- Full suite green: **839 passed, 1 skipped**, with **zero test changes**.
- POC is +91 lines across 2 files (launch.py +66 helper, ticket.py net +7).
- Kickoff verified to land: claude → `[claude, --append-system-prompt, <p>,
  Begin]`; codex → `[codex, -c, developer_instructions=<p>, Begin]`; kickoff=None
  → no Begin (relay chat/launch stay silent).
- **PTY-watcher drift fixed for free**: authoring now spawns via
  `run_with_done_marker` like `relay launch`, not bare `subprocess.run`.

Design notes for the real implementation:
- POC's shared unit starts at `write_prompt_file`; compose stays at call sites
  (cheap, and launch wants `mode_override`/per-step recompose). Real impl can
  decide whether to pull compose in too — minor.
- Real impl still needs to: route launch.py's loop body through the helper,
  route project.py, and carry over #417's greeting text. POC confirms none of
  these fight the design.
- The chain (`while True`, rotation, sentinel, respawn) stayed entirely in
  launch.py — confirms it's a structural wrapper, not something the shared unit
  needs to know about.

## Evaluator fixes applied (2026-06-22)
- Clarified the `cmd.append("Begin")` lives only on the `greet-first-ticket` PR
  branch, NOT `main` — implementer reconciles branch state first.
- Reframed the shared unit as "spawn one agent once" (the inner single-shot body
  extracted out from under launch.py's `while True` supervisor chain). The chain
  stays launch-only wrapping that call — a structural boundary, not a flag.
