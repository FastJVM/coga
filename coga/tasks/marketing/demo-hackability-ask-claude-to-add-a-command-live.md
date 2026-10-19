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
      command (`coga init` from the demo's wheel plus seed tickets and log
      lines so `standup` has something to show).
- [ ] At least three clean rehearsals with the final 1.0 release-candidate
      wheel and the current Claude CLI are logged on the blackboard, each
      with wall-clock time and any agent deviation. A failed take records
      its cause.
- [ ] After 1.0 is published, one smoke take against the published wheel
      confirms the demo still works; this check follows publication and does
      not gate it.
- [ ] Fallback: a pre-recorded good take, and the exact recovery line the
      presenter says if the live take stalls.
- [ ] The claims shown stay within the live
      [claim and wording limits](idea-piece.md#claim-and-wording-limits),
      with the recorded rehearsals supporting the demonstrated behavior.

## Context

Use [README.md](../../../README.md) for current public positioning and
[`coga/principles`](../../../docs/contexts/coga/principles/SKILL.md) for the
design principles. Read the live
[idea-piece claim limits](idea-piece.md#claim-and-wording-limits) before
drafting the script and the [launch plan](build-the-launch-plan.md) before
preparing publication; the retired marketing contexts are not dependencies.

Owner request, 2026-10-16, alongside pulling the microkernel cleanup into v1.
The demo is the visible proof of that cleanup, so **rehearse it after
`coga/tasks/microkernel/` lands** and against the final 1.0
release-candidate wheel. This ticket gates the 1.0 publication, so it cannot
wait for the published wheel; a smoke take on the published wheel follows
release. Drafting the script and reset recipe can start earlier, but
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
  the README, or both is the owner's call under the
  [live launch plan](build-the-launch-plan.md).

Related: README.md, `coga/principles`, `coga/extension-model`,
`coga/launch`, `coga/script-tickets`, `coga/configuration` (aliases).

<!-- coga:blackboard -->

Created 2026-10-16 from an attended `coga chat`. Blocked in practice on
`microkernel/*` (rehearsal only); script drafting can start now.
