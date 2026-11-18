---
title: Remove dead megalaunch agent lookup
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
step: 1 (implement)
agent: claude
launch_generation: pending:e3689fa4-044e-48e2-ba38-c66d00af51ea
---

## Description

The peer review of PR #1233 (merge `93c95405e`), finding 9, found an agent
lookup in megalaunch's preflight whose result is never used:
`megalaunch._preflight_agent_launch` opens with
`agent = cfg.agent_type(launch_agent or "")` and returns the `ConfigError`
text on failure, but nothing reads `agent` afterwards. The authoritative
lookup happens later, inside `launch.prepare_agent_launch`, which calls
`cfg.agent_type(launch_agent)` again and turns a `ConfigError` into
`AgentPreparationError`. `_preflight_agent_launch` already returns that error
as its refusal string. The owner deferred this finding from the report
extraction PR on 2026-11-16 (source:
`v1/microkernel/06-read-report-commands-as-ticket-workflows`, "Publication
obligations").

First confirm that the early lookup has no required validation or diagnostic
effect. Then remove it, so that `prepare_agent_launch` is the only place
megalaunch preflight resolves the agent.

Also narrow `_preflight_agent_launch`'s `launch_agent` parameter from
`str | None` to `str` and drop both `launch_agent or ""` fallbacks. The only
call site passes `agent_override or operator.name`, which is always a `str`.

Done when:
- The early `cfg.agent_type` call, with its `try`/`except`, is gone from
  `_preflight_agent_launch`.
- `launch_agent` is typed `str`.
- A new test calls `_preflight_agent_launch` directly with an unconfigured
  agent name. It asserts that the returned string is the `ConfigError` text
  and that no ticket or log bytes changed.
- `python -m pytest` passes.

## Context

### What to verify before deleting

An independent review (2026-11-17) already confirmed the points below.
Re-check them against current source; don't assume they still hold.

- **The lookup is dead, and the real one comes first.** `cfg.agent_type` is
  still the first fallible call inside `prepare_agent_launch`, before the CLI
  `which` check, prompt composition and secret resolution. That keeps an
  unknown agent's refusal text identical to today's.
- **No side effects sit between the two lookups.** The code in between only
  calls `ticket.render()`, makes an in-memory `Ticket` copy and generates a
  `uuid4()`. Activation and `mark_in_progress` run only after preflight
  returns.
- **The bad-agent path can't be reached through `megalaunch()`.** `--agent`
  is validated when megalaunch starts, `bump.resolve_main_agent` rejects
  unconfigured names, and config loading rejects a peer that isn't
  configured. So moving the agent refusal after the status and
  launch-generation refusals has no practical effect. Say so in the PR. It
  is also why the test has to call `_preflight_agent_launch` directly. No
  existing test pins this refusal: the authoring-path agent test in
  `tests/test_megalaunch.py` covers a different path.
- Keep the separate `cfg.agent_type(agent_override)` validation near the top
  of megalaunch's entry function. It validates `--agent` up front for the
  whole run, which is a different job, and it is out of scope.

### Docs

`docs/contexts/coga-dev/internals/launch-claims/SKILL.md` (cited, not
attached) describes `_preflight_agent_launch` as materializing "the exact
prompt, secret environment … and agent that spawn will use". That is still
true after the change. Update it only if you change the documented refusal
order.

### Related

The sibling ticket `preserve-supervised-environment-in-megalaunch-wind`
(finding 2) edits the same function's Windows preflight. Reconcile with
`main` before publishing, in case it landed first.

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
