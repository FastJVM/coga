---
title: make dream run correctly under codex
status: in_progress
owner: nicktoper
contexts:
- dev/code
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 5 (open-pr)
agent: claude
---

## Description

Selecting `codex` for Dream is a config/flag matter (`coga dream --agent codex`
and `coga recurring --agent codex` already exist; a repo-wide default key is
ticket `dream-should-be-able-to-use-codex-instead-of-claud`). Whether Dream
then *works* under codex had never been established. The design step probed
codex-cli 0.155.1 directly. The evidence is on the blackboard under
`## Findings`. It found three gaps, one of them fatal:

1. **Sandbox (fatal for the execute half).** `coga launch` spawns plain
   `codex <prompt>`. In a trusted project that runs `workspace-write`, where
   `.git` is read-only and network is off. Phases 2–3 (reads and `mktemp`)
   work. Retro, proposal PRs, `coga delete`'s remote landing, `coga create`
   / `mark done` sync, and `coga slack` fail. The only prior codex Dream run
   (2026-07-15) failed exactly this way. A narrow grant (network on, plus the
   repo's `.git` as a writable root) fixes it without bypassing the sandbox.
   Codex reads that grant from a gitignored project `.codex/config.toml`.
2. **Delegation mechanics (degrading).** Codex subagents work: a 6-shard,
   2-wave probe landed every completion line on disk. But a child inherits
   the parent's whole conversation unless spawned with `fork_turns: "none"`,
   at most 3 children run at once, and a child cannot be given a cwd. Dream's
   wording assumes fresh-context children, unlimited fan-out, and (for Retro)
   a native `isolation: worktree`.
3. **Run record (silent loss).** Every codex child writes its own rollout
   with the parent's cwd. `usage._parse_codex_session` then sees more than
   one candidate and records the whole Dream run's usage as `unknown`.

Owner decisions (2026-09-22, design step):

- The grant is **documented machine-local config**, not new Coga launch
  machinery. It applies to every codex session in the repo, which is
  accepted.
- The usage fix is **in scope**.
- **Verification is a real run/fix loop** (owner, 2026-09-24): the implement
  step runs Dream under codex for real, in a loop, until it works (see
  `### Run/fix loop`). The loop runs against a disposable clone that pushes to
  the private scratch repo `FastJVM/coga-dream-scratch`. The run on the real
  repo is a separate confirmation ticket for the first Dream period after
  merge, `verify-dream-under-codex-on-the-real-repo-w40`, launched by the
  owner. That split also keeps autoclose from closing this ticket before a
  real run.
- **Nested-launch exception (owner grant, 2026-09-24).** The base prompt
  forbids `coga launch` from inside a launch. For this ticket's implement
  step only, the owner waives that rule, **scoped to the scratch clone**:
  the implement agent may run exactly `coga dream --agent codex` there, with
  the clone's own `coga` and config. No other launch, no bare
  `coga recurring`, and nothing against this checkout or `FastJVM/coga`.

### Acceptance criteria

- [x] The Dream template (`coga/recurring/dream/ticket.md` and its packaged
      twin, byte-identical) has an **agent capability preflight** that runs
      before Phase 1. It checks three things from Dream's checkout:
      - the Git common dir is writable;
      - `git ls-remote <configured-remote> <configured-control-branch>`
        succeeds;
      - `gh auth status` succeeds.

      On any failure it names the missing capability and points at the
      `coga/testing` sandbox recipe. It then escalates per Session conduct:
      attended, it asks the human; unattended, it runs `coga block` with that
      reason. It does not start Phase 1. A claude run passes it unchanged.
- [x] Dream's delegation wording is agent-neutral and covers the codex
      constraints:
      - every delegated subagent (scan shards and the Retro worker) starts
        with a fresh context and a self-contained delegation message (codex:
        `fork_turns: "none"`);
      - shards run in waves no larger than the agent's concurrent-subagent
        limit (codex: 3), and each wave reaches its barrier before the next
        launches;
      - "returned" at the barrier means that subagent's final answer has been
        delivered.
- [x] `retro/done-ticket` `## Isolation boundary`, item 2, says explicitly
      that a codex child takes no cwd and starts in the caller's cwd. The
      delegation message names the absolute checkout path, and every shell
      command sets it as its working directory. Item 3 says the
      independent-clone fallback only works around a read-only `.git`; fetch,
      push, and PR creation still need network, which the Dream preflight
      establishes.
- [x] `coga/testing` `## Restricted sandboxes` (live and
      packaged twin) owns the codex grant recipe: the exact
      `.codex/config.toml` keys (`sandbox_mode = "workspace-write"`,
      `[sandbox_workspace_write] network_access = true`,
      `writable_roots = ["<abs repo>/.git"]`). It also states that the file
      is gitignored and machine-local, that it needs a trusted project, and
      that it covers every codex session in the repo. `coga/architecture`'s
      Dream scan paragraph (live and twin) gains one sentence on fresh-context
      waves and the preflight, and links to the recipe instead of restating
      it.
- [x] `src/coga/usage.py`: `_parse_codex_session` ignores rollouts whose
      `session_meta.payload` marks a subagent: `thread_source == "subagent"`,
      or a non-empty `parent_thread_id`. A parent rollout plus N child
      rollouts sharing one cwd resolves to the parent's usage. Two genuine
      top-level rollouts on one cwd stay `unknown`, as today.
- [x] Tests:
      - `tests/test_usage.py` gains a parent-plus-subagent-rollouts case, and
        `test_parse_codex_rollout_ambiguous_cwd_matches_are_unknown` still
        passes;
      - `tests/test_dream_worker_templates.py` asserts the preflight, the
        fresh-context and wave wording, and the Retro codex-cwd sentence;
      - `tests/test_packaging.py` twin checks pass;
      - `python -m pytest` passes (modulo failures reproduced on `main`,
        listed on the blackboard);
      - `coga validate --json` adds no error attributable to this branch.
        `main` already exits 1 (2026-09-22: two
        `unsynthesized-draft-blackboard` errors, on
        `clean-up-all-the-working-trees` and `v2/autotrigger-ticket-type`, plus
        50 warnings). Record the observed baseline, and do not repair
        unrelated drafts to clear it.
- [x] **A clean codex Dream run in the scratch clone (run/fix loop).**
      Starting from the branch head, a Dream run launched under codex through
      the real `coga launch` path meets every condition under
      `**A run is clean**` in `### Run/fix loop`. The only human-style input
      it gets is answers to Dream's own attended prompts. Each iteration's
      failures, root causes, and fixes are logged on the blackboard, and the
      clean run's numbers are recorded next to the W39 claude baseline. Every
      fix lands on this branch; the one change allowed only in the clone is
      the scratch reset commit.
- [x] The Retro linked checkout is created under a root that is already
      writable under the grant, and the Retro step checks for write access
      there before delegating. That root is chosen during the loop, from
      what the runs show (evaluator P1), and recorded in the Retro skill and
      the testing topic’s sandbox recipe.

### Proposed shape

1. **`src/coga/usage.py`**
   - `_read_codex_session_meta()` also returns `thread_source` and
     `parent_thread_id` from the payload.
   - `_parse_codex_session()` `continue`s past a subagent rollout before the
     cwd check.
   - Add the matching test in `tests/test_usage.py`, built on the existing
     `_write` / `_window` helpers.
2. **Dream template** (`coga/recurring/dream/ticket.md`, then copy it
   byte-for-byte to `src/coga/resources/templates/coga/recurring/dream/ticket.md`):
   - Add `### Agent capability preflight` before `### Phase 1 — validate-drift`,
     and add "preflight" to the `### Console Progress` phase list.
   - In `### Decide-half scan mechanics`, step 3 ("Run the shards"), add the
     fresh-context and wave rules.
   - In step 4, define "returned".
   - In `### Phase 4`'s delegation paragraph, add the fresh-context rule, and
     note that on an agent without native isolation the delegation message
     carries the absolute checkout path.
   - Name the agent limits as examples ("codex: …"), never as branches that
     change what Dream does.
3. **`src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md`**:
   the two sentences in `## Isolation boundary`. The `## Isolation`
   one-liners near the top stay consistent.
4. **Contexts:**
   - `docs/contexts/coga/testing/SKILL.md`: add the recipe in
     `## Restricted sandboxes`.
   - `docs/contexts/coga/architecture/SKILL.md`: add one sentence to the
     Dream scan paragraph.
   - Mirror both into `src/coga/resources/templates/coga/bootstrap/contexts/coga/`.
5. **Template tests:** add them in `tests/test_dream_worker_templates.py`.
6. **Verify:** run `python -m pytest` and `coga validate --json`, and record
   the commands and results on the blackboard.
7. **Run/fix loop** (below) until a clean run lands. Then `open-pr`.

### Run/fix loop

The loop runs inside the implement step as one long session. A Coga workflow
can't loop (steps are linear and agents never step back), so the ticket
spells out the procedure instead.

**One-time setup** (record the paths on the blackboard):

1. Clone the repo to a directory outside this checkout, for example
   `~/Code/codex/coga-dream-scratch`. Point `origin` at
   `https://github.com/FastJVM/coga-dream-scratch.git` and remove every other
   remote, so `git` and `gh` can only reach the scratch repo. **Never add a
   scratch remote to this checkout.**
2. Give the clone **its own venv** and run `pip install -e ".[test]"` there.
   The global `coga` is a uv tool install that doesn't run branch code.
3. Write `<clone>/coga/coga.local.toml` (the config root is `coga/`): copy
   this checkout's local file (today it holds only `user = "nicktoper"`,
   which the `owner` gate needs), then add
   `[notification.slack]` `enabled = false`, so test runs never post to the
   real channel. That flag also suppresses `--important` posts.
