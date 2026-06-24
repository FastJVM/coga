---
slug: retire-mark-active
title: Retire relay mark active before launch
status: in_progress
autonomy: interactive
owner: zach
human: zach
agent: claude
assignee: zach
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
  - name: review
    skills: []
    assignee: owner
step: 4 (review)
---

## Description

`relay launch` already activates a ticket inline (`_auto_activate`) — launching
*is* the readiness signal — so the old "run `relay mark active` first" step is
already redundant in behavior. The runtime change has shipped; what remains is
documentation/template cleanup so we stop *teaching* the retired step.

Scope (decided 2026-06-16, interactive with zach):

- **Scrub the "activate before launch" guidance** from help text, agent guides,
  docs, and contexts so nothing tells a human or agent to run `relay mark
  active` as a prerequisite to launching.
- **Keep the `relay mark active` command** as a thin convenience. It still has
  legitimate uses (activating without launching) and is the named remedy in
  validate/error paths. Do **not** delete the `active` subcommand — only remove
  the *prerequisite-to-launch* framing.

## Context

- The behavior is already done: `relay launch` brings a draft/paused/done
  ticket to `active` via `_auto_activate` (`src/relay/commands/launch.py:226`,
  `:536`). The `relay mark active` command lives in
  `src/relay/commands/mark.py` and stays.
- **Out of scope:** workflow-less drafts (`workflow: null`) still can't be
  activated by launch ("no workflow, nothing to activate"). That is left as-is
  — a draft with no steps legitimately has nothing to run. Don't expand launch
  to handle it here.
