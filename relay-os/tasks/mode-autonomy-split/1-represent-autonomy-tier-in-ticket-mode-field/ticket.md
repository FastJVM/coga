---
slug: mode-autonomy-split/1-represent-autonomy-tier-in-ticket-mode-field
title: Represent autonomy tier in ticket mode field
status: active
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- autonomy/triage
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
step: 1 (implement)
---

## Description

Split the conflated `mode` field into two orthogonal fields, and hard-migrate the
whole repo to the new vocabulary. **This ticket is the representation +
migration only — it preserves current launch behavior.** Actually unblocking
unattended execution is the follow-up
`2-unblock-unattended-execution-mode-autonomy-auto`.

Today `mode` is a single enum (`interactive` / `auto` / `script`) that conflates
two independent questions. Factor it into a clean 2×2:

- **`mode: agent | script`** — *is there an agent/LLM?* `agent` = agent-driven
  (today's `interactive`/`auto`), `script` = deterministic skill script, no LLM.
- **`autonomy: interactive | auto`** — *is a human at the wheel?* `interactive`
  = attended/TTY, `auto` = unattended/headless.

| | `mode: agent` | `mode: script` |
|---|---|---|
| `autonomy: interactive` | attended agent *(today's `interactive`)* | attended script (needs input) |
| `autonomy: auto` | unattended agent *(today's `auto`)* | unattended/recurring script |

This is where the autonomy decision the triage tier produces gets its enforced
home: `fully-automated → autonomy: auto`, the other three tiers →
`autonomy: interactive`. The four-tier vocabulary stays advisory at authoring
time (per `wire-autonomy-triage-into-impl-ready-workflows`); the binary
`autonomy` field is its coarse, enforced projection.

**Behavior is preserved exactly.** Every place that gates on the old `mode`
values is re-keyed to the new fields with identical effect — in particular
`autonomy: auto` stays blocked at launch (the `auto` hard-bail is re-keyed, not
removed), `retire` keeps its auto ban, and recurring keeps refusing auto. This
ticket is a pure refactor + migration; the reviewer's job is "nothing broke and
the vocabulary is consistent everywhere." Removing those blocks and building the
unattended run path is the follow-up.

Defaults are backwards-compatible: a ticket with neither field = `agent` +
`interactive`, identical to today's default `interactive` behavior.

## Context

Split out of `wire-autonomy-triage-into-impl-ready-workflows`, which wired
`autonomy/triage` into `bootstrap/ticket` at authoring time but deliberately
left the structured representation to this ticket. This ticket was then itself
split (per the evaluator review in `blackboard.md`): representation/migration
here; execution-unblocking in the follow-up.

**Verified live state of `mode` (the older "auto disabled may be stale" note is
NOT stale — auto is actively hard-bailed):**

- `src/relay/ticket.py:116` — `mode` defaults to `interactive`;
  `CANONICAL_TICKET_KEYS` at `ticket.py:26–40`.
- `src/relay/validate.py:64` — `VALID_MODES = {"interactive", "auto", "script"}`;
  schema check at `validate.py:473–481`.
- `src/relay/commands/launch.py:267–279` — `auto` hard-bails (exit 2). TTY check
  `_interactive_stdio_has_tty()` at `281`; PTY done-marker supervisor
  (`run_with_done_marker`) at `485`; all keyed on `mode == "interactive"`. The
  `--mode` override option + validator at `88–92` / `145–146`.
- `src/relay/commands/launch_script.py:150` — `subprocess.run(...)`, no
  stdin/stdout redirection (attended scripts inherit the terminal).
- `src/relay/compose.py:151–165` — interactive vs auto prompt layer; `script`
  composes no prompt.
- `src/relay/recurring.py:480–545` — `_effective_mode()` refuses `auto`; threaded
  through `create_recurring_instance` (`effective_mode=`, `mode=` at 354/377/510).
- **Other `mode` consumers (must all migrate — these were missed in an earlier
  draft, caught by the cold evaluator):**
  - `src/relay/commands/create.py:26–29, 47–50` — `--mode` option default +
    "interactive, auto, or script" help.
  - `src/relay/create.py:31, 135, 176` — `create_task(mode=...)` → frontmatter/log.
  - `src/relay/commands/retire.py:29–33, 51–58` — its **own** `--mode auto` ban /
    `--mode must be 'interactive'` check, independent of launch.py.
  - `src/relay/commands/status.py:29, 130, 202–214` — `mode` column + `--order-by
    mode`.
  - `src/relay/retrofit.py:162–173` — canonical field-ordering list (insert
    `autonomy`).
- Tests: `tests/test_launch_auto.py`, `tests/test_launch_script.py`,
  `tests/test_compose.py`, `tests/test_validate.py` (plus create/retire/recurring
  tests touching mode).

**Migration scope:** ~125 ticket/fixture/template files (≈114 `mode: interactive`,
≈11 `mode: script`, **0 `mode: auto`** live today). Legacy→new mapping:
`interactive → (agent, interactive)`, `auto → (agent, auto)`,
`script → (script, interactive)`.

**Owner's taxonomy note:** `script` = a launch; `auto` = script + `claude -p`.

**Back-compat decision: hard migrate (no dual vocabulary).** Rewrite every file
in the PR; the validator accepts only the new values after migration. Single
vocabulary, per Relay's legibility principle.

**Out of scope:** unblocking unattended execution / output capture / recurring
opt-in (→ `2-unblock-unattended-execution-mode-autonomy-auto`); remote/cloud
dispatch (a later "when mature" ticket).

## Approach

1. **Data model** (`ticket.py`) — add `autonomy` to `CANONICAL_TICKET_KEYS`
   (default `interactive`); `mode` values become `agent | script` (default
   `agent`).
2. **Validation + migration** (`validate.py`) — `VALID_MODES = {"agent",
   "script"}`, new `VALID_AUTONOMY = {"interactive", "auto"}`; hard-migrate every
   existing `mode` value in the repo (tickets, fixtures, `example/`, both template
   copies). Validator rejects legacy values after migration.
3. **Launch dispatch** (`launch.py`) — re-key the `(mode, autonomy)` gates with
   identical behavior: re-key the TTY check (`281`), the PTY supervisor (`485`),
   and **keep** the auto hard-bail but re-key it to `autonomy == "auto"`. Decide
   the `--mode` override CLI option + validator (`88–92`/`145–146`): split into
   `--mode` / `--autonomy` (recommended) and update its allowed values.
4. **Other CLI consumers** — migrate `commands/create.py` (`--mode` default/help,
   add `--autonomy`), `create.py` (`create_task` signature + frontmatter/log),
   `commands/retire.py` (re-key its own auto ban — preserved, not removed),
   `commands/status.py` (`mode` column + ordering; add an `autonomy` column),
   `retrofit.py` (insert `autonomy` into field ordering).
5. **Prompt composition** (`compose.py`) — interactive-vs-auto layer keys on
   `autonomy`, not `mode`; `mode: script` still composes nothing.
6. **Recurring** (`recurring.py`) — `_effective_mode` resolution produces both
   `mode` and `autonomy`; the auto refusal is **preserved** (re-keyed to
   `autonomy == "auto"`) — its removal is the follow-up.
7. **Contexts / templates / docs** (keep `relay-os/` and
   `src/relay/resources/templates/` in sync per CLAUDE.md) — update
   `_template/ticket.md` (both copies); document the enforced tier→autonomy
   mapping in `relay-os/contexts/autonomy/triage/SKILL.md`; update the `mode`
   references in `bootstrap/ticket/SKILL.md`.
8. **Tests** — `test_validate.py` (new field + legacy values now error),
   `test_compose.py` (re-key), `test_launch_auto.py` (auto still blocked, now via
   `autonomy`), plus create/retire/recurring tests for the migrated vocabulary.
   Whole suite green; behavior unchanged.

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design decisions (bootstrap/ticket interview, nick + claude)

Final model — **split the conflated `mode` enum into two orthogonal fields:**

- `mode: agent | script` — is there an agent/LLM? (default `agent`)
- `autonomy: interactive | auto` — is a human at the wheel? (default `interactive`)

The 2×2 expresses the two cells the old enum couldn't: attended script (needs
input) and unattended agent. Decisions reached, with reasons:

- **Rejected** stuffing the tier into `mode` as a value, a separate `human|ai`
  field, and a merged enum — all either lossy or duplicative. Two orthogonal
  fields is the clean factoring.
- **Tier → field:** the four-tier triage stays advisory at authoring time; the
  binary `autonomy` field is its enforced projection (`fully-automated → auto`,
  other three → `interactive`).
- **`auto` was NOT stale** — it is actively hard-bailed (launch.py:267,
  recurring.py:489, and retire.py per evaluator). Unblocking it is the point.
- **Why unattended is OK now:** recurring/scheduled runs have no live watcher;
  their observability bar is "logged + Slack notify," not a live TTY. Output
  capture provides that.
- **stdin:** unattended runs close stdin (fail fast, no hang) — but verify each
  agent CLI's prompt-input contract first (evaluator flag).
- **Capture gated on unattended only** — piping an attended TTY run would
  clobber interactivity.
- **Back-compat: hard migrate** (option a). One vocabulary; rewrite all
  tickets/fixtures/templates; validator rejects legacy values.
- **Out of scope:** remote/cloud dispatch — "(b) when mature," a later ticket.

### Split decision (post-evaluator, nick approved)

This ticket = **scope A only**: split `mode` → `mode: agent|script` +
`autonomy: interactive|auto`, hard-migrate the repo, **preserve all current
behavior** (auto stays blocked, retire keeps its ban, recurring keeps refusing).
Pure refactor + migration; reviewer checks "nothing broke, vocabulary
consistent." File list expanded to the call sites the evaluator caught
(create.py, commands/create.py, commands/retire.py, commands/status.py,
retrofit.py, launch.py `--mode` validator).

Scope B+C (unblock unattended execution + capture/notify machinery + recurring
opt-in) split into the follow-up draft
`2-unblock-unattended-execution-mode-autonomy-auto` (depends on this). Remote/cloud
dispatch remains a third, later ticket.

## Evaluator review

I read this ticket cold and verified its claims against the source. Overall it is an unusually well-researched ticket — the "Context" section's line-numbered citations are accurate (I confirmed `launch.py:267-279` hard-bail, `validate.py:473-481`, `recurring.py:480-502`, `launch_script.py:150` all match). But it has one serious problem (scope) and one factual problem (incomplete file list), plus a couple of assumptions worth challenging before launch.

### 1. Description clarity — mostly good, a few gaps

The 2×2 framing (`mode: agent|script` × `autonomy: interactive|auto`) is clear and an agent could understand the *target state*. What's ambiguous or missing:

- **The observability deliverable is underspecified.** Step 4 says "capture stdout/stderr → task log + Slack notify on done/fail," but doesn't say *where* in the log, what format, or whether it tees vs. redirects. For `launch_script.py` there's already a Slack `post` on failure (lines 159-169) and an `append_log` of the exit code — the ticket should say whether it's reusing that path or adding a new one. For the *agent* auto path (`claude -p`/`codex exec`), there is currently no capture machinery at all, and "capture to task log" is hand-waved over what is actually the hardest part of the ticket.
- **"Slack notify on done/fail" for unattended *agent* runs** — the done-marker/sentinel supervisor (`run_with_done_marker`) is only wired for `interactive` today (launch.py:485-499). For unattended agent runs there's no supervisor, so "notify on done" needs a mechanism that doesn't exist yet. The ticket treats this as a small gating change but it's a new code path.
- The migration mapping is stated clearly, but the ticket never says what happens to **`--mode` CLI flags** that humans/scripts pass (see #4).

### 2. Workflow fit — `code/with-review` is appropriate but strained by size

The shape (multi-file Python change + tests + docs, peer-reviewed before PR) genuinely fits `code/with-review`. No mismatch in *kind*. The strain is *volume*: the peer-review step (a single `/code-review` or `codex review` pass) and the human `review` gate are sized for a normal diff. This ticket's diff will touch ~125 ticket files plus core launch/validate/compose/recurring logic — a peer reviewer cannot meaningfully review a 125-file mechanical migration mixed in with a semantically tricky stdin/capture change. That argues for splitting (see #4) more than for changing the workflow.

### 3. Contexts — `autonomy/triage` is correct; nothing should be inlined

`autonomy/triage` is the right and only attachment: the ticket's core claim ("`fully-automated → autonomy: auto`, other three → `interactive`") is exactly the projection of that context's four tiers, which I confirmed reads as described. It is genuinely needed as live behavioral contract, not a copyable fact — so attaching (not inlining) is correct per Relay's principle.

One thing arguably missing: the ticket references `wire-autonomy-triage-into-impl-ready-workflows` and `bootstrap/ticket/SKILL.md` as the upstream/downstream of this change but does **not** attach `bootstrap/ticket` as a context even though step 7 edits it. The implementer will have to go find the current `mode` references in it cold. Either attach it or copy the exact lines being changed.

### 4. Scope — this is the ticket's biggest problem: it bundles ~3 tickets

This is **not** one coherent change. It's at least three:

- **(A) Schema split + hard migration** — add `autonomy`, redefine `mode` to `agent|script`, migrate ~125 files (114 `mode: interactive`, 11 `mode: script`), update validator, templates (both copies), `retrofit.py:165` ordering, contexts/docs. This is large but mechanical and low-risk.
- **(B) Unblock unattended *agent* execution** — delete the `auto` hard-bail, build the headless run path, stdin handling, **output capture** (the genuinely novel/risky engineering), done/fail notification without the interactive supervisor.
- **(C) Recurring + retire integration** — `recurring.py` auto-refusal removal, and (unmentioned) `retire.py`'s own auto ban.

(A) is a pure refactor that should land first and green on its own. (B) is where the real design risk lives and deserves its own review. Bundling them means the reviewer can't separate "did the rename break anything" from "is the unattended-capture design sound." I'd split A from B+C at minimum.

### 5. Assumptions to question before launch

- **"Close stdin to /dev/null for unattended runs" — partly right, partly risky.** For `claude -p` / `codex exec` (headless agents), closing stdin is standard and fine. But the *rationale* given ("so input-needing work fails fast instead of hanging") is questionable for an LLM agent: `claude -p` doesn't read interactive stdin anyway, and some agent CLIs read the *prompt itself* from stdin in headless mode. The implementer must verify how each configured agent CLI consumes its prompt before redirecting stdin to `/dev/null`, or an unattended run could get an empty prompt. The ticket asserts the behavior without checking the CLI contract.
- **Gating capture on attended-vs-unattended is sound in principle** (don't pipe a TTY REPL — correct, piping would break `claude`'s interactive UI). But note the gate key changes from `mode` to `autonomy`, and the existing TTY check (`_interactive_stdio_has_tty()`, launch.py:281) and the PTY supervisor (launch.py:485) are *also* keyed on `mode == "interactive"`. The plan mentions re-keying compose and dispatch but does **not** explicitly call out re-keying these two, which are the load-bearing ones.
- **The migration mapping loses no information for what's actually in the repo** — but note: there are **zero `mode: auto` tickets** in the entire repo right now (I counted: 114 interactive, 11 script, 0 auto). So the `auto → (agent, auto)` arm of the mapping is exercised only by tests/templates, not live tickets. That's fine, but it means the "unblock auto" half of the ticket has no real consumer until recurring templates opt in — worth confirming the recurring templates (`digest`, `dream`, `skill-update`, `autoclose-merged`) are actually meant to flip to `autonomy: auto`, since today they're `mode: script` or interactive.

**Call sites the plan's file list MISSES** (this is a concrete defect — these will break the hard migration if untouched):

- `src/relay/commands/create.py:26-29, 47-50` — `--mode` option default `"interactive"` and help text "interactive, auto, or script." Not in the plan. After migration, `relay draft --mode interactive` would write a now-invalid value.
- `src/relay/create.py:31, 135, 176` — `create_task` takes `mode` and writes it to frontmatter / log. The default and the field need to account for `autonomy`.
- `src/relay/commands/retire.py:29-33, 51-58` — has its **own** `--mode auto` ban and `--mode must be 'interactive'` check, independent of `launch.py`. The plan deletes the launch.py bail but never mentions retire's. This will be left enforcing dead vocabulary.
- `src/relay/commands/launch.py:88-92, 145-146` — the `--mode` override option and its validator (`mode_override not in ("interactive", "auto")`). Plan says "rework the override guards" for dispatch but doesn't mention this CLI-level validator, which will reject `agent`/`script` and accept the now-invalid `auto`/`interactive`. The override semantics also get muddy: should `--mode` still exist, or split into `--mode`/`--autonomy`?
- `src/relay/commands/status.py:29, 130, 202-214` — `status` table has a `mode` column and `--order-by mode`. Cosmetic, but if `autonomy` matters operationally it probably wants a column too; at minimum the displayed value changes meaning.
- `src/relay/retrofit.py:162-173` — canonical field-ordering list includes `mode` but not `autonomy`; needs the new field inserted or retrofit will scatter it.
- `src/relay/recurring.py:354, 377, 489, 510, 545` — `_effective_mode` is threaded through `create_recurring_instance` (`effective_mode=`, `mode=`), so removing the auto refusal isn't a one-line delete; the whole `effective_mode` resolution needs to produce both `mode` and `autonomy`.

The plan's "Approach" file list names `ticket.py`, `validate.py`, `launch.py`, `launch_script.py`, `compose.py`, `recurring.py`, templates, contexts, and four test files. It does **not** name `create.py`, `commands/create.py`, `commands/retire.py`, `commands/status.py`, or `retrofit.py`. An agent following the file list literally would ship a half-migrated CLI that writes invalid tickets via `relay draft`/`relay retire`.

### Bottom line

Strong research, accurate citations, clean conceptual model. But: **split it** (schema-migration vs. unattended-execution are different risk classes), **expand the file list** to the five missed call sites above (especially `create.py`, `retire.py`, and the `launch.py --mode` validator — those are correctness, not polish), and **firm up two hand-waved deliverables** — stdin handling per actual agent-CLI prompt contract, and the agent-side output-capture/done-notification path, which has no existing machinery and is the real engineering in this ticket.
