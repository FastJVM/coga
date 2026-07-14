---
slug: install/relay-help-and-cli-should-not-require-user
title: relay CLI should not require user to be set (default to $USER)
status: in_progress
mode: agent
owner: zach
human: zach
agent: claude
assignee: zach
contexts:
- dev/code
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
step: 4 (review)
---

## Description

The `user` config requirement surfaces constantly during onboarding — a new user
can't even run `relay --help` without it, and sometimes the command then reports
it's ignoring the requirement anyway. Relax it: read-only / help commands should
not need `user` at all, and where a name is genuinely needed, default to `$USER`
when there is no local config override rather than hard-failing.

## Context

Reported by Greg as the single most pervasive friction. The name-*capture*
mechanism (`relay init --user`) already landed
(`relay-init-captures-name-via-user-param`, done); this is the complementary
*strictness* problem — the requirement is enforced far too broadly. Config
loading and `current_user` live in `src/relay/config.py`.

**Retest 2026-07-08 (fresh-container):** released 0.2.0 is fixed — `--help`
works everywhere, blank `user` tolerated. But unreleased main REGRESSES this:
`load_config` hard-fails on missing/empty `user` for every command including
`--help` (`src/coga/config.py` ~304, `src/coga/cli.py` `main()`), and since
`coga.local.toml` is gitignored, every teammate who clones a coga repo hits
it before they can run anything. Scope this ticket to main's behavior:
read-only/help commands must not need `user`, and document (or automate) the
teammate step that creates `coga.local.toml`.

<!-- coga:blackboard -->

## Dev
pr: https://github.com/FastJVM/coga/pull/546
branch: relax-user-requirement
worktree: /home/n/Code/claude/coga/.coga/worktrees/coga-relax-user

## Plan (implement step)

Scope per the ticket's 2026-07-08 retest note: fix unreleased main so
read-only/help commands don't need `user`, and document the teammate step
that creates `coga.local.toml`. Deliberately NOT adding a `$USER` fallback:
`src/coga/config.py` documents the never-guess decision (a guessed name can
disagree with ticket `owner` tokens; unattended sweeps would fail silently),
and the retest note rescopes the ticket away from the description's $USER
wording (that applied to relay 0.2.0, already fixed).

Changes:
1. `load_config(..., require_user: bool = True)` — lenient mode returns
   `current_user = ""` instead of raising; strict default unchanged so every
   mutating command still fails loud at load time with the actionable message.
2. Error message: mention `coga.local.toml` is gitignored, so each clone
   creates its own (the teammate-onboarding case `coga init` can't fix —
   it refuses an existing `coga/`).
3. Lenient call sites: `cli.py main()` eager load (fixes `coga --help`, `-h`,
   bare `coga`, `--version`, and every `<cmd> --help`), plus the read-only
   commands that never read `current_user`: status, show, validate (Typer cmd
   + `validate.main`), usage, secret get. Verified via grep none of these
   consume `cfg.current_user`.
4. `coga validate` gains a warn-severity finding when `user` is unset, so the
   diagnostic command surfaces the setup step instead of hiding it.
5. README: short "Joining an existing Coga repo" note (coga.local.toml is
   gitignored; create it with `user = "<name>"`).
6. Tests in tests/test_config.py + CLI-level tests mirroring existing style.

Findings: eager `load_config()` in `cli.py:331` is why even `--help` dies;
`sync_coga_state` doesn't read `current_user`; read-only commands verified
user-free by grep.

## Implement step — done (commit 5c7e21e8 on relax-user-requirement)

All six planned changes landed as one commit; branch rebased onto
origin/main 692a0d15 (post-rebase suite re-run, green).

- `load_config(..., require_user=True)` keyword; lenient mode returns
  `current_user = ""`. Strict path unchanged for every mutating command.
- Lenient call sites: `cli.main()` eager load, `status`, `show`, `validate`
  (Typer head + `validate.main`), `usage`, `secret get`.
- `coga validate` emits a warn finding `missing-user` / task `(config)` when
  `user` is unset, so a fresh clone doesn't validate silently clean.
- Error message + README "Joining an existing Coga repo" section document the
  teammate step (coga.local.toml is gitignored; create it next to coga.toml).
- Tests: new `tests/test_cli.py` (help/status/show/validate/usage without
  user; bump still fails loud; no warn once user set) + `tests/test_config.py`
  additions (lenient missing/blank user; message asserts).

Verification: `python -m pytest` → 1180 passed, 1 skipped (scratch venv with
editable install, python3.12). End-to-end smoke on a fixture repo without
coga.local.toml: `coga --help` 0, `create --help` 0, `status` 0, `validate`
prints the warn, `bump` exits 2 with the actionable message.

Notes for reviewer:
- `tests/test_launch_script.py::test_bootstrap_script_launch_is_stateless`
  fails without an editable install (subprocess can't import coga); it fails
  identically on unmodified main, i.e. environment-only, and passes in the
  venv run above.
- Behavior nuance: for a repo with missing `user`, the end-of-command sweep
  (`sync_coga_state`) now runs after a mutating command fails its own strict
  load (before, main() died pre-dispatch). The sweep never reads
  `current_user` and is non-fatal, so this is benign.

## Peer review — done

Native `codex review --base main` found two must-fix P2s: the read-only
`coga skill status` and `coga recurring list` views still loaded config
strictly, and `coga validate --task <slug>` skipped the new missing-user
warning. Both were reproduced and fixed in commit `3e65d4f5`, with CLI
regression coverage. Mutating skill/recurring paths remain strict.

The branch was unconditionally rebased onto current `origin/main` at
`e7c1f60d`; it is clean, two commits ahead, and zero behind. Verification:
focused missing-user coverage passed (94 tests), `git diff --check` passed,
and the full Python 3.12 suite passed (1206 passed, 1 skipped).

## PR

Relax Coga's local `user` requirement for help and every read-only CLI view
while preserving fail-loud identity checks for commands that create or move
work. Missing/blank `user` now produces an empty `current_user` only on
explicitly lenient paths; `coga validate` reports the machine-local setup
warning (including task-scoped validation), and the README documents how a
teammate joining an existing repo creates the gitignored `coga.local.toml`.
Coga deliberately still does not guess from `$USER` because ticket identity
tokens must match explicit team names.

Test plan: `python -m pytest` (1206 passed, 1 skipped).

## Usage

{"agent":"claude","cache_creation_input_tokens":347176,"cache_read_input_tokens":13469634,"cli":"claude","input_tokens":243,"model":"claude-fable-5","output_tokens":108284,"provider":"anthropic","schema":1,"session_id":"f7ed48e2-b6f3-4524-ab69-d8492f706220","slug":"install/relay-help-and-cli-should-not-require-user","step":"implement","title":"relay CLI should not require user to be set (default to $USER)","ts":"2026-07-14T19:09:16.834906Z","usage_status":"ok"}

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":4739072,"cli":"codex","input_tokens":143229,"model":"gpt-5.6-sol","output_tokens":12475,"provider":"openai","schema":1,"session_id":"019f6208-9bef-7053-af35-eb075d462a9b","slug":"install/relay-help-and-cli-should-not-require-user","step":"peer-review","title":"relay CLI should not require user to be set (default to $USER)","ts":"2026-07-14T19:23:35.945110Z","usage_status":"ok"}
