---
slug: fix-the-autofix-analyst
title: Fix the autofix analyst
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- coga/recurring
- coga/codebase
- coga/principles
- coga/extension-model
skills: []
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 4 (review)
---

## Description

Three independent fixes to the recurring sweep's autofix analyst
(`src/coga/recurring_autofix.py`). They were found together while diagnosing a
real sweep failure, but each stands alone.

**1. Report the failure that actually happened.**
`analyze_record` builds its error detail as
`detail = (result.stderr or result.stdout or "").strip()`. `stderr` short-circuits,
so any warning on stderr hides the real cause on stdout. Observed on the
20260825T105618 sweep: the operator was told

    claude exited 1: ⚠ claude.ai connectors are disabled because
    ANTHROPIC_API_KEY or another auth source is set ...

when the actual cause, on stdout, was `Credit balance is too low`. The connector
line is an unrelated warning. This is a principle-6 defect: it fails loud, but
loudly wrong, which is worse than quiet for a human trying to act on it.
Include both streams (labelled) in `AutofixUnavailable` rather than picking one.

**2. Don't inherit stdin.** The `subprocess.run` in `analyze_record` passes no
`stdin`, so the analyst inherits the parent sweep's. `codex exec` documents that
a piped stdin is *appended to the prompt* as a `<stdin>` block, so an inherited
pipe silently grafts unrelated bytes onto the analysis prompt. Pass
`stdin=subprocess.DEVNULL`; it is correct for every one-shot CLI, not just codex.

**3. Make the analyst's agent selectable on its own.** `_analyze_agent` falls
back to `cfg.default_agent()` — literally the first `[agents.*]` table in
`coga.toml`, i.e. the create-time ticket default. The two existing levers are
both wider than the intent:

- reordering `coga.toml` switches the analyst *and* every new ticket's default;
- `coga recurring --agent codex` switches the analyst *and* every agent-backed
  period task in the sweep.

Neither can express "the meta-loop uses a different vendor than the work" — which
is a thing you want, both because a different vendor is a genuine second opinion
on sweeps the default agent ran, and because it decouples self-analysis from the
same auth path that just broke. Add one narrow config key, read by
`_analyze_agent` before the `default_agent()` fallback:

```toml
[autofix]
agent = "codex"
```

The explicit `--agent` override still wins over it; `default_agent()` remains the
fallback when the key is absent, so behavior is unchanged out of the box. Adding
a config section means adding it to its table's allowlist in `config.py` or the
next command fails loud (that is the intended fail-loud behavior — wire it up).

Keep it to one key and one branch. This is not a plugin seam or a general
per-command agent-routing mechanism; resist growing it into one.

## Context

**Verified on this machine, 2026-08-25** (both from
`/home/n/Code/claude/coga`):

    $ claude -p "Reply with exactly: ok"
    exit=1
    stdout: Credit balance is too low
    stderr: ⚠ claude.ai connectors are disabled because ANTHROPIC_API_KEY ...

    $ codex exec "Reply with exactly: ok"
    exit=0

`ANTHROPIC_API_KEY` is exported in the operator's shell environment. Headless
`claude -p` resolves auth to it instead of the claude.ai login — there is no
interactive "use this API key?" gate — and that key's account has no credit.
Every other agent Coga spawns is an interactive PTY REPL on the subscription
login, which is why the autofix analyst is the only Coga call that fails this
way. Note that fixing the operator's environment would make this particular
symptom disappear without fixing any of the three defects above; do not treat a
green sweep as evidence.

Codex's `exec` banner (version, workdir, model, session id) does **not** need
stripping: `parse_analysis` regex-scans for `^VERDICT:` anywhere in the reply
rather than parsing by position, so the preamble is already inert. Don't add
output-scrubbing that isn't needed.

Relevant existing surface:

- `DEFAULT_ANALYZE_TEMPLATES` and `[agents.<name>].analyze` already give each CLI
  its one-shot argv — that part of the vendor-swap story works and needs nothing.
- `recurring_runner.py` already threads `agent_override` into `run_autofix`, so
  `coga recurring --agent <type>` reaches the analyst. Keep that precedence:
  explicit flag > `[autofix].agent` > `default_agent()`.

Tests belong in `tests/` next to the existing autofix coverage; the error-detail
and stdin changes are both directly unit-testable with a faked `subprocess.run`.


<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Investigation

- The ticket's Description and Context are empty, and there is no attached run
  log or recorded symptom.
- The focused baseline passes: `python -m pytest
  tests/test_recurring_autofix.py -q` -> 31 passed.
- The immediately preceding draft was titled "Make the autofix analyst legible
  and its agent selectable", but that ticket was also empty before it was
  deleted and replaced by this one.