4. Write `<clone>/.codex/config.toml` from the recipe, with the **clone's**
   absolute `.git` in `writable_roots`. Trust the clone in codex. That adds
   one `[projects."<clone path>"] trust_level` entry to `~/.codex/config.toml`,
   the one edit outside the clone that the loop is allowed to make.
5. Codex is 0.156.1 as of 2026-09-24; the design probed 0.155.1. In the first
   iteration, re-check that `fork_turns` and the 3-child limit still behave
   as recorded in the design findings.

**Each iteration** (cap: 5 full runs):

1. **Reset the scratch repo to the branch.** Run every step from inside the
   clone, whose only remote is the scratch repo:
   - clear the previous run: `tmux kill-session`, then
     `git worktree remove --force` every extra worktree and `git worktree
     prune`, delete every local branch except `main`, close every open PR on
     the scratch repo, and delete every remote branch there except `main`;
   - `git fetch <abs path of this checkout> <branch>` then
     `git reset --hard FETCH_HEAD`;
   - **make the current period launchable.** `main` already holds a
     serviced Dream run for the current ISO week (W39 on 2026-09-24):
     `coga/tasks/recurring/dream/` is `done`, and `coga/log.md` records the
     period in the serviced ledger (`recurring.read_serviced_ledger`). As
     long as both are there, `recurring.create_template` returns the done
     task and `coga dream` launches nothing. In the clone only, delete that
     task directory and remove the log lines that record Dream's current
     period as serviced, then commit that as a "scratch reset" commit.
     Confirm with a check that the ledger no longer reports the period
     (don't guess the log format). This commit never goes to the branch;
   - `git push --force origin HEAD:main`. Force-pushing is fine only for the
     scratch repo, and only from the clone.
2. **Launch.** Start a detached `tmux` session with the clone as cwd. In it:
   - put the clone venv's `bin` first on `PATH`, because Dream's own `coga`
     calls go through `PATH`;
   - `unset` every inherited `COGA_*` variable. `COGA_LOCAL_CONFIG` in
     particular would load this checkout's local config, with Slack on;
   - check with `which coga` and `coga --version`;
   - then run exactly `coga dream --agent codex`.

   Launches are interactive-only (they need a TTY), which is why it runs
   under tmux. Drive the session with `tmux capture-pane` and `send-keys`:
   - answer Dream's attended prompts the way the owner would;
   - answer codex's trust, update, and notice prompts;
   - don't approve anything aimed outside the clone or the scratch repo.
3. **Watch and collect.** Follow:
   - the pane;
   - the clone's `coga/log.md`;
   - the Dream ticket's blackboard;
   - the `.coga/` run records;
   - the parent and child rollouts under `~/.codex/sessions/`.
4. **Log, fix, repeat.** Add an iteration entry to the blackboard: what
   failed, the evidence, the root cause, and the fix. Fix it on the branch
   in this checkout, with a test when the fix is in code. Commit, then go
   back to step 1. Nothing gets patched only in the clone. The one exception
   is the scratch reset commit.

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

**Stop and ask the owner** when any of these happens:
- five runs have failed;
- a fix would need machinery that `### Out of scope` rules out;
- a failure is outside Coga's control, such as a codex bug with no
  workaround.

A run takes about an hour, so the loop may outgrow one session. Before the
context runs out, write a checkpoint to the blackboard: the iteration
number, the branch head, what is still open, and the clone path. The owner
then relaunches the implement step and the loop continues from there.

**Out of bounds for the loop:**
- any write to `FastJVM/coga`. Read-only `gh` calls on its PR URLs are
  fine, because many task files carry them;
- this checkout's `coga/tasks/**` state;
- the real Slack channel;
- codex config outside the clone, except for the one trust entry;
- `coga recurring` without the `launch dream` target, which would fire
  other templates, including `upstream-coga`;
- any `coga launch` other than the exact `coga dream --agent codex` in the
  clone.

### Out of scope

- The repo-wide default-agent key (sibling ticket
  `dream-should-be-able-to-use-codex-instead-of-claud`).
- Any new `coga.toml` launch-args / per-template sandbox machinery. The owner
  chose the documented local config instead.
- Counting subagent tokens in usage, for either agent. Parity is
  parent-session only.
- A `name_flag` / `session_id_flag` for codex.
- REM and the other recurring templates. The preflight and the grant recipe
  obviously benefit any recurring job that pushes or opens PRs under codex:
  note that, don't wire it.
- Rewriting `dev/code`'s independent-clone fallback. The grant also removes
  the read-only `.git` wall for codex code tickets, but that context stays as
  is.
- Running Dream against the real repo. That happens in
  `verify-dream-under-codex-on-the-real-repo-w40`, after merge and launched
  by the owner.
- Turning the run/fix loop into a Coga workflow or skill. If a second ticket
  needs this dogfood loop, propose a skill then.

## Context

- **Dream dispatch contract:** `coga/recurring/dream/ticket.md` plus its
  packaged twin (byte-identity enforced by `tests/test_packaging.py`). Phase
  skills ship packaged-only under
  `src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/`
  (`scan/knowledge-scan`, `scan/contract-audit`, `scan/scan-protocol`,
  `tasks/validate-drift`, `tasks/cleanup-orphan-markers`). Retro is
  `.../bootstrap/skills/retro/done-ticket/SKILL.md`. The scan-protocol's
  barrier wording ("Reconcile at the barrier") needs no change beyond the
  template's definition of "returned".
- **How codex is launched:** `src/coga/commands/launch.py`
  `build_agent_command()` builds `[agent.cli, *name_args, *session_id_args,
  prompt]`. `[agents.codex]` in `coga/coga.toml` has no `name_flag` or
  `session_id_flag`, so there are no extra args, and the sandbox comes
  entirely from codex's own config layers. No `AgentType` field
  (`src/coga/config.py`) carries launch args, and none is to be added.
- **Usage recovery:** `src/coga/commands/launch.py` `spawn_agent_session()`
  passes `session_id=None` for codex (no `session_id_flag`). So
  `src/coga/usage.py` `parse_session("codex", ...)` goes through
  `_parse_codex_session()`, which filters `~/.codex/sessions/**/rollout-*.jsonl`
  by `_read_codex_session_meta()`'s `cwd` and the launch window. A child
  rollout's first line is `session_meta` with `payload.thread_source:
  "subagent"`, `payload.parent_thread_id: <parent id>`, and
  `payload.source.subagent.thread_spawn`. The parent has
  `thread_source: "user"` and no `parent_thread_id`.
- **Codex subagent tools** (0.155.1, `multi_agent` stable/on):
  `spawn_agent(task_name, message, fork_turns?="all", model?,
  reasoning_effort?)`, `wait_agent(timeout_ms)`, `send_message`,
  `followup_task`, `interrupt_agent`, `list_agents`. There are 4 slots
  including the parent, and no cwd parameter or close tool. Children share
  the parent's cwd and sandbox. Codex's system prompt permits spawning only
  when instructions explicitly ask for delegation.
- **Existing sandbox knowledge:** `docs/contexts/coga/testing/SKILL.md`
  `## Restricted sandboxes` describes restricted `.git` writes and links
  to the independent-clone fallback in `dev/checkouts`. The grant recipe
  extends that section. `.codex` and `.codex/skills/coga` are already in
  `.gitignore`.
- **Prior art:** done ticket `dream-phases-2-3-cannot-complete-scan-subagents-re`
  (PR #703) introduced the sharded, disk-delivered scan protocol. It is why
  codex's final-message delivery does not matter for Phases 2–3.
- **Evaluator recommendations to honor** (2026-09-22 review):
  - Keep a wave's **join** separate from the attempt's **reconciliation**.
    Waiting for one wave only frees slots, so manifest rows not launched yet
    are not missing or due for retry. Reconcile the whole attempt once every
    wave has joined (scan-protocol `Reconcile at the barrier`).
  - "Git common dir is writable" means creating and then removing a
    uniquely named probe file in the resolved absolute common dir, not a
    permission-bit check, and not a Git lock name.
  - The template tests assert that the preflight fails before Phase 1 and
    takes the Session-conduct route, not only that the heading exists.
  - Usage tests cover `thread_source` alone and `parent_thread_id` alone
    each excluding a child, and show that a set with only children stays
    unknown.
- **Scratch target:** `FastJVM/coga-dream-scratch` (private, created
  2026-09-24, seeded from `main`). It is disposable, so force-pushes and junk
  PRs there are expected.
- **Baseline:** W39 Dream under claude, 2026-09-21: validate-drift 50 issues
  (3 class drafts), 4 knowledge PRs + 7 deletes, 6 stale/drift PRs, 12
  drafts, ~1 h, 94 agent turns.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: dream-under-codex
worktree: /home/n/Code/codex/coga

Single-checkout layout (primary checkout on the feature branch).

## Implementation (2026-09-24)

Commit `83a00b9aa` on `dream-under-codex`:
- `usage._parse_codex_session` skips rollouts whose session_meta has
  `thread_source == "subagent"` or a non-empty `parent_thread_id`
  (`_read_codex_session_meta` now returns both). Tests: parametrized
  parent + 3 children (each marker alone, and both), child-only set stays
  unknown; existing ambiguous-cwd test unchanged and passing. Confirmed live on
  a real 0.156.1 parent + 4 child rollouts: resolves to parent, `ok`.
- Dream template (live + packaged twin): `### Agent capability preflight`
  before Phase 1; fresh-context + wave rules in scan step 3; "returned" and
  once-per-attempt reconciliation in step 4; retry in waves; Retro delegation
  fresh-context, linked checkout at `<run-dir>/checkout` with a write probe
  before delegating, absolute path in the delegation message.
- Retro `## Isolation boundary` items 2/3 + top summary.
- `coga/testing` `### Codex sandbox grant` (live + twin).
- **Deviation:** the "Dream scan paragraph" no longer lives in
  `coga/architecture` (now overview + topic map); it lives in `coga/dream`,
  so the one-sentence summary went there (live + twin), linking the testing
  recipe. Architecture untouched.
- Retro linked-checkout root: `<run-dir>/checkout` inside the `mktemp -d` run
  dir. Initial choice; confirm in the loop.

Verification:
- `.venv/bin/python -m pytest -q` → 2912 passed (no baseline failures seen).
- `coga validate --json` → exit 1; 1 error (`unsynthesized-draft-blackboard`
  on `v2/autotrigger-ticket-type`, pre-existing) + 45 warnings. Nothing
  attributable to this branch; baseline has shrunk since 2026-09-22.

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

## Superseded designs

### 2026-09-24: verification only after merge, by an owner W40 run

The design step's plan: land the prompt, doc, and usage changes, then check
them with one owner-launched W40 codex Dream run at the `review` gate. The
owner replaced it, because the design findings were probes, not proof that
Dream works end to end. Now the implement step tests in a real run/fix loop
against a scratch clone (`### Run/fix loop`), and the real-repo run moved to
`verify-dream-under-codex-on-the-real-repo-w40`.

The body now resolves the 2026-09-22 evaluator review below:
- P1 Retro root: chosen in the loop, with an acceptance criterion;
- P1 autoclose: resolved by the split;
- P2 validator baseline: "no new attributable errors".

A second cold review of the loop (2026-09-24) raised five issues, all folded
into `### Run/fix loop`: the W39 serviced reset, the clone `PATH` and
`COGA_*` isolation, the codex trust entry, the reset and force-push scope,
and the concrete clean-run checks.

## Evaluator review

### Review-design follow-up — 2026-09-24

The revised body addresses the three original findings: the Retro root is
an explicit run/fix-loop acceptance condition; real-repo verification has
its own existing draft ticket; validation permits only reproduced baseline
errors. The chosen Retro root still needs runtime evidence during implement.

One documentation target has drifted: `coga/codebase` no longer contains
`Sandbox and cross-machine dev loop`. Current sandbox guidance lives in
`docs/contexts/coga/testing/SKILL.md`, `## Restricted sandboxes`, linked to
`dev/checkouts`. Owner approved the correction and advancement to implement
(2026-09-24): put the grant recipe
in that testing section and its packaged twin, and point Dream's preflight
and the architecture summary there. Keep codebase as an overview link;
do not recreate a second sandbox owner. No implementation or runtime tests
were performed. Ticket-body targets now reflect the approved correction;
advancing to implement with `coga bump` is the final action of this step.

2026-09-22 — Cold review of the body against the current repository.
**Verdict: resolve the following before implementation.** The proposed usage
filter and prompt/documentation changes form one coherent PR and respect the
microkernel boundary; no launch machinery is needed. Owner approval remains
the next step.

### Must resolve

1. **P1 — Specify a writable location for the isolated Retro checkout.**
   The recipe grants the primary repo's `.git`, but Phase 4 still says only
   "temporary linked checkout." A sibling checkout outside the primary repo
   and temporary writable roots can fail even after all three preflight checks
   pass. Changing a shell command's cwd does not grant filesystem access.
   Evidence: `coga/recurring/dream/ticket.md`, `Phase 4`, and packaged
   `retro/done-ticket/SKILL.md`, `Isolation boundary`, specify `/tmp` only for
   the independent-clone fallback, not for the preferred linked checkout.
   Codex's workspace-write contract limits writes to granted roots; its
   [configuration reference](https://developers.openai.com/codex/config-reference)
   documents additional writable roots and the options excluding temporary
   roots. Specify an already-writable temporary root for the linked checkout
   too, and require an actual write check there before delegation. This keeps
   the narrow grant and avoids relying on an implementer's choice of path.

2. **P1 — Protect the post-merge W40 verification from autoclose.**
   The frozen workflow ends at `review`; the acceptance criterion requires
   merging and then recording a real run before this ticket closes.
   `src/coga/autoclose.py::_candidate`, `_on_final_step`, and `_try_bump_one`
   close an active/in-progress final-step ticket when its recorded PR is
   merged. They do not inspect unchecked acceptance criteria. The scheduled
   sweep can therefore close this ticket before W40 runs. Specify the owner's
   lifecycle procedure, for example pausing the ticket before merge and
   explicitly resuming/finalizing after verification (paused is excluded by
   `OPEN_STATUSES`), or use a separately tracked verification ticket with a
   corresponding acceptance change. This does not require new core behavior.

3. **P2 — Make the validator criterion baseline-aware.**
   The suite permits reproduced baseline failures, but `coga validate --json`
   is required to be clean without the same allowance. On the untouched
   implementation it exits 1: two `unsynthesized-draft-blackboard` errors on
   `clean-up-all-the-working-trees` and `v2/autotrigger-ticket-type`, plus 50
   warnings. The codebase context's `Sandbox and cross-machine dev loop`
   explicitly prohibits repairing unrelated drafts to clear this gate; its
   older four-error baseline has also drifted. Require no new attributable
   validator errors and record the observed baseline, or name separate work
   that must clear it. Do not expand this PR into draft adjudication.

### Recommendations

- Distinguish each wave's **join** from the whole attempt's **reconciliation**.
  Dream's scan mechanics step 2 creates every manifest row before launching;
  step 4 compares all active leaves to completion IDs. The packaged
  `bootstrap/dream/scan/scan-protocol/SKILL.md`, `Reconcile at the barrier`,
  says to read progress once after the attempt's children return. State that
  waiting for a wave's final answers only frees slots; do not classify the
  later, unlaunched manifest rows as missing/retry candidates. Reconcile the
  complete attempt after every scheduled wave joins.
- Define "Git common dir is writable" as creation and removal of a unique
  temporary probe file in the resolved absolute common dir, not only a
  permission-bit/access check. Keep it separate from Git lock names. Add
  template assertions for failure-before-Phase-1 and the Session-conduct route,
  not merely the presence of a preflight heading.
- Parameterize usage coverage so `thread_source` alone and `parent_thread_id`
  alone each exclude a child, and a child-only set remains unknown. Existing
  top-level fixtures omit both fields, preserving compatibility coverage.

### Verification and limits

- Inspected `usage.py::_read_codex_session_meta`, `_parse_codex_session`,
  launch's `build_agent_command` and session-id selection, Dream and Retro
  templates, scan protocol, relevant contexts, frozen/bundled workflow,
  `test_usage.py`, `test_dream_worker_templates.py`, and packaging's derived
  twin discovery. Named implementation points exist and match the design.
- Official OpenAI configuration reference confirms the named sandbox keys and
  trusted-project requirement. The design author's successful `.git` grant
  and six-child probes were not repeated; they remain recorded design evidence.
  Local `codex --version` reports 0.155.1.
- `coga validate --json`: exit 1, baseline detailed above.
- `python -m pytest tests/test_usage.py tests/test_dream_worker_templates.py -q`:
  collection failed because this shell's Python lacks declared dependency
  `tomlkit`; this is environment setup, not an established test regression.
  No full suite or real Dream run was performed in this review step.
- No ticket-body, configuration, implementation, branch, or PR changes.

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

## Open Questions

None open. The three design decisions were put to the owner in the design
session and resolved on 2026-09-22 (recorded in `## Description`):

- grant = documented local `.codex/config.toml`;
- usage fix in scope;
- verification = the implement-step run/fix loop in the scratch clone
  (revised 2026-09-24; see `## Superseded designs`).

One implement-time check: confirm the pre-existing `main` test failures (if
any) before attributing a red suite to this change.

### Iteration 1 (branch head 83a00b9aa + scratch reset 81b90f5f7), started 2026-09-24T20:19Z

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

### Iteration 2 — CLEAN (branch head 096e35b4b + scratch reset 4b7a3ceb0), 2026-09-24T22:03Z–23:34Z

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

### Checkpoint / handoff (2026-09-24)

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
