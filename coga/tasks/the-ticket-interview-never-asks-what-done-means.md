---
slug: the-ticket-interview-never-asks-what-done-means
title: The ticket interview never asks what done means
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
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
    requires: branch
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
step: 2 (review-design)
---

## Description

`bootstrap/ticket` never asks the filer what would count as done. The new-title
greeting is "What should it do, and why? I'll turn your answer into the ticket",
and the Step 3 question list runs Description → Context → Workflow → Contexts →
Assignee → extension fields. Nothing anywhere asks for a definition of done, so
tickets reach `implement` with intent but no agreed finish line. Three separate
efforts asked for this independently and all three parked before it landed
(see `## Context`), so the gap is still open in the shipped skill.

### The decision (design step, 2026-09-02)

Both open questions were re-opened with the owner's permission and both land on
the **July verdict, confirmed with new facts**. No fact discovered since July
argues the other way.

**Q1 — does the interview ask, and how? Yes, folded into the existing first
substantive question.** The new-title greeting and Step 3 question 1 both grow
from "what and why" to "what, why now, and what would count as done". This adds
no seventh question: the interview stays at the same number of human-facing
prompts, inside the deliberate 4–6 budget on SKILL.md line 12. The three
independent rediscoveries are the proof that the interview *should ask* — that
is exactly what they all agreed on.

**Q2 — where does the answer land? As prose inside `## Description`, not a new
`## Acceptance Criteria` section, and with no `coga validate` check.** Three
verified facts, none of which were available in July, all push the same way:

1. **A section would never reach the implementer.** `src/coga/compose.py`
   composes exactly `## Description`, `## Context`, and the blackboard. Every
   other heading is silently dropped. An interview-authored
   `## Acceptance Criteria` would be invisible to the agent that has to satisfy
   it. Making it visible means a fourth ticket layer in `compose.py` — a core
   change — so the section option is not the cheap option. It costs
   `compose.py` + `create.py` + both `_template/ticket.md` copies +
   `validate.py`; prose costs skill text alone and stays entirely at the edge.
2. **A validator check has no stable target.** The 17 of 162 ticket files that
   already carry `## Acceptance Criteria` are `code/design` output: long
   `- [ ]` checklists of implementation-level assertions. A one-line answer
   from a human at interview time is a different artifact in a different
   register. A check strict enough to be useful would reject the interview's
   own output; one loose enough to accept both asserts only that a heading
   exists. Plus ~89% of the corpus lacks the section, so an error-severity
   check fails the repo on day one.
3. **The `--ac1/--ac2` flag is out.** `coga create` takes only a title and
   `--workflow` — it has no `--description` flag at all. Acceptance-criteria
   flags would be the only body-prose input on a command that cannot accept a
   body. The interview is the right place to elicit done criteria, and it is
   conversational. (nicktoper owns `v2/acceptance-criteria` as of 2026-09-01,
   so this call is his alone; it is recorded here, not there.)

**How this relates to `code/design`.** `code/design` stays the *sole* author of
`## Acceptance Criteria`. The interview's done sentence in `## Description` is
the seed that step expands and reconciles — not a competing version under the
same heading. Both skills get told this in their own text so the boundary is
durable rather than implicit.

### What to build

Four edge edits plus two test edits, all listed in `## Proposed Shape`. **The
exact replacement wording lives in `## Context` under "Exact replacement
wording", not in `## Proposed Shape`** — deliberately, because this ticket
dogfoods its own finding: `## Proposed Shape`, `## Acceptance Criteria`, and
`## Out of Scope` do not compose into the `implement` prompt, and `## Context`
does.

## Acceptance Criteria

- [ ] The shipped `bootstrap/ticket` SKILL.md new-title greeting asks what the
      ticket should do, why now, **and what would count as done**.
- [ ] The existing-ticket empty-body pivot line asks the same three things, so
      a batch-created draft opened for editing gets the same question.
- [ ] Step 3 question 1 asks for the done criteria, states that they are
      written as prose inside `## Description`, states that an
      `## Acceptance Criteria` section is not to be added by the interview, and
      gives the reason (only `## Description`, `## Context`, and the blackboard
      compose into a launch prompt).