## Ambiguity

Resolved with the owner: the recurring autofix analyst failed because its
Claude Code call used an unusable authentication source.

## Reproduced failure

- The machine-local run record at
  `/home/n/Code/claude/coga/coga/.coga/recurring-runs/20260825T105618.md`
  shows a healthy 10:56 sweep: three completed tasks and zero run problems.
- The corresponding Claude analyst session started at 10:58:05 and returned
  `billing_error: Credit balance is too low`.
- `claude auth status` says the user is logged in through claude.ai, but also
  reports `apiKeySource: ANTHROPIC_API_KEY`; that exported variable is present
  in `.bashrc` and takes precedence. No credential value was read or recorded.
- Running the same auth-status check with only `ANTHROPIC_API_KEY` removed
  confirms a usable claude.ai Max subscription login, so the analyst has a
  working automatic fallback on this machine.
- With no override, `recurring_autofix._analyze_agent` chooses the first agent
  declared in `coga.toml` (Claude here). The existing recurring `--agent`
  override also changes agent-backed task launches, so it cannot independently
  route only the analyst around this auth failure.

The owner confirmed the automatic fallback contract below.

## Proposed fix

Keep the configured Claude authentication source as the first attempt. When
that attempt exits with a recognized authentication or billing error and an
ambient `ANTHROPIC_API_KEY` is present, check whether Claude Code has a usable
claude.ai login without the variable and retry the analyst once with only that
variable removed. Announce the fallback, preserve API-key-only installations,
and leave unrelated failures single-attempt and loud. Cover the auth failure,
successful subscription retry, missing-subscription, and unrelated-failure
paths with deterministic subprocess fakes; update the recurring contract and
its packaged copy.

## Dev

pr: https://github.com/FastJVM/coga/pull/724
branch: autofix-claude-auth-fallback
worktree: /tmp/coga-autofix-auth-fallback

## Implemented

- The analyst keeps the configured environment for its first call. A
  successful Claude API-key call is never probed or replaced.
- A non-zero Claude result containing a recognized authentication or billing
  marker now triggers a bounded `claude auth status` check with only
  `ANTHROPIC_API_KEY` removed. Coga retries once in that environment only when
  the JSON status confirms a signed-in claude.ai account and no other API-key
  source.
- The fallback is announced on stderr. API-key-only installations retain the
  original failure, and unrelated failures plus non-Claude agents never switch
  authentication.
- Updated the live `coga/recurring` contract, `docs/reference.md`, and the
  packaged CLI context that describes recurring autofix behavior.

## Verification

- `python -m pytest tests/test_recurring_autofix.py -q`: 35 passed.
- Full suite with the feature `src/` and the already-cached declared build
  dependencies on `PYTHONPATH`: 1990 passed in 119.28s. The first bare
  worktree run had 19 environment-only failures because child Python
  processes could not import the uninstalled src-layout package and
  `hatchling` was absent; representative child-process/wheel tests and then
  the full suite passed once the declared test environment was supplied.
- `git diff --check origin/main...HEAD`: clean.
- `env -u ANTHROPIC_API_KEY claude auth status` confirmed the real fallback
  account is logged in through claude.ai with a Max subscription. No real
  analyst/model call was made during verification.
- Commit: `8e3f6451` (`Retry autofix analyst with Claude subscription`).
- `git fetch origin main` followed by `git rebase FETCH_HEAD`: already current;
  the branch is clean and one commit ahead of `origin/main`.

## Self-QA

- `codex review --base main` found that the initial fallback check did not
  prove the retry would use an entitled first-party subscription: custom
  analysis argv or Anthropic routing could change the effective credential,
  a forced Console login policy was ignored, and a signed-in free account was
  accepted without a subscription entitlement.
- The `/simplify` UI command was unavailable in this launched session, so an
  equivalent `codex exec` simplify pass reviewed the diff and consolidated the
  duplicated analyzer subprocess calls into a bounded two-attempt loop.
- Applied the review findings by limiting fallback to Claude's built-in
  analysis argv and standard auth routing, honoring `forcedLoginMethod`, and
  requiring a first-party Pro, Max, Team, or Enterprise subscription with no
  other API-key source. Added deterministic coverage for every rejected path
  and updated the live, reference, and packaged contracts.
- `python -m pytest tests/test_recurring_autofix.py -q`: 41 passed.
- Full suite with the feature `src/` and declared test dependencies on
  `PYTHONPATH`: 1996 passed in 132.66s.
- `git diff --check`: clean; feature worktree clean after commit.
- QA commit: `947aad11` (`self-qa: harden Claude subscription fallback`).
