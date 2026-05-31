---
title: test autobump
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow:
  name: test/relaunch-chain
  steps:
  - name: draft
    skills: []
    assignee: agent
  - name: expand
    skills: []
    assignee: agent
  - name: peer-pass
    skills: []
    assignee: other-agent
  - name: human-check
    skills: []
    assignee: owner
  - name: finalize
    skills: []
    assignee: agent
---

## Description

Probe the `relay launch` auto-relaunch chain end to end now that autoquit
works. The vehicle is throwaway doc-writing (`artifact.md`, one section per
step); the real subject under test is what the supervisor does at each step
boundary. The `test/relaunch-chain` workflow is arranged
`draft (claude) → expand (claude) → peer-pass (codex) → human-check (human) →
finalize (claude)` so a single run hits every boundary type once:

1. `draft` (claude) → `relay bump` → autoquit
2. `expand` (claude) — **same assignee → should auto-relaunch with no human launch**
3. `peer-pass` (codex) — claude → codex assignee change
4. `human-check` (human) — codex → human, the human gate
5. `finalize` (claude) — human → claude, then `relay mark done`

Per the supervisor code (`commands/launch.py` `_harness_stop_reason`) only
boundary 1→2 keeps the same assignee, so only that hop should auto-relaunch;
the other three are assignee changes and should **stop**, with a human running
`relay launch` for the next step. That prediction is what we're verifying — the
deliverable is the per-boundary observations in the blackboard, not the doc.

Done = the run reached `finalize` and `relay mark done`, every step left a
blackboard entry recording what actually happened at its boundary, and any
errors / not-ok behavior are captured precisely for Nick to pick up later. The
headline result is boundary 1→2: did the supervisor auto-relaunch `expand` as
claude without a human launch?

## Context

This is a test of Relay's own machinery, not a feature change. `artifact.md` is
throwaway scaffolding; the deliverable is the relaunch observations in
`blackboard.md`. Steps are skill-less by design — instructions live in the
`test/relaunch-chain` workflow body — which also exercises the "skill-less agent
steps still chain" path from #240.

**Environment (resolved during setup — see blackboard `## Environment`):** the
PATH `relay` now runs this repo's main tree editable (autoquit + autorelaunch +
#242 self-destruct fix); `relay validate` is clean and the ticket is active.
Launch **from a real TTY** (interactive auto-relaunch runs through the PTY
watcher; headless/piped won't exercise the same teardown). Do not
`conda activate relay-py312` — that env runs an older marker-branch relay.

**Prerequisite:** `peer-pass` uses `other-agent`, which resolves to codex (the
non-coder, since `agent: claude`). This needs **exactly two** `[agents.*]`
configured — with one, or three+, it raises at *bump time* on the
`expand → peer-pass` bump (one hop before codex would launch), not at codex
launch. Also confirm codex is both configured (`[agents.codex]`) and on PATH
(`command -v codex`). A missing-codex / misconfig failure is its own finding —
don't conflate it with a chain-relaunch failure.

**Logging protocol — every step appends to `blackboard.md` under `## Relaunch
test log` before it bumps**, in plain prose:

- which step / agent you are
- **were you auto-relaunched by the supervisor, or did a human `relay launch`
  you?** — and how you can tell. Don't rely on your own inference: **quote the
  supervisor's verbatim console/`log.md` lines** — its stop-reason (e.g.
  `next step assignee changed: claude → codex`), its bump chain-hint, and the
  `launched in <mode> mode` line. Those are ground truth; your prose
  interpretation is the thing under test, so anchor on the lines.
- did the **previous** step tear down cleanly (no stray process, lingering
  REPL, leftover lock, half-written state, duplicated or missing Slack post)?
  _(N/A for `draft` — it's first.)_
- did `assignee:` resolve to the expected agent for your step?
- anything that errored, looked wrong, or surprised you — be specific.

**What "not-ok" looks like — log any of these precisely:** boundary 1→2 (same
assignee) that did **not** auto-relaunch; any assignee-change boundary that
*did* auto-relaunch when it should have stopped; a step that failed to exit
cleanly after its bump; a duplicated/missing Slack post; an `assignee:` left
wrong; the chain failing to stop at `human-check`; a crash or non-zero exit
that wasn't a deliberate `relay panic`.

If a step cannot reach its bump (crash, ambiguous state, codex missing,
supervisor misbehaved), write the blocker to the blackboard and `relay panic`
with a specific reason — never stop silently. A panic mid-chain is a valid,
informative outcome.
