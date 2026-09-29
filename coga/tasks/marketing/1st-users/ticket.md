---
title: Audit and record the first-user ICP
status: draft
owner: nicktoper
contexts:
  - product/vision
  - marketing/positioning
workflow: draft-for-human
---

## Description

Audit the owner's draft ideal-customer profile (ICP) for Coga's first users,
then record the audited version as a new context, `marketing/first-users`, at
`docs/contexts/marketing/first-users/SKILL.md`. The draft is saved verbatim
in this task directory as `icp-draft.md`; read it first. Why now: the idea
piece and Show HN (see Context) are being written for a reader nobody has
pinned down, and the ICP is also the filter for sorting launch responses into
candidate teams.

The audit checks the draft on four points:

1. **Consistency with the owning topics.** `product/vision` → *Intended
   audience* already owns Coga's broad audience. The ICP must narrow it, not
   restate or contradict it. `marketing/positioning` owns the public-claim
   limits. Flag wording that crosses them, e.g. "never have to explain it
   again" implies automatic learning, which positioning rules out;
   corrections become durable only through reviewed file edits.
2. **Product support today.** Check each fit signal against what Coga ships
   now, e.g. multiple agents on one repo (`claude`/`codex` agent types),
   corrections turning into contexts/skills, recurring maintenance
   workflows. Mark each signal as supported, partial, or aspirational,
   citing the owning `coga/*` topic.
3. **Testability.** Can someone decide in one short conversation whether a
   team fits the beachhead ("2–5 engineers, technically novel product,
   several hours a day with agents, repeatedly correcting agent work")?
   Propose concrete qualifying questions or signals.
4. **Gaps and overlap.** Look for missing disqualifiers, contradictions
   between the 2–8 fit range and the 2–5 beachhead, and overlap with the
   idea piece's selected reader.

Done means `marketing/first-users` exists with the owner's approval, and
every audit finding has been either applied or explicitly overruled by the
owner (record which). The context contains the beachhead, fit signals,
qualifying questions and anti-targets, and links to `product/vision` for the
broad audience instead of repeating it. The same change registers the new
topic in `marketing/map` and adds `"marketing/first-users"` to
`LOCAL_ONLY_CONTEXT_REFS` in `tests/test_packaging.py` with the reason
"This project's own marketing material." (otherwise the packaging test
fails). `python -m pytest tests/test_packaging.py` and `coga validate --json`
must pass.

## Context

Workflow `draft-for-human`:

- **agent-produces:** write the audit, as a findings list on the blackboard
  with a suggested resolution for each, plus the draft context file.
- **human-owns-and-finishes:** the owner decides each finding and edits the
  context.
- **report-to-coga:** record the decisions and where the context landed
  (commit/PR).

Scope boundaries:

- Recruiting first users (target list, outreach, done criteria for "we have
  users") is out of scope. That is the separate draft
  `marketing/recruit-first-users`, which depends on this ticket.
- Do not edit `product/vision` or `marketing/positioning` without asking. If
  the audit shows the vision audience itself should change, propose it as a
  finding for the owner to decide.

Sequencing (owner-agreed 2026-09-29):

- The ICP should land before the idea piece is published, so the idea
  piece's reader and the Show HN framing can target it.
- Neither this ticket nor recruiting gates Show HN; the owner removed extra
  launch gates on 2026-09-21.
- The launch is owned by `marketing/build-the-launch-plan` (in progress) and
  the idea piece by `marketing/idea-piece` (draft; its reader is currently
  "a technical reader already using coding agents who wants to carry more
  work forward without surrendering direction and judgment").

Knowledge placement follows `coga/knowledge` (one owner per fact): the ICP is
marketing targeting, so it lives under `marketing/`, and the vision keeps
the broad audience.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
