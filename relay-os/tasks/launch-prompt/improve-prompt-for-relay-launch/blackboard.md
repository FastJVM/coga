The blackboard is a notepad to be written to often as the human and agent works through a task.

## Status
Draft, filled 2026-06-19. T1 of a two-ticket split (both under
`relay-os/tasks/launch-prompt/`). Workflow `code/with-review`, assignee claude.
This is the mechanical/structural trim; sibling
`review-and-edit-the-relay-launch-prompt-editorial` (nick, assist-only) is the
broader editorial pass. Ready for nick to launch with `relay launch
improve-prompt-for-relay-launch`.

Correction applied after evaluator review: the prompt files are SINGLE-SOURCE
under `src/relay/resources/` — there is no `templates/relay-os/prompt*.md` and
no live `relay-os/` copy. Earlier "keep both copies in sync" framing was wrong
and has been removed from the ticket.

## What "relay launch prompt" means here
The composed launch prompt assembled by `compose.py` (`compose_prompt_report`), in order:
header → base prompt (`prompt.md`) → mode overlay (`prompt-interactive.md`/`prompt-auto.md`)
→ global rules → repo context → contexts → inline `## Context` → skill → workflow-inline
→ `## Description`. The base prompt `prompt.md` is inlined into EVERY launch, so its
length is a compounding token cost. Note the packaged twin under
`src/relay/resources/` and the live copy under `relay-os/` must stay in sync (CLAUDE.md).
`compose_prompt_report` exposes per-layer byte/token sizes → before/after is measurable.

## Findings — improvement candidates for prompt.md
1. REPETITION (top issue). The bump / don't-go-backward / don't-set-status-done /
   don't-relay-launch-from-inside rules each appear 3–4×: "Finishing a step" prose,
   then its bulleted Rules, then "What you don't do". `panic`-for-rework stated twice.
   Interactive overlay re-states "one step, one session" a 3rd time.
   → Dedupe to one authoritative statement each. Highest value-to-risk. Pure win.
2. AGENT-CAN'T-ACT-ON REFERENCE. Large chunks explain supervisor/human mechanics to the
   agent: `bump --to`/`--backward` (human-only), supervisor respawn/teardown rules.
   Agent can't act on these → move to a context loaded when relevant, not every launch.
   Biggest length cut.
3. CORE LOOP IS BURIED. The load-bearing instruction (run bump LAST then stop; never
   stop silently; if blocked panic) is diluted across 3 sections. Lead with a short sharp
   loop: read blackboard → work → bump-last-or-panic → stop. Demote rest to reference.
4. TASK-DIR NESTING para teaches path reconstruction then says "use the header path
   instead" — partly dead weight if header is authoritative.
5. OVERLAYS should be mode-DELTAS only. Interactive's genuinely-new content (present
   human always gets a real response; don't go mute on `done`) is good; "still write to
   blackboard" / "exit cleanly" are re-statements of the base.
6. "Read the blackboard first" for relaunch is buried in the Blackboard section; arguably
   belongs at top of the core loop since it's a relaunched agent's first action.
7. No self-awareness about cost — ~250 lines re-teaching CLI semantics with no "be concise,
   this is inlined everywhere" framing.

## Priority ranking
1. Dedupe repeated rules (low risk, compounding).
2. Move supervisor/human reference out of base prompt into a context (biggest cut).
3. Lead with the core loop, demote rest to reference.
4. Tighten overlays to mode-deltas only.

## If/when this becomes real work
- Behavioral contract → treat as a reviewed PR (code/with-review), not a quick edit.
- SINGLE-SOURCE edit under `src/relay/resources/` (prompt.md + the two overlays).
  Earlier note about a `templates/relay-os/` copy was WRONG — corrected per
  evaluator (no prompt*.md under templates/; don't touch the vendored
  `relay-os/.relay/` snapshot).
- Measure before/after per-layer tokens via `compose_prompt_report`.

## Evaluator review (T1, independent cold read — 2026-06-19)

**Cold-read evaluation: `improve-prompt-for-relay-launch`**

