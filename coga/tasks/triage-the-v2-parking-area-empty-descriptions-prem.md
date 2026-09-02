---
slug: triage-the-v2-parking-area-empty-descriptions-prem
title: 'Triage the v2 parking area: empty descriptions, premise-dead drafts, permanently
  red validate'
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
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
step: 1 (implement)
---

## Description

The `coga/tasks/v2/` parking area needs a human triage pass. Dream 2026-08-24 found it mechanically;
the counts below are re-derived against `main` on 2026-09-02 and supersede the scan's own figures.

- **17 of the 81 tasks in `v2/` have an empty `## Description`** — and all 17 are title-only stubs:
  frontmatter, an empty `## Description`, an empty `## Context`, the placeholder blackboard, 328–714
  bytes total. The v2 README's premise check cannot be run on them because there is nothing to run it
  against. They need an owner interview, not an edit.
- **A premise-dead cohort of 8 drafts**, of which only 2 are confirmed dead on verified evidence and
  1 is demonstrably still alive. The cohort is broken out by evidence strength in `## Context`;
  cancelling any of them is a lifecycle write and human-gated.
- **The known-stale-surfaces table is incomplete.** Its `relay-os/… -> coga/…` rename mapping sends
  readers to `workflows/code/*` paths that exist only inside the package. Separately, 15 drafts carry
  a dead `script:` field — see `## Context` for why this may not warrant a table row at all.
- **`coga validate` is permanently red**, and all 4 errors in the repo come from this directory. A
  green validate is not achievable today, which quietly weakens the gate everywhere else.

Cancelling a premise-dead draft is a lifecycle change and human-only, which is why this is a ticket
and not a PR.

## Context

Found by Dream 2026-08-24, Phase 2 knowledge scan (shards 06, 09, 11, 12), classified `gap`.
Re-verified against `main` 2026-09-02, including an independent cold review whose corrections are
folded in below. **Where this section and the original Dream findings disagree, this section wins.**

**The contract for this directory is `coga/tasks/v2/README.md`.** Read it first. It defines the
two-question premise check, carries the known-stale-surfaces table this ticket amends, and records
the `decide-the-fate-of-two-premise-dead-v2-drafts-whos` precedent for cancelling a parked draft
with a recorded reason. Cancel spelling is `coga mark canceled v2/<slug> --message "<reason>"`.

### Counting `v2/` correctly

`coga status v2 --all` reports **81 tasks** (1 in_progress, 65 draft, 12 paused, 3 canceled). Do not
count with `ls coga/tasks/v2/*.md` — that glob returns 76, because it counts the
`cleanup-core-commands/` directory as one entry and misses its six children, all of which have real
Descriptions.

Exactly **17** drafts have an empty `## Description`. Two files that a naive glob also flags are
**directory indexes that must never receive a Description**: `coga/tasks/v2/README.md` and
`coga/tasks/v2/cleanup-core-commands/README.md`. The Dream scan's "18" was this artifact.

### The 17 stubs — interview, do not invent

Every one is title-only with no recoverable content; for `model-selector` and `add-subproject` the
entire informational payload is the slug. Titles include `docs-and-contt-block-should-be-merged`,
`remote-stale-command-line-toosl`, `generic-lib-to-use-e-g-patent-models`.

**Writing a Description inferred from the slug is forbidden.** That fabricates a record of what
someone wanted, which is the precise failure `coga/tasks/v2/README.md:15-19` exists to prevent.

The owner has chosen to be interviewed on each one. In the `implement` step, walk the owner through
all 17 — slug, title, and any repo evidence you found — and write only what they tell you. Where
they have no intent left for a stub, cancel it with their reason rather than leaving it empty.

### The premise-dead cohort — graded by evidence, not asserted

Do not treat the original 8 as a uniform "confirmed dead" list. It is not.

**Confirmed dead (evidence verified — cancel is correct):**
- `audit-rules-md-usage-across-relay-and-decide-wheth` — `rules.md` survives only as a stale-artifact
  fixture in a prune test (`tests/test_init.py:1379`); the "Global rules" compose layer it audits is
  gone (`grep rules src/coga/compose.py src/coga/paths.py` is empty).
