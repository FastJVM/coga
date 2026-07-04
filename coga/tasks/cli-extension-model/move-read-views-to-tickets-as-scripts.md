---
slug: cli-extension-model/move-read-views-to-tickets-as-scripts
title: Move show/status into their lowest-tier mechanism
status: in_progress
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
contexts:
- coga/extension-model
- coga/architecture
- coga/codebase
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
secrets: null
step: 2 (peer-review)
---

## Description

Per Nico's plan — push each command to the **lowest tier** it can use — move
zach's remaining core read commands out of `commands/*.py`:

- **`show`, `status`** (read-only views) → **tickets-as-scripts** (`mode:
  script`), per Nico's reads decision below. *(The other reads — `validate`,
  `skill status`, `recurring list` — share this destination but aren't the
  immediate focus.)*
- **`chat`, `build`** → already aliases — lowest tier already; verification
  tracked by `audit-chat-and-build-are-core-free`.
- *(`ticket`'s move is tracked separately by `move-ticket-authoring-out-of-core`
  — the redo of closed PR #425 — not part of this.)*

This is **group 1** of `cli-extension-model/move-command-logic-to-tickets`.
Immediate work: `show` and `status`. Per the *no-inversion* guardrail the
render Python relocates **unchanged**; only its home changes. Start with `show`
(a pure render of one task's files) as the proof.

**Depends on `remove-the-shim-concept` landing first** — that ticket purifies
the model (these reads are *tickets-as-scripts*, not "script shims") and
rewrites the `extension-model` contract, which resolves the contradiction noted
below.

## Decision (Nico, 2026-06-23)

Reads **do** move to tickets-as-scripts (`mode: script`) — Nico chose
"minimize core" over `extension-model`'s "reads stay commands" rule.
Consequences:
1. `extension-model` currently **contradicts** this — it says reads are
   commands and "wrapping these in a task buys nothing." `remove-the-shim-concept`
   is rewriting that contract; coordinate so the ratified context matches (flag
   to Nico at design review).
2. The **crux below still stands** — Nico set the *direction*, not the
   *mechanism*: a `mode: script` ticket can't take a transient `<slug>` arg.
3. `relay show` likely **stays** as a thin command entry that *launches* the
   script render — the command isn't removed (per zach), the render moves.

## Context

Understand these before touching code, in order:

1. `relay/extension-model` — the three homes and the two guardrails: *no
   inversion* (relocate tested Python unchanged; never rewrite a deterministic
   render as agent judgment) and *no worse Typer*. The reads are classified
   movable there.
2. The two shipped precedents to copy: `automerge → autoclose-merged/sweep` and
   `digest → digest/post` — deterministic command logic *already* running as
   `mode: script` steps. The move is "do what these did."
3. `bootstrap/orient` — the stateless ticket shape (no status/log/lock) the
   reads become.
4. The current read commands in `src/relay/commands/` (`show.py`, `status.py`,
   …) — the Python to relocate unchanged.
5. `relay/architecture` — `mode: script` launches and the env vars a script
   step receives (`RELAY_TASK_SLUG`, `RELAY_RELAY_OS_ROOT`, …).

**The crux to settle before writing code (this is the `design` step):** the
reads are *parameterized* (`relay show <slug>`, `relay status [dir]`), but a
stateless script ticket is arg-less. The central question to answer first is
*how a parameterized read hands its argument to a script step* — does it stay a
thin command that shells to a script, or something else? This is the **same
parameterized-command-to-ticket problem** as `move-ticket-authoring-out-of-core`;
coordinate on one arg-materialization mechanism rather than inventing two.
Resolve that, then `relay show` (a pure render of one task's files) is the
simplest first conversion.

<!-- coga:blackboard -->

## Implement notes (claude, 2026-07-03)

### Recovered design (was dropped when Nico re-authored the ticket)
The `design`/`review-design` steps ran and a full spec was written to the
blackboard (commit `5108cfec`), but Nico re-authored the ticket to a straight
`code/with-review` workflow (commit `9a14151e`), which reset the body/blackboard
and relaunched into `implement`. No answers to the 4 open questions were
recorded, so I proceed on the spec's **recommended defaults**:

1. **(a) #491-faithful:** render logic → tested `src/coga/views.py` (package);
   thin `coga/show` `script: run.py` skill imports it. Keeps tested Python in the
   package (no-inversion guardrail), matches #491's `ticket`→`coga.authoring`
   collapse and the "coordinate on one mechanism" instruction.
2. **`status`:** keep a thin Typer command over the extracted module; its
   8-flag surface has no clean env channel, so `show` (single operand) gets the
   full script-skill treatment as the proof; `status` gets render extracted + a
   default-view script home.
3. Reword the `coga/extension-model` reads row/prose in this PR (mirrors how
   #491 reworded the `ticket` row) — closes the contradiction Nico flagged.
4. Scope = `show` + `status` only.

### Plan
1. New `src/coga/views.py` — typer-free: `ViewError`, `render_show`,
   `render_status` + helpers (`_format_relative`, `_build_table`,
   `_summary_line`, `_print_blocked`, `_list_dirs`, `_done_hint`,
   `_safe_open_blockers`) and constants (`NARROW_WIDTH`, `ORDER_BY_CHOICES`)
   moved **verbatim**. `sys.exit(2)`/`typer.secho` become raised typed errors
   (`ViewError` for bad `--order-by`; existing `UnknownDirectoryError`/
   `TaskNotFoundError` propagate). `typer.echo` → `print`.
2. Shrink `commands/show.py` + `status.py` to thin heads: Typer sig,
   `load_config`, catch `ConfigError`/`TaskNotFoundError`/`UnknownDirectoryError`/
   `ViewError` → `sys.exit(2)`, call `views.render_*`.
3. `coga/show` script skill (SKILL.md + run.py reading `COGA_VIEW_TARGET`),
   in both packaged `src/coga/resources/templates/coga/bootstrap/skills/` and
   live `coga/skills/` copies (CLAUDE.md sync rule). Mirrors
   `coga/ticket/finalize`.
4. `tests/test_views.py` for the extracted renders; `tests/test_status.py`
   stays green (it exercises the CLI + `coga.tasks`, not command internals).
5. Reword `coga/extension-model` reads row/prose.

### Dev
branch: move-read-views-to-views-module
worktree: /home/n/Code/claude/coga-move-read-views
commit: 3089433e (not pushed; PR is the open-pr step)

### Done (implement step)
- **`src/coga/views.py`** (new): `ViewError`, `render_show`,
  `render_show_from_env` (reads `COGA_VIEW_TARGET`), `render_status`, plus the
  helpers/constants moved **verbatim**. Typer-free; raises typed errors instead
  of `sys.exit`.
- **`commands/show.py` / `status.py`**: shrunk to thin heads (351-line
  status.py → ~92 lines). Catch `ConfigError`/`TaskNotFoundError`/
  `UnknownDirectoryError`/`ViewError` → `sys.exit(2)`, call `views.render_*`.
- **`coga/show` script skill** (SKILL.md + run.py) in both packaged bootstrap
  and live `coga/skills/` copies. Mirrors `coga/ticket/finalize`.
- **`tests/test_views.py`** (new). `tests/test_status.py` unchanged + green.
- **`coga/extension-model`** reads row + Pass-2 prose reworded to the shipped
  thin-head + script-render shape (closes the contradiction Nico flagged).

### Verification
- `python -m pytest`: **1062 passed, 1 skipped** (packaging importorskip).
- **Byte-identical check**: captured `coga show`/`coga status` output across all
  flags (`--all/--order-by/--reverse/--dirs/--blocked/--no-recurse`, `[DIR]`,
  bootstrap-ref, unknown-task/dir, bad `--order-by`) on the branch vs. the
  pre-change files from `main` → **diff empty (IDENTICAL)**.
- `coga/show` `run.py` end-to-end: happy path exit 0; missing env var and
  unknown target both fail loud exit 2.

### Deferred (per design, not this ticket)
- `status`'s 8-flag surface got render-extracted + a thin head but **no**
  dedicated script skill (no clean env channel for 8 flags — Open Question 2);
  `show` (single operand) is the script-skill proof.
- `validate` / `skill status` / `recurring list` share the destination —
  separate follow-ups.

## Adjacent observations (not fixed here)
- The re-authoring dropped a completed design spec from the ticket without
  merging it into the body. Recovered from git; not a code issue.

## Usage

{"agent":"claude","cache_creation_input_tokens":292755,"cache_read_input_tokens":10102182,"cli":"claude","input_tokens":30533,"model":"claude-opus-4-8","output_tokens":104572,"provider":"anthropic","schema":1,"session_id":"a30c8543-13eb-4145-bfee-e8084dee0dfe","slug":"cli-extension-model/move-read-views-to-tickets-as-scripts","step":"implement","title":"Move show/status into their lowest-tier mechanism","ts":"2026-07-04T01:25:06.353364Z","usage_status":"ok"}
