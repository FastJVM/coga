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
