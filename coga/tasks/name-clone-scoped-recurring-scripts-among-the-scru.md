---
title: Name clone-scoped recurring scripts among the scrubbed children in coga secrets
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
launch_generation: pending:b9f6b387-823f-4069-a855-6dd8c146332b
---

## Description

Filed by Dream recurring/dream, period 2026-W47 (run 20261118T170921Z), Phase 6 disposition. Target src/coga/resources/templates/coga/bootstrap/contexts/coga/secrets/SKILL.md is also edited by open PR #1246 (support-commands boundary), which does not carry this fix. Phase 2 shard ks-27.

Route: open a PR against the target once the overlapping PR(s) have landed or been rebased; the fix is pr-required (human review).

Finding: coga/secrets omits the scrubbed env for clone-scoped recurring scripts

- shard: ks-27
- class: stale
- target: src/coga/resources/templates/coga/bootstrap/contexts/coga/secrets/SKILL.md
- area: coga/secrets
- owner: local

The "A declaration plus an env scrub, not a sandbox" section enumerates what the 1Password-auth scrub covers ("launch ... The same scrub covers the `coga ticket` interviewer and the recurring autofix analysis call") and then says "`coga recurring` runs its inner scan unscrubbed". Current code has a further scrubbed child the topic does not name: `src/coga/recurring_clone.py` (line ~168) builds a `scope: clone` template's `ticket.py` environment with `build_launch_env(cfg, secrets)`, which applies `scrub_op_auth_env` and drops `env:VAR` sources, before the sweep runs the script directly inside that unscrubbed scan. Because the topic says the recurring scan is unscrubbed and lists the scrubbed exceptions, a reader would conclude a clone script inherits `OP_SERVICE_ACCOUNT_TOKEN` and can `op read` ad hoc; it cannot unless its template declares the token as a destination. Add clone-scoped recurring scripts to the scrub sentence (the `coga/recurring/scheduling` passage "The script gets the template's `secrets`" can link here rather than restate it).

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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: docs/secrets-clone-scrub

## Plan

- Name `scope: clone` recurring scripts among the scrubbed children in
  `coga/secrets` ("A declaration plus an env scrub, not a sandbox"); code:
  `recurring_clone.run_clone_template` builds its env with
  `config.build_launch_env`, which applies `config.scrub_op_auth_env` and drops
  `env:VAR` sources.
- Make `coga/recurring/scheduling` link to that section instead of implying
  the script inherits the scan's environment.
- Overlap: PR #1246 (open) edits only the `coga secret get` section of the same
  file; hunks are disjoint, so no conflict expected.

## Handoff (implement)

- Done: commit `2cf8838` on `docs/secrets-clone-scrub` (pushed, based on
  current origin/main `45ecb5e`). Docs-only, two shipped topics; no code, test
  or fixture change (behavior unchanged, topics now match it).
- Next (peer-review): check that the wording matches
  `recurring_clone.run_clone_template` / `config.build_launch_env`, and that
  the scheduling link anchor resolves.
- open-pr: PR #1246 was still open at implement time. Its edit to
  `coga/secrets` is the `coga secret get` section only, disjoint from this
  hunk; rebase if it lands first.
- Unrelated flake: `tests/test_repl_supervisor.py::test_terminal_ticket_backstop_waits_for_a_live_pending_command`
  failed once in the full run (`assert seen and all(seen)`), then passed 3/3
  in isolation. It looks timing-sensitive under load, and this docs-only diff
  can't affect it. Not fixed here.

## PR

```yaml
title: Name clone-scoped recurring scripts among the scrubbed children in coga/secrets
author: claude
author_evidence: >-
  Implement session ran as Claude Code (claude-opus-5-5); manual (no launch-prepared) checkout.
head: 2cf8838dc013e9b3a4eea2815d84044123576cd4
base: 45ecb5e2992f6a9fd7e0ad326d3a2a83ec1ad43a
depth: skim
rationale: >-
  Docs-only correction of one sentence plus a cross-link; it brings coga/secrets in line with
  recurring_clone.run_clone_template, which builds the clone script env via build_launch_env.
implementation: >-
  coga/secrets now names a scope clone template's ticket.py among the scrubbed children and
  states that the clone scripts the unscrubbed recurring scan runs are not part of that scan.
  coga/recurring/scheduling links its "gets the template's secrets" sentence to that section
  instead of restating the rule.
deviations: None.
limitations: >-
  No rendered-markdown check of the new anchor link; the relative path and slug were checked by hand.
files:
  src/coga/resources/templates/coga/bootstrap/contexts/coga/secrets/SKILL.md: >-
    Add clone-scoped recurring scripts to the env-scrub coverage sentence.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: >-
    Link the clone-script secrets sentence to the coga/secrets scrub section.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: >-
    Not reviewed yet; the workflow's peer-review step follows implement.
checks:
  - command: .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_packaging.py tests/test_layout_contexts.py tests/test_validate.py tests/test_recurring_clone.py
    status: passed
    head: 2cf8838dc013e9b3a4eea2815d84044123576cd4
    base: 45ecb5e2992f6a9fd7e0ad326d3a2a83ec1ad43a
    detail: 257 passed, 2 skipped.
  - command: .venv/bin/python -m pytest -q -p no:cacheprovider
    status: failed
    head: 2cf8838dc013e9b3a4eea2815d84044123576cd4
    base: 45ecb5e2992f6a9fd7e0ad326d3a2a83ec1ad43a
    detail: >-
      1 failed, 5003 passed, 33 skipped. The one failure was
      test_repl_supervisor.py::test_terminal_ticket_backstop_waits_for_a_live_pending_command,
      which then passed 3/3 when rerun alone; it is a timing flake unrelated to this docs-only diff.