- [ ] Step 3 question 1 tells the interviewer to ask one targeted follow-up
      when the answer leaves done implicit, rather than inventing a criterion.
- [ ] The Step 6 evaluator checklist includes a done question.
- [ ] The interview still asks no more questions than before — Step 3 has the
      same six numbered items, and the 4–6 budget line is unchanged.
- [ ] `code/design` SKILL.md says it is the sole author of
      `## Acceptance Criteria` and treats an interview-authored done sentence
      in `## Description` as the seed to expand, and warns that the sections it
      writes do not compose into the `implement` prompt.
- [ ] `coga/tasks/_template/ticket.md` `## Description` placeholder asks for
      done, and no longer claims the agent does not read this body.
- [ ] No new `## Acceptance Criteria` section is added to the template, to
      `create.py`, or to `compose.py`; `validate.py` is unchanged.
- [ ] Both twin pairs edited (`code/design/SKILL.md`, `_template/ticket.md`)
      are byte-identical between the live and packaged copies, and both are
      added to `tests/test_packaging.py::IDENTICAL_LIVE_PACKAGED_PAIRS`.
- [ ] `tests/test_bootstrap_ticket_skill_template.py` gains a test asserting
      the done wording in the greeting and in Step 3.
- [ ] `python -m pytest` passes.
- [ ] `coga validate --json` issue count is no worse than the 2026-09-01
      baseline of 28 issues / 144 ok.

## Proposed Shape

Exact replacement text is in `## Context` → "Exact replacement wording"
(that section composes into the implement prompt; this one does not).

1. **`src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md`**
   — one file, four edits (the `coga/.agent-skills/` path is a symlink into it;
   nothing to sync). New-title greeting (~line 81), existing-ticket pivot
   (~line 94), Step 3 item 1 (~line 164), Step 6 evaluator bullet list (~line
   293).
2. **`code/design` SKILL.md, twin pair** — `coga/skills/code/design/SKILL.md`
   and `src/coga/resources/templates/coga/bootstrap/skills/code/design/SKILL.md`.
   Extend the `## Acceptance Criteria` bullet in "Order of operations" step 3,
   and add one Gotcha about compose. Keep both copies byte-identical.
3. **`_template/ticket.md`, twin pair** — `coga/tasks/_template/ticket.md` and
   `src/coga/resources/templates/coga/tasks/_template/ticket.md`. Replace the
   `## Description` placeholder prose. Content is unchecked by `validate.py`
   (the ~line 1049 template check is for `recurring/`, not `tasks/_template/`);
   `tests/test_init.py` only asserts the file is copied.
4. **`tests/test_packaging.py`** — add both pairs from (2) and (3) to
   `IDENTICAL_LIVE_PACKAGED_PAIRS` (19 entries today; neither is present, so a
   half-edit passes CI right now).
5. **`tests/test_bootstrap_ticket_skill_template.py`** — extend, do not start a
   new file. Add `test_bootstrap_ticket_interview_asks_what_done_means`
   asserting the greeting phrase and the Step 3 done/no-section rule.

Order of work: 1 → 5 (red/green on the skill text), then 2 and 3 → 4, then the
full suite and `coga validate --json`.

## Out of Scope

- **Any `compose.py` change.** Making `## Acceptance Criteria` reach the
  implement prompt is a real gap but a separate ticket — see the follow-up
  recommendation on the blackboard.
- **Any `coga validate` body-prose check** for acceptance criteria, and the
  severity/status/grandfathering policy it would need. Deferred, and largely
  moot until compose reads the section at all.
- **`create.py`** — no scaffold change, so no new empty section on every draft.
- **`--ac1/--ac2` or any new CLI surface.** Decided out, reasons in
  `## Description`.
- **The other five changes in `v2/implement-accepted-ticket-interview-improvements`**
  (context buckets, evaluator severity rubric, thin-answer recovery, stale
  task-shape guidance, conservative Step 4). Adding a done bullet to the Step 6
  evaluator list is *not* the severity rubric; that stays parked.