- `document-workflow-less-concept-capture-drafts-as-s` — deliverable shipped at
  `coga/contexts/coga/architecture/SKILL.md:363-400`, which names the exact validator-nagging
  problem the draft was written about.

**Subject was never built, not deleted — this is NOT the README's premise test:**
- `autotrigger-ticket-type` — the evidence offered was "every cross-reference dead" (6 of 7 named
  slugs confirmed absent). But dead cross-references make a draft harder to *act on*; they do not
  make its subject gone. Recurring is alive (`src/coga/recurring_runner.py`, three workflows under
  `coga/workflows/`), so the proposed unification was never built. Re-adjudicate on the README's
  actual two questions.

**Cancel only if the surviving residue is named in the reason:**
- `skill-update-aborts-on-uncommitted-log-file` — the stated root cause is genuinely gone
  (`src/coga/commands/launch_script.py` and `run_script_mode` no longer exist). But its secondary
  finding is live: `_assert_no_unmerged_paths` (`src/coga/skill_manager.py:417`) still filters on
  `--diff-filter=U` only, so an ordinary dirty tracked file still walks past it into `_checkout`
  (line 488). A bare cancel silently drops a real bug.

**Asserted with no recorded evidence — re-derive before touching:**
- `dev-loop-git-hygiene`, `relay-design-repositories`, `split-context-to-doc-user-accessible-and-editable`
  were each given a one-clause reason with no pointer to where the settlement is recorded.
- `add-relay-skill-search-with-candidate-eval` was listed as settled and **is not**. `coga skill`
  exposes install / install-local / install-url / update / remove / status — there is no `search`.
  The subject was never built, the surfaces it names are still live, and `coga/log.md` records no
  decision. It passes both of the README's questions. **Do not cancel this one** absent new evidence.

**Guard:** a green `coga validate` is never a reason to cancel a draft. Two of the four errors sit on
`autotrigger-ticket-type` and `split-context-to-doc`, so ruling them dead is the cheapest path to a
green gate. Adjudicate each on the README's two questions alone and accept a still-red validate if
that is where the evidence lands.

### The `script:` field — correction

An earlier draft of this ticket claimed core "has no reader" for `script:`. **That is wrong.**
`src/coga/ticket.py:74-80` is a bounded migration that pops `script` when its value is `None`, and
all 15 occurrences are `script: null` — so they are already handled and self-heal on the next write
through core. Do not add a README row asserting the field is unhandled. Either omit the row, or write
it accurately: "`script:` — Gone; a bounded migration in `src/coga/ticket.py:74` strips `script: null`
on next write." Decide which with the owner; the honest answer may be no row.

The other table defect is real and unqualified: the `relay-os/… -> coga/…` row misleads for workflow
refs, because `coga/workflows/code/` does not exist. The `code/*` workflows resolve only from
`src/coga/resources/templates/coga/bootstrap/workflows/code/`.

### The two blackboard syntheses

`measure-relay-prompt-scope-and-agent-precision` (4,215-char blackboard) and
`use-worktree-when-starting-a-dev-task` keep the synthesis route; do **not** synthesize any draft you
cancel. "Synthesize" is defined in `coga/contexts/coga/architecture/SKILL.md` (~lines 720-730): fold
durable content from the blackboard up into the ticket body, or move deliberate launch notes under a
`## Production notes` heading, which the validator accepts as the alternative. Read that passage
before starting — it is not attached as a context because the file is 59 KB.

### Green validate is achievable

`unsynthesized-draft-blackboard` fires only on `status == "draft"` (`src/coga/validate.py:447`), so
cancelling or synthesizing each of the four clears it. Everything else `coga validate` prints is a
WARN, not an ERROR. But see the guard above: do not let this goal drive a cancel verdict.

### Human gate placement — known, accepted, and how to escalate

This ticket runs `code/with-review`, whose only human gate is the final `review` step. The owner
chose this deliberately. Two consequences the `implement` step must respect:

1. **Do not fire the 8 cancels unreviewed.** Present the per-draft verdict with evidence and get
   explicit confirmation first. Step 1 launched by the owner runs attended, so ask directly.
