## Plan

Tight, isolated change. `relay panic` should exit 1 on the success path so
parent shells / supervising agents can distinguish a panicked child from a
clean exit. All other side effects (blackboard blocker, log line, Slack
@mention, lock release, status untouched) stay exactly as they are.

## Implementation

- `src/relay/commands/panic.py` — added `sys.exit(1)` at the end of the
  success path, with a one-line comment explaining why. The `_bail` error
  path keeps using `sys.exit(2)`, matching the rest of the codebase.
- `tests/test_commands.py::test_panic_writes_blocker_and_releases_lock` —
  flipped expected exit code from 0 → 1.
- `tests/test_smoke.py` — same flip on the smoke-test panic invocation.
- `docs/spec-audit.md` §C.8 — flipped the "Stop the agent" row from 🟡 to
  ✅ and updated the note to reflect the new exit code.

## Verification

- `python -m pytest` → 111 passed.
- `python -m relay.validate --json` → 13 ok, 0 issues.

## PR

https://github.com/FastJVM/relay/pull/47 — open, awaiting human review.
