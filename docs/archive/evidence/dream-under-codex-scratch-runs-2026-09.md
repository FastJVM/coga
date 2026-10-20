# Dream under codex: scratch run/fix loop — 2026-09-22 to 2026-09-24

> **Evidence, archived 2026-10-20.** Copied without rewording from the
> blackboard and body of the done ticket `make-dream-run-correctly-under-codex`
> (PR [#891](https://github.com/FastJVM/coga/pull/891)) when Retro deleted that
> ticket. It is the comparison source for the real-repo confirmation ticket
> `verify-dream-under-codex-on-the-real-repo-w40`. Point-in-time and
> machine-specific: codex-cli 0.155.1–0.156.1, the private scratch repo
> `FastJVM/coga-dream-scratch`, and the clone at
> `/home/n/Code/codex/coga-dream-scratch`. The current procedure lives in
> `coga/recurring/dream/ticket.md` and the `coga/testing` codex sandbox grant
> recipe. Not instructions.

## Clean-run conditions (from the ticket body, `### Run/fix loop`)

**A run is clean** when all of these hold:
- the pane shows the preflight line and every phase's console completion
  line;
- no parent or child rollout contains a sandbox or network denial;
- every PR the run reports exists on `FastJVM/coga-dream-scratch`;
- the Dream task ends `done`;
- the run record shows `usage_status: ok`.

Record the numbers next to the W39 baseline. That comparison is for the
record, not a pass/fail gate. A single clean run ends the loop. Then kill
the tmux session; the clone and the scratch repo stay until the PR merges.

## Findings (design step, 2026-09-22)

Probed codex-cli 0.155.1 (`gpt-6-astra`) directly; scratch probes only, no repo writes.

**Subagents work; the sharded-disk protocol carries over.** `multi_agent` is
stable+enabled. Tools: `spawn_agent(task_name, message, fork_turns?, model?,
reasoning_effort?)`, `wait_agent(timeout_ms)`, `send_message`, `followup_task`,
`interrupt_agent`, `list_agents`. Probe: 6 children in two waves of 3, each
appending a completion line to a shared file — all 6 lines landed, every
FINAL_ANSWER arrived, finished children freed their slots. Constraints Dream's
wording does not account for:
- `fork_turns` defaults to `"all"`: a child inherits the parent's whole
  history unless told `"none"`. A shard forked from mid-run Dream starts with
  Dream's context already spent — defeats the 150 KB shard budget.
- 4 slots including the parent => at most 3 concurrent children. Shards must
  run in waves.
- No cwd / worktree parameter; children share the parent's cwd and sandbox.
  Retro's "tell the subagent its exact cwd" is the only path (skill already
  says so; its `show-toplevel != caller root` proof fails safe).
- No close tool; not needed (slots free on finish).
- Codex's own system prompt forbids spawning unless instructions explicitly
  ask — Dream's "Delegate each shard to a subagent" is explicit enough.

**The real blocker is the sandbox, not subagents.** `coga launch` spawns plain
`codex <prompt>`; in a trusted project that is `workspace-write`. Via
`codex sandbox -c sandbox_mode="workspace-write"` in this repo: mktemp + repo
writes OK; `.git` write FAILS (Read-only file system), `git worktree add`
FAILS, `git ls-remote` / `gh api` / DNS FAIL. The only prior codex Dream run
(2026-07-15, log.md ~L1384) hit exactly this: RO `.git` sync failures and a
Slack DNS failure. Codex sessions still hit RO `.git` today (log.md 2026-09-19,
2026-09-22). Consequence: decide half (Phases 2-3) works; Phase 1 recipe works
but its sync fails; Phase 4 Retro (fetch, worktree/clone, push, gh pr create,
`coga delete` remote landing), Phase 6 proposal PRs, `coga create` sync,
`coga slack`, `coga mark done` sync all fail or need per-command escalation.
The independent-clone fallback fixes RO `.git` only, not network.

**Narrow grant works without bypass.** `network_access=true` + the repo's
`.git` in `sandbox_workspace_write.writable_roots` => `.git` write, git network,
`gh` all OK. Codex honors a project-local `.codex/config.toml` for a trusted
project (verified: model reported workspace-write, network on, `.git` writable
root). `.codex` is already gitignored here (machine-local, like the absolute
path it needs).

**Run record: usage goes `unknown` for any codex run that spawns children.**
Each codex child writes its own `~/.codex/sessions/**/rollout-*.jsonl` with
the parent's `cwd` and `session_meta.payload.thread_source: "subagent"` /
`parent_thread_id`. `usage._parse_codex_session` matches rollouts by cwd and
returns `_unknown("multiple codex rollouts matched cwd")` on >1 candidate — so
every codex Dream run loses its usage record. No `name_flag` just leaves the
codex session unnamed in its picker; no other run-record effect.

**Baseline for comparison:** W39 claude run (2026-09-21, ~1 h): validate-drift
50 issues / 3 class drafts, 4 knowledge PRs + 7 deletes, 6 stale/drift PRs,
12 drafts.

## Run/fix loop

Setup:
- Clone: `/home/n/Code/codex/coga-dream-scratch`, only remote `origin` =
  `https://github.com/FastJVM/coga-dream-scratch.git`; venv `.venv` (editable).
- `coga/coga.local.toml`: `user = "nicktoper"` + `[notification.slack]
  enabled = false`.
- `.codex/config.toml`: grant recipe with the clone's `.git`.
- `~/.codex/config.toml`: added `[projects."/home/n/Code/codex/coga-dream-scratch"]
  trust_level = "trusted"` (backup in the session scratchpad).
- Reset script: `scratch_reset.sh` (session scratchpad) — clears worktrees,
  branches, scratch PRs/remote branches, resets to the branch, deletes
  `coga/tasks/recurring/dream/` and the `created recurring/dream for <period>`
  log line, confirms via `recurring.serviced_periods`, force-pushes.

Codex 0.156.1 re-check (`codex exec` probe in the clone, grant active):
- sandbox banner: `workspace-write [workdir, /tmp, $TMPDIR, <clone>/.git]
  (network access enabled)`; `.git` probe, `ls-remote`, `gh auth status`,
  `git worktree add` under `mktemp -d` all OK.
- 4 `spawn_agent(fork_turns:"none")` calls all returned without a limit error,
  but rollout timestamps show max 3 concurrent (4th started after the 1st
  ended): the cap now queues instead of erroring. Wave wording still correct.
- Child session_meta still has `thread_source:"subagent"` +
  `parent_thread_id`.
- Gotcha: `codex exec` with a piped/non-TTY stdin waits for stdin EOF; use
  `</dev/null`.

## Iteration 1 (branch head 83a00b9aa + scratch reset 81b90f5f7), started 2026-09-24T20:19Z

- Launched in tmux `dream` in the clone via `coga dream --agent codex`
  (venv coga, no `COGA_*`). Parent rollout
  `rollout-2026-09-24T13-19-08-01a0d512-...jsonl`.
- Preflight ran first and passed (git-common-dir probe, `ls-remote origin
  main`, `gh auth status`); reported in prose rather than the example
  `preflight: ...` line.
- validate-drift: 45 issues (0 direct, 2 pr-proposal, 43 human-needed).
- Knowledge scan: 380 files, 30 shards; spawns use `fork_turns:"none"`, first
  wave of 3, then `wait_agent`.
- **Harness finding (not a Dream bug):** codex runs commands with
  `bash -lc`; `~/.profile` prepends `~/.local/bin`, so Dream's `coga` inside
  codex resolves to the global uv tool (editable `/home/n/Code/coga`, branch
  `split-ticket-contract`), not the clone venv. The supervising `coga launch`
  (which records usage) is the venv. Fix for iteration 2+: add
  `allow_login_shell = false` to the clone's `.codex/config.toml` (clone-local
  harness setting; not part of the published recipe).

