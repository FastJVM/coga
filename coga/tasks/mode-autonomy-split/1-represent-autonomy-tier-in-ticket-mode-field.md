---
slug: mode-autonomy-split/1-represent-autonomy-tier-in-ticket-mode-field
title: Represent autonomy tier in ticket autonomy field
status: in_progress
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
step: 3 (open-pr)
---

## Description

Finish the `mode` removal by aligning the repo with the current architecture:
`autonomy: interactive | auto` is the only declared execution axis, and
script-vs-agent is deduced from the task's launch shape.

The old `mode` enum (`interactive` / `auto` / `script`) conflated two questions:

- **Is a human at the wheel?** This is declared as
  `autonomy: interactive | auto`.
- **Does this launch run an agent or a deterministic script?** This is deduced:
  a current workflow step whose skill declares `script:`, or a no-skill
  step/workflow-less task with ticket-level `script:`, runs as a script;
  otherwise Coga composes an agent prompt.

There is no replacement `mode: agent | script` field. Deducing script dispatch
keeps ticket frontmatter smaller and avoids redundant state that can drift from
the workflow or skill that actually determines execution.

This is where the autonomy decision the triage tier produces gets its enforced
home: `fully-automated -> autonomy: auto`, the other three tiers ->
`autonomy: interactive`. The four-tier vocabulary stays advisory at authoring
time (per `wire-autonomy-triage-into-impl-ready-workflows`); the binary
`autonomy` field is its coarse, enforced projection.

**Behavior is preserved exactly.** This ticket is a representation cleanup, not
the unattended-execution work. In particular:

- `autonomy: auto` agent launches stay blocked in `coga launch`.
- `coga retire --autonomy auto` stays blocked.
- Recurring still refuses `autonomy: auto` agent templates, while script
  templates bypass the agent-only ban because script dispatch is deduced and no
  agent prompt is composed.

Removing the auto blocks, adding unattended agent output capture, and changing
recurring opt-in behavior remain the follow-up
`2-unblock-unattended-execution-mode-autonomy-auto`.

Defaults are backwards-compatible: a ticket with no `autonomy:` behaves as
`autonomy: interactive`, identical to the old attended-agent default.

## Context

Split out of `wire-autonomy-triage-into-impl-ready-workflows`, which wired
`autonomy/triage` into `bootstrap/ticket` at authoring time but deliberately
left the structured representation cleanup to this ticket. The implementation
has since moved to the better shape: declare autonomy only, deduce script vs.
agent.

**Verified live state on current `main`:**

- `src/coga/ticket.py` — `CANONICAL_TICKET_KEYS` includes `autonomy` and no
  `mode`; `Ticket.autonomy` defaults to `interactive`.
- `src/coga/validate.py` — `VALID_AUTONOMY = {"interactive", "auto"}`;
  there is no `VALID_MODES`.
- `src/coga/commands/launch.py` — exposes `--autonomy`, rejects invalid
  `autonomy` overrides, blocks agent launches when effective autonomy is `auto`,
  and applies the TTY/supervisor path only for `autonomy == "interactive"`.
- `src/coga/commands/launch_script.py` — `is_script_launch()` deduces script
  dispatch from the current step's script-backed skill or the ticket-level
  `script:` field.
- `src/coga/compose.py` — the interactive vs auto prompt layer keys on
  `autonomy`; script launches do not compose a prompt.
- `src/coga/recurring.py` — `_effective_autonomy()` defaults templates to
  `auto`, refuses `auto` for agent templates while the freeze remains, and lets
  script templates bypass the agent-only ban.
- `src/coga/create.py`, `src/coga/commands/create.py`,
  `src/coga/commands/retire.py`, and `src/coga/commands/status.py` already use
  `autonomy`.
- `coga/contexts/coga/architecture/SKILL.md` already documents the
  autonomy-only model and says script-vs-agent is deduced.

