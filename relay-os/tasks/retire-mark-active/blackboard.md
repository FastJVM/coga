# Blackboard — retire-mark-active

## Dev

- branch: `retire-mark-active-docs`
- worktree: `/home/n/Code/codex/relay-retire-mark-active`

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