- **Retro-fitting done criteria onto the 145 existing tickets without them.**
- **Resurrecting `eval/ticket-diagnostic`** — it no longer exists in the repo,
  so the July proposal's "aligns with its Done axis" argument is dead. The
  Step 6 evaluator list is where the done check goes instead.

## Context

### Prior decisions — this ticket is a rediscovery, not a new idea

- **`improve-prompt-for-relay-ticket`** (done 2026-07-22) ran this analysis and
  produced a ranked proposal on its blackboard. Verdict: *ask for "done" up
  front, and land it as a sentence in `## Description`, not a new section.* A
  formal `## Acceptance Criteria` section was ranked **P2 and deliberately
  deferred**. **The file was deleted in `ffb0a383` (2026-07-23) — it is not on
  disk.** Recovered at design time with:

  ```
  git show ffb0a383^:coga/tasks/improve-prompt-for-relay-ticket.md
  ```

  In that blob: `### Ranked changes` at line 185, the P0 greeting wording at
  ~196 (*"What should it do, why now, and what would count as done?"*), the
  explicit P2 deferral (*"Do not add a permanent `Acceptance Criteria` section
  yet"*) at ~319, and a "Final report" recording that the human accepted all
  P0/P1 changes and deferred P2.
- **`v2/implement-accepted-ticket-interview-improvements`** (paused 2026-07-27,
  "Parked to v2 for the release") carries that verdict as change 1 of 6. Its
  `## Context` also says a formal Acceptance Criteria section is out of scope
  for it.
- **`v2/acceptance-criteria`** (nicktoper as of 2026-09-01, paused) wants the
  section, the interview question, and a CLI flag.
- **Dream 2026-08-24**, Phase 2 knowledge scan (shard-12), classified this a
  `gap` and filed the present ticket, unaware of all three.

**This ticket supersedes `v2/acceptance-criteria` entirely, and change 1 of
`v2/implement-accepted-ticket-interview-improvements`.** Both have a note
pointing here. The other five changes in that ticket stay with it.

### Exact replacement wording

Apply these verbatim (adjust only surrounding whitespace/line wrapping).

**(a) `bootstrap/ticket` SKILL.md — new-title greeting (~line 81).** Replace:

> "Your `<slug>` ticket has been created (draft). What should it do, and why?
> I'll turn your answer into the ticket."

with:

> "Your `<slug>` ticket has been created (draft). What should it do, why now,
> and what would count as done? I'll turn your answer into the ticket."

**(b) Same file — existing-ticket empty-body pivot (~line 94).** Replace
`("…it's empty right now, so: what should it do, and why?")` with
`("…it's empty right now, so: what should it do, why now, and what would count as done?")`.

**(c) Same file — Step 3 item 1 (~line 164).** Replace:

```
1. **Description** — what needs to happen and why, in 2–4 sentences. This
   becomes the `## Description` body.
```

with:

```
1. **Description and done** — what needs to happen, why now, and the smallest
   observable result that means the ticket is finished, in 2–4 sentences. This
   becomes the `## Description` body. Write the done criteria as prose inside
   `## Description` — do **not** add an `## Acceptance Criteria` section.
   `code/design` is the only author of that section, and `coga launch` composes
   only `## Description`, `## Context`, and the blackboard into an agent's
   prompt, so anything written under another heading never reaches the agent
   who has to satisfy it. If the human's answer leaves done implicit, ask one
   targeted follow-up ("how will you know it worked?") rather than inventing a
   criterion.
```

**(d) Same file — Step 6 evaluator question list (~line 293).** Insert as the
second bullet, directly after "Is the description clear enough…":

```
- Is it clear what would count as done — could a reviewer tell whether the
  finished work satisfies the ticket?
```

**(e) `code/design` SKILL.md (both copies) — "Order of operations" step 3.**
Replace the `## Acceptance Criteria` bullet:

```
   - `## Acceptance Criteria` — a checklist an implementer and a
     reviewer can both verify objectively.
```

with:

```
   - `## Acceptance Criteria` — a checklist an implementer and a
     reviewer can both verify objectively. This step is the only
     author of that section. The ticket interview may already have put
     a done sentence in `## Description`; treat it as the seed to
     expand and reconcile, not a competing version to argue with.
```

**(f) `code/design` SKILL.md (both copies) — new bullet under `## Gotchas`:**

```
- `coga launch` composes only `## Description`, `## Context`, and the
  blackboard into a step's prompt. The other sections you write here
  are for the owner at `review-design` and for humans reading
  `ticket.md`; they do not reach the `implement` agent on their own.
  Carry anything the implementer must know into `## Description` or
  `## Context`.
```

**(g) `_template/ticket.md` (both copies) — `## Description` placeholder.**
Replace:

```
What needs to happen and why. The agent reads the composed prompt at
launch time, not this body — these sections exist to help humans
organize their thinking.
```

with:

```
What needs to happen, why now, and what would count as done. `coga
launch` composes this section, `## Context`, and the blackboard into
the agent's prompt; other sections are for humans reading this file.
```

(The old sentence is not just stale here — it flatly contradicts the reason
this ticket keeps done criteria in `## Description`.)

### Verified at design time (2026-09-02)

Everything below was re-checked against the working tree, not taken on trust.

- **`compose.py` composes exactly three ticket layers.** `_extract_section`
  (line ~378) matches `^##\s+(.+?)$` and stops at the next `##`; only
  `"Description"` (line ~280) and `"Context"` (line ~290) are extracted, plus
  the blackboard. Confirmed live:
  `coga launch nightly-auto-drain-run-for-ready-tickets --prompt-report` prints
  `task_description`, `task_context`, `blackboard` and nothing else, while that
  ticket's body carries `## Acceptance Criteria`, `## Proposed Shape`,
  `## Out of Scope`, `## Design notes`, `## Decisions`.
- **`coga create` has no `--description` flag.** `src/coga/commands/create.py`
  takes `title` and `--workflow` only; `src/coga/create.py` (~line 226) writes
  `f"## Description\n\n{desc_body}\n\n## Context\n\n"` and never reads
  `_template/ticket.md`.
- **17 of 162 ticket files carry `## Acceptance Criteria`** (was quoted as
  17/151; the corpus grew). Sampled `review-slack-channels.md`,
  `secrets-instructions-correction.md`, and
  `v2/cleanup-core-commands/launch-decomposition.md`: all are long `- [ ]`
  checklists of implementation-level assertions, i.e. `code/design` output.
- **Twin pairs are currently byte-identical**, both `code/design/SKILL.md` and
  `_template/ticket.md`, and **neither is in
  `tests/test_packaging.py::IDENTICAL_LIVE_PACKAGED_PAIRS`** (19 entries, the
  assertion loop is at ~line 210). A half-edit passes CI today.
- **`bootstrap/ticket` is a single file.** `coga/.agent-skills/bootstrap/ticket`
  symlinks into `src/`; `src/` is an editable install, so edits are live.
  Ignore the stale `site-packages/coga/` shadow copies.
- **`coga validate` has one body-region precedent only**:
  `unsynthesized-draft-blackboard` in `_check_one_task`
  (`src/coga/validate.py` ~line 454), draft-only, error severity, reads the
  blackboard. The `~line 1049` template check found in earlier notes governs
  `recurring/` templates, **not** `coga/tasks/_template/` — so editing the
  ticket template's prose trips no validator.
- **`eval/ticket-diagnostic` no longer exists** in either the live or packaged
  skills tree.
- **The 4–6 question budget is stated in exactly one place**: `bootstrap/ticket`
  SKILL.md line 12. Not in `docs/vision.md`, not in `coga/principles`.

### Constraints and traps

- **Microkernel rule** (CLAUDE.md): every edit in this ticket is edge — skill
  text, template text, tests. Nothing enters `src/coga/` core. If an
  implementation idea starts pulling in `compose.py`, `create.py`, or
  `validate.py`, it has left this ticket's scope.
- **Neither twin pair is test-enforced until step 4 of the Proposed Shape
  lands** — diff each pair by hand before opening the PR. The open draft
  `live-and-packaged-twin-pairs-are-edited-together-b` covers the general hole.
- **Do not expect a clean `coga validate --json`.** The 2026-09-01 baseline is
  28 issues / 144 ok (4 error `unsynthesized-draft-blackboard`; warns: 11
  `unfrozen-workflow`, 6 `stuck-in-progress`, 5 `unknown-assignee`, 2
  `large-blackboard`). Compare counts before and after; don't chase zero.
- The repo is mid Relay→Coga rename; use Coga wording in anything you touch.
- Verify with `python -m pytest` and `coga validate --json`.

<!-- coga:blackboard -->

## Design notes (2026-09-02)

Design step complete. Spec is in the body above. Summary of how the two open
questions were settled:

- **Q1 (does the interview ask): yes — confirmed, same as July.** Folded into
  the existing first question and the greeting, so the question count does not
  change and the 4–6 budget (SKILL.md line 12) is untouched. The three
  independent rediscoveries are exactly the evidence for this half.
- **Q2 (prose vs. section + validator): prose in `## Description` — confirmed,
  same as July, on evidence July did not have.**

**No fact reversed the July verdict.** Three new facts strengthened it:

1. `compose.py` composes only Description / Context / blackboard — verified in
   source and empirically via `--prompt-report`. An interview-authored
   `## Acceptance Criteria` would be invisible to the implementing agent, so
   the section option requires a core `compose.py` change and is the expensive
   option, not the tidy one.
2. `coga create` has no `--description` flag at all, which kills the
   `--ac1/--ac2` proposal on its own terms: acceptance-criteria flags would be
   the only body input on a command that takes no body.
3. The 17 existing `## Acceptance Criteria` sections are uniformly `code/design`
   output — long `- [ ]` implementation checklists. An interview answer is a
   different artifact, so a validator check has no single shape to assert.

The rediscovery-count argument ("three rediscoveries are the proof a section is
needed") was weighed and rejected on a distinction: all three efforts agreed
the *interview should ask*; only one wanted a *section*. The rediscoveries
prove Q1, not Q2.

## Open Questions

None blocking implementation. Two judgement calls made rather than deferred,
flagged here so `review-design` can overrule cheaply:

1. **Two extra files pulled in beyond the interview skill.** The spec also
   edits `code/design/SKILL.md` (the section-ownership boundary) and
   `_template/ticket.md` (its `## Description` placeholder still says "the
   agent reads the composed prompt at launch time, not this body", which is
   false for Description and contradicts this whole decision). Both are
   one-paragraph edits and both are the durable home for the explanation, per
   CLAUDE.md's "don't leave the durable explanation only in chat". If the owner
   wants the tightest possible diff, dropping either leaves the interview
   change working but the boundary implicit.
2. **The Step 6 evaluator bullet.** One added question, not the severity rubric
   from the parked ticket. Cheap and directly in service of this ticket; drop
   it if the owner would rather all evaluator changes move together.

## Recommended follow-ups (do not build here)

- **`compose` should carry `## Acceptance Criteria` into the `implement`
  prompt.** This is the real gap behind the whole thread: even `code/design`'s
  acceptance criteria never reach the agent expected to satisfy them. That is a
  `compose.py` core change with a prompt-size effect on every launch, and it is
  ticket-sized. File it; this ticket's `code/design` Gotcha edit documents the
  current behavior in the meantime.
- **A `coga validate` acceptance-criteria check** stays deferred, and should
  stay deferred until the compose ticket above lands — until then it would
  enforce a section no agent ever reads. When revisited it needs its own
  severity decision, status scoping, and a grandfathering plan for the ~145
  tickets without the section.
- **Add `_template/ticket.md` and `code/design/SKILL.md` to
  `IDENTICAL_LIVE_PACKAGED_PAIRS`** — folded into this ticket rather than
  waiting for `live-and-packaged-twin-pairs-are-edited-together-b`, since this
  ticket edits both pairs.

**No split needed.** The ticket anticipated a split if Q2 landed on a validator
check; it did not, so the remaining scope is one small PR of edge text plus
tests.

## Note for the implement step

This ticket dogfoods its own finding: `## Acceptance Criteria`,
`## Proposed Shape`, and `## Out of Scope` above **will not compose** into the
implement prompt. Everything the implementer needs — including the verbatim
replacement wording — is deliberately in `## Description` and `## Context`,
which do compose. Read `## Context` → "Exact replacement wording".
