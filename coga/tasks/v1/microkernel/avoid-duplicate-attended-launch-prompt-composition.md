---
title: Avoid duplicate attended launch prompt composition
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
---

## Description

Peer review of PR #1233, finding 10, observed that an attended agent launch
composes its prompt twice: once as a throwaway pre-flight before any
lifecycle write, and again for the spawn. Identify both paths and make one
composition authoritative, so a normal attended launch composes the prompt
only once. Keep four properties intact. **Freshness**: the spawned prompt still
reflects the ticket and checkout notice the agent actually starts on.
**Diagnostics**: a missing context or skill layer, or a vanished layer file,
still refuses before activation, the `in_progress` flip, or any started
notification. **Resource provenance**: the layers and refs that compose stay
the same. **Launch admission**: the refusal order in `coga/launch`
"Agent preflight order" does not change.

The owner explicitly deferred this finding from the report extraction PR on
2026-11-16. Source: `v1/microkernel/06-read-report-commands-as-ticket-workflows`,
Peer review, finding (10).

Done means the first step of an attended agent launch, managed-checkout or
not, performs exactly one full prompt composition. Three later compositions are
legitimate and out of scope: the confirm-time recompose when control's ticket
gained notes, the per-step compose for later chained steps, and the
`before_recompose` re-run. A missing layer still refuses before any lifecycle
write. Regression tests in `tests/test_launch.py` (or the nearest launch test
module) prove both properties for managed-checkout and plain launches. They
count compositions by monkeypatching `compose_prompt` in `coga.launch`, as
`test_spawn_agent_session_uses_precomposed_prompt_without_rederiving_it`
already does. `coga/launch` "Agent preflight order" describes the new
sequence in the same PR.

## Context

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

### The two composition paths (as of 2026-11-16)

All of them are in `src/coga/launch.py`. Cite symbols, not lines.

- **Pre-flight (discarded result).** This is in the agent-launch setup of the main launch
  class, right after the agent CLI lookup and before `build_launch_env`. It calls
  `compose_prompt(self.cfg, self.ref, self.ticket, launch_context=...)` and
  throws away the result. It exists only to fail loud on `ComposeError` or
  `FileNotFoundError` (`missing_launch_file_message`) before any status write. The
  comment there says "the per-step loop below re-composes; this is a cheap
  pre-flight".
- **Authoritative composition, managed-checkout path.** The inner `compose(plan)`
  helper in `_prepare_step_checkout` composes from the plan's ticket bytes
  plus `checkouts.ticket_notice(...)`. It returns `(ticket, notice, prompt)`, and the
  spawn passes it as `composed_prompt=`.
- **Authoritative composition, other paths.** The module-level spawn helper (the
  one that takes `composed_prompt`, `checkout_notice` and `before_recompose`)
  calls `compose_prompt(...)` itself when `composed_prompt is None`. It logs
  "composing prompt" in that case and "using preflighted prompt" otherwise.

So every attended agent launch runs the pre-flight plus one of the two later
compositions. `--prompt-report` is a separate early-return branch that calls
`compose_prompt_report` and is not part of the duplication.

### Why naive reuse is wrong

The pre-flight runs on the pre-activation ticket with no checkout notice.
The authoritative prompt needs the prospective final ticket and the runtime
checkout notice. Reusing the pre-flight text would therefore break freshness.
Possible directions for the implementer to weigh:

- A resolve-only validation that checks every layer ref and file without
  assembling the prompt.
- Moving the single composition earlier with the notice and ticket it needs.
- Composing once and recomposing only on a detected change (`before_recompose`
  already exists for owner-note recomposition).

Whichever direction is chosen must keep the missing-layer refusal ahead of
secrets, push auth and every lifecycle write. The pre-flight passes neither
`checkout=` nor `include_blocker_preamble`, but the spawn passes both. Any
replacement validation must cover every layer the spawn reads, the checkout
notice and blocker preamble included, so that no spawn-only failure gets
through.

The pre-flight's comment says it is cheap ("file reads only"), so the gain is
mainly removing redundant work and a misleading second pass, not a large
saving in time.

### Other composition sites (leave them, but don't count them as regressions)

- `_prepare_step_checkout` composes a second time when
  `confirm_ticket_checkout` returns changed ticket bytes. That recompose is
  needed for freshness.
- The supervisor loop calls the spawn helper once per chained agent step. Only
  the first step pays the pre-flight.
- `launch_with_before_spawn` raises `_RecomposeAfterLaunchPublication` and
  re-runs `_launch` in full, pre-flight included.

### Docs to update (cited, not attached)

- `coga/launch` (`src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md`),
  section "Agent preflight order". It currently says "a full prompt
  composition (a missing layer refuses)" and later "compose from the
  prospective final ticket and checkout notice". Update it to the new
  sequence.
- `coga/prompt-composition` is reference only. Read "Layer order" for the
  runtime checkout-notice layer and "Measuring" for `--prompt-report`.
- `coga/state-publication/launch-boundaries` classifies startup sequences.
  Check it if the change moves composition relative to startup publication.

### Related follow-ups (out of scope)

Sibling drafts from the same review are in `coga/tasks/v1/microkernel/`:
`normalize-signal-exits-from-read-only-launch`,
`preserve-supervised-environment-in-megalaunch-wind`,
`remove-dead-megalaunch-agent-lookup`, and
`restore-sweep-policy-after-read-only-launch-api-ca`. Megalaunch also calls
`compose_prompt` (`src/coga/megalaunch.py`). Leave it alone unless it shares the
same duplication through the launch class.

<!-- coga:blackboard -->

## Dev

branch: coga/v1-microkernel-avoid-duplicate-attended-launch-p-f53f94


The blackboard is a notepad to be written to often as the human and agent works through a task.
