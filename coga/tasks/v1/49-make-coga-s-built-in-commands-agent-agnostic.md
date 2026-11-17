---
title: Make coga's built-in commands agent-agnostic
status: in_progress
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
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
step: 2 (evaluate-design)
agent: claude
launch_generation: 5a43a6ea-2bc4-41d7-b1c4-0933aeb0a020
---

## Description

`coga chat`, `coga ticket` and `coga build` launch tickets pinned to `agent: claude` (`bootstrap/orient`, `bootstrap/ticket`, `coga-build`). In a repo that declares only Codex, which `coga init` now writes on a Codex-only machine (v1/20), those commands fail, and `--agent codex` cannot rescue them because it cannot override a pin naming an undeclared agent.

Done when each built-in command runs on whichever agent the repo declares, with no hard-coded agent, and the Codex-only limitation note in `coga/configuration` is removed. Also fix init's none-found next steps, which still say "Run `coga build` with Claude Code".

Root cause: each launch target names `claude` in its own `agent:`. Launch
derives the operator *before* applying `--agent` (`src/coga/launch.py`
`_target_operator()` → `src/coga/bump.py` `resolve_main_agent()`), and
`resolve_main_agent()` refuses an explicit name missing from `cfg.agents`, so
the override never gets a chance. The fix is to stop pinning: an absent
`agent:` already resolves to `Config.default_agent()` on every path these
commands use, so removing the pin makes each command follow the repo's
declared agents with no new resolution code.

### Acceptance criteria

- [ ] `src/coga/resources/templates/coga/bootstrap/orient/ticket.md` and
      `src/coga/resources/templates/coga/bootstrap/ticket/ticket.md` carry no
      `agent:` key.
- [ ] `src/coga/resources/templates/coga/tasks/coga-build.md` carries no
      `agent:` key and ships as an activatable draft (see Proposed shape), so
      its main agent is selected from the repo's configured default at first
      launch rather than baked into the template.
- [ ] In a repo whose config declares only `[agents.codex]`:
      `coga chat`, `coga ticket` (bare and with a title), and `coga build`
      each resolve to `codex` without `--agent`; `coga chat --agent codex`
      and `coga build --agent codex` also work. Covered by tests (CLI or
      launch-level, with the agent binary faked as existing tests do).
- [ ] In a repo declaring both with `default_agent = "codex"`, `coga chat`
      and `coga build` route to codex; with no `default_agent`, they route to
      the first-declared table (today `claude` in the shipped `coga.toml`), so
      a default install's behavior is unchanged.
- [ ] `coga build` on a freshly initialized empty repo activates `coga-build`,
      persists `agent: <default>`, and lands on step 1 `gather-and-spec`
      exactly as before; `coga validate --json` on a fresh init (interactive
      found-one, interactive none-found, non-interactive) reports no
      `unknown-agent` / `missing-main-agent` finding for `coga-build`.
- [ ] Init no longer rewrites `agent:` in delivered tickets:
      `_stamp_agent_into_delivered_tickets()` and its call site in
      `src/coga/commands/init.py` are removed (nothing ships a pin to
      repoint). `_template_default_agent()` is kept only if the next-steps
      text still needs it.
- [ ] Init's next steps never name an agent the repo does not declare. With
      at least one declared agent the line stays
      "Run `coga build` with <first declared>" plus the `--agent`
      alternatives. With none declared (interactive none-found), the line
      names no agent — e.g. "Once an agent CLI is installed and its
      `[agents.*]` table uncommented, run `coga build` …" — and
      `tests/test_init.py`'s none-found test asserts "with Claude Code" is
      absent.
