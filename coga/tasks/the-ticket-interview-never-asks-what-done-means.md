---
slug: the-ticket-interview-never-asks-what-done-means
title: The ticket interview never asks what done means
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/design-then-implement
secrets: null
---

## Description

`bootstrap/ticket` never asks the filer what would count as done. The new-title
greeting is "What should it do, and why? I'll turn your answer into the ticket",
and the Step 3 question list runs Description → Context → Workflow → Contexts →
Assignee → extension fields. Nothing anywhere asks for a definition of done, so
tickets reach `implement` with intent but no agreed finish line.

Three separate efforts have asked for this independently and every one of them
parked before it landed, so the gap is still open in the shipped skill. This
ticket is the single owner of the question and supersedes both parked drafts
(see below). It has to settle two things and then implement the outcome:

1. **Does the interview ask, and how?** Wording, and where it fits inside the
   deliberate 4–6 question budget.
2. **Where does the answer land?** Prose inside `## Description`, or a
   first-class `## Acceptance Criteria` section that `coga validate` checks.

Question 1 was already answered once (yes, as prose). Question 2 is the part
that was deferred and never resolved. Do not treat question 1 as reopened
without a reason drawn from the prior art below.

**Two notes for the `design` step.** First, read the `compose.py` bullet under
"Prior art" *before* proposing an `## Acceptance Criteria` section, so
`review-design` is not asked to approve something that never reaches the
implementing agent. Second, this ticket dogfoods the problem: `code/design`
will write its spec into these very sections, and per that same bullet the
Acceptance Criteria / Proposed Shape / Out of Scope it writes will **not**
compose into the `implement` prompt. Carry anything the implementer must know
into `## Description` or `## Context` before bumping.

**Splitting is an expected outcome, not a failure.** If question 2 lands on a
validator check, that check — a first-ever body-prose rule, plus severity and
status policy, plus grandfathering ~134 tickets — is ticket-sized on its own.
The interview wording can ship without it. Recommend the split at
`review-design` rather than building both here.

## Context

### Prior decisions — this ticket is a rediscovery, not a new idea

