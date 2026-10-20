---
title: Audit and record the first-user ICP
status: draft
owner: nicktoper
workflow: draft-for-human
---

## Description

Audit the owner's draft ideal-customer profile (ICP) for Coga's first users,
then record the audited version as `first-users.md` beside this ticket.
Keep this as a task deliverable; do not recreate a marketing context library.
The draft is saved verbatim in this task directory as `icp-draft.md`; read it
first. Why now: the idea
piece and Show HN (see Context) are being written for a reader nobody has
pinned down, and the ICP is also the filter for sorting launch responses into
candidate teams.

The audit checks the draft on four points:

1. **Consistency with the owning topics.** Read the root `README.md`,
   especially *Who it is for, and its limits*, for Coga's broad audience and
   fit. It is cited here, not attached; links do not load their targets.
   The ICP must narrow that audience, not restate or contradict it.
   Read the [idea-piece claim limits](../idea-piece.md#claim-and-wording-limits).
   Flag unsupported wording: "never have to explain it again" implies
   automatic learning; corrections become durable only through reviewed
   file edits.
2. **Product support today.** Check each fit signal against what Coga ships
   now, e.g. multiple agents on one repo (`claude`/`codex` agent types),
   corrections turning into contexts/skills, recurring maintenance
   workflows. Mark each signal as supported, partial, or aspirational,
   citing the owning file: `coga/agents` for multiple agents,
   `coga/recurring` for recurring maintenance, and `coga/recurring/dream/ticket.md` /
   `coga/skill-management` for corrections becoming contexts and skills.
   Read these files; they are cited here, not attached.
3. **Testability.** Can someone decide in one short conversation whether a
   team fits the beachhead ("2–5 engineers, technically novel product,
   several hours a day with agents, repeatedly correcting agent work")?
   Propose concrete qualifying questions or signals.
4. **Gaps and overlap.** Look for missing disqualifiers, contradictions
   between the 2–8 fit range and the 2–5 beachhead, and overlap with the
   idea piece's selected reader.

Done means `first-users.md` has the owner's approval, and every finding has
been applied or explicitly overruled with a recorded reason. The brief holds
the beachhead, fit signals, qualifying questions and anti-targets, linking to
the root README for the broad audience. Hand the approved brief to the idea
piece, launch and recruiting tickets; no topic registration is required.

## Context

Workflow `draft-for-human`:

- **agent-produces:** record findings and suggested resolutions on the
  blackboard, and draft `first-users.md` beside this ticket.
- **human-owns-and-finishes:** the owner decides findings and edits the brief.
- **report-to-coga:** apply accepted edits, check links and ticket validation,
  and hand the approved brief to the consuming tickets. Before this ticket
  retires, preserve the brief with any unfinished work that still needs it.

Scope boundaries:

- Recruiting first users (target list, outreach, done criteria for "we have
  users") is out of scope. That is the separate draft
  `marketing/recruit-first-users`, which depends on this ticket.
- Do not edit `README.md` or the design principles
  without asking. If the audit shows the broad audience itself should change,
  propose it as a finding for the owner to decide.

Sequencing (owner-agreed 2026-09-29):

- The ICP should land before the idea piece is published, so the idea
  piece's reader and the Show HN framing can target it.
- Neither this ticket nor recruiting gates Show HN; the owner removed extra
  launch gates on 2026-09-21.
- The launch is owned by `marketing/build-the-launch-plan` (in progress) and
  the idea piece by `marketing/idea-piece` (draft; its reader is currently
  "a technical reader already using coding agents who wants to carry more
  work forward without surrendering direction and judgment").

The README owns the broad audience and fit. Read its *Key ideas* and *Who it
is for, and its limits* before drafting. Keep only what narrows that audience;
the brief may be short. The dependency from `marketing/recruit-first-users`
is in prose; launch order does not enforce it.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
