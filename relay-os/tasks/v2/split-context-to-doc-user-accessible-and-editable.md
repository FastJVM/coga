---
slug: v2/split-context-to-doc-user-accessible-and-editable
title: 'split context to doc: user accessible and editable'
status: draft
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/architecture
- relay/principles
- relay/codebase
- relay/project-stage
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
---

## Description

The repo context (`relay-os/context.md`) is composed as layer 4 of every
launch prompt, living inside `relay-os/` next to agent-facing machinery
(tickets, workflows, skills). But it is really the project's living
documentation — what the repo is, who works on it, the defaults agents
should know — which a human reads and edits far more often than they touch
tickets, workflows, or skills. This ticket designs how to split that
human-owned documentation out to an accessible, editable location under
`docs/` while `relay launch` still composes it into the prompt. The right
boundary between "human-owned doc" and "agent-prompt context" is not yet
settled, so the first step is a design proposal for owner review before any
code is written.

## Context

- **Composition today:** `src/relay/compose.py:178` reads the repo context
  via `repo_context_path(cfg)` and emits the `"Repo context"` layer
  (`ref=context.md`). The resolver is `repo_context_path` in
  `src/relay/paths.py:84`, exported via `__all__` (`paths.py:120`) — both
  move together with any rename.
- **Two copies stay in sync:** the live `relay-os/context.md` and the
  packaged template `src/relay/resources/templates/relay-os/context.md`
  (see CLAUDE.md — keep both in sync unless intentionally divergent).
- **Docs that reference the path:** `relay/architecture` SKILL.md documents
  the 8-layer composition order and names `relay-os/context.md` at layer 4
  (~line 184). If the path moves, update that context in the same change.
- **Decision: `docs/` in repo** (alongside `docs/vision.md`) for the
  human-facing doc location. Exact filename (`docs/context.md` vs
  `docs/project.md`) is for the design step to recommend.
- **Open design questions for the proposal:** the exact filename; whether
  `relay launch` reads the new path directly or via a configurable pointer.
  Note: `relay/project-stage` says "No backwards-compat hacks" — so prefer a
  clean direct move over a compat shim unless the design surfaces a real
  reason. Markdown-first, git-backed, human-legible posture must hold (see
  `relay/principles`).
- **Template + seeding:** the packaged template
  `src/relay/resources/templates/relay-os/context.md` must move/rename in
  lockstep, and the design should confirm what reads it (the `relay init` /
  update seeding path and the `example/` fixture) before relocating — not
  just move the file.
- **Tension to resolve, not assume:** `relay/architecture` and
  `relay/codebase` frame `relay-os/` as the single tree relay operates on,
  with `context.md` as a composed layer inside it. Moving it to `docs/`
  splits that boundary; the design must justify why the human-doc framing
  outweighs keeping all composed layers under `relay-os/`.
- **Out of scope:** rewriting what the context *says*, and re-homing the
  broader `relay/*` contexts that also double as docs — this ticket is only
  about where the repo-level `context.md` lives and who owns it. The design
  may *note* the broader pattern but should not expand to it without owner
  sign-off.

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Bootstrap decisions (2026-05-28)

- Framed as a **design ticket**: the human-doc / agent-context boundary isn't
  settled, so design + owner sign-off precede code. Workflow:
  `code/design-then-implement`.
- Scope locked to the repo-level `relay-os/context.md` only. Broader `relay/*`
  contexts-as-docs are explicitly out of scope (design may note the pattern,
  not act on it without owner sign-off).
- Doc destination: `docs/` (alongside `docs/vision.md`); exact filename left
  to the design step.
- Contexts attached: `relay/architecture` (composition model),
  `relay/principles` (markdown-first / legible constraints),
  `relay/codebase` (source layout), `relay/project-stage` (added after
  evaluator review — its "no backwards-compat hacks" posture pre-answers the
  shim question).
- Assignee set to `claude` (step 1 `design` is an agent step).

## Evaluator review

I have enough to assess. Let me note one factual discrepancy: the ticket says the resolver lives in `config.py`, but it's actually in `paths.py`.

## Assessment: `split-context-to-doc-user-accessible-and-editable`