2. **If no human is reachable** (the supervisor auto-chains agent steps —
   `code/with-review.md:39,44`), the correct action is `coga block --task <slug> --reason "<the
   verdict table and the 17 stub questions>"`. Do **not** defer them to the `review` step: that step
   runs `code/address-pr-comments`, which is explicitly barred from advancing or closing a task
   (`code/with-review.md:134-135`). Prior art for this stalling: `coga/log.md:3794`.

### Where future `gap` findings go

The v2 README records that two drafts it cancelled as premise-dead "were themselves Dream `gap`
findings originally" — findings parked here decay. This ticket should decide where they go instead,
and that decision is durable routing policy, so it lands in a file, not in this ticket: write it into
`coga/tasks/v2/README.md` (the contract for what this directory accepts) and, if it changes Dream's
own behavior, the roadmap's "Deferred work" section. Confirm the target with the owner.

### Out of scope

Re-validating the premise of all 81 tasks. This ticket triages the 8-draft cohort, the 17 stubs, and
the 4 validate errors; the rest of the parking area stays as-is.

<!-- coga:blackboard -->

## Split into three tickets — 2026-09-02

This ticket was split and is to be canceled. The cold review below is the reason; its findings are
folded into the three children, not lost here.

- `correct-the-v2-known-stale-surfaces-table-and-rout` — README table + gap-finding routing + the 2
  blackboard syntheses. `code/with-review`. No lifecycle writes.
- `adjudicate-the-eight-premise-dead-v2-drafts` — the 8 verdicts. `code/design-then-implement`, so
  the owner gates the table before any cancel runs.
- `interview-the-owner-on-the-17-title-only-v2-stubs` — the stub interview.
  `code/design-then-implement`.


## Evaluator review

Independent cold read, 2026-09-02. Verbatim.

I read the ticket, the v2 README, the `code/with-review` workflow, and spot-checked the claims against `main`. Findings below, ordered within each point by how likely they are to make the launched agent do the wrong thing.

### 1. Description clarity — one blocking gap

**The "18 empty descriptions" half has no stated deliverable.** The Description states the *finding* — "18 of ~75 drafts have an empty `## Description`" — and never says what the agent should do about it. The only place a verb attaches is a parenthetical: "the file edits (empty descriptions, README table, the two blackboard syntheses)". "Do file edits to empty descriptions" is not a task; write them? cancel them? ask the owner?

That gap is load-bearing because of what those files actually contain. I checked all 17 (see #5): every one is a title-only stub — frontmatter, an empty `## Description`, an empty `## Context`, and the 77-byte placeholder blackboard. Total file size 328–714 bytes. There is **zero** material to write a description from except the slug. Titles include `docs-and-contt-block-should-be-merged`, `remote-stale-command-line-toosl`, `generic-lib-to-use-e-g-patent-models`. An agent told to "fix the empty descriptions" with no other instruction will infer the description from the title — which is precisely the failure the contract file it's told to read exists to prevent (`coga/tasks/v2/README.md:15-19`). Inventing a Description fabricates a record of what someone wanted at the time.

**The count is wrong, and the 18th item is a trap.** I count 17 files with an empty `## Description` under `coga/tasks/v2/*.md`. The 18th is `coga/tasks/v2/cleanup-core-commands/README.md` — a directory *index* whose first lines read "Directory index for the core-command cleanup tickets. Launch one of the child tickets below, not this file." It has no `## Description` by design and must not get one. Its six child tickets all have real Descriptions (420–1300 chars). An agent that trusts "18" will either burn time hunting a nonexistent 18th or write a Description into the index.

**"76 drafts" is also wrong.** `coga status v2 --all` reports 81 tasks (78 live, 3 canceled). 76 is what you get from `ls coga/tasks/v2 | wc -l` minus README — it counts the `cleanup-core-commands/` directory as one draft and ignores its six children. Same glob artifact that produced the 18.

### 2. Workflow fit — the mitigation is not adequate as written

**a) "the session is attended, so ask" contradicts the workflow's own documented behavior.** `code/with-review.md` states the supervisor "auto-chains across these agent boundaries… it only returns control to the human at the final `review` step." The implement step is not guaranteed attended. The mitigation should key off the actual launch mode (the workflow's own guidance is "ask the attending human, or `coga block` in a queue run") rather than asserting attendance.