**Migration scope:** remove remaining stale `mode:` frontmatter and stale
`mode` prose from live tasks, example fixtures, bootstrap templates, packaged
contexts/skills, README/docs, and tests. The old mapping is:

- `mode: interactive` -> `autonomy: interactive`
- `mode: auto` -> `autonomy: auto`
- `mode: script` -> remove `mode`; make sure the task has a script-backed
  workflow step or ticket-level `script:`

**Back-compat decision: hard migrate (no dual vocabulary).** Rewrite shipped
files in the PR. The live system should not present `mode` as a supported task
frontmatter field or CLI option.

**Out of scope:** unblocking unattended agent execution / output capture /
recurring agent opt-in (-> `2-unblock-unattended-execution-mode-autonomy-auto`);
remote/cloud dispatch (a later "when mature" ticket).

## Approach

1. **Confirm code shape** — keep `autonomy` as the only declared execution
   field; do not reintroduce `mode: agent|script`.
2. **Frontmatter migration** — replace remaining `mode:` frontmatter in live
   tasks, example fixtures, bootstrap tickets, and tests. For old script tasks,
   ensure script execution is represented by `script:` or a workflow step whose
   skill declares `script:`.
3. **Docs / contexts / skills** — update stale prose in README/docs, packaged
   bootstrap contexts/skills, and local Coga contexts to say `--autonomy` and
   explain script dispatch as deduction rather than `mode: script`.
4. **Validation** — make sure no shipped task/template relies on `mode`; if a
   `mode` key appears in task frontmatter, it should fail loud enough that the
   old vocabulary does not silently persist.
5. **Tests** — update stale fixture strings and expectations, then run
   `python -m pytest` and `coga validate --json`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: codex/mode-autonomy-field
worktree: /tmp/coga-mode-autonomy-field
commit: 9c94404e Represent ticket autonomy without mode

## Implement summary (Codex, 2026-06-26)

Implemented the hard migration in the feature worktree:

- Migrated remaining actual `mode:` frontmatter to `autonomy:` in bootstrap
  tickets, install-era task fixtures, tests, and embedded examples.
- Updated README/docs/live contexts/packaged contexts/skills to teach
  `--autonomy` plus deduced script dispatch instead of declared task `mode`.
- Added validator coverage so a legacy `mode:` frontmatter key is now a
  `legacy-frontmatter-key` error instead of a generic orphan-extension warning.
- Kept behavior unchanged: agent `autonomy: auto` launches and
  `retire --autonomy auto` remain blocked; script dispatch remains deduced.

Verification:

- `python -m pytest` -> 898 passed, 1 skipped.
- `PYTHONPATH=/tmp/coga-mode-autonomy-field/src python -m coga.cli validate --task mode-autonomy-split/1-represent-autonomy-tier-in-ticket-mode-field --json` -> clean.
- Full `coga validate --json` still fails on pre-existing unrelated repo-state
  drift: install/README bad frontmatter, old install tasks missing slugs/fences,
  several marketing/v2 missing-step errors, plus existing unknown-assignee and
  stale in-progress warnings. No legacy `mode:` frontmatter remains in the
  changed shipped/task surfaces.

## Decision update (Codex + nick, 2026-06-26)

Nick confirmed the better model is to **deduce script-vs-agent** rather than
reintroduce a declared `mode: agent|script` field.

Current final model:

- `autonomy: interactive | auto` is the only declared execution axis.
- Script-vs-agent is deduced from the current workflow step or ticket:
  a script-backed skill / ticket-level `script:` runs a script; otherwise Coga
  composes an agent prompt.
- The four-tier autonomy rubric still projects to the binary field:
  `fully-automated -> autonomy: auto`; everything else -> `interactive`.
- Back-compat remains a hard migration: clean up stale `mode:` frontmatter and
  stale `--mode` / `mode: script` prose rather than supporting two vocabularies.

Behavior remains unchanged in this ticket:

