---
slug: ticket-must-merge-blackblaord
title: ticket must merge blackblaord
status: draft
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - coga/codebase
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

The `bootstrap/ticket` flow writes authoring notes into a draft's blackboard
(`## Evaluator review`, `## Proposals`, `## Ticket authoring notes`) but nothing
clears them, so drafts are handed back carrying that cruft — and `coga mark
active` then *refuses* to activate until it's synthesized. Two changes:

1. **Bootstrap synthesizes, then clears its own blackboard.** As its **final
   action, after** the human has confirmed the step-7 summary, make the
   `bootstrap/ticket` skill **fold the evaluator review (and any other authoring
   notes) into the ticket body** — synthesize the durable substance into
   `## Context` (or an appropriate body section) — and **then** reset the
   blackboard to the stock placeholder. Nothing is lost: the review survives in
   the body (and the human edits from there), not only in git history. Update
   the step-7 summary line accordingly — it must no longer point at a
   `## Evaluator review` blackboard section that no longer exists.
2. **`validate.py` flags a non-empty blackboard.** Add a `coga validate` finding
   that surfaces a draft whose blackboard still holds prelaunch authoring notes.
   **Flag only** — no `--fix` mutation; it just makes the condition visible
   outside the `mark active` boundary. **Critical:** gate the finding to
   `status == "draft"` only. `prelaunch_blackboard_synthesis_reason` is
   status-agnostic, so reusing it unguarded would false-flag nearly every
   active/in_progress ticket (working blackboards routinely carry headings or
   >600 chars). Honor the existing `## Production notes` opt-out the helper
   already respects.

## Context

- **Blackboard helpers** live in `src/coga/blackboard.py`:
  `render_blackboard()` (stock template from `src/coga/resources/blackboard.md`),
  `_is_stock_blackboard()`, and `prelaunch_blackboard_synthesis_reason()` /
  `_text()` — the heuristic that decides whether a draft blackboard still holds
  authoring content (the `## Evaluator review` / `## Proposals` /
  `## Ticket authoring notes` headings, or >600 chars of non-placeholder text,
  unless a `## Production notes` section marks it intentional). "Empty" means
  reset to the stock placeholder, which `_is_stock_blackboard` treats as clean —
  not literally zero bytes.
- **Existing enforcement:** `src/coga/mark.py:240`
  `_refuse_unsynthesized_draft_blackboard()` calls that helper at the
  draft→active boundary and raises `BlackboardNeedsSynthesis`. The new validate
  check should **reuse the same helper** (single source of truth) rather than
  reimplement the heuristic. Do **not** change the mark.py refusal — validate is
  additive.
- **The skill to edit** is `bootstrap/ticket`. Two copies must stay in sync
  (see CLAUDE.md): the live repo copy
  `coga/bootstrap/skills/bootstrap/ticket/SKILL.md` and the packaged copy
  `src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md`.
  The relevant region is step 6 ("Run the evaluator review") through step 7
  ("Show the summary…"); the clear happens after the human confirms. **Note:
  the two copies already differ on disk today** (`diff -q` reports them
  non-identical) — diff and reconcile both deliberately before editing, don't
  assume they start in lockstep.
- **Tests:** `tests/test_validate.py` (new finding), `tests/test_mark.py`
  (existing refusal must stay intact), `tests/test_blackboard.py` (helper).
- **validate finding infra:** `src/coga/validate.py` already emits blackboard
  findings (e.g. `kind="large-blackboard"` at line 318) and has a `--fix` path;
  add the new finding as flag-only, consistent with the size-warning finding.
- **Resolved design decision (fold-then-clear):** the skill currently keeps the
  evaluator review in the blackboard so the human can re-read it. The decision
  for this ticket is to **synthesize the review into the ticket body before
  clearing** (not accept git-only retention, not skip the clear). So the
  ordering is: human confirms step-7 summary → skill folds review substance into
  `## Context`/body → skill resets blackboard to stock → human then edits the
  body as desired. The synthesis should be a faithful fold, not a verbatim dump
  of the whole review. Note this partly neuters the `mark.py` synthesis refusal
  for the bootstrap path (the draft now hands back already-synthesized) — that
  is intended; leave the mark.py backstop in place for non-bootstrap tickets.

**Out of scope:** changing mark.py's refusal; adding `--fix` auto-clear to
validate; the deferred "every ticket resets its blackboard at `done`" idea
(this ticket is bootstrap-flow-only cleanup).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