**b) The fallback normalizes a half-done ticket.** "leave the cancels undone, land the mechanical half" — but there is no mechanical half. The empty-description work is 17 judgment calls, not edits. The fallback lands a README edit plus two syntheses and defers everything requiring judgment (8 cancels + 17 stub verdicts) to `review`.

**c) `review` can't absorb that.** Its skill is `code/address-pr-comments`, and the workflow file's `## review` section explicitly bounds an assisting agent: it "must not… run `coga bump` or `coga mark done`, or otherwise advance/close the task." Eight `coga mark canceled` calls are exactly that class of write. The escape hatch routes decisions into the one step contractually barred from making them. Add this repo's history of the post-PR gate stalling (`coga/log.md:3794`: a prior ticket blocked because four `code/with-review` tickets sat on open PRs).

The mitigation would be adequate if it (i) tested launch mode instead of asserting attendance, and (ii) said explicitly that with no human reachable the correct action is `coga block` with the verdict table as the ask — not "hand it to review."

### 3. Contexts — the no-contexts call is right, with one real omission

Attaching nothing is defensible on size alone: `coga/contexts/coga/architecture/SKILL.md` is 59 KB (~15k tokens), which would quadruple a 20 KiB prompt to answer a handful of questions. Copying facts in was the right call.

**But one required fact wasn't copied.** The ticket assigns two blackboard syntheses and never says what "synthesize" means. The only place in the repo that defines it — including the `## Production notes` marker that is the alternative — is `coga/contexts/coga/architecture/SKILL.md:~720-730`. Copy those three lines in, or cite the file:line. `measure-relay-prompt-scope-and-agent-precision`'s blackboard is 4,215 characters — this is not a trivial synthesis to improvise.

### 4. Context breadth — one item is too broad, one claim is wrong

**Too broad for inlining:** the "Standing pattern worth naming" paragraph asks the ticket to decide "where future `gap` findings go instead." That is a durable routing policy for the Dream pipeline, not a fact about this cohort. Per `CLAUDE.md`, whatever gets decided belongs in a context or the roadmap, and the ticket should name the target file rather than leaving an agent to invent a home for it mid-triage.

**Wrong, and it would get committed into a contract file:** the ticket asserts `script:` "is ticket frontmatter, and core has no reader for it anywhere." There is a reader. `src/coga/ticket.py:74-80`:

```python
# Bounded model migration: older Coga versions wrote `script: null`
# into every ticket. The launch-integrated script field no longer
# exists, so treat that inert legacy value exactly like an absent key.
if fm.get("script") is None:
    fm.pop("script", None)
```

All 15 occurrences are `script: null`, so they are already handled and self-heal on the next write through core. The proposed new README row would be false prose in the file that is the contract for the directory. The correct row is "`script:` — Gone; a bounded migration in `src/coga/ticket.py:74` strips `script: null` on next write," which also means this may not warrant a row at all.

**Verified correct** (no action needed): the empty-`## Description` mechanic; 15 drafts carrying `script:`, all null; `coga/workflows/` exists but has no `code/` subdirectory; `coga validate` reports exactly 4 ERRORs, all `unsynthesized-draft-blackboard`, all under `v2/`; the draft-only gating at `src/coga/validate.py:447`; everything else WARN.

### 5. Scope — this is three tickets

The "18 empty descriptions" half is **not** the cheap mechanical half the framing implies. All 17 real files are title-only stubs with an empty `## Context` as well. For `model-selector` (328 B) or `add-subproject` (328 B) the entire informational content is the slug. Each one is an owner-interview question or a cancel decision. That is 17 human judgments, not 17 edits.