- Agent `autonomy: auto` launches stay blocked.
- `retire --autonomy auto` stays blocked.
- Recurring agent templates with `autonomy: auto` stay blocked, while recurring
  script templates can still run unattended because they do not compose an agent
  prompt.

Scope B+C (unblock unattended agent execution + capture/notify machinery +
recurring agent opt-in) remains the follow-up draft
`2-unblock-unattended-execution-mode-autonomy-auto`. Remote/cloud dispatch
remains later.

## Peer review (Codex, 2026-06-26)

Ran native review from the feature worktree:

- First sandboxed `codex review --base main` failed before review with
  read-only filesystem app-server init error.
- Retried escalated; review completed with one must-fix P2:
  hard-failing legacy `mode:` was correct, but shipped guidance/templates still
  taught old mode vocabulary in places like `coga/principles` and recurring /
  skill templates.

Applied the must-fix on branch `codex/mode-autonomy-field`:

- Commit `5244dcbd` — `peer-review: finish mode vocabulary cleanup`.
- Updated canonical + packaged principles, recurring scaffolds, skill template,
  seed log text, base prompt wording, and user-facing launch/ticket/project
  output so shipped Coga surfaces no longer present old task `mode` vocabulary.
- Left historical task bodies and `coga/log.md` alone; those are not shipped
  guidance and the log is CLI-owned.

Verification after the peer-review fix:

- `python -m pytest` -> 898 passed, 1 skipped.
- `PYTHONPATH=src python -m coga.cli validate --task mode-autonomy-split/1-represent-autonomy-tier-in-ticket-mode-field --json` -> clean.
- Focused grep over README/docs/canonical contexts/recurring/skill template/
  resources/commands for stale `mode: ...`, `--mode`, `Pick a mode`,
  `mode=auto`, and `three modes` shipped-guidance patterns -> clean.

## Historical evaluator review (superseded two-field proposal)

This review predates the deduced-script decision above. Keep it only as history
for why unattended-agent execution was split out; do not treat its
`mode: agent|script` target shape as current spec.

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

## Usage

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":1327872,"cli":"codex","input_tokens":385151,"model":"gpt-5.5","output_tokens":17086,"provider":"openai","schema":1,"session_id":"019f05d4-a21b-7973-8911-e4cb2900a998","slug":"mode-autonomy-split/1-represent-autonomy-tier-in-ticket-mode-field","step":"implement","title":"Represent autonomy tier in ticket mode field","ts":"2026-06-26T21:57:25.602259Z","usage_status":"ok"}

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":12339200,"cli":"codex","input_tokens":289069,"model":"gpt-5.5","output_tokens":33801,"provider":"openai","schema":1,"session_id":"019f05f0-3ad8-75c2-8bcb-aff2e6a6e177","slug":"mode-autonomy-split/1-represent-autonomy-tier-in-ticket-mode-field","step":"implement","title":"Represent autonomy tier in ticket autonomy field","ts":"2026-06-27T00:03:49.777616Z","usage_status":"ok"}

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":4979456,"cli":"codex","input_tokens":246900,"model":"gpt-5.5","output_tokens":14422,"provider":"openai","schema":1,"session_id":"019f0663-c6b2-7682-9249-db96ab2ebdf3","slug":"mode-autonomy-split/1-represent-autonomy-tier-in-ticket-mode-field","step":"peer-review","title":"Represent autonomy tier in ticket autonomy field","ts":"2026-06-27T03:49:00.675245Z","usage_status":"ok"}

{"agent":"claude","cache_creation_input_tokens":null,"cache_read_input_tokens":null,"cli":"claude","input_tokens":null,"model":null,"output_tokens":null,"provider":"anthropic","schema":1,"session_id":"5ac22599-7093-4d98-b224-7a1b116d72c1","slug":"mode-autonomy-split/1-represent-autonomy-tier-in-ticket-mode-field","step":"open-pr","title":"Represent autonomy tier in ticket autonomy field","ts":"2026-06-27T03:49:00.752108Z","usage_status":"unknown"}
