---
slug: sync-context-omits-preflight-post-from-the-notific
title: Sync context omits preflight_post from the notification contract
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
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
secrets: null
step: 1 (implement)
---

## Description

`coga/contexts/coga/sync/SKILL.md` explains at length why lifecycle broadcasts pass
`fatal=False` — the markdown is already written, so a delivery miss must not abort the
command or skip `emit_done_marker` — and asserts that "Misconfiguration (an unresolved
webhook) still crashes on both paths".

What it never says is *when* that crash happens, or that keeping it useful required a
separate mechanism: `notification.preflight_post`, whose own docstring is "Fail before a
state mutation when a selected live channel is unusable".

Without the preflight, a repo with an unresolved webhook would flip the ticket, write the
audit line, sync to the control branch, and only then die inside `SlackChannel` — the
exact half-applied outcome `fatal=False` exists to prevent, arriving through the
configuration branch instead of the delivery branch.

The context's "Design rule for new features" section is where an author is told what to
wire up when adding a state-changing command. It lists cadence, destination, the
post-after-write ordering, and `git.sync_task_state` — but not the preflight. So the next
such command will omit it, and **the omission is invisible in any repo whose webhook
resolves**.

Deliverable: document the preflight as the third element of the notification contract
alongside cadence and destination, naming its call sites and the `important=True` form.

## Context

Citations name symbols and files, not line numbers.

`notification.preflight_post(cfg, *, important=False)` calls `require_webhook` for every
enabled channel and is invoked at five independent call sites ahead of the mutation:

- `src/coga/commands/block.py`
- `src/coga/commands/bump.py`
- `src/coga/commands/mark.py`
- `src/coga/launch_script.py`
- `src/coga/autoclose.py`

Verify the list is still exactly five before writing — `grep -rn preflight_post src/coga/`
is the check.

Related but separate: Dream 2026-W36 opened a proposal PR correcting two other claims in
this same context (the live-producer module list, and the missing
`slack_response.py` classification and `redact_slack_webhook_credentials` boundary). Check
whether that PR has merged before starting, and rebase onto it rather than editing the same
section twice.

`coga/contexts/coga/sync/SKILL.md` is an enforced byte-identical twin with
`src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md`
(`IDENTICAL_LIVE_PACKAGED_PAIRS` in `tests/test_packaging.py`) — edit both. It is 59 KB;
locate the target section with grep rather than reading it whole.

Filed by Dream 2026-W36, Phase 2 knowledge scan (shard `ks-08`), classified `gap`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