Full inventory of decisions in this ticket:
- 17 stub verdicts (interview / cancel / leave), each needing the owner
- 8 premise verdicts, 3 of them with no evidence supplied (#6)
- 8 `coga mark canceled` lifecycle writes with Slack notifications
- 2 README table rows (one of which is currently wrong)
- 2 blackboard syntheses, one over a 4.2 KB blackboard
- the "where do future gap findings go" policy question (#4)

The natural split: (a) README table correction — small, PR-shaped, no lifecycle writes; (b) premise-dead cohort adjudication — 8 slugs, human-gated, needs evidence for 3; (c) the stub cohort — an owner interview, not a code ticket.

### 6. Assumptions to question — the premise-dead list does not hold uniformly

I spot-checked four of the eight.

**Holds cleanly (2):**
- `audit-rules-md-usage-across-relay-and-decide-wheth` — confirmed dead. `rules.md` exists nowhere except as a stale-artifact fixture in a prune test (`tests/test_init.py:1379`). `grep rules src/coga/compose.py src/coga/paths.py` returns nothing — the "Global rules" layer the draft audits no longer exists.
- `document-workflow-less-concept-capture-drafts-as-s` — confirmed dead. Its deliverable shipped: `coga/contexts/coga/architecture/SKILL.md:363-400` documents workflow-less drafts as a valid authoring state and explicitly names the validator-nagging problem the draft was written about.

**Does not hold as stated (1) — highest-value flag:**
- `add-relay-skill-search-with-candidate-eval` is listed under "each settled the other way." I find no settlement. `coga skill --help` shows install / install-local / install-url / update / remove / status — **no `search`**. The subject the draft proposes was never built, and the surfaces it names are still live. `coga/log.md` contains only its creation and two unrelated git-sync failures — no decision, no cancel, no counter-ticket. By the README's own two-question test it passes both. It is a live gap, not premise-dead. Cancelling it would delete an open gap with a recorded reason that isn't true.

This generalizes: **five of the eight slugs get a parenthetical reason; three — `dev-loop-git-hygiene`, `relay-design-repositories`, `add-relay-skill-search-with-candidate-eval` — get only "each settled the other way,"** with no pointer to where the settlement is recorded. Those three are exactly the ones an agent must re-derive from nothing, and the one I checked contradicts the claim.

**Partially holds (2):**
- `skill-update-aborts-on-uncommitted-log-file` — the stated root cause is genuinely gone (`src/coga/commands/launch_script.py` no longer exists, no `run_script_mode` anywhere). But the draft's *secondary* finding is untouched: `_assert_no_unmerged_paths` at `src/coga/skill_manager.py:417` still filters on `--diff-filter=U` only, so it still walks past an ordinary dirty tracked file before `_checkout` at line 488. A cancel reason must name the surviving residue or it silently drops a live gap. (Note the repo's `git status` at session start: `M coga/log.md` — the dirty-tree condition is not hypothetical.)
- `autotrigger-ticket-type` — evidence given is "every cross-reference dead." I verified 6 of 7 named slugs do not exist. But dead cross-references make a draft *harder to act on*; they are not the README's premise test. The subject is a proposed unification of recurring + idle triggers — recurring is very much alive — so the subject was never deleted, it was never built. **Compounding incentive:** this slug and `split-context-to-doc` are 2 of the 4 `coga validate` ERRORs, and the ticket notes that cancelling them is what turns validate green. An agent under pressure to deliver a green gate has a direct incentive to rule "dead." Worth stating explicitly that a green validate must not be a reason to cancel.

### Composed-prompt size

`workflow_skill` (code/implement) at 8.1 KiB is **40.3% of the 20.1 KiB total** — the one layer over the flag line. But it's generic, fixed, per-launch overhead shared by every `code/with-review` ticket; trimming it is a repo-wide change, not a fix for this ticket, and I'd rate it low-value.

The more useful reading is the inverse. Ticket-specific payload — `task_description` (1.4 KiB) + `task_context` (3.3 KiB) — is 4.7 KiB, **23% of the prompt**, carrying roughly 27 distinct judgment calls. That's ~175 bytes of guidance per decision. The composition isn't bloated; the ticket is under-specified for its own scope.

### Bottom line

The mechanical claims re-verified on 2026-09-02 mostly hold and hold precisely — the `coga/workflows/code/` observation and the `validate.py:447` draft-only gating are genuinely good catches. The problems are on the judgment side: one half of the ticket (17 stubs) has no deliverable and no recoverable material; one of the two "confirmed dead" cohorts contains at least one draft that a five-minute check shows is alive; one Context fact is wrong in a way that would land false prose in a contract file; and the human-gate mitigation routes decisions into a step that is barred from making them. I would not launch this as-is.
