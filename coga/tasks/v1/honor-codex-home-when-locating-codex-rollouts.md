---
title: Honor CODEX_HOME when locating Codex rollouts
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
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
agent: claude
---

## Description

`usage._codex_rollout_paths` globs `~/.codex/sessions/**/rollout-*.jsonl`
unconditionally. Codex keeps its sessions under `$CODEX_HOME/sessions` when
`CODEX_HOME` is set. For a user who sets it, every Codex launch would therefore
record `usage_status` unknown with reason `codex rollout not found for cwd`.
This has not been seen in this repo, where `CODEX_HOME` is unset. It was found
while closing `v1/35-recheck-codex-usage-completeness-after-the-session`.

Done means:

- The rollout root is `$CODEX_HOME/sessions` when `CODEX_HOME` is set and
  non-empty, and `~/.codex/sessions` otherwise. The value is used exactly as
  written, with no `~` expansion, to match Codex.
- A regression test in `tests/test_usage.py` sets `CODEX_HOME` to a directory
  outside `HOME`, writes a rollout there, and asserts that the session is
  snapshotted and parsed to `ok`.
- The existing Codex tests in `tests/test_usage.py` clear `CODEX_HOME`, for
  example with an autouse fixture, so they pass when a developer has it set.
- `coga/usage` and `coga-dev/internals/activity-capture` both state the
  lookup rule.
- `python -m pytest tests/test_usage.py tests/test_packaging.py` passes.

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

### Code pointers

- `usage._codex_rollout_paths` is the only place the root is built:
  `Path.home() / ".codex" / "sessions"`. Two functions call it.
  `usage.snapshot_session_files` takes the pre-spawn snapshot, and
  `usage._parse_codex_session` takes the post-run diff. Because both go through
  the same helper, they read the same root. Keep it that way by deciding the
  root in that one helper.
- `CODEX_HOME` is read from the environment of the coga process. The agent
  child inherits that environment, so coga and Codex see the same value.
  An empty string counts as unset. Do not expand `~`. The cold review
  recalled, without checking, that codex-rs `find_codex_home` treats empty as
  unset, uses the literal value, and errors if the path is missing. Confirm
  that against Codex's docs or source before you implement, and if Codex
  behaves differently, write down what you found on the blackboard.
- Out of scope, and to be documented as unsupported:
  - a relative `CODEX_HOME`, which Codex resolves against its own working
    directory (the checkout), while coga's cwd may differ;
  - a `CODEX_HOME` set only in the agent child's environment, through ticket
    `secrets:` or agent env config.
- The other `.codex` references in `init.py`, `uninstall.py`, `update.py`, and
  `skill_manager.py` are about the repo-local `.codex/skills` directory, not
  rollouts. Leave them alone.
- Existing Codex tests in `tests/test_usage.py` set `HOME` with
  `monkeypatch.setenv("HOME", tmp_path)` and write rollouts under
  `tmp_path/.codex/sessions`. Give the new test the same shape, and make the
  existing tests clear `CODEX_HOME` with `monkeypatch.delenv(...,
  raising=False)`, so that a developer with `CODEX_HOME` set does not see them
  fail.
- Out of scope: the Claude transcript root (`~/.claude/projects/...` in
  `usage`) has the same kind of hard-coded path but a different override
  (`CLAUDE_CONFIG_DIR`). Leave it alone and only mention it on the blackboard
  as a possible follow-up.

### Docs to edit (cited, not attached — this ticket edits them)

- `coga/usage`: the package owner is
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/usage/SKILL.md`.
  It has a legacy live copy at `docs/contexts/coga/usage/SKILL.md`, listed in
  `tests/legacy_removal_inventory.txt`. Edit the package copy, mirror the
  change into the live copy byte for byte, and commit both together, or
  `tests/test_packaging.py` fails. The topic does not mention Codex rollouts
  yet. Add one sentence near the explanation of `unknown`: where Codex
  rollouts are looked up, and that a rollout missing from that root is
  recorded as unknown, not as zero.
- `coga-dev/internals/activity-capture`
  (`docs/contexts/coga-dev/internals/activity-capture/SKILL.md`, local only):
  the Codex paragraph currently says capture snapshots
  `~/.codex/sessions/**/rollout-*.jsonl`. Change it to give the
  `CODEX_HOME` rule.

<!-- coga:blackboard -->

## Dev

branch: coga/v1-honor-codex-home-when-locating-codex-rollouts-5b4cd1


The blackboard is a notepad to be written to often as the human and agent works through a task.
