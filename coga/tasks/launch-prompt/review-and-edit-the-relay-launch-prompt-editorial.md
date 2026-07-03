---
slug: launch-prompt/review-and-edit-the-relay-launch-prompt-editorial
title: review and edit the relay launch prompt (editorial pass)
status: active
mode: agent
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- coga/architecture
- coga/principles
skills: []
workflow:
  name: autonomy/assist-only
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: human
  - name: report-to-relay
    skills: []
    assignee: agent
secrets: null
step: 1 (agent-produces)
---

## Description

A human-owned editorial pass over the Relay launch prompt. Where the sibling
ticket (`improve-prompt-for-relay-launch`) does the mechanical/structural trim,
this ticket is nick's broader review-and-edit of the prompt's wording, tone,
and clarity — the parts that are taste and judgment on the behavioral contract,
not a clean code change.

Claude drafts support material (a marked-up read of the launch prompt:
remaining redundancy, awkward phrasings, instructions that could be sharper or
clearer, anything ambiguous to a launched agent). Nick reviews, edits the
wording to the bar he wants, and owns the result.

Best done after the sibling trim ticket lands so this pass refines the already-
trimmed prompt rather than churning against it — though it can start earlier if
nick wants to set direction first.

## Context

- Scope is the launch prompt surface: `prompt.md` plus the mode overlays
  `prompt-interactive.md` / `prompt-auto.md`, all single-source under
  `src/relay/resources/` (no `templates/relay-os/` copy and no live `relay-os/`
  copy; don't touch the vendored `relay-os/.relay/` snapshot).
- This is `autonomy/assist-only` by design: the prompt is a taste/voice
  artifact, so the agent produces input and the human owns final wording. The
  agent draft is support material, not the delivered edit.
- Sibling ticket: `improve-prompt-for-relay-launch` (Claude, `code/with-review`)
  does dedupe, reference-relocation, core-loop-first, and overlay-trim. This
  ticket assumes that mechanical work and layers editorial judgment on top.
- The prompt is the behavioral contract for every launched agent — wording
  changes still must not silently drop a load-bearing rule, and must keep the
  `relay-os/contexts/relay/` contexts accurate.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Status
Draft, filled 2026-06-19. T2 of a two-ticket split (both under
`relay-os/tasks/launch-prompt/`). Workflow `autonomy/assist-only`, assignee nick.
This is the human-owned editorial/voice pass over the launch prompt; sibling
`improve-prompt-for-relay-launch` (claude, code/with-review) does the mechanical
trim first. Best launched after the sibling lands.

## Scope notes
- Three files in scope: `src/relay/resources/{prompt.md,prompt-interactive.md,prompt-auto.md}`.
  SINGLE-SOURCE (no `templates/relay-os/` copy, no live `relay-os/` copy).
- assist-only = agent drafts a marked-up read (redundancy, awkward phrasings,
  ambiguities), nick edits to his bar and owns final wording, agent reports.
- Soft ordering only (co-located, not hard-gated): run after the trim ticket so
  the markup is against the trimmed prompt, not churned mid-restructure. Can
  start earlier if nick wants to set direction first — but then the markup is
  throwaway.

## Evaluator review (T2, independent cold read — 2026-06-19)

The packaged prompt files exist; there is no live `relay-os/` copy of the prompt files. The ticket's "and any live `relay-os/` copy" hedge is accurate (there isn't one). Here's my assessment.

---

**Overall: well-formed and pickup-ready. The description is clear enough to start, the workflow fits, and the sibling boundary is articulated. One real assumption to check before launch.**

**Description / drafting readiness — good.** An agent on the `agent-produces` step has enough to act: deliverable is explicitly "a marked-up read of the launch prompt" flagging redundancy, awkward phrasing, unclear/ambiguous-to-a-launched-agent instructions. Scope files are named (`prompt.md`, `prompt-interactive.md`, `prompt-auto.md` under `src/relay/resources/`) and I confirmed they exist. The deliverable being support material (not an applied edit) is stated plainly, which matches the workflow.

**Workflow fit — correct choice.** `autonomy/assist-only` (agent-produces → human-owns-and-finishes → report-to-relay) is the right shape for a taste/voice pass: the agent annotates, nick edits to his bar and owns the wording, the agent records. The workflow even says "for quality, taste, or differentiating judgment, not feasibility, so do not run the automated-tier downgrade ladder" — exactly this ticket. No mismatch.

**Sibling boundary — clear in principle, one churn risk.** The split is well-drawn: sibling = mechanical/structural (dedupe, relocate reference, lead-with-core-loop, trim overlays to deltas, with a token measurement and `code/with-review`); this = subjective wording/tone/clarity, human-owned. The ticket explicitly sequences this *after* the trim lands "so this pass refines the already-trimmed prompt rather than churning against it." The residual risk is the "can start earlier if nick wants to set direction first" escape hatch — if both run concurrently, the editorial markup will be written against a prompt the sibling is simultaneously restructuring, and the annotations (which cite "remaining redundancy," "awkward phrasings") could go stale. Recommend honoring the stated ordering unless nick deliberately wants a direction-setting pre-pass.

**Scope — reasonable, not too vague.** Bounded to three named files, deliverable shape is concrete, and the guardrail (don't silently drop a load-bearing rule; keep `relay-os/contexts/relay/` accurate) is carried over from the sibling and from CLAUDE.md. It's appropriately open-ended for a judgment task without being unactionable.

**Assumptions to question before launch:**
- *Sequencing dependency is soft.* The ticket leans on the sibling having landed but permits starting early — decide explicitly which, since it changes whether the markup is durable or throwaway.
- *"Live `relay-os/` copy" may not exist.* The ticket hedges "any live `relay-os/` copy" — confirmed there is none today (only the packaged `src/relay/resources/` copies). Not a defect, but the keep-in-sync instruction is currently a no-op; the agent should not go hunting for a second copy.
- *Empty `contexts: []`.* Both tickets leave contexts empty despite repeatedly invoking the behavioral-contract / `relay-os/contexts/relay/` framing. An editor doing a clarity pass would benefit from `architecture` and `principles` being loaded; consider populating `contexts` so the agent's markup is checked against the actual contract rather than from memory.
- *Two owners, `mode: interactive`.* `owner/human/assignee` all = nick and the first step is agent-assigned — consistent with assist-only, just confirm nick intends to be live in the loop for the human-owns step rather than this running unattended.

_Note: T2 ticket text simplified to single-source after this review (no live relay-os/ copy). The contexts:[] suggestion (attach relay/architecture + principles) is left for nick to decide — see open question._