**Clarity / pickup-readiness — strong.** The Description is unusually actionable for a cold start: four concrete, enumerated changes, each naming the specific rules to dedupe (bump / don't-go-backward / don't-set-status-done / don't-relay-launch-from-inside) and where they're repeated. The Context block correctly maps the compose order in `compose.py` and names the exact `compose_prompt_report` API to use for the token measurement. An agent with no prior context could start. The intent ("trim without dropping a load-bearing rule; relocate, don't delete") is clear and the editorial pass is explicitly carved out to a sibling ticket, so scope creep is pre-empted.

**Scope — reasonable for one ticket.** It's a single coherent edit to three files (`prompt.md` + two mode overlays) with a clear done-definition. Item 2 (relocating supervisor/teardown and human-only `bump --to`/`--backward` mechanics into "a context loaded when relevant") is the one open-ended sub-task — it requires choosing/creating a target context and wiring it, which is more than mechanical text-shuffling. Worth flagging but not a separate ticket.

**The two-copies-in-sync claim — inaccurate, and this is the main thing to fix before launch.** The ticket says the prompt files "exist in two places that must stay in sync (see CLAUDE.md)... the packaged copies under `src/relay/resources/` and any live `relay-os/` copy." That misreads CLAUDE.md. CLAUDE.md's sync rule is about shipped *contexts/templates*: `relay-os/` vs `src/relay/resources/templates/relay-os/`. The base prompt files live in exactly **one** canonical place: `src/relay/resources/prompt.md`, `prompt-interactive.md`, `prompt-auto.md`. They are loaded via `_resource()` (`files("relay.resources")`), not from `templates/`. I confirmed `src/relay/resources/templates/relay-os/` exists but contains **no** `prompt*.md`. The only other on-disk copies are `relay-os/.relay/src/...` and `relay-os/.relay/.venv/...` — those are a pinned vendored install of the package (`relay-os/.relay/` has its own `pyproject.toml`/`RELAY_PIN`/`.venv`), i.e. a build artifact, not a source-of-truth copy to hand-edit. An agent that takes the "touch both in the same PR" instruction literally will waste time hunting for a second canonical file, or worse, hand-edit the vendored snapshot. **Recommend: drop the two-copies framing for these files — it's a single-source edit under `src/relay/resources/`.**

**Path references — otherwise accurate.** `compose.py` / `compose_prompt_report` / per-layer `byte_count`/`approx_tokens`, the compose ordering, and the rule-repetition claims all check out against source. The duplication the ticket targets is real (e.g. the bump/panic/no-silent-stop rules appear in "Finishing a step" prose, its "Rules" bullets, and "What you don't do").

**Workflow fit — good, with one caveat.** `code/with-review` (implement → peer-review by the other agent → open-pr → human review) fits a source edit that benefits from a second set of eyes, and the peer-review step is genuinely valuable here since the risk is *silently dropping a load-bearing behavioral rule* — exactly what an independent reviewer diffing old-vs-new should catch. Caveat: this prompt **is** the behavioral contract every launched agent (including the reviewer) reads, so the peer-review agent will itself be running under a freshly-trimmed prompt — fine, but the human `review` gate should explicitly diff rule coverage, not just token savings.

**Assumptions to question before launch:**
1. The "live `relay-os/` copy" assumption is false (above) — fix the ticket text.
2. Verification mentions "watch for tests asserting on prompt text" — there is at least one: `tests/test_compose.py:186` asserts an exact string (`"relay bump` marks the task `done`" not in prompt`). Any reword near that phrasing can break/weaken that test; the agent should re-read prompt-text assertions in `test_compose.py` rather than assume `pytest` green means rules preserved.
3. Item 2's "context loaded when relevant" has no named destination — the agent must decide where supervisor/respawn semantics live (likely `relay-os/contexts/relay/architecture`) and confirm it's actually loaded on the launches where that reference matters, or the relocation just hides the rule.

_Resolution: findings 1, 2, 3 all folded into the ticket (single-source corrected; test_compose.py pointer added; relay/architecture named as relocation target)._
