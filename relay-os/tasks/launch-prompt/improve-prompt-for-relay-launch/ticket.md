---
slug: launch-prompt/improve-prompt-for-relay-launch
title: improve prompt for relay launch
status: in_progress
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/architecture
- relay/principles
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

Trim and restructure the Relay launch base prompt so it is shorter and less
repetitive without losing any load-bearing rule. The base prompt
(`prompt.md`) is inlined into every composed launch by `compose.py`, so its
length is a compounding token cost paid on every run. This is a mechanical /
structural cleanup with high-confidence wins; the broader editorial/voice pass
is a separate sibling ticket
(`review-and-edit-the-relay-launch-prompt-editorial`, owned by nick), in the
same `launch-prompt/` task directory.

Concrete changes:

1. **Dedupe repeated rules.** The bump / don't-go-backward /
   don't-set-status-done / don't-relay-launch-from-inside rules each appear
   3–4× ("Finishing a step" prose, its bulleted Rules, and "What you don't
   do"). State each once, authoritatively; shrink "What you don't do" to only
   items not covered elsewhere.
2. **Move agent-can't-act-on reference out of the base prompt.** Supervisor
   respawn/teardown semantics and human-only `bump --to` / `--backward`
   mechanics are reference an agent can't act on. Relocate to a context (likely
   `relay-os/contexts/relay/architecture`, which already covers prompt
   composition and the launch planes) rather than paying for it every launch.
   Confirm the destination is actually loaded on the launches where the
   reference matters — otherwise the relocation just hides the rule.
3. **Lead with the core loop.** Surface the load-bearing instruction (read
   blackboard → do work → run `bump` LAST then stop; never stop silently; if
   blocked, `panic`) up top; demote the rest to reference.
4. **Tighten the mode overlays to deltas only.** Keep interactive's genuinely
   new content (present human always gets a real response; don't go mute on
   `done`); drop re-statements of the base ("still write to blackboard",
   "exit cleanly").

Done = the trimmed prompt preserves every behavioral rule and the PR records a
before/after token measurement.

## Context

- The launch prompt is assembled by `src/relay/compose.py`
  (`compose_prompt_report`), in order: header → base prompt (`prompt.md`) →
  mode overlay (`prompt-interactive.md` / `prompt-auto.md`) → global rules →
  repo context → contexts → inline `## Context` → skill → workflow-inline →
  `## Description`. Only the base prompt and the two mode overlays are in
  scope here.
- The prompt files have a **single canonical home**:
  `src/relay/resources/prompt.md`, `prompt-interactive.md`, and
  `prompt-auto.md`, loaded via `_resource()` in `compose.py`. There is no
  `templates/relay-os/prompt*.md` and no live `relay-os/` copy — CLAUDE.md's
  "keep both copies in sync" rule is about shipped contexts/templates, not
  these prompts. Edit the resources copy only; do not hand-edit the vendored
  `relay-os/.relay/` snapshot (a build artifact).
- This prompt is the **behavioral contract** for every launched agent — per
  CLAUDE.md, behavior changes must keep the matching `relay-os/contexts/relay/`
  contexts (e.g. `architecture`, `principles`) accurate. Don't drop a rule to
  save tokens; relocate it.
- `compose_prompt_report` exposes per-layer byte/token sizes — use it to
  produce the before/after measurement for the PR description.
- Verification: `python -m pytest` and `relay validate --json`. Note
  `tests/test_compose.py` has assertions on exact prompt text (e.g. it checks a
  specific phrase is *absent* from the prompt) — a green run does not by itself
  prove rules were preserved, so re-read the prompt-text assertions there and
  diff old-vs-new rule coverage by hand, don't rely on pytest alone.

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
- branch: `trim-launch-prompt`
- worktree: `/home/n/Code/claude/relay-trim-prompt`
- pr: https://github.com/FastJVM/relay/pull/416
- Implement step done 2026-06-19. Committed, not pushed (open-pr is a later step).
- open-pr step done 2026-06-20. Pushed `trim-launch-prompt`; opened PR #416.
  `gh auth status` OK (nicktoper, repo+workflow scopes). No CI configured on
  this repo (`gh pr checks` → "no checks reported"), so there is no green-CI
  signal to wait on — human review is the next gate.

## Implement results (2026-06-19)

**Files changed (worktree):**
- `src/relay/resources/prompt.md` — restructured: leads with a 4-point **The
  loop** (read blackboard → do work + write blackboard → run `bump` last then
  stop / `mark done` on final step → never stop silently/panic). Deduped the
  bump / exit-cleanly / don't-go-backward / mark-done rules to one
  authoritative statement each under **Finishing a step**. Trimmed Files,
  Panic, FYIs, YAML sections. Shrank **What you don't do** to only the two
  items not implied elsewhere (don't `relay launch` from inside; don't touch
  `relay.toml`/`.local.toml`). Folded the standalone Blackboard section into
  the loop.
