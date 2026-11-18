---
title: Preserve supervised environment in megalaunch Windows preflight
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 2 (peer-review)
agent: claude
launch_generation: pending:6d6c53ee-c103-491d-b26b-f743e14f6680
---

## Description

Megalaunch's native-Windows preflight decides whether the agent's command line
is representable using the plain launch environment, not the supervised step
environment the agent actually receives. PR #1233 (merge `93c95405e`, commit
`0bf44d2a1`) introduced this. It moved megalaunch onto the shared
`launch.prepare_agent_launch` readiness operation, which runs
`agent_command_refusal` against `build_launch_env(...)` alone. Megalaunch wraps
the result with `build_supervised_step_env` only afterwards. Before that PR,
`_preflight_agent_launch` built the supervised environment first and planned
against it.

The impact today is not observable. The Windows planner reads the environment
only through `resolve_executable` (PATH/PATHEXT), and the supervised builder
never changes those keys. So the plain and supervised environments produce the
same plan. This is a consistency and drift-proofing fix. The preflight must
vouch for the exact mapping it hands to `spawn_agent_session`, so a future
environment-sensitive check cannot silently diverge. Megalaunch must still
refuse before claim admission or any startup write, and a refusal must still
fail only that ticket.

Done when:

- megalaunch's representability check receives the supervised step
  environment;
- a wiring test proves it. Fake `os.name` / spy on `agent_command_refusal` or
  the Windows planner, assert that the env it receives carries the supervised
  witnesses, and show the test fails on current `main`;
- a separate test covers the refusal path: an unrepresentable command fails
  only that ticket and writes no claim. No such megalaunch test exists today;
- `coga-dev/internals/agent-spawn` states which environment the check uses.

## Context

### Where the code is

- `megalaunch._preflight_agent_launch` calls `launch.prepare_agent_launch(...,
  launch_context="megalaunch")`, then
  `repl_supervisor.build_supervised_step_env(prepared.env, task_path=ref.path,
  step=launch_ticket.step, agent=launch_agent)`. The supervised result is what
  `_PreparedAgentLaunch.env` carries to spawn. The check inside
  `prepare_agent_launch` saw only the plain `prepared.env`.
- `launch.agent_command_refusal(agent, *, env, ref, name, discussion, kickoff)`
  returns None unless `os.name == "nt"`. It plans the pointer form via
  `_plan_windows_agent_command` → `repl_supervisor_nt.plan_agent_command`,
  where `resolve_executable` is the only consumer of the environment.
  `fresh_batch_variable` runs only at spawn (`_prepare_spawn`), not in
  planning.
- The supervised builder sets `COGA_SUPERVISED=1` and the expected
  task/step/agent witnesses, and drops `CHECKOUT_RETURN_ENV`.
- Pre-PR shape: `git show 64dff1e1e:src/coga/megalaunch.py`, then search for
  `_preflight_agent_launch`. It built
  `build_supervised_step_env(build_launch_env(cfg, launch_ticket.secrets), ...)`
  and then called `agent_command_refusal(agent, env=env, ...)`.

### Design constraints

- Keep one shared readiness operation. Do not bring back megalaunch's own copy
  of the CLI/prompt/secrets sequence, because removing it was the point of PR
  #1233. The implementer chooses the approach and records it, with its tradeoff,
  in the PR. Two options:
  - Let `prepare_agent_launch` accept the supervised identity, or an env
    transform, and apply it before the check. This gives one check, but widens
    the shared API.
  - Have megalaunch re-run `agent_command_refusal` on its supervised env. This
    leaves the API unchanged, but plans twice.
- Ordinary launch (`_LaunchInvocation._prepare_agent`) also checks `self.env`
  and spawns with the supervised env plus `CHECKOUT_RETURN_ENV`. That predates
  PR #1233 and is out of scope unless the chosen design fixes both at no extra
  cost. Either way, say so in the PR.
- Resolve secrets once per preparation, and do not cache across the
  publication boundary.
- The sibling tickets for the other deferred PR #1233 findings stay out of
  scope. Finding 9 (dead megalaunch agent lookup) touches the same function, so
  expect a small conflict.
- The `peer-review` step needs a configured peer agent (`other-agent`).

### Tests and verification

Put the tests in `tests/test_megalaunch.py`, next to the existing preflight
tests. Follow `coga-dev/testing` for the Linux receipts. It is cited, not
attached: `docs/contexts/coga-dev/testing/SKILL.md`, "Verification tiers and
receipts". Native Windows verification is owned by the release process.

### Doc to update (cited, not attached)

`docs/contexts/coga-dev/internals/agent-spawn/SKILL.md` has two passages to fix:

- "Launch API and phases": the `prepare_agent_launch` paragraph that says
  "megalaunch adds its supervised identity to the prepared environment";
- "Large prompts": the `agent_command_refusal` caller list.

`coga/megalaunch` has no preflight-environment text and needs no change.

### Provenance

This is finding 2 of the PR #1233 independent review, recorded in
`v1/microkernel/06-read-report-commands-as-ticket-workflows` under "Publication
obligations — 2026-11-16". The owner deferred it to this ticket on 2026-11-16.

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
          checkout: create-or-reuse        # Entry checkout: control, create-or-reuse, reuse-required, manual.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: v1/microkernel/preserve-supervised-environment-in-megalaunch-wind

