---
title: Launch must not re-activate a done ticket
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/principles
- relay/architecture
- relay/codebase
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
---

## Description

`relay launch` on a `done` ticket silently restarts its workflow at step 1,
then crashes and leaves the ticket wedged. Launching a `done` ticket must not
re-activate it — it should refuse (or no-op) and leave the ticket untouched.

### Repro

```
$ relay launch <slug>          # ticket is done
Launch: task <slug> (status=done, mode=interactive, assignee=nick)
<slug>: active — auto on launch
Agent type 'nick' is not defined in [agents]. Known: ['claude', 'codex'].
```

### What goes wrong

`launch` brings any status outside `{active, in_progress}` to `active` inline
(`commands/launch.py:227-232` → `_auto_activate`), and that set **includes
`done`**. For a done ticket this calls `mark_active` →
`_freeze_workflow_ref` (`mark.py:208-211`), which re-seeds `step: 1` on the
re-activated ticket. So just typing `relay launch` a second time restarts a
finished workflow from the top.

It then crashes: re-seeding `step: 1` does not re-resolve `assignee:`, which
still holds the final step's resolved value (`nick`, the human `owner` from the
`review` step). Launch resolves the agent type straight from `assignee`
(`launch.py:277`, `cfg.agent_type("nick")`) → `Agent type 'nick' is not
defined`.

Worse, the failure is **not clean**: `mark_active` already wrote
`status: active` + `step: 1` and git-synced before the crash, so the ticket is
left wedged — `status: active, step: 1, assignee: <human>`. Re-launching now
skips `_auto_activate` (status is already `active`) and crashes again on the
same `agent_type` lookup. It does not self-heal without a hand-edit.

### Fix

`relay launch` must refuse to re-activate a `done` ticket. `_auto_activate`'s
status guard should exclude `done` so a done ticket is never restarted by a
launch. Decide the surface: a fail-loud error with a hint (e.g. "ticket is
done; `relay mark active` to reopen, or relaunch a different ticket") vs. a
quiet "nothing to do" no-op mirroring the freshness-check message. Draft /
paused re-activation is unchanged.

Note the separate `assignee`-not-re-resolved-on-step-reseed gap is real but
becomes unreachable for the done case once launch stops re-activating done
tickets; reopening is the deliberate `relay mark active` path, which can carry
its own assignee re-resolution if/when re-activation of a done ticket is wanted.

### Verification

- `relay launch <done-slug>` leaves the ticket `done` and unmodified (no git
  commit, no `step` reseed).
- Draft and paused tickets still activate on launch as before.
- A unit/CLI test covering launch-on-done.

## Context

Surfaced while debugging a `done` ticket that had been auto-bumped on PR merge
and then restarted by a second `relay launch`. The auto-bump-trigger half of
that story is tracked separately by
`v2/retire-standalone-relay-automerge-triggers-recurri` (move merge-detection
to the recurring `autoclose-merged` sweep, drop the launch-time freshness
check). This ticket is only the launch-restart guard and is independent of
where merge-detection lives.

