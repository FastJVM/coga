---
slug: dream-phases-2-3-cannot-complete-scan-subagents-re
title: 'Dream phases 2-3 cannot complete: scan subagents return no findings'
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

Dream's two decide-half scan phases could not complete in the `2026-W34` run.
Phases 1, 4, 5 and 6 all worked; Phases 2 and 3 produced **no findings at all**,
so that run routed no `stale`/`drift` proposal PRs and no `gap` tickets — an
absence of input, not a clean repo.

Phase 2 (`bootstrap/dream/scan/knowledge-scan`) and Phase 3
(`bootstrap/dream/scan/contract-audit`) are both specified as
"delegate this phase to a subagent". In that run every scan subagent spawned,
read part of the corpus, and then stopped without ever returning a findings
list to Dream:

- `knowledge-scan` — read ~120KB of corpus, output froze after ~1 minute.
- `contract-audit` — read ~53KB including `coga/log.md`, froze after ~5 minutes.
- a retry with an explicitly tightened reading budget produced no transcript at
  all and returned nothing within its 5-minute window.

All three later emitted `idle_notification` / `idleReason: available`. Messaged
directly and asked to return whatever partial findings they had — including one
request that forbade any tool use and asked only for plain text — each replied
with another bare idle notification and no content.

Notably, Phase 4's Retro subagent *did* work in the same session (86 tool uses,
~9.5 minutes, opened PR #698 and landed 10 direct deletes). So this is not
simply "subagents are broken here". The distinguishing feature of the two failed
phases is that each is a single long read-only sweep over the whole corpus whose
entire value is delivered in one final message.

### What to work out

1. Reproduce, and establish whether the cause is a context/output-size limit on
   the final message, a liveness timeout on a long tool-free stretch, or
   something specific to how these two scans are prompted.
2. Decide whether a silently result-less scan phase should be *detectable* by
   Dream. Today Dream cannot tell "scan ran, found nothing" from "scan never
   returned", and only noticed because the subagent's own progress was being
   watched. A scan that must report `no findings` explicitly, or a required
   heartbeat, would remove the ambiguity.
3. Consider making the scans stream durable partial output the way Phase 4 was
   made to. The `2026-W34` Retro pass only survived scrutiny because it was told
   to append every step to an on-disk progress log; that log, not the agent's
   final message, is what made the phase verifiable. The same hedge would have
   salvaged partial scan findings.
4. If the corpus is simply too large for one subagent read, the fix may be to
   partition the scan (by area, or contexts-vs-tickets) rather than to keep
   retrying one sweep — but that changes the "single full-corpus read" design in
   `knowledge-scan/SKILL.md`, which exists so the running delta can de-duplicate
   across the whole corpus. Weigh that tradeoff explicitly.

Any behavior change here must update the matching skill file(s) under
`coga/.agent-skills/bootstrap/dream/scan/` and the packaged copies, plus the
Dream template body in both `coga/recurring/dream/ticket.md` and
`src/coga/resources/templates/coga/recurring/dream/ticket.md`.

## Context

Raised by the `recurring/dream` run for period `2026-W34`. That Dream task is
`done` and will be deleted by the next firing, so this ticket is the durable
record — its blackboard is gone by then.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
