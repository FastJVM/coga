---
title: Give the three-kinds-of-work taxonomy an owning doc
status: in_progress
owner: nicktoper
contexts:
- coga/knowledge
workflow:
  name: docs/with-review
  steps:
  - name: implement
    skills: []
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills: []
    assignee: agent
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
agent: claude
---

## Description

Coga's pitch rests on a taxonomy of human work that no repo file owns yet.
Humans do three kinds of work: **routine** (fix merge conflicts, bump
dependencies), **understood** (fully specifiable before doing: support, adding
a feature), and **unknown** (work you discover by doing, with a "known cone"
of what you have done and blur beyond it). Coga maps to all three: routine to
scripts, recurring jobs and recipes; understood to a ticket with a frozen
workflow and megalaunch; unknown to chat, the blackboard, rewind that keeps
everything learned, superseded designs and Dream. It is built for the third.
Under the one-owner rule in `coga/knowledge`, the pitch can only summarize
this if one topic owns it.

Do three things:

1. **Own the taxonomy in `product/vision`.** Add a new section right after
   `## The bet` in `docs/contexts/product/vision/SKILL.md`. The bet's last
   paragraph already holds the three what-to-automate questions; the new
   section should connect to it rather than repeat it. Name each kind, its
   Coga mechanisms (as short links/receipts, not restated contracts), and
   state that Coga is built for unknown work.
2. **Point to it from `coga/principles`.** One sentence in the root paragraph
   so "think better" names what the human thinks about (the unknown work),
   naming the vision section. Edit the canonical topic and its packaged
   twin together. The twin ships to other repos, which have no
   `product/vision`, so name it as a plain repo path the way
   `## Not covered here` names `marketing/strategy`, not as a relative link.
3. **Relabel the human rewind** (`coga bump --to` / `--backward`) as both:
   recovery for understood work, and a normal move for unknown work. Fix the
   one surviving "exceptional recovery operation" phrase in
   `coga/current-direction`, and add the dual framing to the rewind bullet in
   `coga/lifecycle` (canonical and packaged twin).

Done when: the vision section exists and is the only place the taxonomy is
specified; principles links to it in one sentence; `grep -rni "exceptional"
docs/contexts src/coga/resources` finds no rewind described as only
exceptional; lifecycle states both framings; `python -m pytest
tests/test_packaging.py` and `coga validate` pass. `marketing/strategy` and
the pitch may summarize and link, but this ticket adds no second restatement.

## Context

Source of the taxonomy: the owner's pitch draft of 2026-09-16/17 (chat
session, `bootstrap/orient`). It is not in any repo file; as of authoring,
`grep` for "three kinds of work", "unknown work" and "known cone" finds only
this ticket and one passing phrase in
`docs/evidence/research-work-comparison.md`.

Topics this ticket edits (cited, not attached; read each first):

- `docs/contexts/product/vision/SKILL.md` — sections `## The bet` and
  `## Operating model`. Local-only topic (listed in
  `tests/test_packaging.py` `LOCAL_ONLY_CONTEXT_REFS`), no twin.
- `docs/contexts/coga/principles/SKILL.md` — the root paragraph above
  `## 1. Hackable`. Packaged twin:
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/principles/SKILL.md`.
- `docs/contexts/coga/lifecycle/SKILL.md` — `## Step: where in the workflow`,
  the `--to` / `--backward` bullet ("is a **human** rewind … It repositions
  only"). Packaged twin under the same bootstrap contexts path.
- `docs/contexts/coga/current-direction/SKILL.md` — the "Control and data
  planes stay split" bullet ("a human rewind is an exceptional recovery
  operation"). Local-only, no twin.

Check `## Operating model` in vision before writing: link to it rather than
restate any mechanism it already describes.

Twins must stay byte-identical (`tests/test_packaging.py`).

Receipts to link from the vision section, rather than restate:

- Routine: recurring templates (`coga/recurring`), the `ticket.py` sibling
  (`coga/script-tickets`), `coga run` recipes (`runner.RECIPES`).
- Understood: `coga create --workflow`, frozen steps (`coga/workflows`),
  `coga megalaunch` (`coga/megalaunch`).
- Unknown: `coga chat` (the packaged orient ticket
  `src/coga/resources/templates/coga/bootstrap/orient/ticket.md`; not a
  topic), the blackboard
  (`coga/blackboard`), human rewind (`bump.rewind_status_error` /
  `REWINDABLE_STATUSES`: reposition-only, status and blackboard untouched, so
  everything learned stays), `## Superseded designs` (kept out of the prompt
  by `blackboard._without_superseded_designs`), `coga ticket <slug>`
  re-authoring at any status (`coga/tickets`), Dream (`coga/dream`).

Out of scope: rewriting the pitch or `docs/contexts/marketing/strategy/SKILL.md`
beyond an optional one-line summary-and-link; any code or CLI behavior change.

Related evaluation record: `docs/evidence/pitch-evaluation.md`,
`docs/evidence/research-work-comparison.md` (unknown work vs CE/Kortix).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
