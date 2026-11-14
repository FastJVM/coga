---
title: 04 Compare prompt assembly output quality
status: in_progress
owner: nicktoper
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
    checkout: manual
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
    checkout: manual
  - name: report-to-coga
    skills: []
    assignee: agent
    checkout: manual
step: 2 (human-owns-and-finishes)
agent: claude
---

## Description

Compare the current prompt assembly with a revised candidate on the quality of the work agents produce: PRs, specs and documents. Ticket 02 (`02-compare-current-and-candidate-prompt-assembly`) measured rule compliance only (checkout, completion, authority, input, deterministic gates) on tiny fixture tasks; both arms scored 21/22 and C1 was disqualified for merging an unrequested branch. It never asked whether either form produces better output, which is the improvement the owner wants. Done means the owner has judged blinded output pairs and recorded a decision: positive selection, negative, or inconclusive. Only a positive selection makes `03-implement-the-proven-prompt-assembly` eligible.

### Candidate

C1 is not reused as is. Freeze a revised candidate before any run: C1 with the owner-assist and reconciliation guidance restored so a read-only assist does not merge into a prepared branch (see the reopening conditions in `record-the-prompt-assembly-non-replacement-ruling`). Record its complete prompts and the baseline's in this ticket's directory.

### Cases

Four to six realistic tasks, each ending in an artifact a person can judge, with enough room for quality to differ (no one-line edits). Candidates: a small code change through `code/implement` to a PR; a design spec through `code/design`; a doc/topic edit through `docs/with-review`; a ticket authored with `coga ticket`; optionally an autofix analysis of a real failure record. Two to three repetitions per arm per case, counterbalanced order.

### Primary measure: owner's blinded judgment

The owner judges each pair directly, with arm labels removed: which output is better, or a tie, plus a short reason. No agent pre-filling. Keep the protocol light; the owner expects a clear difference if one exists. If judgments turn out mixed or hard to call, record that as inconclusive and decide then whether a fixed rubric or threshold is worth adding, rather than predeclaring one now.

### Gates

Ticket 02's correctness gates stay hard pass/fail: a better artifact produced through an unrequested merge, unauthorized transition, skipped completion or other gate violation disqualifies that run's arm.

### Secondary, reported only

Wall time, tokens, and how much correction each output needed before it would be acceptable.

### Out of scope

Production prompt or launcher code. Reuse the 02 harness (`adapter.py`, sandbox profile, blinding pack) adapted for larger tasks; it remains disposable evidence, not core.

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
          checkout: create-or-reuse        # Entry checkout: control, create-or-reuse, reuse-required, manual.
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

## Plan (owner-confirmed 2026-11-14, attended session)

- Agent/model: Codex `gpt-6.1-sol`, reasoning `medium`, same pins as ticket 02 (codex-cli 0.167.2 binary, sha256 `a9672d0f…f56b`).
- Candidate C1′ = C1 with the baseline's `## Check the starting checkout` and
  `## Reconcile before publishing` sections restored verbatim in place of C1's
  compressed checkout/reconcile text. Everything else stays C1. Built
  mechanically from baseline prompts by `c1prime.py`. Before C1′ is frozen,
  the builder must reproduce ticket 02's frozen C1 byte for byte.
- Fixture: a clone of this repo at a pinned commit under `/tmp`, with a local
  bare `origin` and no GitHub. Live trial packages (`03-prompt-assembly/`) are
  stripped from the fixture.
- Cases (unattended megalaunch conduct except authoring), each running only
  the step that produces the artifact:
  1. code: `fail-validation-when-local-user-is-required-for-ex`, implement step → branch diff + PR body
  2. design: `warn-when-coga-delete-or-coga-retire-leaves-a-live`, design step → spec
  3. docs: `document-untrusted-tool-output-verify-through-grou`, docs/with-review implement → topic edit
  4. authoring: `coga ticket` guided authoring from a fixed intent with scripted replies → ticket
- 2 reps × 2 arms × 4 cases = 16 sessions in counterbalanced order (rep 2 reverses the pair order). That gives 8 blinded X/Y pairs.
- Gates (ticket 02) are checked mechanically and disqualify the run's arm. Time, tokens and correction are secondary and reported only.
- Owner action needed before the model runs: set `/etc/codex/requirements.toml` aside again (it overrides the sandbox pins, as in ticket 02 containment C1).

## Frozen inputs (2026-11-14, before any model session)

- Pin: production `abbe9ece3` (origin/main at start). Trial venv = non-editable
  `coga 0.4.1` built from `git archive abbe9ece3` with `[test]` (scratchpad, disposable;
  every run hashes its site-packages before and after).
- `c1prime.py verify`: the builder reproduces all 8 of ticket 02's non-analysis
  C1 prompts byte for byte. C1′ = the same builder with `prime=True`.
- `prompts/<case>/{baseline,candidate}.md` were rendered by `adapter.py render`
  through the real path (`launch._launch` / `commands.ticket.ticket`), captured at
  `spawn_agent_session`. A second render was byte-identical for all 8 files.
  Hashes are in `prompts/SHA256SUMS`. At run time the adapter aborts if
  production's prompt differs from the frozen baseline. Otherwise it substitutes
  the frozen arm text as `composed_prompt`.
