---
slug: document-the-ticket-blackboard-writer-s-contract
title: Document the ticket-blackboard writer's contract
status: active
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
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
    skills: []
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

The contract for *writing* to a ticket blackboard is implemented in `src/coga/` and stated in
scattered pieces across the contexts, but it is not written down anywhere a writer will find it.
Agents that needed a rule re-derived it, and two of them corrupted a ticket doing so.

Write the contract down as a new focused context, `coga/blackboard`. **This is a transcription
job, not a design job:** every rule below already has a determinate answer in shipped code or a
shipped context. Match them; do not invent. Where this ticket's prose and the source disagree,
the source wins.

1. **Append vs. rewrite** — when a pass appends, and when it may rewrite a section in place.
   Generalize from the three existing conventions rather than inventing a fourth (see `## Context`).
2. **The fence is a boundary.** How the fence is located, what may edit the region above it (per
   the base prompt: the body sections and `contexts:`, nothing else), and that no edit may match
   or operate across it. Transcribe the exact semantics from `src/coga/taskfile.py`.
3. **Concurrent writers** — a launched agent versus a shipped command or sweep writer.
   Cross-checkout reconciliation is **out of scope**; see `## Context`.
4. **Rewritten sections.** What happens to content a later pass replaces.

Then add a one-line cross-reference from `coga/architecture`, next to the fence definition, so a
reader who starts there finds the contract.

## Context

Found by Dream 2026-08-24, Phase 2 knowledge scan (shard-09), classified `gap`.

### Why this exists: two recorded corruptions, same shape

That Dream run hit the failure itself: an operator dedup of a duplicated recipe section matched a
mention of the same heading in the ticket *body* and truncated 258 lines of the body. It was
recoverable only because the recipe auto-commits.

A second instance, hit while authoring this ticket (2026-09-10): splitting the file on the first
occurrence of the fence *string* matched the mention of it inside this ticket's own prose, not the
fence line, and truncated the body. Recovered with `git checkout`.

Both are the same mistake — locating the fence (or a section) by substring rather than by an
exact anchored line match. `taskfile.py` already guards against it and its regex comment already
names this case; the gap is that neither writer knew the guard existed.

### The rules are already answered — transcribe, don't invent

An earlier draft of this ticket asserted that `coga/architecture` "defines the fence and stops
there." **That is wrong**, and the correction matters: an implementer who believes it will write a
context that contradicts shipped behavior. The real sources:

- **`src/coga/taskfile.py`** — the fence contract in code. `BLACKBOARD_FENCE`, the anchored
  `_FENCE_RE = ^<!-- coga:blackboard -->[ \t]*\r?$`, `fence_count()`, `split_body()`,
  `TaskFileError` on zero or multiple fences. Two details the contract must state exactly, because
  the obvious paraphrase gets both wrong: the fence line **tolerates trailing spaces/tabs and a
  CRLF carriage return** (it is not "a line equal to the fence and nothing else"), and
  `split_body(blackboard_required=False)` exists because **bootstrap tickets legitimately carry no
  fence** — so "zero matches is an error" is true for task tickets only.
- **`coga/contexts/coga/architecture/SKILL.md:920-950`** — the concurrency policy, in full. There
  is deliberately **no ownership mutex**: "The failure mode of two divergent workers (two
  blackboard edits, two PR branches) is visible and recoverable in git; the cost of a hard
  ownership mutex (stale lock state, `--force` flags, orphan-lock cleanup) is not." A narrow
  **state admission/publication barrier** does exist, and "Shipped blackboard writers use the same
  read/transform/compare/write boundary." That passage, not this ticket, is the answer to rule 3;
  the new context should point at it rather than restate it.
- **`src/coga/blackboard.py`** — that barrier in code. `update_blackboard_under_barrier` holds
  `git.state_publication_barrier` and compare-and-swaps on `expected_bytes`, raising rather than
  overwriting. Also `PRELAUNCH_AUTHORING_HEADINGS`, `_is_stock_blackboard`, and
  `append_to_section_text` — the shipped answer to "append into a named section."
- **`coga/contexts/coga/patterns/SKILL.md:83`** ("Durability and concurrency") — atomic
  replacement buys **crash-safety, not a lock**; correctness comes from shape. The complement to
  the barrier for rule 3.

### The three conventions rules 1 and 4 must generalize

Do not invent a fourth. These already exist and must not be contradicted:

- **Rewrite in place** — `coga/contexts/dev/code/SKILL.md:130`, the `## Dev` section with
  machine-readable `branch:` / `worktree:` / `pr:` lines.
- **Append oldest-to-newest, never delete** — `dev/code:242`, `## Superseded designs` and its
  dated-entry archive for replaced content.
- **Append before launch, then reset at activation** — the pre-launch authoring regime in
  `bootstrap/skills/bootstrap/ticket/SKILL.md:375-393` and `PRELAUNCH_AUTHORING_HEADINGS` in
  `blackboard.py`: `## Evaluator review`, `## Ticket authoring notes`, and `## Proposals` are
  folded into the body and cleared, while blockers, dev notes, and superseded designs survive.

Two constraints that shape rule 1: `architecture:878-899` — the blackboard is the *only* region
composed into the next prompt, so it must not accumulate without bound, while the log is never
composed and may. And `architecture:125` — the audit line lives in the union-merged log precisely
so "a co-writer rewriting a region of a template's blackboard cannot destroy an appended line."

Also consistent with, and not to be contradicted: `coga/recurring/SKILL.md:20` (a recurring
template's blackboard **persists** across every run and holds last-run state) and
`coga/period-task/SKILL.md:17,26` (a period task's own blackboard **disappears** at Dream's retro
cleanup, while its parent template's persists).

Line numbers into files under active edit will rot; each cite above carries its sentence so the
fact survives the drift.

### Out of scope

- **Cross-checkout reconciliation.** Rule 3 covers a launched agent versus a command/sweep writer
  only. Two checkouts diverging is the live subject of
  `detect-stranded-ticket-writes-across-checkouts` (`in_progress`, step 3 `review-design`);
  writing a policy here would collide with a design still in flight. Name the deferral in the
  context and point at that slug.
- **Changing any writer's behavior**, and **adding validation** for the rules. This ticket writes
  the contract down; enforcing it is a separate ticket.

### Packaging twins

Shipped Coga contexts are twinned, so both copies move in the same PR:
`src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md` for the new
context, and the matching twin for the `coga/architecture` edit.

**The new file's twin is not enforced.** `tests/test_packaging.py` walks the *packaged* tree and
pairs a file only when its live counterpart already exists — so creating only the live context and
forgetting the packaged copy fails nothing, and `EXPECTED_BOOTSTRAP_RESOURCES` is hand-maintained
and won't list it either. The `coga/architecture` edit *is* enforced (its twin exists, so a
one-sided edit fails loudly). Create both copies of the new file deliberately.

### Why a new context, and why `contexts:` is empty

Placement is a new context, not an extension of `coga/architecture` — architecture is the largest
context in the repo (~1,266 lines) and a broad orientation context the authoring rules discourage
attaching, whereas a small focused context can be attached per-ticket cheaply. `dev/code` also
closes with "Extend in a separate context if broader blackboard conventions need a home," which
permits this placement (it does not name this scope specifically). The leaf name `coga/blackboard`
is a suggestion; it collides with nothing (`src/coga/blackboard.py` is a different namespace).

`contexts:` is empty on purpose. Every file cited above is one the implementer opens and reads
directly, so composing them would pay their full size on every step to inline what the agent
already has. `coga/architecture` alone would be paid on all four steps.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
