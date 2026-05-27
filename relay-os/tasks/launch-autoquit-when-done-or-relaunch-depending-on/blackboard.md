The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

Good — every section the ticket references actually exists. I have enough to evaluate cold.

---

### Review: `launch-autoquit-when-done-or-relaunch-depending-on`

**Overall: solid ticket. An agent could pick this up and start.** The problem statement is grounded in real code (`DONE_MARKER` exists, the watcher exists, nothing emits it), the fix is small and well-scoped, and the boundary to the follow-up ticket is drawn clearly.

**1. Clarity:** Strong. The opening paragraph names the exact constant, the exact gap (no emitter), and the exact symptom (idle REPL after `bump`). "Done looks like" is concrete and observable. An agent with zero prior context could start.

**2. Workflow fit:** `dev/with-self-review` is appropriate. This is a small implementation + tests change with no design ambiguity that would benefit from `with-review` peer review. Self-QA pass on a four-file diff is right-sized.

**3. Contexts:** `contexts: []` and `skills: []` in frontmatter. That's defensible here — the workflow's `code/implement` skill pulls in what's needed, and the body inlines every relevant file path. No missing context jumped out. The inline file list is the right call vs. attaching contexts that would just point at the same files.

**4. Scope:** Reasonable. Three command files + one prompt doc + tests. The out-of-scope callout for auto-chaining is the single most important thing this ticket gets right — that's a genuinely separate concern and would have doubled the surface area.

**5. Assumptions worth questioning:**

- **"Don't gate on `RELAY_SUPERVISED`"** — the ticket says skip unless testing shows disruption, but `launch.py` (lines 264–267) explicitly comments that there is no `RELAY_SUPERVISED` hint by design. Worth a quick check that emitting the marker to humans running `relay bump` in a normal terminal is genuinely harmless. It probably is, but the ticket asserts it without evidence.
- **"`mark done` only, not other transitions"** — correct, but `mark.py` is 198 lines and likely has a shared code path. The ticket should flag that the emission belongs at the `done`-specific branch, not in a shared helper. Minor.
- **Prompt.md edit at line 52** says "After bumping, exit cleanly." The ticket's replacement text is good but should also touch the `## What you don't do` section (line 135) if it currently says anything about exiting — the ticket only commits to one of the two sections explicitly. Worth confirming during work, not before launch.

**Recommendation:** Launch as-is.

---

## Dev

branch: feat/autoquit-done-marker
worktree: ../relay-autoquit-marker
pr: https://github.com/FastJVM/relay/pull/235

## Plan

1. Add `emit_done_marker()` helper in `relay.repl_supervisor` (single source
   of truth for the byte sequence).
2. Call it on the success path of `bump`, `mark done`, `panic`.
3. Sanitize the composed prompt in `PromptComposition.prompt` so any
   verbatim `DONE_MARKER` in injected text is broken (insert ZWSP after `<<<`).
4. Restore `run_with_done_marker(cmd, env)` in `launch.py` interactive branch.
5. Update `prompt.md` "After bumping, exit cleanly" bullet to explain that
   the CLI commands signal the supervisor — agent does not paste the marker
   string.
6. Tests:
   - per-command marker emission on success / absence on error
   - composer strips marker injected via context or body

## Decisions

- Marker break: insert U+200D (ZWJ) right after the leading `<<<` token.
  Reason: cheapest invisible break; tests check by importing DONE_MARKER and
  asserting it does NOT appear in the composed prompt — so the fix follows
  any future rotation of the constant.
- No `RELAY_SUPERVISED` gating on emission. The marker is opaque and shows
  up as one tagged line in a non-supervised terminal; ticket's design notes
  call this out as preferred.
- Helper lives in `relay.repl_supervisor` next to `DONE_MARKER` itself, not
  duplicated per command module.

## What changed

- `relay.repl_supervisor.emit_done_marker()` — new helper that prints the
  marker on its own line (decoded ASCII; same bytes the supervisor watches
  for).
- `relay.commands.bump.bump()` — calls `emit_done_marker()` on the success
  path, after the optional `RELAY_SUPERVISED` hint. Error paths bail via
  `_bail()` and do not emit.
- `relay.commands.mark.done()` — calls `emit_done_marker()` after the
  `_mark_done` helper succeeds. `mark active` / `mark paused` deliberately
  do not (not session-end transitions).
- `relay.commands.panic.panic()` — calls `emit_done_marker()` before the
  non-zero `sys.exit(1)`. Panic is the session-end signal; the non-zero
  exit is just the distress flag.
- `relay.compose._defuse_done_marker()` — invoked from
  `PromptComposition.prompt` to replace any verbatim DONE_MARKER with a
  zero-width-joiner-spliced variant so injected text can't trigger the
  supervisor.
- `src/relay/resources/prompt.md` — "After bumping, exit cleanly" bullet
  now explains the bump/panic/mark-done commands signal the supervisor
  themselves; agents must not paste any marker string by hand.
- `src/relay/commands/launch.py` was already calling
  `run_with_done_marker(cmd, env)` on `main` — no edit needed in the
  worktree (the TEMP block was an uncommitted local-branch hack only).

## Tests added

- `tests/test_done_marker_emission.py` — per-command marker emission on
  success, absence on every error/non-terminal path.
- `tests/test_compose.py` — composer sanitizes a literal DONE_MARKER
  injected via ticket body and via blackboard.

## Verification

- `python -m pytest` — 437 passed, 1 skipped.
- `relay validate --json` against `example/relay-os/` — clean.
- Manual relaunch of this very ticket post-bump is the canonical end-to-end
  check; it'll happen as part of the workflow's next step.

## Self-QA

No fixes applied. `/code-review` and `/simplify` both surfaced only
nit-level findings, all skipped per skill scope ("leave optional/nit-level
findings for the human reviewer"):

- `bump.py:139` — the `RELAY_SUPERVISED` cyan hint ("Exit the agent
  session (Ctrl-D or /exit)") is now redundant given `emit_done_marker`
  tears the REPL down. Predates this PR; `launch.py:266` never sets
  `RELAY_SUPERVISED`, so it's effectively dead in production. Worth a
  separate cleanup, not this PR's scope.
- `compose.py:82` — `PromptComposition.byte_count` is post-defuse but
  `PromptLayer.byte_count` is pre-defuse, so the launch report's per-layer
  column won't sum to the Total row when a layer quotes the marker (3
  bytes/occurrence). Cosmetic.
- `compose.py:36` — `_DONE_MARKER_DEFUSED` uses `[:3]` to splice after
  the `<<<` prefix. If `DONE_MARKER` ever rotates the prefix, the splice
  point silently moves into the wrong token. Defusal still defeats the
  supervisor's literal match (any insertion does); the only cost is the
  visible string. `repl_supervisor.py:31-32` already flags rotation as a
  breaking change, so a future rotator will revisit the defuser too.

Re-ran `python -m pytest` (437 passed, 1 skipped) and
`relay validate --json` against `example/relay-os/` (clean) after the
QA pass. Working tree unchanged.
