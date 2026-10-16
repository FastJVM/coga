---
title: 'Demo hackability: ask Claude to add a command live'
status: draft
owner: nicktoper
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
  - name: report-to-coga
    skills: []
    assignee: agent
step: 1 (agent-produces)
contexts:
  - marketing/plan
  - marketing/positioning
  - coga/extension-model
  - coga/script-tickets
  - coga/configuration
---

## Description

Script and rehearse a short recorded demo of Coga's "yours and hackable"
principle. The presenter runs `coga chat` in a fresh repo, tells Claude
"add this feature: a `coga standup` command", and within the take Claude adds
a new working `coga` command entirely at the edge: no file under `src/coga/`
changes and no package reinstall happens. The presenter then runs the new
command and it works.

The deliverable is demo material the owner records, not the recording
itself: a beat-by-beat script, the exact prompt to say, a reset-able demo
repo recipe, a rehearsal log proving the take works, and a fallback plan.

### Acceptance criteria

- [ ] A demo script (beats, spoken prompt, expected screen at each beat,
      target length 90 seconds or less) is committed under
      `docs/archive/launch-programs/` or attached to this ticket.
- [ ] The default feature is `coga standup`: a command that summarizes the
      last day of `coga/log.md` plus open tickets. The script explains why
      that feature was chosen (useful, legible, one screen of output). Any
      substitute must meet the same bar.
- [ ] The feature lands at the edge by the mechanism `coga/extension-model`
      documents for the shipped version: a repo-local command ticket
      (`coga/bootstrap/<name>/ticket.md`, with a `ticket.py` only if the
      work is deterministic) reached by an `[aliases]` spelling. The rehearsal
      shows `git diff --stat` touching only `coga/` and `coga.toml`.
- [ ] A reset recipe brings a scratch repo to the pre-demo state in one
      command (`coga init` from the released wheel plus seed tickets and log
      lines so `standup` has something to show).
- [ ] At least three clean rehearsals with the released wheel and the
      current Claude CLI are logged on the blackboard, each with wall-clock
      time and any agent deviation. A failed take records its cause.
- [ ] Fallback: a pre-recorded good take, and the exact recovery line the
      presenter says if the live take stalls.
- [ ] The claims shown stay within `marketing/positioning` proof limits.

## Context

Owner request, 2026-10-16, alongside pulling the microkernel cleanup into v1.
The demo is the visible proof of that cleanup, so **rehearse it after
`coga/tasks/cleanup-core-commands/` lands** and against the released 1.0
wheel. Drafting the script and reset recipe can start earlier, but
re-validate the mechanism against `coga/extension-model` before rehearsing,
because the cleanup may change it.

Open questions to settle in the script, not to block on:

- **`coga.toml` edits.** The base prompt tells agents not to edit
  `coga.toml`, yet the alias lives there. Choose one: the presenter adds the
  alias line on camera ("one line to name it"), the demo invokes
  `coga launch bootstrap/standup` with no alias, or the owner changes the rule
  for attended chats in its owning topic first. Recommended: the presenter
  adds the line, which also shows the human stays in charge.
- **Determinism.** A `ticket.py`-only command is reproducible on camera; an
  agent-backed command shows more "agent" but varies per take.
  Recommended: `ticket.py` for the summary, so a re-take shows the same
  output.
- **Placement in the campaign.** Whether this clip goes in the Show HN post,
  the README, or both is the owner's call under `marketing/plan`.

Related: `marketing/plan`, `marketing/positioning`, `coga/extension-model`,
`coga/launch`, `coga/script-tickets`, `coga/configuration` (aliases).

<!-- coga:blackboard -->

Created 2026-10-16 from an attended `coga chat`. Blocked in practice on
`cleanup-core-commands/*` (rehearsal only); script drafting can start now.