- [ ] The Codex-only limitation paragraph ("One limit to know in a repo that
      declares Codex but not Claude Code …") is removed from
      `coga/configuration` (`src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md`),
      and the surrounding text says chat/ticket/build follow
      `default_agent` (or `--agent`, or `[authoring] agent` for `coga ticket`).
- [ ] Every other surface that states the pin is corrected in the same PR:
      the `default_agent` comment in `src/coga/resources/templates/coga/coga.toml`
      ("their packaged tickets pin `agent: claude`"), `README.md` ("chat and
      ticket interviews default to Claude even when new tasks use Codex"),
      `coga/init` (the "repoints delivered tickets" sentence and the
      none-found "`coga validate` reports the onboarding ticket's `agent:` as
      unknown" sentence), and `docs/contexts/coga-dev/internals/agent-config/SKILL.md`
      ("The packaged … tickets pin `agent: claude`, which outranks the
      default"). `grep -rn "agent: claude" src/coga/resources` matches only
      the illustrative example in `coga/calendar-reminder`.
- [ ] `python -m pytest` passes; `coga validate --json` passes on this repo.

### Proposed shape

1. **Bootstrap tickets.** Delete the `agent: claude` line from
   `bootstrap/orient/ticket.md` and `bootstrap/ticket/ticket.md`.
   - `coga chat`: `_target_operator()` handles a `BootstrapRef` by calling
     `resolve_main_agent(..., allow_prospective_default=True)`, which returns
     `cfg.default_agent()` for an absent value. No code change.
   - `coga ticket`: `src/coga/authoring.py` `resolve_authoring_agent()` then
     skips term 5 (`bootstrap_ticket.agent` is None) and falls through to
     `cfg.default_agent()`. Update its docstring: term 5 is now a repo-local
     override hook (a local `bootstrap/ticket` copy may still set `agent:`),
     not a packaged default. Keep the term itself.
2. **Onboarding ticket.** Rewrite `tasks/coga-build.md` frontmatter to an
   unactivated draft: `status: draft`, `workflow: build/onboarding` (bare
   string ref), no `step:`, no `agent:`. `coga launch` already
   auto-activates a draft (`launch.py` `_prepare_auto_activate()` →
   `mark.py` `prepare_active()`), which freezes the workflow from
   `bootstrap/workflows/build/onboarding.md`, seeds step 1, and persists the
   configured default via `_select_main_agent()`. This keeps the
   "live tickets always carry `agent:`" invariant (`validate.py`
   `_check_main_agent()`) intact instead of weakening it.
   - The draft blackboard gate (`mark.py`
     `_refuse_unsynthesized_draft_blackboard()` →
     `blackboard.py` `prelaunch_blackboard_synthesis_reason_text()`) refuses
     a non-stock draft blackboard at or above
     `PRELAUNCH_SYNTHESIS_TEXT_CHARS`. Verify the shipped onboarding
     blackboard prose passes; if not, move that prose into `## Context` (or
     shorten it to the stock placeholder) rather than adding a
     `## Production notes` escape.
   - In `src/coga/commands/init.py`, change the seeded audit line from
     `created (mode=interactive, status=active)` to `status=draft`, and
     update `tests/test_init.py` (`test_init_records_onboarding_creation_at_runtime`
     and the coga-build template test that asserts `status: active` /
     `step: 1 (gather-and-spec)`; assert instead `status: draft`,
     `workflow: build/onboarding`, and no `agent:`).
   - Check `tests/test_clean_install_harness.py` and any test that seeds a
     `coga-build` fixture with `status: active` for assumptions about the
     template's status; fixtures that hand-write their own ticket can stay.
3. **Init.** Remove `_stamp_agent_into_delivered_tickets()` and the
   `configured_agents[0] != template_default_agent` block that calls it.
   In the next-steps builder (the `if is_empty:` branch that computes
   `build_agent`), when `declared_agents` is empty emit an agent-neutral
   `coga build` line instead of falling back to `template_default_agent` /
   `AGENT_CLIS[0]`. Drop `_template_default_agent()` and its local if
   nothing else uses them.
4. **Docs and comments** as listed in the acceptance criteria. For
   `coga/configuration`, replace the limitation paragraph with one sentence
   that `coga chat`, `coga ticket`, and `coga build` run on the default
   agent unless `--agent` (or `[authoring] agent` / `COGA_AUTHORING_AGENT`
   for `coga ticket`) says otherwise. Also amend the preceding sentence
   ("This does not change … or select the interviewer for `coga chat` and
   `coga ticket`") — it is now false: `default_agent` does select them.
5. **Tests.** Add a Codex-only routing test per command (chat, ticket,
   build) and a `default_agent = "codex"` two-agent test; update
   `tests/test_init.py` none-found next-steps assertions. Existing tests that
   hand-write `agent: claude` into their own fixtures are unaffected.

Order: 1 → 2 → 3 → 4 → 5, running `python -m pytest tests/test_init.py
tests/test_launch.py tests/test_authoring*.py tests/test_cli.py` between steps.

### Out of scope

- Migrating already-initialized repos whose committed `coga/tasks/coga-build.md`
  still says `agent: claude`. `coga update` treats it as a mutable fresh
  scaffold (`FRESH_SCAFFOLDS` in `src/coga/commands/update.py`) and must not
  rewrite it; such a user fixes it by editing the line or passing a declared
  agent through authoring. Mention this in the PR description only.
- Making `--agent` able to override an explicit pin that names an undeclared
  agent. The fail-loud rule in `resolve_main_agent()` stays.
- Making `--agent` on a draft's first launch persist as the ticket's
  `agent:` (today it overrides that session only and activation freezes the
  default). Same behavior as every other draft.
- The `agent: claude` in the `coga/calendar-reminder` skill's example
  frontmatter — illustrative, not a launch target.
- Any change to `default_agent()` precedence, peer selection, or `[agents.*]`
  parsing.

## Context

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design notes (design step)

- Mechanism verified: `_target_operator()` resolves the ticket's own
  `agent:` before `--agent` is consulted (`launch_agent = agent_override or
  operator.name` comes after), and `resolve_main_agent()` rejects an
  undeclared explicit name. An absent `agent:` with
  `allow_prospective_default=True` already yields `default_agent()`.
- Today `coga build` survives Codex-only *interactive* init only because
  `_stamp_agent_into_delivered_tickets()` repoints `claude`→`codex`. It
  still breaks in the none-found path (nothing stamped, user later
  uncomments `[agents.codex]`) and in any repo hand-edited to Codex-only.
- coga-build as a draft was chosen over "active without `agent:`" because the
  latter fails `validate._check_main_agent()` (`missing-main-agent`) and
  would need the activation invariant weakened.
- Checked: the shipped coga-build blackboard (273 chars, no authoring
  headings) passes `prelaunch_blackboard_synthesis_reason_text()` (limit
  600), so it can stay as-is under `status: draft`.

## Open Questions

1. **coga-build as `status: draft`.** Recommended above. Side effects to
   accept: `coga status` lists it as draft rather than active, and if a
   human picks it in `coga megalaunch` with draft authoring on, megalaunch
   would run the authoring interview on it before launching. Alternative:
   keep it `active` with a frozen snapshot and have init *insert*
   `agent: <first declared>` (none-found case: insert nothing and let
   `coga validate` flag it until an agent is declared — i.e., today's
   none-found limitation remains for `coga build`). Owner: draft (fully
   agnostic) or active+init-insert (smaller blast radius)?
2. Should `coga ticket`'s resolution chain keep term 5
   (`bootstrap/ticket`'s `agent:`) as a local-override hook, or drop it now
   that the packaged ticket never sets it? Spec keeps it (zero-cost, and
   `[authoring] agent` already covers the machine-local case).