**Clarity — strong.** An agent could start cold. The Description states the problem (repo context.md lives among agent machinery but is really human-owned documentation) and the goal (split it to `docs/`, keep `relay launch` composing it). The `## Context` block is unusually good: it names the exact compose site, the two-copies-in-sync rule, the doc that hard-codes the path, the decided location (`docs/`), and a crisp Out of Scope. The design-first framing ("the boundary isn't settled, so propose before coding") is explicit and appropriate.

**One factual error to fix before launch.** The Context says "The resolver lives in `config.py`." It does not — `repo_context_path` is defined in `src/relay/paths.py:84` (and re-exported there). `compose.py` imports it from `paths.py`. An agent trusting the ticket would grep config.py and come up empty. Worth correcting the inline note to point at `paths.py`.

**Workflow fit — good.** `code/design-then-implement` is the right shape. The work has a genuine undecided design (direct-read vs configurable pointer vs back-compat shim, filename choice, template migration) that warrants an owner review gate before code. The two owner checkpoints (review-design, review-PR) match the stated need for sign-off on the boundary. No mismatch.

**Attached contexts — mostly right, with one redundancy and one gap.**
- `relay/principles` is load-bearing here — markdown-first / git-backed / human-legible / short-correction-loop are exactly the constraints the design must respect. Keep.
- `relay/codebase` is relevant: it gives the src/relay vs relay-os split and the relay-os layout (showing `context.md` as the repo-context layer). Keep, though see below.
- `relay/architecture` is relevant for the 8-layer composition model. **But** the single fact the agent actually needs from it — that context.md is layer 4 and where that's documented — is already restated inline in `## Context` (with the ~line 184 pointer). Attaching the full architecture SKILL to deliver one already-inlined fact is borderline; the inline note arguably makes the attachment redundant. Not harmful, but if trimming, this is the candidate.
- **Gap:** nothing tells the agent the resolver is in `paths.py` (the ticket misdirects to config.py) and that `paths.py` also keeps an `__all__` export (line 120) that must move with any rename. Since the relevant fact lives in neither the attached codebase context (which doesn't mention `paths.py` or `repo_context_path`) nor correctly inline, this belongs inline in `## Context`.

**Scope — reasonable and well-bounded.** It is one ticket: re-home one file, keep composition working, update the one doc that names the path, migrate the packaged template. The Out of Scope explicitly fences off the two natural scope-creep traps (rewriting the content, and re-homing the broader `relay/*` contexts). Good discipline.

**Assumptions worth questioning before launch.**
- *"`docs/` is decided."* Fine, but note the principle tension: relay's design keeps everything legible inside one tree and the architecture SKILL documents `relay-os/context.md` as part of the OS surface. Moving it to `docs/` splits the "what relay operates on" boundary that `relay/codebase` draws so cleanly. The design should explicitly justify why the human-doc framing outweighs keeping all composed layers under `relay-os/` — not just assume `docs/` wins.
- *Back-compat / migration.* The ticket lists "direct read vs configurable pointer vs shim" as open, which is right, but the agent should be steered by `relay/project-stage` (which the principles SKILL says holds the "no backwards-compat needed" posture). That context is **not** attached and would materially change whether a shim is even worth designing. Consider attaching `relay/project-stage` or noting the stage posture inline.
- *Template migration affects `relay init`/update behavior.* Renaming/moving the packaged template (`src/relay/resources/templates/relay-os/context.md`) may touch the seeding/update path and `example/` fixtures; the design step should confirm what reads that template, not just move the file.

**Bottom line:** Launch-ready after two small fixes — correct the `config.py` → `paths.py` reference (and mention the `__all__` export at paths.py:120), and decide whether to attach `relay/project-stage` so the shim-vs-direct-read question is answered against the project's actual back-compat posture. The architecture attachment is arguably redundant with the inline note but is low-cost to keep.

### Disposition of evaluator findings
- ✅ `config.py` → `paths.py` corrected (paths.py:84, `__all__` at :120 noted inline).
- ✅ `relay/project-stage` attached; the "no backwards-compat hacks" posture now steers the shim question inline.
- ✅ Template/seeding + `example/` fixture caveat added inline.
- ✅ Architecture-vs-docs boundary tension added as an explicit "resolve, don't assume" note.
- Kept `relay/architecture` attached (low-cost; gives the design agent the full composition model).
