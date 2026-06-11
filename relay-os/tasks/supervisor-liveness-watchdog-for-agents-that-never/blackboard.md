The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: timeout-vs-done-classification
worktree: ../relay-timeout-classification
pr: https://github.com/FastJVM/relay/pull/346
commit: 32e627f

## Open PR (2026-06-11) — open-pr step done

Pushed `timeout-vs-done-classification` (HEAD `32e627f`, 2 commits ahead of
main, worktree clean) and opened PR #346
(https://github.com/FastJVM/relay/pull/346) against `main`. No CI checks are
configured on this repo (`gh pr checks` reports none — same as prior merged
PRs), so nothing to wait on. Bumping to the human review step.

## Peer review (2026-06-11) — peer-review step done

Native review: `codex review --base main` completed after an initial sandbox
app-server read-only failure; reran with approval outside the sandbox. It found
two P2 must-fixes, both fixed in commit `32e627f`:
- **Explicit config disarm preserved.** `[launch].idle_timeout = 0` no longer
  collapses to "unset" and falls back to the 900s recurring default. `Config`
  now keeps `launch_idle_timeout_present`; recurring falls back only when the
  key is absent. Regression tests cover parser state and a bare recurring sweep
  with `idle_timeout = 0`.
- **Direct launch timeout fails loud.** Public `relay launch --idle-timeout` /
  `--max-session` now exits with the supervisor timeout code (`124`) on a
  watchdog timeout. `relay recurring` uses an internal hidden `return_timeout`
  path so it can still receive `"timeout"`, record the watchdog pause/log/Slack
  state, and continue the sweep.

Verification:
- `PYTHONPATH=src python -m pytest -p no:cacheprovider tests/test_config.py
  tests/test_launch.py tests/test_recurring.py tests/test_repl_supervisor.py`
  → `192 passed`.
- `PYTHONPATH=src python -m pytest -p no:cacheprovider` → `670 passed, 1 skipped`.
- `git diff --check` clean.

Note: the implement-step tradeoff that said standalone timeout exits 0 is now
superseded by the peer-review fix above.

## Implemented (2026-06-11) — implement step done

All four scoped items landed; full suite green (`668 passed, 1 skipped` via
`PYTHONPATH=src python3.12 -m pytest`). Note: project's checked-in venv is
unrelated; tests run under python3.12 (3.11+ needed for `tomllib`).

What changed (commit 952af1a on `timeout-vs-done-classification`):
- **repl_supervisor.py** — `run_with_done_marker` returns `ReplOutcome(exit_code,
  kind)` instead of a bare int; kind ∈ natural/done/timeout/crash.
  `_trigger_term(reason, *, kind)`; idle + new **max-session** breaches are
  kind="timeout", sentinel/pty are "done". `_classify_exit(status, term_kind)`
  → 3-tuple; timeout teardown reports `_TIMEOUT_EXIT_CODE` (124). A non-our
  signal is still surfaced as a crash regardless of teardown kind.
- **launch.py** — `--max-session` flag; threads it through; on kind=="timeout"
  echoes + **returns "timeout"** (no sys.exit) so recurring continues. launch's
  return type is now `str | None`. Crash path (non-zero, non-timeout) unchanged.
- **recurring.py** — `_recurring_idle_timeout(cfg)` + new `_recurring_max_session
  (cfg)` with precedence env > `[launch].*` > default (idle default 900;
  max-session has no default). `_stop_if_unfinished_after_launch(timed_out=...)`:
  new branch pauses a timeout as `actor=system:watchdog` (⏱️ Slack, distinct log)
  rather than the `human:<user>` masquerade; sweep continues. Debug sweep armed too.
- **config.py** — `[launch]` table → `Config.launch_idle_timeout/max_session`
  (`_parse_launch`; <=0/non-finite/omitted → None; non-number fails loud).

Tests: flipped the idle-timeout assertion to 124/"timeout"; pinned done vs
timeout vs crash in `_classify_exit`; new max-session output-producing-loop PTY
test; `[launch]` parse/precedence tests; recurring timeout-disposition test
asserting the `[system:watchdog]` (not human) trace.

Decisions/tradeoffs for reviewer:
- Standalone `relay launch --idle-timeout` timeout now exits 0 (returns instead
  of sys.exit) — no regression (it already mapped timeout→0) and it prints the
  timeout clearly. Acceptance's "non-zero exit" is the supervisor classification
  (124), unit-tested against a real PTY. Recurring needs the no-sys.exit so a
  SIGTERM doesn't abort the whole sweep.
- max-session is opt-in (no built-in default): a legitimately long interactive
  step shouldn't be killed unless the team sets `[launch].max_session`.
- Example fixture not touched — it doesn't document `[git]` either, and the new
  keys are optional with safe defaults; no task-layout/prompt/workflow change.

## Implement plan (2026-06-11)

Human decisions (asked on launch of implement step):
- **Wall-clock cap (item 4): INCLUDE.** Idle-timeout misses an output-producing
  infinite loop; add a `max_session` wall-clock cap alongside `idle_timeout`.
- **Config surface: SIMPLE `[launch]` table.** Precedence env > relay.toml >
  hardcoded default. Not per-mode.

Design (threads a termination *kind* supervisor → launch → recurring):

1. `repl_supervisor.py`
   - New `ReplOutcome(exit_code:int, kind:str)` frozen dataclass; `kind ∈
     {natural, done, timeout, crash}`. `run_with_done_marker` now returns it
     (was bare int). No-tty fallback returns `ReplOutcome(code, "natural")`.
   - `_trigger_term(reason, *, kind)`. Call sites: sentinel(:248)/pty(:273) =
     "done"; idle breach(:255) = "timeout"; NEW max-session breach = "timeout".
   - Loop tracks `term_kind: str|None` + `session_start`. New max-session check
     mirrors the idle check but measures wall-clock from spawn, so it fires even
     while the child is streaming output (the gap idle misses).
   - `_classify_exit(status, term_kind)` (was `sent_term: bool`) → returns
     `(exit_code, kind, notes)`. term_kind None = passthrough. "done" → our-signal
     0/done, non-our-signal crash. "timeout" → our-signal `_TIMEOUT_EXIT_CODE`
     (124, the `timeout(1)` convention)/timeout, non-our-signal crash.
2. `commands/launch.py`
   - Add `--max-session` option (default None, parity with `--idle-timeout`).
   - Use `outcome = run_with_done_marker(...)`. On `outcome.kind == "timeout"`:
     echo a timeout line and **`return "timeout"`** (do NOT sys.exit — recurring
     must continue the sweep + record it). Crash path (non-zero, non-timeout)
     keeps today's `sys.exit(exit_code)`. launch now returns `str | None`.
     Standalone `relay launch --idle-timeout` timeout exits 0 (prints clearly) —
     no regression (it already mapped timeout→0). Acceptance's "non-zero exit" is
     the supervisor classification (124), unit-tested against a real PTY.
3. `commands/recurring.py`
   - `kind = launch_cmd(...)`; pass `timed_out=(kind=="timeout")` to
     `_stop_if_unfinished_after_launch`.
   - That fn: new `timed_out` branch FIRST → `mark_paused` with timeout flavor
     (`actor="relay:watchdog"`, ⏱️ slack, "liveness watchdog … timed out") instead
     of the human-pause masquerade. Pause+continue (don't abort sweep) so one
     stuck agent can't starve later tasks. Existing human-pause / loud-stop
     branches unchanged.
   - `_recurring_idle_timeout(cfg)` + new `_recurring_max_session(cfg)`:
     env > `cfg.launch_idle_timeout`/`launch_max_session` > default.
4. `config.py`
   - Parse `[launch]` → `Config.launch_idle_timeout`, `launch_max_session`
     (`float | None`, <=0/non-finite/omitted → None). New `_parse_launch`.
5. Tests (`tests/test_repl_supervisor.py`)
   - Update `_classify_exit` 3 tests to `term_kind=` + 3-tuple; helpers return
     `ReplOutcome`; flip idle-timeout test to assert `exit_code==124`,
     `kind=="timeout"`; pin `kind=="done"` on sentinel/marker tests; NEW
     max-session test (output-producing loop, idle never trips). New
     `tests/test_config*.py` case for `[launch]` parse; recurring disposition
     test if a sibling harness exists.

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