**Iteration 1 result (ended 2026-09-24T21:59Z, ~1h41m, `done`): all five
clean-run conditions hold, but not counted as clean** — Dream's own `coga`
calls ran the global uv tool (`/home/n/Code/coga`, branch
`split-ticket-contract`), violating the loop's "branch code on PATH" setup.
- Phase results: preflight pass; validate-drift 45 issues; knowledge scan 30
  shards (22 first-attempt, 8 retries, all complete), 60 findings total with
  the audit; contract audit 20 shards, no retries; Retro 7 eligible → PR #1 +
  6 direct deletes, verified on `origin/main`, checkout at
  `/tmp/dream-retro-<rand>/checkout` (the `<run-dir>/checkout` root works
  under the grant); cleanup-orphan-markers none; disposition 8 more PRs + 5
  drafts; 101 retirement debt; Slack suppressed locally; `coga mark done`.
- 9 PRs on scratch (#1–#9), all exist. No sandbox/network denial in the parent
  or any of the ~68 child rollouts (all denial-string hits were corpus text
  quoting old failures); no escalation requests.
- Run record: `usage_status: ok`, session = parent id, 77 agent turns,
  input 557,899 / output 58,562 / cache-read 27,693,312, 6040 s. The usage
  fix works on a real run (without it: `multiple codex rollouts matched cwd`).
- Consequence of the harness flaw: global coga froze `code/with-review` with
  a `code/split-ticket` skill absent here → `broken-skill`; Dream noticed,
  deleted and re-created the four code drafts with `PYTHONPATH=src`.
- **Fix:** `allow_login_shell = false` (top-level) in the clone's
  `.codex/config.toml`; verified `command -v coga` → clone venv. Documented the
  gotcha in `coga/testing` "Which code you are actually testing" (commit
  on branch). No Dream/template defect found.
- Observation (not a gate): 8/30 knowledge shards returned `incomplete` on
  the first attempt (budget exhausted by comparison reads); the retry path
  handled all of them.
- **Adjacent finding, not fixed here:** with `coga dream --agent codex`, the
  audit actor and Slack label say `agent:claude` / "claude on" (log lines
  for `slack`, `task done`). `commands/common.py::completion_identity` and
  `commands/slack.py` resolve the operator via `resolve_operator` from the
  ticket/default agent; the launch-time `--agent` override is not persisted,
  so they fall back to the configured default (claude). The launch line
  itself records `launch_agent=codex, agent=codex`. Existing follow-up: none
  found yet.

## Iteration 2 — CLEAN (branch head 096e35b4b + scratch reset 4b7a3ceb0), 2026-09-24T22:03Z–23:34Z

Harness: clone `.codex/config.toml` + `allow_login_shell = false`; Dream's
`coga` calls confirmed on the clone venv (parent rollout
`rollout-2026-09-24T15-03-58-01a0d572-...jsonl`).

Clean-run conditions:
- Preflight line + every phase result (summary table and console): pass.
- No sandbox/network denial or escalation request in the parent or any child
  rollout (every denial-string hit is corpus text quoting old failures).
- 7 reported PRs all exist on `FastJVM/coga-dream-scratch` (#10–#16).
- Dream task `done`; run record `usage_status: ok`, session = parent id.
- Retro linked checkout at `/tmp/dream-retro-<rand>/checkout` again →
  root confirmed; now named in the Retro skill (commit "Name Retro's verified
  linked-checkout root").

Numbers vs W39 claude baseline (record only, not a gate):

| | W39 claude (2026-09-21) | codex run 2 (2026-09-24) |
|---|---|---|
| wall time | ~1 h (3609 s) | ~1 h 31 m (5449 s) |
| agent turns | 94 | 78 |
| validate-drift | 50 issues, 3 class drafts | 45 issues (2 proposals, 43 human-needed), classes already owned |
| knowledge scan | complete | **partial**: 57 shards launched (37 + 20 retries), 42/45 final leaves |
| contract audit | — | 11/11 shards, 13 findings (8 new) |
| Retro | 4 knowledge PRs + 7 deletes | 1 knowledge PR + 5 direct deletes (6 eligible) |
| proposal PRs | 6 stale/drift | 6 (incl. 1 Phase-1 history compaction) |
| drafts | 12 | 2 (29 findings already ticketed) |
| tokens | in 824 / out 409,502 / cache-read 82.9 M | in 717,280 / out 62,220 / cache-read 34.7 M |

Knowledge scan `partial` (for owner judgment): 3 attempt-2 leaves
(k26r1a, k27r1a, k30r1a) read every owned file but their owner-search
output (rg/owner-description dumps of 55–95 KB) blew the 150 KB allowance;
Dream reported `partial`, kept `/tmp/dream-knowledge-ogovzjt2`, and filed a
human-needed line — the protocol working as specified, not a codex
capability failure. Run 1 had the same pressure (8/30 first-attempt
retries) but all retries completed. Possible follow-up: bound owner-search
output in the scan protocol. Not changed here (scan budget is out of this
ticket's scope).

Also seen again: `[agent:claude]` on the `slack` and `task done` log lines and
`[human:nicktoper]` on agent-run `coga create` lines — the adjacent actor
attribution finding from iteration 1.

## Checkpoint / handoff (2026-09-24)

- Loop ended after 2 runs (1 clean). tmux session killed. Clone
  `/home/n/Code/codex/coga-dream-scratch` and scratch PRs #10–#16 kept until
  merge, per ticket. `~/.codex/config.toml` trust entry for the clone remains.
- Branch `dream-under-codex` rebased onto origin/main `b95983e4d`; commits:
  `dc8810521` (implementation), `c1b8fbbac` (codex login-shell PATH note in
  `coga/testing`), `7ea57bfbd` (Retro root named in the Retro skill).
- `python -m pytest` after rebase: 2940 passed, 1 failed —
  `test_packaging.py::test_live_and_packaged_copies_stay_identical` on
  `coga/recurring/phone-home/ticket.md` vs packaged twin. **Reproduced on
  main** (`b95983e4d` itself has differing bytes); this branch does not touch
  those files. Both Dream runs also reported this drift.
- `coga validate --json` after rebase: exit 1, 49 issues, 1 error (the
  pre-existing `unsynthesized-draft-blackboard` on
  `v2/autotrigger-ticket-type`); none attributable to this branch.
- Not pushed, no PR (open-pr step).