- **`improve-prompt-for-relay-ticket`** (done 2026-07-22) ran this analysis and
  produced a ranked proposal on its blackboard. Verdict: *ask for "done" up
  front, and land it as a sentence in `## Description`, not a new section.* A
  formal `## Acceptance Criteria` section was ranked **P2 and deliberately
  deferred**. **The file was deleted in `ffb0a383` (2026-07-23) — it is not on
  disk.** Recover it before you start; it is the most load-bearing prior art
  here and it already contains ready-to-adapt prompt wording:

  ```
  git show ffb0a383^:coga/tasks/improve-prompt-for-relay-ticket.md
  ```

  In that blob: `### Ranked changes` at line 185, the P0 greeting wording at
  ~196 (*"What should it do, why now, and what would count as done?"*), and the
  explicit P2 deferral (*"Do not add a permanent `Acceptance Criteria` section
  yet"*) at ~319.
- **`v2/implement-accepted-ticket-interview-improvements`** (paused 2026-07-27,
  "Parked to v2 for the release") carries that verdict as change 1 of 6. Its
  `## Context` also says a formal Acceptance Criteria section is out of scope
  for it.
- **`v2/acceptance-criteria`** (zach, paused 2026-07-01) wants the section, the
  interview question, and a CLI flag (see the `--ac1/--ac2` constraint below).
- **Dream 2026-08-24**, Phase 2 knowledge scan (shard-12), classified this a
  `gap` and filed the present ticket, unaware of all three.

**This ticket supersedes `v2/acceptance-criteria` entirely, and change 1 of
`v2/implement-accepted-ticket-interview-improvements`.** Both have a note
pointing here. The other five changes in that ticket (context buckets,
evaluator severity rubric, thin-answer recovery, stale task-shape guidance,
conservative Step 4) stay with it and are out of scope here.

### Prior art that constrains the answer

- **`## Acceptance Criteria` already exists in this system.** The `code/design`
  skill writes a ticket body of Description / Acceptance Criteria / Proposed
  Shape / Out of Scope, and `code/design-then-implement`'s `review-design` gate
  is the owner reviewing exactly that. Any answer must say how an
  interview-authored section relates to the design step's — same section
  reused, or two authors fighting over one heading.
- **Most tickets never run `code/design`.** `code/with-review`,
  `code/with-self-review` and `direct/body` have no design step, so today a
  ticket only gets acceptance criteria if it happened to pick the one workflow
  that writes them.
- **Read this before proposing a section: `compose` drops it.**
  `src/coga/compose.py` extracts exactly two body sections into the launched
  prompt — `_extract_section(body_above, "Description")` (line ~280) and
  `_extract_section(body_above, "Context")` (line ~290) — plus the blackboard
  region. `_extract_section` (line ~378) stops at the next `##`, so **every
  other body section is silently dropped**. Confirmed empirically:
  `coga launch nightly-auto-drain-run-for-ready-tickets --prompt-report` lists
  only `task_description`, `task_context`, `blackboard`, while that ticket's
  body carries `## Acceptance Criteria`, `## Proposed Shape`, `## Out of Scope`,
  `## Design notes` and `## Decisions`. None of them reach the agent.

  Three consequences this ticket turns on:

  1. The asymmetry above is worse than "most workflows lack a design step" —
     even `code/design`'s acceptance criteria never reach the `implement`
     agent's prompt. Today they exist only for a human reading `ticket.md`.
  2. The section option is therefore **not** a text-only edge change. It needs
     a fourth ticket layer in `src/coga/compose.py` — a core change. Weigh it
     against the microkernel rule deliberately; don't discover it at
     `implement`.
  3. It is an independent argument for the prior verdict (a sentence inside
     `## Description`, which already composes). That verdict was reached
     without this fact; it survives it, and is strengthened by it.
- **`coga validate` has no body-prose checks today** — every check is
  frontmatter, refs, secrets, or workflow/step shape. The one precedent for
  reading the body region is `unsynthesized-draft-blackboard`
  (`src/coga/validate.py`, in `_check_one_task`): draft-only, error severity,
  reads the blackboard region. If an AC check is added, that is the model to
  follow, and adding it means the validator starts inspecting body prose for
  the first time — a real widening, not a one-line addition.

### Where the code is

- **Skill text: one file, one edit.** The single source is
  `src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md`.
  `coga/.agent-skills/bootstrap/ticket` is a **symlink** into it. An earlier
  version of this ticket called them an "identical pair" to keep in sync —
  that was wrong; there is nothing to sync. **Edits to `src/` are live — no
  reinstall needed.** The PATH `coga` is an editable install
  (`_editable_impl_coga.pth` → `/home/n/Code/claude/coga/src`), and
  `coga.__file__` resolves into `src/`. The `site-packages/coga/` directories
  are stale shadow copies; ignore them and never edit them.
- **`coga create` hardcodes the scaffold — the template is not the source.**
  `src/coga/create.py` (~line 226) writes
  `ticket_body = f"## Description\n\n{desc_body}\n\n## Context\n\n"` and
  never reads `_template/ticket.md`. Editing the template alone changes nothing
  about what `coga create` / `coga ticket` actually produce. Any new section
  needs `create.py` too.
- **Ticket template: a genuine twin pair, and separately maintained.**
  `coga/tasks/_template/ticket.md` and
  `src/coga/resources/templates/coga/tasks/_template/ticket.md` are two real
  files, currently byte-identical; the template is `coga init` seed material
  and a validator-checked artifact (`validate.py` ~1049). If a section is added,
  both must change (CLAUDE.md live/packaged sync rule) — *in addition to*
  `create.py`, not instead of it.
- **`code/design` is also a real twin pair.** `coga/skills/code/design/SKILL.md`
  and `src/coga/resources/templates/coga/bootstrap/skills/code/design/SKILL.md`
  are two separate identical files — unlike `bootstrap/ticket`, which is a
  symlink. If this ticket changes how the design step's section relates to an
  interview-authored one, that is two edits kept in sync, not one.
- **Neither twin pair is test-enforced — a half-edit will pass CI.**
  `tests/test_packaging.py::IDENTICAL_LIVE_PACKAGED_PAIRS` has 19 entries and
  includes **neither** `code/design/SKILL.md` nor `_template/ticket.md`. Diff
  each pair by hand before opening the PR. The open draft
  `live-and-packaged-twin-pairs-are-edited-together-b` covers this hole; if this
  ticket edits either pair, consider adding them to that tuple here rather than
  waiting.
- **Validator:** `src/coga/validate.py`.
- **Tests:** `tests/test_bootstrap_ticket_skill_template.py` already asserts
  properties of the shipped skill text — extend it rather than starting a new
  file. `tests/test_ticket.py` covers `coga ticket`.

### Constraints and traps

- **The 4–6 question interview budget is deliberate**, but it is written in
  exactly one place: `bootstrap/ticket` SKILL.md **line 12** ("Keep the
  interview short — 4–6 questions, not a survey"). Neither `docs/vision.md` nor
  `coga/contexts/coga/principles/SKILL.md` states it — don't go looking there
  and conclude it isn't real. The deleted proposal's "the interview can stay at
  five human-facing prompts" is the supporting reference. Fold "done" into an
  existing question; do not add a seventh.
- **Microkernel rule** (CLAUDE.md): skill and template text is the edge. The
  prose option stays entirely at the edge. The section option does **not** — it
  touches `compose.py`, `create.py`, both template copies, and possibly
  `validate.py`. That cost difference is a first-class input to the decision,
  not an implementation detail to be discovered later.
- **Grandfathering is the hard part of the validator option.** As of
  2026-09-01, **17 of 151** ticket files under `coga/tasks/` already have an
  `## Acceptance Criteria` section (`grep -rl '^## Acceptance Criteria'
  coga/tasks --include=*.md | wc -l`) — mostly tickets that ran `code/design`.
  So the section has real de-facto adoption, but ~89% of tickets lack it and an
  error-severity check would fail the repo on day one. Decide severity and which
  statuses it applies to. Also check whether those 17 existing sections share a
  shape the check could actually assert — if the design step's freeform criteria
  and an interview-authored version disagree, the check has no stable target.
  `coga validate --json` on this repo is the smoke test, but **do not expect
  zero**: the 2026-09-01 baseline is 28 issues / 144 ok (4 error
  `unsynthesized-draft-blackboard`; warns: 11 `unfrozen-workflow`, 6
  `stuck-in-progress`, 5 `unknown-assignee`, 2 `large-blackboard`). Compare
  counts before and after, don't chase a clean run.
- **Zach's `--ac1/--ac2` CLI flag**: decide explicitly in or out and say why.
  New CLI surface needs a stronger justification than a text change, and
  `coga create` currently writes only the scaffold.
- The repo is mid Relay→Coga rename; use Coga wording in anything you touch.
- Verify with `python -m pytest` and `coga validate --json`.

<!-- coga:blackboard -->

## Evaluator review

Cold review by an independent session, 2026-09-01. Verdicts below are against
the ticket *as submitted*; every `must-fix before launch` has since been applied
to the body and re-verified. Delivered in four parts; assembled verbatim.

### Verification of the ticket's factual claims

**Verified correct:**

- `coga/.agent-skills/bootstrap/ticket` **is** a symlink -> `../../../src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket`. One file, one edit — correct, and the ticket is right that the earlier "identical pair" framing was wrong.
- `coga/tasks/_template/ticket.md` and `src/coga/resources/templates/coga/tasks/_template/ticket.md` **are** two real files, byte-identical (`d28ce707...`, 1269 B each).
- `src/coga/validate.py` has **no** body-prose check other than `unsynthesized-draft-blackboard` (`_check_one_task`, ~line 447): draft-only (`if ticket.status == "draft" and fences == 1`), `severity="error"`, reads the blackboard region. The module docstring's check list confirms every other check is frontmatter/refs/workflow/shape. Accurate.
- `coga/skills/code/design/SKILL.md` writes Description / Acceptance Criteria / Proposed Shape / Out of Scope; `code/design-then-implement`'s `review-design` prose names exactly those four. Accurate.
- `code/with-review`, `code/with-self-review`, and `direct/body` have **no** design step. Accurate. (`coga/workflows/` has no live `code/` dir; the packaged bootstrap copies are the only ones — the ticket's parenthetical is fine.)
- `tests/test_bootstrap_ticket_skill_template.py` exists (7 tests) and asserts exact substrings of the shipped SKILL.md. `tests/test_ticket.py` exists (19 tests) and covers `coga ticket`. Extending the former is the right call.
- Skill text: greeting at line 81 is verbatim *"What should it do, and why? / I'll turn your answer into the ticket."*; Step 3's order is Description -> Context -> Workflow -> Contexts -> Assignee -> extension fields. `4-6 questions` is at SKILL.md line 12. Accurate.
- Sibling tickets: `coga/tasks/v2/acceptance-criteria.md` (owner zach, `paused`, log line 612 confirms paused 2026-07-01) and `coga/tasks/v2/implement-accepted-ticket-interview-improvements.md` (`paused`, log line 2999 confirms 2026-07-27 with the exact reason "Parked to v2 for the release"). **Both already carry the supersession notes the ticket claims.** Change 1 of 6 is the done-criteria change; changes 2-6 are correctly described as out of scope.
- `improve-prompt-for-relay-ticket`: done 2026-07-22 (log 2825-2827), and its blackboard's "Ranked changes" section says exactly what this ticket claims — P0 *"Your `<slug>` ticket has been created (draft). What should it do, why now, and what would count as done?"*, land it as a sentence in `## Description` not a new section; and a separate *"P2 — Do not add a permanent `Acceptance Criteria` section yet."* Accurate.
- `coga create` writes only the scaffold (`src/coga/create.py:226`), no AC surface. Accurate.
- Repo is mid Relay->Coga rename: yes, tickets and log still carry `relay` slugs.

### Factual problems

**1. `improve-prompt-for-relay-ticket` no longer exists on disk — the ticket sends the implementer to a deleted file. `must-fix before launch`**
The ticket says twice "read the 'Ranked changes' section of that ticket's blackboard", but the file was deleted in `ffb0a383` (2026-07-23). `ls coga/tasks/improve-prompt-for-relay-ticket*` -> no such file. It is recoverable, but only if you know to look:

```
git show ffb0a383^:coga/tasks/improve-prompt-for-relay-ticket.md
```

The ranked proposal is at lines 185-330 of that blob (P0 wording ~185-207, the P2 deferral ~319-327, the human's acceptance at ~377). Put that command in the ticket. Without it a cold agent hits a dead reference on the single most load-bearing piece of prior art, and will most likely re-derive question 1 from scratch — the exact thing the Description forbids.

**2. "Every existing ticket under `coga/tasks/` lacks an `## Acceptance Criteria` section" is FALSE. `must-fix before launch`**
17 of 151 ticket files already have one (`grep -rl '^## Acceptance Criteria' coga/tasks/`) — written by past `code/design` runs, e.g. `nightly-auto-drain-run-for-ready-tickets.md`, `retire-never-removes-a-worktree-that-ran-the-tests.md`, and four under `v2/cleanup-core-commands/`. The directional point survives (a repo-wide error check would still fail ~134 tickets on day one), but the stated fact is wrong, and those 17 are useful prior art: they show what the design step actually produces, which is the best available evidence for what an interview-authored section should look like.

**3. Missing, and decisive for question 2: `compose` never puts an `## Acceptance Criteria` section into the launched prompt. `must-fix before launch`**
The biggest gap in the ticket. `src/coga/compose.py` (step 6, ~line 273) extracts **only** `## Description` and `## Context` from the body, plus the blackboard region; `_extract_section` (line 378) stops at the next `##`, so every other section is silently dropped. Verified empirically — `coga launch nightly-auto-drain-run-for-ready-tickets --prompt-report` lists only `task_description`, `task_context`, `blackboard`, while that ticket's body carries `## Acceptance Criteria` (71 lines), `## Proposed Shape` and `## Out of Scope`. None of them reach the agent.

Consequences the ticket needs to absorb:

- The asymmetry it cites is worse than stated. It isn't just that non-design workflows lack acceptance criteria — even the design workflow's criteria never reach the `implement` agent's prompt. They exist only for a human reading `ticket.md`.
- The "section" option is therefore **not** a text-only edge change: it requires a fourth ticket layer in `src/coga/compose.py`, a core change the ticket's own microkernel constraint ("only reach into `src/coga/` if the validator check genuinely needs Python logic") doesn't anticipate.
- It is an independent argument for the prior verdict (a sentence inside `## Description`), which the ticket currently presents as merely "already answered once".

Without this in `## Context`, the design step will very likely propose a section, get it approved at `review-design`, and only discover at `implement` that the section is inert.

**4. The `_template/ticket.md` twin pair is not where new ticket bodies come from. `must-fix before launch`**
`src/coga/create.py:226` hardcodes the scaffold (`ticket_body = f"## Description\n\n{desc_body}\n\n## Context\n\n"`); `create.py` never reads `_template/ticket.md` (grep confirms). The template is `coga init` seed material plus a validator-checked artifact (`validate.py` ~1049). So "if a section is added to the template, both must change" is true but incomplete — an implementer who edits both template copies and stops has changed nothing about what `coga create` / `coga ticket` actually produce. Name `src/coga/create.py` in "Where the code is".

**5. The `4-6 question budget` citation to `docs/vision.md` and "Coga principles" is unsupported. `nice-to-have`**
Neither `docs/vision.md` nor `coga/contexts/coga/principles/SKILL.md` contains `4-6` or any interview budget; vision.md line 177 only says the authoring skill "asks clarifying questions". The budget lives in exactly one place: SKILL.md line 12. The constraint is real and worth honoring, but citing two sources that don't say it invites a design agent to check, fail to find it, and discount it. Cite SKILL.md line 12; the deleted proposal's own "the interview can stay at five human-facing prompts" is the better supporting reference.

**6. `coga/skills/code/design/SKILL.md` is itself an unenforced live/packaged twin. `must-fix before launch`**
It exists both live and under `src/coga/resources/templates/coga/bootstrap/skills/code/design/` (identical today). The ticket requires deciding how an interview-authored AC section relates to the design step's, so touching this skill is a likely outcome — yet "Where the code is" reads as exhaustive and omits it. Worse: neither this pair nor the `_template/ticket.md` pair is in `tests/test_packaging.py::IDENTICAL_LIVE_PACKAGED_PAIRS` (25 pairs, I checked the full list), so tests will not catch a half-edit on either. `coga/tasks/live-and-packaged-twin-pairs-are-edited-together-b.md` is an open draft about exactly this hole — worth a one-line cross-reference.

**7. The install question is answerable now — answer it instead of delegating it. `nice-to-have`**
Both `.venv/bin/coga` and the PATH `coga` (`~/.local/share/uv/tools/coga/`) are editable installs pointing at `/home/n/Code/claude/coga/src`; `coga.__file__` resolves into `src/`, as does `packaged_template_path(...)`. Edits to `src/` are live, no reinstall needed; the `site-packages/coga/` dirs are stale shadow copies and inert. Swapping the instruction for the answer removes a detour and shortens `## Context`.

**8. `coga validate --json` is not clean today. `nice-to-have`**
Baseline: 28 issues / 144 ok — 4 x `unsynthesized-draft-blackboard` (error), 11 x `unfrozen-workflow`, 6 x `stuck-in-progress`, 5 x `unknown-assignee`, 2 x `large-blackboard` (all warn). "Run before and after" is right, but say *compare counts*; don't expect zero.

### Assessment

**1. Description clear enough to start cold?** Yes, unusually so. The two-question framing is crisp and "don't reopen question 1 without a reason drawn from prior art" is the right guard against a fourth re-derivation. The only blocker to a genuine cold start is finding 1 — the prior art it points at isn't on disk.

**2. Workflow fit (`code/design-then-implement`).** Good fit: the centre of gravity is an unresolved design decision needing an owner call, and `review-design` is exactly that gate. Correct escalation from the sibling's `code/with-review`, which assumed the decision was made. `nice-to-have`: tell the design step to check `compose.py` before proposing a section, so `review-design` isn't approving something inert. `question for human`: the design step will write `## Acceptance Criteria` into this very ticket — harmless dogfood, but per finding 3 those ACs won't reach the implement agent either, so add one line saying to carry them into `## Description` before bumping.

**3. Contexts (`contexts: []`, facts inlined).** Right call. `codebase` and `architecture` are large orientation contexts and the ticket already extracts the sentences it needs; the facts it depends on (symlink vs twin pair, validator precedent, design skill headings) aren't in any context body — they're properties of files. One exception: finding 3's compose behavior is a genuine architectural fact, but it's one paragraph — inline it with the `compose.py:273` / `:378` pointers. Do not attach `coga/architecture`; a live prompt report shows that costs ~14,800 tokens alone.

**4. Facts inlined that should be refs, or vice versa?** No inversions in either direction.

**5. Scope.** Reasonable, and consolidating rather than bundling — section-vs-sentence can't be settled in two tickets independently, and both siblings already carry the pointer notes. The real risk is the validator option: a first-ever body-prose check plus grandfathering ~134 tickets plus severity/status policy is ticket-sized on its own. `nice-to-have`: say up front that splitting the validator check into a sibling ticket is an expected outcome, not a failure — the interview wording can ship without it.

**6. Assumptions to question.**

`must-fix` — that a `## Acceptance Criteria` section would be read by anyone but a human; all of question 2 rests on it and it is currently false (finding 3).

`question for human` — **That question 1 is really settled.** The 2026-07-21 verdict was reached by an agent and accepted the same day, justified partly by "it does not yet prove every ticket needs a new top-level section." Three subsequent rediscoveries are arguably that proof. The ticket forbids reopening question 1 "without a reason drawn from the prior art" — finding 3 is exactly such a reason, and it happens to point the same way (sentence, not section). Worth the owner confirming the guard stands as written rather than having the design step quietly relitigate it.

`question for human` — **Zach's `--ac1/--ac2` flag.** Requiring an explicit in/out call is right, but zach owns the superseded `v2/acceptance-criteria` and nicktoper owns this one. If the answer is "out", someone should tell zach rather than leaving the decision buried in a paused ticket's `## Context`.

`nice-to-have` — **That the validator check can ship in this ticket.** The ticket treats it as one of two outcomes of a single decision, but a first-ever body-prose check plus grandfathering ~134 tickets plus severity/status policy is ticket-sized on its own. Say up front that splitting it to a sibling is an expected outcome, not a failure.

### Prompt size (current shape)

16.9 KiB / ~4313 tokens total is still small in absolute terms — a context-attaching ticket in this repo runs ~35k. But `task_context` at ~2168 tokens is now 50% of the prompt and **7.4x its own `## Description`**, and that ratio is the thing to watch, not the percentage: the agent's instructions are now a footnote to its briefing. I'd still call it earned — the ticket's whole purpose is to stop a fourth rediscovery, three of its four prior-art sources are parked or deleted, and finding 3 alone saves a design step from proposing something inert. Don't trim on principle.

Two specific cuts if you want it under ~45% without losing anything load-bearing: (a) the "Prior decisions" bullet for `v2/acceptance-criteria` can drop to one line — its substance is fully restated in the `--ac1/--ac2` constraint bullet lower down, so it's said twice; (b) the grandfathering paragraph now carries both the 17-existing-ACs correction and the severity/status/draft-only policy questions — keep the count and the "decide severity" sentence, cut the restatement of how `unsynthesized-draft-blackboard` works, since the validator bullet above it already gives the file, function and shape. Together ~200 tokens. What I would **not** cut: the `git show` recovery command, the compose fact, `create.py:226`, or the twin-pair list — those are the four things a cold agent cannot rediscover cheaply, and they are why this layer is large.

## Ticket authoring notes

Applied since the review: all six `must-fix` items, plus nice-to-haves 5, 7, 8,
the two workflow-fit suggestions from assessment Q2, the split-is-expected note
from Q5, and both trims (a) and (b).

Corrected against the reviewer where it was itself off: `IDENTICAL_LIVE_PACKAGED_PAIRS`
has **19** entries, not 25 — the claim that neither twin pair appears in it holds
(verified by parsing the tuple).

Two `question for human` items remain open for the owner — see the closing summary.