- `src/relay/resources/prompt-interactive.md` — trimmed to mode-deltas: kept
  "present human always gets a real response / don't go mute on `done`",
  "discuss before code", "surface tradeoffs". Dropped restatements of the base
  ("still write to the blackboard", "exit cleanly") and the
  "notifications are still live" bullet (base FYI section already covers
  broadcast discipline). Folded "it's OK to sit and wait" into "Ask when
  uncertain".
- `src/relay/resources/prompt-auto.md` — **unchanged** (already lean and
  genuinely auto-specific).
- `relay-os/contexts/relay/architecture/SKILL.md` **and** its packaged twin
  `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/architecture/SKILL.md`
  — relocation target (item 2). The supervisor respawn/teardown mechanics were
  already in architecture's interactive bullet; I augmented it to preserve the
  two details the base prompt carried that architecture didn't yet state
  explicitly: the extra stop conditions (no-skill step, panic/non-zero exit)
  and the "clean prompt scope, no carryover reasoning from the previous skill"
  rationale. Edited BOTH copies identically (the edited region was identical in
  both; pre-existing `scaffold`/`create` + auto-disabled-note divergences left
  untouched). Human-only `bump --to`/`--backward` flag mechanics were already
  in architecture (lines ~192-193), so the base prompt now just says "the human
  decides whether to rewind" without re-teaching flags.
- `tests/test_compose.py::test_base_prompt_teaches_exit_after_bump` — updated.
  It pinned `"respawns the next agent step"` and `"clean prompt scope"` as
  present in the BASE prompt; both are now relocated to architecture (which
  this test's ticket does not attach, contexts=[]), so I assert they are
  ABSENT and instead assert the new core-loop essentials (`Never stop
  silently`, the `relay/architecture` pointer). Kept the still-true pins.

**Measurement (per-file; base prompt is inlined every launch):**
| file | bytes | ~tokens | lines |
|---|---|---|---|
| prompt.md | 7781 → 6036 (−1745) | 1945 → 1509 (−436, −22%) | 160 → 126 |
| prompt-interactive.md | 1925 → 1470 (−455) | 481 → 367 (−114, −24%) | 39 → 31 |
| prompt-auto.md | 2096 → 2096 (0) | 524 → 524 (0) | 45 |

Net per **interactive** launch ≈ −550 tokens; per **auto** launch ≈ −436
tokens. (Only the base prompt + overlays changed, so the composed-prompt delta
equals the per-file delta exactly.)

**Rule-coverage hand-diff (no load-bearing rule dropped):** verified each rule
from the old prompt survives — frontmatter edit perms + no-hand-edit of
status/step/workflow, don't-write-log.md, bump-advances-one-step/can't-skip,
exit-cleanly/one-step-one-session, API-manual-don't-chain + don't-launch-from-
inside, don't-go-backward→panic, don't-edit-workflow-snapshot, mark-done-on-
final/no-workflow + never-set-status-done-by-hand, panic conditions + write-
blocker-first + --reason-specific, FYIs (bump --message vs slack, not for
blockers, one line), YAML discipline, don't-touch-relay.toml. The only content
*removed* from the base prompt is the supervisor mechanics → relocated to
architecture (augmented so nothing is lost).

**Relocation soundness (item 2 caveat):** architecture is loaded only when a
ticket attaches `relay/architecture`. That's fine — the supervisor mechanics
are explanatory reference an agent can't act on; the *actionable* part
(bump-last, then stop) stays in the base prompt's loop. Relay-internals tickets
(like this one) attach `relay/architecture`, so the reference is present where
it matters.

**Verification run:** full `pytest` = 822 passed, 1 skipped. `relay validate
--json` against `example/` = ok_count 1, 0 issues. (Tests run via the pinned
`.relay/.venv` with `PYTHONPATH` shadowing to the worktree `src` — relay is not
installed in the default python.)

## Peer review (Codex, 2026-06-20 UTC)

Native review run: `codex review --base main` from
`/home/n/Code/claude/relay-trim-prompt`. The first in-sandbox attempt failed
with the known app-server read-only filesystem error, then the same command ran
outside the sandbox and reported one P2 must-fix:

- The relocated architecture wording said the interactive supervisor returns to
  the caller when the next step has no skill. Current launch/bump behavior
  chains whenever the next assignee is a configured agent, including skill-less
  agent steps, so that line was inaccurate.

Fix applied and committed on `trim-launch-prompt`:

- `ab1fb2d peer-review: apply review finding`
- Removed the false no-skill stop condition from both
  `relay-os/contexts/relay/architecture/SKILL.md` and the packaged twin under
  `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/architecture/SKILL.md`.

Verification after the fix:

- `python -m pytest` from the feature worktree: 822 passed, 1 skipped. Pytest
  also warned that it could not write `.pytest_cache` because this sandbox sees
  that sibling worktree as read-only; test execution itself passed.
- `git diff --check`: clean.
- `relay validate --task launch-prompt/improve-prompt-for-relay-launch --json`
  from the primary checkout: ok_count 1, no issues.
- Repo-wide `relay validate --json` from the primary checkout still has
  unrelated pre-existing task-state errors/warnings (missing-step, unknown
  assignee, stuck-in-progress), so it is not a clean PR signal.

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