## Implement handoff (2026-11-17, claude)

Design chosen: option 1. `launch.prepare_agent_launch` gains a keyword-only
`env_transform`. It is applied to `build_launch_env(...)` before
`agent_command_refusal`, and `PreparedAgentLaunch.env` returns the transformed
mapping. `megalaunch._preflight_agent_launch` passes a lambda that calls
`repl_supervisor.build_supervised_step_env` with task path, step and agent, and
spawns with `prepared.env` directly. The result is one check and one secrets
resolution. Tradeoff: the shared API gains one optional parameter. Megalaunch
keeps no copy of the CLI/prompt/secrets sequence.

Ordinary launch (`_LaunchInvocation._prepare_agent`) is unchanged. Its spawn
step and `CHECKOUT_RETURN_ENV` are only settled after checkout preparation, so
fixing it would not be free. The agent-spawn doc says this. The PR must say it
too.

Tests (`tests/test_megalaunch.py`):
- `test_megalaunch_command_check_sees_supervised_step_env` spies on
  `coga.launch.agent_command_refusal` and asserts `COGA_SUPERVISED` and the
  task/step/agent witnesses, the absence of an inherited `CHECKOUT_RETURN_ENV`,
  and that the checked env equals the spawned env. On pre-fix code it fails at
  `env["COGA_SUPERVISED"]` (verified by stashing `src/`).
- `test_megalaunch_command_refusal_fails_only_that_ticket` covers a refused
  ticket: failed row, `launched` False, unchanged bytes, no
  `launch_generation`, no launch log line. The healthy ticket still launches.

Doc: `docs/contexts/coga-dev/internals/agent-spawn/SKILL.md`, in "Launch API
and phases" and in "Large prompts" (the caller list).

Rebase: main had moved (#1242 added the `defer_prompt` parameter to
`prepare_agent_launch`). I resolved the launch.py signature conflict and the
agent-spawn doc paragraph by keeping both changes. Finding 9 (the sibling
ticket) is still not merged, so a small conflict can be expected there.

Native Windows verification is deferred to release, per coga-dev/testing.
`coga validate` was not run because validation behavior did not change.

Next: peer review by other-agent on the pushed branch.

## PR

```yaml
title: Plan megalaunch's Windows command check against the supervised step env
author: claude
author_evidence: >-
  Implement session ran as Claude Code (claude-opus-5-5) under megalaunch,
  launch f960b016-5946-4ae1-9002-358934ae6d80.
head: e4583951f4ccdf34a5fe0b857fa05c4e3c8aab17
base: 7f24c3fe3017a3b01d6282b53d0faac90d2cfb80
depth: skim
rationale: >-
  Small, bounded wiring change with no observable behavior change today. The
  Windows planner reads only PATH/PATHEXT, which the supervised builder leaves
  alone. Read the description for the API tradeoff and the ordinary-launch
  scope note.
implementation: >-
  prepare_agent_launch takes an optional env_transform, applied after
  build_launch_env and before agent_command_refusal. The returned env is the
  transformed one. Megalaunch passes build_supervised_step_env through it, so
  the representability check vouches for the exact mapping handed to
  spawn_agent_session. Secrets are resolved once, and nothing is cached across
  publication.
deviations: >-
  None. This is the first option the ticket allowed: one check, at the cost of
  one more optional parameter on the shared API.
limitations: >-
  Ordinary launch still checks the plain launch env. Its spawn step and
  checkout-return witness are settled after checkout preparation, so it is out
  of scope, as the ticket allows. Native Windows verification is deferred to
  the release process.
files:
  src/coga/launch.py: >-
    Add env_transform to prepare_agent_launch and apply it before the command
    check.
  src/coga/megalaunch.py: >-
    Pass the supervised step env builder through preparation and spawn with
    prepared.env.
  tests/test_megalaunch.py: >-
    Wiring test (the check sees the supervised witnesses and equals the spawn
    env) and refusal-path test (fails only that ticket, writes no claim).
  docs/contexts/coga-dev/internals/agent-spawn/SKILL.md: >-
    State which environment each caller's representability check uses.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: >-
    Independent review is the next workflow step (peer-review by
    other-agent). It has not run yet.
checks:
  - command: PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q -p no:cacheprovider
    status: passed
    head: e4583951f4ccdf34a5fe0b857fa05c4e3c8aab17
    base: 7f24c3fe3017a3b01d6282b53d0faac90d2cfb80
    detail: >-
      4985 passed, 33 skipped in 792s; Pop!_OS 24.04 LTS, Python 3.12.12, on
      the committed, clean tree. Python 3.11 floor not exercised (3.12 only).
  - command: >-
      git stash push src/ && .venv/bin/python -m pytest tests/test_megalaunch.py
      -k "command_check_sees or command_refusal_fails"
    status: passed
    head: 89d0a51cd50aaaf5b18209925d582f83a11beb9a
    base: 87539213998ea0c298318ee9d2bd866447f16de1
    detail: >-
      Pre-rebase negative control. With the src fix removed, the wiring test
      failed at env["COGA_SUPERVISED"] and the refusal test passed, as
      expected.
  - command: python -m pytest on native Windows/macOS
    status: not-run
    detail: Native checks are release-only per coga-dev/testing.
```
