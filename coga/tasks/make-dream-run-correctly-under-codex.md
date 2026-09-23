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
step: 3 (review-design)
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
- The real-run verification is an **owner-launched W40 Dream run under
  codex** after merge.

### Acceptance criteria

- [ ] The Dream template (`coga/recurring/dream/ticket.md` and its packaged
      twin, byte-identical) has an **agent capability preflight** that runs
      before Phase 1. It checks three things from Dream's checkout:
      - the Git common dir is writable;
      - `git ls-remote <configured-remote> <configured-control-branch>`
        succeeds;
      - `gh auth status` succeeds.

      On any failure it names the missing capability and points at the
      `coga/codebase` sandbox recipe. It then escalates per Session conduct:
      attended, it asks the human; unattended, it runs `coga block` with that
      reason. It does not start Phase 1. A claude run passes it unchanged.
- [ ] Dream's delegation wording is agent-neutral and covers the codex
      constraints:
      - every delegated subagent (scan shards and the Retro worker) starts
        with a fresh context and a self-contained delegation message (codex:
        `fork_turns: "none"`);
      - shards run in waves no larger than the agent's concurrent-subagent
        limit (codex: 3), and each wave reaches its barrier before the next
        launches;
      - "returned" at the barrier means that subagent's final answer has been
        delivered.
- [ ] `retro/done-ticket` `## Isolation boundary`, item 2, says explicitly
      that a codex child takes no cwd and starts in the caller's cwd. The
      delegation message names the absolute checkout path, and every shell
      command sets it as its working directory. Item 3 says the
      independent-clone fallback only works around a read-only `.git`; fetch,
      push, and PR creation still need network, which the Dream preflight
      establishes.
- [ ] `coga/codebase` `## Sandbox and cross-machine dev loop` (live and
      packaged twin) owns the codex grant recipe: the exact
      `.codex/config.toml` keys (`sandbox_mode = "workspace-write"`,
      `[sandbox_workspace_write] network_access = true`,
      `writable_roots = ["<abs repo>/.git"]`). It also states that the file
      is gitignored and machine-local, that it needs a trusted project, and
      that it covers every codex session in the repo. `coga/architecture`'s
      Dream scan paragraph (live and twin) gains one sentence on fresh-context
      waves and the preflight, and links to the recipe instead of restating
      it.
- [ ] `src/coga/usage.py`: `_parse_codex_session` ignores rollouts whose
      `session_meta.payload` marks a subagent: `thread_source == "subagent"`,
      or a non-empty `parent_thread_id`. A parent rollout plus N child
      rollouts sharing one cwd resolves to the parent's usage. Two genuine
      top-level rollouts on one cwd stay `unknown`, as today.
- [ ] Tests:
      - `tests/test_usage.py` gains a parent-plus-subagent-rollouts case, and
        `test_parse_codex_rollout_ambiguous_cwd_matches_are_unknown` still
        passes;
      - `tests/test_dream_worker_templates.py` asserts the preflight, the
        fresh-context and wave wording, and the Retro codex-cwd sentence;
      - `tests/test_packaging.py` twin checks pass;
      - `python -m pytest` passes (modulo failures reproduced on `main`,
        listed on the blackboard) and `coga validate --json` is clean.
- [ ] **Real run (review gate, owner-launched).** After merge, the owner
      applies the `.codex/config.toml` recipe and launches W40 with
      `--agent codex`, attended. The run completes all six phases and routes
      findings to PRs, draft tickets, and markers. Its run summary, its usage
      record (`usage_status: ok`), and any new gaps are recorded on this
      ticket's blackboard, next to the W39 claude baseline, before the ticket
      closes. A new gap gets a fix or a filed ticket; it is never left only on
      the blackboard.

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
   - `coga/contexts/coga/codebase/SKILL.md`: add the recipe as a bullet in the
     sandbox section.
   - `coga/contexts/coga/architecture/SKILL.md`: add one sentence to the
     Dream scan paragraph.
   - Mirror both into `src/coga/resources/templates/coga/bootstrap/contexts/coga/`.
5. **Template tests:** add them in `tests/test_dream_worker_templates.py`.
6. **Verify:** run `python -m pytest` and `coga validate --json`. Optionally
   repeat the `codex sandbox -c ...` capability probe (blackboard) with the
   documented keys, to prove the recipe text is exact. Record commands and
   results on the blackboard.

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
- Running Dream from inside the implement agent. `coga launch` from inside a
  launch is forbidden, and the real run makes real PRs and deletes.

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
- **Existing sandbox knowledge:** `coga/contexts/coga/codebase/SKILL.md`
  `## Sandbox and cross-machine dev loop` already lists the codex
  read-only-`.git` wall and the independent-clone fallback. The grant recipe
  extends that section. `.codex` and `.codex/skills/coga` are already in
  `.gitignore`.
- **Prior art:** done ticket `dream-phases-2-3-cannot-complete-scan-subagents-re`
  (PR #703) introduced the sharded, disk-delivered scan protocol. It is why
  codex's final-message delivery does not matter for Phases 2–3.
- **Baseline:** W39 Dream under claude, 2026-09-21: validate-drift 50 issues
  (3 class drafts), 4 knowledge PRs + 7 deletes, 6 stale/drift PRs, 12
  drafts, ~1 h, 94 agent turns.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

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
- verification = owner-launched W40 codex run at the review gate.

One implement-time check: confirm the pre-existing `main` test failures (if
any) before attributing a red suite to this change.