- Distinction to hold throughout: **drop "activate before launch" framing,
  keep factual command mentions.** Lines that just document what `mark active`
  does (the command cheat-sheet, the workflow-less-refusal note, the "same
  remedy" error text) stay; lines that sequence it as a step you do *before*
  `relay launch` get reworded or removed.
- Touch points to scrub (verified 2026-06-16 — start here, but grep the repo
  for `mark active` to confirm completeness):
  - `README.md` — **highest-priority, most user-facing.** Has the prerequisite
    framing in several spots: the normal-path snippet (~line 164,
    `mark active` then `launch`), the boot-sequence step (~line 263), and
    ~line 411 ("launch … runs the `relay mark active` step for you"). Note
    ~line 274 (command cheat-sheet), ~279 (workflow-less refusal), and ~414
    (the "same remedy" error text) are factual mentions to **keep**.
  - `src/relay/commands/init.py:102` — `AGENT_GUIDE_TEMPLATE` lists
    `relay mark active <slug> — activate a draft before launch`. Reword so it
    no longer frames activation as a pre-launch step. This template is
    single-source (no packaged duplicate), so editing it here is sufficient.
  - `relay-os/contexts/relay/current-direction/SKILL.md:217` — shows the
    `mark active → launch` sequence as the flow.
  - `relay-os/contexts/relay/architecture/SKILL.md` and `.../sync/SKILL.md` —
    several references describing `mark active` as the activation path.
  - `relay-os/contexts/relay/roadmap/SKILL.md:145` — the
    `implicit-activation-inrpogress` roadmap entry literally tracks this work;
    update/close it rather than just scrubbing the phrase.
  - `docs/relay-vs-paperclip.md:70` — a table cell lists `mark active` as a
    human gate; factual, likely **keep** — judgment call.
  - Sync note: these `relay/` contexts are **not** duplicated under
    `src/relay/resources/templates/relay-os/` (only `_template`/`autonomy`/
    `browser` ship there), so the usual "sync both copies" rule does not apply
    to the files above. The one packaged file that mentions `mark active` is
    `src/relay/resources/templates/relay-os/relay.toml` — check whether it
    needs the same treatment.
- Surfaced while prototyping `relay build` (2026-06-16): the onboarding batch
  hands the human a bare `relay launch <slug>` with no mark-active step — see
  `marketing/relay-build-onboarding-flow`. That flow is already correct; this
  ticket makes the docs match it.

<!-- relay:blackboard -->

# Blackboard — retire-mark-active

## Dev

- branch: `retire-mark-active-docs`
- worktree: `/home/n/Code/codex/relay-retire-mark-active`
- pr: https://github.com/FastJVM/relay/pull/380

## open-pr step (2026-06-17)

Pushed `retire-mark-active-docs` and opened PR #380. No CI checks are configured
on this repo (`gh pr checks 380` → "no checks reported"), so there is no green
gate to wait on. Working tree was clean; two commits ahead of main.

## Implement step (2026-06-16)

Classified every `mark active` hit (grep across `*.md`/`*.py`/`*.toml`, minus
task dirs) into **scrub** (prerequisite-to-launch framing) vs **keep** (factual
command docs, workflow-less refusal, "same remedy" error text, current
inline-auto-activation descriptions).

**Scrubbed (prerequisite framing removed/reworded):**
- `README.md` normal-path snippet (~164): dropped the standalone
  `relay mark active` line — `relay launch` activates inline.
- `README.md` boot sequence (~259-265): folded step 3 (`mark active`) into the
  `relay launch` step; noted launch activates a draft inline.
- `README.md` launch section (~411): "runs the `relay mark active` step for
  you" → "activates the ticket inline for you" (drops the "step" framing). Kept
  the "same remedy `mark active` gives" error text two lines down.
- `src/relay/commands/init.py:102` (AGENT_GUIDE): "activate a draft before
  launch" → "activate a draft without launching it". Single-source, no packaged
  duplicate.
- `current-direction/SKILL.md:216`: dropped `mark active` from the boot arrow.
- `roadmap/SKILL.md:145`: `implicit-activation-inrpogress` retagged
  `[draft]` → `[shipped]`, reworded to record the runtime landed + this docs
  ticket. (No `[done]` convention exists in the contexts; `[shipped]` is the
  honest "update/close" the ticket asked for.)

**Kept as factual (verified, not prerequisite framing):**
- `README.md` cheat-sheet (~274), workflow-less refusal (~279), recurring "can't
  go through the mark active gate" (~320), "same remedy" (~414).
- `architecture/SKILL.md` (129, 142, 176, 191, 277, 280): all describe the
  activation *gate* or launch's *inline* auto-activation — current/correct
  behavior, not the retired pre-launch step. No scrub needed.
- `sync/SKILL.md` (59, 276): notification/sync surface command lists — factual.
- `relay.toml` x3 (`relay-os/`, `example/`, `templates/`): comment "human
  approves and runs `relay mark active`" — describes the standalone approval
  command, still valid. Left as-is (low risk; could reword but not prerequisite-
  to-launch sequencing).
- `docs/relay-vs-paperclip.md:70`: comparison-table cell listing `mark active`
  as an approval mechanism — factual, kept (ticket flagged as judgment call).
- Source comments in `create.py`, `launch.py`, `mark.py`, `config.py`,
  `ticket.py`, `validate.py` and tests: factual descriptions of `mark active`
  semantics / current inline behavior; out of the docs-cleanup scope.

## Peer review (2026-06-17)

Native review:
- Ran `codex review --base main` from `/home/n/Code/codex/relay-retire-mark-active`.
- First sandboxed attempt failed with the known Codex app-server
  `Read-only file system` initialization error; reran outside the sandbox.
- Finding: packaged bootstrap guides still taught `relay mark active <slug>` →
  `relay launch <slug>` in
  `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/cli/SKILL.md`
  and
  `src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md`.

Applied fix:
- Reworded the packaged bootstrap CLI reference so the draft/ticket boot path
  goes directly to `relay launch <slug>`, with `relay mark active <slug>`
  reserved for approving/queueing without launching.
- Reworded the bootstrap ticket-authoring skill so its handoff says to run
  `relay launch <slug>` when ready, and only use `relay mark active <slug>` to
  approve without launching.

Verification:
- `rg` check over docs/templates/source/tests found no remaining
  prerequisite-style `mark active` → `launch` guidance in the patched bootstrap
  guides; remaining hits are factual command docs, source comments, tests, or
  historical task text.
- `git diff --check` passed.
- `python -m pytest` passed: 754 passed, 1 skipped. Pytest emitted one cache
  write warning because the sandbox could not write `.pytest_cache`; tests were
  otherwise clean.

## Bootstrap notes (2026-06-16, interactive with zach)

- Runtime change already shipped: `relay launch` auto-activates via
  `_auto_activate` (`launch.py:226`/`:536`). This ticket is the docs/template
  cleanup follow-up, not a behavior change.
- Decisions:
  - **Keep** `relay mark active` as a thin convenience — scrub only the
    "before launch" framing, do not delete the subcommand.
  - **Out of scope:** workflow-less-draft activation (launch still refuses
    `workflow: null`; that's fine).
- Workflow: `code/with-review` (implement → peer-review → open-pr → owner review).
- Contexts: none attached — the load-bearing fact (`_auto_activate`) is copied
  into `## Context`; the relay/ contexts are edit targets, not references.

### Post-evaluator corrections folded into the ticket
- Added **README.md** to the touch-point list (the evaluator's catch — it's the
  most prominent offender and was missing). Distinguished keep-vs-scrub lines.
- Corrected the sync caveat: the `relay/` contexts are **not** packaged under
  `src/relay/resources/templates/relay-os/` (only `_template`/`autonomy`/
  `browser` are), and the AGENT_GUIDE is single-source in `init.py`. Only
  `templates/relay-os/relay.toml` mentions `mark active` in the packaged tree.
- Added `roadmap/SKILL.md:145` (the `implicit-activation-inrpogress` entry that
  tracks this very work) and `docs/relay-vs-paperclip.md:70` (likely keep).

## Evaluator review

I have enough to assess. The README has the most prominent "before launch" framing (lines 161-165, 263, 264-265) and is entirely absent from the ticket's touch-point list. The packaged templates do not contain a duplicate of the AGENT_GUIDE (it's generated from init.py, single source), so the "keep both copies in sync" caveat may be a red herring for the init.py touch point specifically.

### Assessment

**1. Clear enough to start cold?** Yes, largely. The intent is crisp and well-bounded: scrub the "activate before launch" *guidance* from docs/help/contexts while keeping the `mark active` command. The decision rationale (launch is the readiness signal, behavior already shipped) is stated and verifiable — `_auto_activate` at `launch.py:226` does exactly what the ticket claims. An agent could start immediately. The one soft spot is "scrub" vs "reword": the ticket says reword to drop the prerequisite framing but keep factual command mentions, which requires judgment per-site, but it gives enough guidance to make those calls.

**2. Does `code/with-review` fit?** Mostly, with friction. This is a docs/template/help-text edit — no logic change, the runtime already shipped. A code-implement + peer-review + PR flow works, but peer-review here is value-light (`/code-review` on a prose diff finds little) and the workflow's emphasis on `python -m pytest` re-runs is near-irrelevant. A lighter doc-focused workflow would fit better, but `code/with-review` is not *wrong* — the edits touch `init.py` (Python source) and packaged resources, so a review gate is defensible.

**3. Contexts — empty `contexts: []` correct?** This is the weakest point. The ticket *edits* `relay-os/contexts/relay/architecture/SKILL.md`, `current-direction/SKILL.md`, and `sync/SKILL.md`, yet attaches no contexts. The implementer must read those files to edit them regardless, so nothing is strictly blocked — but attaching `architecture` and `current-direction` (or copying the launch/auto-activate behavioral fact into `## Context`) would be the cleaner move. As written, the key behavioral fact *is* already copied into `## Context` (the `_auto_activate` explanation), which is the load-bearing one, so this is acceptable rather than broken.

**4. Scope — one ticket?** Reasonable and well-scoped. It is deliberately narrowed to documentation cleanup, with the runtime change explicitly out of scope (already shipped) and workflow-less drafts explicitly excluded. The "keep the command, only remove the framing" boundary prevents scope creep into deleting the subcommand. This is a single coherent ticket.

**5. Assumptions to question before launch — the touch-point list is the real risk.** The ticket says the list is "not exhaustive — grep for the rest," which is honest, but the omissions are large enough that an implementer who trusts the list will miss the most visible offenders:

- **`README.md` is entirely absent from the list yet contains the most explicit prerequisite framing** — the "normal path" snippet (lines 161-165: `mark active` then `launch` as sequential steps), the "boot sequence" steps 3-4 (lines 263-264), and line 411 which literally says launch "runs the `relay mark active` step for you." README is the single highest-priority scrub target and it's not mentioned. An agent must run the grep to catch it.
- **`relay-os/contexts/relay/current-direction/SKILL.md:217`** is listed, but the parallel offender **`docs/relay-vs-paperclip.md:70`** and **`roadmap/SKILL.md:145`** (which references the now-being-retired "mark active" step) are not.
- **The "keep both copies in sync" caveat is partly misapplied for init.py.** The AGENT_GUIDE is generated from `init.py` (single source — no duplicate string exists under `src/relay/resources/templates/`, confirmed by grep). The sync caveat is real for the `relay-os/contexts/` SKILL files (which *are* duplicated under `src/relay/resources/templates/relay-os/contexts/`), so the implementer must scrub both copies of each edited SKILL.md — but the ticket's framing might lead them to hunt for an init.py template duplicate that doesn't exist while under-checking the context-file duplicates that do.

Net: the ticket is executable and honestly flags its list as incomplete, but it omits README — the most user-facing offender — so success depends entirely on the implementer actually running the grep rather than working the bullet list. I'd add README explicitly and note the init.py-vs-context-file sync asymmetry before launch.

### My verification of the evaluator's claims (2026-06-16)
- README omission: **confirmed and fixed** — added to ticket.
- `docs/relay-vs-paperclip.md:70`, `roadmap/SKILL.md:145`: **confirmed** — added.
- Evaluator's claim that `relay/` context SKILLs are duplicated under
  `src/relay/resources/templates/relay-os/contexts/`: **incorrect.** That tree
  only ships `_template`/`autonomy`/`browser`. No packaged copies of the edited
  files exist; AGENT_GUIDE is single-source in init.py. Only
  `templates/relay-os/relay.toml` mentions `mark active` in the packaged tree.
  Ticket's sync note corrected accordingly.