- Fixture: `git archive abbe9ece3` → `/tmp/coga-quality-trial` with the
  `03-prompt-assembly/` packages stripped. Its single snapshot commit hides the
  trial history. Local bare origin. Case tickets moved to `coga/tasks/<slug>.md`,
  `agent: codex`, and activated with the real `coga mark active`
  (`pristine.json`). Config: pinned codex agent with `peer = "claude"`; the
  claude CLI is set to a missing binary, so the supervisor stops after the one
  measured step. Slack and telemetry are off; `user = "trial-owner"` is set in
  `coga.local.toml`.
- **Design note (megalaunch conduct):** production prepares a branch only for
  `launch_context == "attended"` (`launch._manages_branch_checkout`). Under
  unattended conduct, launch therefore supplies no checkout and the agent runs
  the manual `coga/checkouts` procedure itself. It works this way in production
  megalaunch too, identically in both arms. `facts.checkout` is `null`, as in
  ticket 02's megalaunch cases.
- Codex `max_session` is 1800 s for every case. Authoring dialogue is fixed in
  `dialogues.json`.
- Run order (counterbalanced; B = baseline, C = C1′):
  r1: code B→C, design C→B, docs B→C, author C→B;
  r2: code C→B, design B→C, docs C→B, author B→C.

## Infrastructure events

- 2026-11-14: owner set `/etc/codex/requirements.toml` aside. An infra no-op
  `codex exec` with the pins (6,619 tokens, not a trial session) succeeded on
  the model, committed in the fixture, and was blocked from writing the live repo.
- **F1, replaced run:** the first `code__baseline__r1` (947 s, 3.84 M tokens,
  integrity checks all clean) blocked on four packaging/publication test failures
  on the fixture's unchanged main. Cause: the fixture build's `git add -A` left
  untracked the files that `abbe9ece3` tracks despite matching ignore rules
  (`src/coga/resources/templates/coga/skills/_template/SKILL.md`). Those 4 tests
  pass on live main. Fixed: the build force-adds PIN's exact tracked set and
  asserts equality. The pristine fixtures were rebuilt, and all 8 frozen prompts
  re-render byte-identical. The run is kept in
  `runs/_replaced/code__baseline__r1__untracked-template` and does not count.
  Its agent behaved correctly: it reproduced the failures on main and blocked.

## Progress

- [x] ticket promoted to directory form (attachments)
- [x] c1prime builder reproduces 02's C1
- [x] fixture + case tickets; baseline/C1′ prompts frozen under `prompts/`
- [x] owner set `/etc/codex/requirements.toml` aside (2026-11-14)
- [x] infra check; 16 counted sessions (2026-11-14, 18:42–20:20 UTC)
- [x] blind pack `blind/` (8 pairs), key and gates sealed
- [ ] owner: blinded verdicts, then decision (step human-owns-and-finishes)
- [ ] owner: restore `/etc/codex/requirements.toml` from `.trial-aside`

## Handoff (agent-produces → human-owns-and-finishes)

- **Judge** `blind/<pair>/{X,Y}/artifact.md` and fill `blind/verdicts.csv`:
  `better` = X | Y | tie, a one-line reason, and optionally `correction_X`
  and `correction_Y`. `blind/README.md` explains what each case's artifact
  contains.
  - Do not open `blind-key.json` (sha256 `d5580c5f…094ce`) or `gates.json`
    (arm-labeled) until every verdict is in.
  - Raw runs are under `runs/`. Their `record.json`, delivered prompts and
    rollouts reveal the arm.
- **Gates:** all 16 runs passed the mechanical checks, so no arm is
  disqualified and the comparison is on quality alone. Details are in
  `report.md` §1.
- **Not yet known:** whether the arms differ in quality, and the arm-split
  secondary numbers (wall time and tokens). Per-run totals ranged from about
  120–180 s for design and docs, about 835–870 s for code, and about 230–300 s
  for authoring.
- **After the verdicts:** record the verdict-sheet hash in `report.md` §3,
  unblind, and fill §3–5. The decision is positive, negative or inconclusive,
  and only a positive one makes ticket 03 eligible. Report-to-coga then
  records it.
- **Evidence publication:** this directory is 35 MB and launch publishes it
  to `main` after this session. `runs/*/codex-session-*.jsonl` are full Codex
  rollouts, including `session_meta` account/user IDs and encrypted reasoning.
  Owner decision (2026-11-14): publish everything as is, then bump.
- **Machine:** `/etc/codex/requirements.toml` is still set aside. Restore it
  from `.trial-aside` once no more sessions are needed. The `/tmp/coga-quality-trial*`
  fixtures and the scratchpad venv are disposable.
- **Disposable tooling** in this directory, which is evidence and not core:
  `adapter.py`, `c1prime.py`, `blind.py`, `ctl.sh`, `seq.sh`, `answer.sh`,
  `autoanswer.sh`.
