The blackboard is a notepad to be written to often as the human and agent works through a task.

## Bootstrap notes (2026-06-11)

Frontmatter filled during bootstrap interview: `workflow: code/with-review`,
`contexts: [dev/code]`, `assignee: claude` (was nick / null / empty).
Evaluator flagged the ticket as stale — idle-timeout backstop already landed
(verified: `repl_supervisor.py:120,251-256`, `launch.py:88 --idle-timeout`,
`recurring.py:41 _RECURRING_IDLE_TIMEOUT_SECONDS` + `RELAY_REPL_IDLE_TIMEOUT`,
test `tests/test_repl_supervisor.py:139`). Human approved rescoping the Description to the remaining delta.

Rewrite done (2026-06-11): Description/Context now target the classification
gap, not the landed detection. Decisions baked in:
- Max-session wall-clock duration: included as item 4, **optional / decide on
  review** — folded into the config-surface work since it's cheap there and
  closes the output-producing-infinite-loop gap idle-timeout misses. Human can
  drop it on review.
- Corrected the original's wrong claim that `_stop_if_unfinished_after_launch`
  "chains off each exit code" — it re-reads ticket status from disk. Real silent
  path reframed as the interactive-timeout-pauses-as-human-pause masquerade
  (`recurring.py:872-896`).
- All line refs refreshed against current source.

## Evaluator review (round 2, post-rewrite)

Verdict: **ready-with-nits** — every line ref and technical claim verified
accurate against current source; scope is a single coherent ticket targeting
only the classification delta (not re-implementing landed detection); auto-vs-
interactive correction matches the code. Nits raised: (a) `:139` collides
between repl_supervisor docstring and the test file — left as-is, both correct;
(b) item 4 wall-clock cap is explicitly optional, human makes keep/drop call;
(c) folded in — enumerated the three `_trigger_term` call sites (sentinel/pty =
done, idle = timeout); (d) folded in — steered item 2's writer to `recurring.py`
since the supervisor has no Slack/log.md plumbing today. No correctness blockers.
Safe to launch.

## Evaluator review

## Verdict: needs-work

The ticket is well-written and technically literate, but it is **stale**: its core premise — "there is no timeout, no idle-output watchdog" — is no longer true. PR #277 (`recurring: skip unattended interactive templates + idle-timeout backstop`) already landed most of what the ticket asks for. An agent picking this up cold would either re-implement existing code or be badly confused on first contact with the source. Rescope to the remaining delta before launch.

### Findings

1. **Clarity (good, but built on a false premise).** The description is unusually concrete — motivation, mechanism, failure mode, acceptance criteria. An agent could start immediately. The problem is what it would find: `run_with_done_marker` already takes an `idle_timeout` parameter (`src/relay/repl_supervisor.py:114-146`, teardown trigger at lines 250-257), `relay launch` exposes `--idle-timeout` (`src/relay/commands/launch.py:88`), and the recurring sweep already arms a 900s default with `RELAY_REPL_IDLE_TIMEOUT` env override and disarms it for `--interactive` (`src/relay/commands/recurring.py:41, 122, 911-929`). Even the acceptance test exists: `tests/test_repl_supervisor.py:139` (`test_idle_timeout_terminates_silent_child`, a real PTY running `sleep 30` against a 0.5s limit).

2. **What genuinely remains** (this is the real ticket, and it's worth doing):
   - **Exit classification.** The ticket's claim about `_classify_exit` is accurate and still unfixed: any supervisor-sent SIGTERM/SIGKILL maps to exit 0 / "done-signal received" (`repl_supervisor.py:333-339`), and the idle-timeout teardown reuses the same `_trigger_term` path — the docstring even admits "idle-timeout trigger, reported exit 0" (line 140). The existing test *asserts* exit 0 for a timeout. Threading a termination kind (done vs timeout) through `_trigger_term` → `_classify_exit` is real, undone work.
   - **`log.md` entry + Slack post classifying the timeout.** Not implemented; a timed-out run leaves no durable timeout record.
   - **Max-session duration.** Only idle exists; the ticket's "and/or" leaves it to the agent to decide whether wall-clock matters. Decide before launch.
   - **Config surface.** The greenfield claim holds: `config.py` has no `[launch]`/timeout keys; configuration is a hardcoded constant plus an env var. Moving per-task/per-mode config into `relay.toml` is legitimate scope.

3. **Stale line numbers throughout.** `run_with_done_marker` is at line 114, not ~79; `_classify_exit` at 316, not 251; the `sent_term` branch at ~333-348, not 268-283; the sequential launch loop at `recurring.py:126-142`, not 66-81. Harmless individually, but combined with the stale premise they signal the ticket predates #277 (created 2026-05-29) and was never refreshed.

4. **One factual claim is wrong.** "`_stop_if_unfinished_after_launch` chains off each exit code" — it doesn't; it ignores the exit code entirely and re-reads ticket status from disk (`recurring.py:852-905`). Consequently the "silent failure" claim is overstated for the bare sweep: a timed-out auto-mode task leaves the ticket `in_progress`, so the sweep stops loudly with exit 1. The *real* residual silent path is interactive-mode tickets: a timeout there gets **paused** as if a human deliberately parked it (`recurring.py:872-896`) — indistinguishable from intent. That's the sharper framing the rewritten ticket should use.

5. **Workflow fit: good.** `code/with-review` (implement → peer-review → open-pr → human review) matches a supervisor/classification code change with tests cleanly. No mismatch.

6. **Contexts: adequate.** `dev/code` is relevant (branch/worktree/PR conventions for exactly this workflow) and narrow enough that nothing needs copying into the ticket body — the ticket already carries its technical context inline, which is the right pattern. Nothing important missing; there is no more-specific supervisor context to attach.

7. **Scope.** As written it bundles five things, but two are already shipped. The remaining delta (exit-kind threading + log/Slack classification + toml config surface, optionally max-session duration) is one coherent ticket. If max-session duration is wanted, say so explicitly; "and/or" invites scope drift.

**Recommendation:** rewrite the Description/Context to acknowledge the landed `idle_timeout` (cite PR #277, `_RECURRING_IDLE_TIMEOUT_SECONDS`, `RELAY_REPL_IDLE_TIMEOUT`) and target only the delta: timeout-vs-done exit classification, timeout records in `log.md`/Slack, the interactive-timeout-masquerades-as-pause hole, and the `relay.toml` config surface. Update line references while at it.