**Evaluator review (cold read)**

**Overall:** This is an unusually well-specified draft. The `## Description` states the problem and two concrete changes crisply, and the `## Context` block does the heavy lifting a picked-up agent needs: exact file/symbol pointers (`render_blackboard`, `_is_stock_blackboard`, `prelaunch_blackboard_synthesis_reason`, `mark.py:240`, `validate.py:318`), the "reuse the same helper" instruction, the two-copies-in-sync note, and a clear out-of-scope fence. An agent with no prior context could start. The items below are refinements, not blockers.

**Workflow fit — good.** `code/with-review` matches: the work is a real source change (`validate.py`) plus prompt/skill edits, shipped via PR, and the `## Context` explicitly names a design tension that wants human judgment. No mismatch. (The bulk of the diff is markdown/prompt rather than "code," but with-review still fits.)

**Contexts — appropriate.** `coga/codebase` is the right single attachment for a change spanning source layout + tests, and — importantly — the ticket already followed the "copy the specific fact into `## Context`" rule rather than leaning on breadth: the blackboard/mark/validate specifics are inlined. Nothing critical is missing. One gap: the ticket never names the test surface. `code/with-review` will expect tests, so pointing at `tests/test_validate.py` / `tests/test_mark.py` / `tests/test_blackboard.py` (whichever exist) would save the agent a search.

**Scope — reasonable, single ticket.** Skill edit (×2 copies) + one flag-only validate finding + tests. The deferred "every ticket resets at done" idea is correctly pushed out of scope.

**Assumptions to question before launch:**

1. **The `mark active` "refuses until synthesized" claim is accurate — but narrower than stated.** `_refuse_unsynthesized_draft_blackboard` fires *only* at the `draft → active` boundary (`if prior_status != "draft": return`). So the refusal only guards a draft's first activation, not later transitions. The description reads as if it's a general gate; it isn't. Fine for this ticket, but the implementer should know the scope.

2. **The new validate finding MUST be status-gated to `draft` — the ticket implies this but doesn't make it a hard requirement.** `prelaunch_blackboard_synthesis_reason` is status-agnostic: it flags any non-stock blackboard carrying authoring headings *or* >600 chars of non-placeholder text. Active/in_progress/paused tickets have working blackboards (blockers, notes, running commentary) that will routinely exceed 600 chars or carry headings — so a naive reuse of the helper in `_check_one_task` would false-flag nearly every live ticket. The finding has to be scoped to `ticket.status == "draft"` (and honor the `## Production notes` opt-out the helper already respects). This is the single most important precision the ticket underspecifies; call it out explicitly rather than relying on "surfaces a draft whose blackboard…".

3. **The bootstrap auto-clear collides with the step-7 summary, and this is left undecided.** Step 7 prints `Evaluator review: see the ticket.md blackboard region ## Evaluator review`, and the stated reason the review lives in the blackboard is so the human can re-read it. If the skill wipes the blackboard to stock *as its final action after* confirmation, that pointer goes stale and the evaluator review survives only in git history. The ticket half-acknowledges this ("consider whether the review should be folded into the body first") but defers the decision to the reviewer. This is the crux and should be resolved *before* launch: either (a) fold the review into `## Context`/body before clearing, or (b) don't clear the review section, or (c) accept git-only retention and reword the step-7 summary line so it doesn't dangle. Shipping the clear without picking one produces a visibly broken summary.

4. **No hard contradiction with `mark.py`, but a philosophical one worth naming.** Clearing to stock makes `_is_stock_blackboard` true, so `prelaunch_blackboard_synthesis_reason` returns `None` and the refusal passes — the two mechanisms are complementary, not contradictory. However, the refusal exists to *force the human to synthesize authoring notes into the body before launch*; auto-wiping to stock discards those notes instead of synthesizing them. So the new behavior largely neuters the refusal's intent for the bootstrap path (it remains a backstop only for tickets authored outside bootstrap). That's a defensible design, but it's a behavior change to the correction loop and should be stated as such, not framed purely as "cleanup."

**One factual correction for the ticket:** the two skill copies do **not** currently match — `diff -q` reports the live copy and the packaged `src/coga/resources/templates/...` copy already differ on disk today. The agent should diff both before editing and reconcile deliberately, rather than assuming they start identical and editing them in lockstep.

**Cosmetic:** title/slug typo "blackblaord" (slug is baked, so live-with-it).
