---
title: 03 Implement the proven prompt assembly
status: active
owner: nicktoper
contexts:
- coga-dev/microkernel/objectives
- coga-dev/principles
- coga-dev/codebase/gotchas
- coga-dev/testing
- coga-dev/microkernel
- coga-dev/project-stage
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
    checkout: control
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
    checkout: control
  - name: review-design
    skills: []
    assignee: owner
    checkout: control
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 1 (design)
agent: claude
---

## Description

Fix structural defects in the current prompt assembly (`compose.compose_prompt_report`). Owner rewrite, 2026-11-15: the experiment line ended with no positive selection (ticket 02: C1 disqualified; ticket 04: output quality inconclusive, current assembly kept), so this ticket no longer migrates to a new assembly form. Instead, it fixes defects in the current form that are visible in any captured launch prompt. Done means each defect below is fixed with unit-test coverage, a before/after `coga launch <ref> --prompt-report` (plus the full composed text) shows the change on a real ticket, and `coga/prompt-composition` describes the result.

### Defects to fix

Observed in the composed prompt for this ticket on 2026-11-15 (85 KiB, ~21.7k tokens):

1. **Template comments compose.** The ticket-guide HTML comment (`<!-- Ticket guide — keep this comment … -->`, about 5 KiB, in 83 tickets) is in `## Context` and is passed through verbatim as "Task-specific context" on every launch. Template comments must not reach the agent. The file on disk keeps the comment for human editors.
2. **Frontmatter composes.** Context and skill layers include their YAML frontmatter (`---\nname: …\ndescription: …\n---`). Its `---` delimiters are indistinguishable from the `---` separators between layers.
3. **Heading hierarchy collides.**
   - Each layer's wrapper `## <title>` is followed by the resource's own H1, so titles repeat (`## Coga base prompt` / `# Coga base prompt`, `## Repo context` / `# Context`).
   - The resources' `##` sections sit at the same level as the layer headings, so the prompt is one flat list of `##` headings.
   - The blackboard's own `## Blockers` and `## Gate status` look like top-level prompt sections.

   Make the layer boundaries unambiguous, for example by demoting headings inside each layer. The design picks the mechanism, which must stay fence-aware (no rewriting `#` lines inside code fences).
4. **Open blockers appear twice.** When the blocker preamble lists them, the blackboard repeats them under `## Blockers`. Compose them once, and keep resolved blocker history available where it matters.
5. **Template filler composes.** The blackboard placeholder ("The blackboard is a notepad to be written to often …") goes in as current state.

### Tests

Add unit tests in `tests/test_compose.py` (and fixtures as needed) that cover each defect: template comment absent from the composed prompt, frontmatter absent, heading levels inside layers below the layer level (including a fenced `#` line left untouched), blockers composed once, and filler absent. Keep the `--prompt-report` layer accounting correct. Update the seeded fixture under `tests/fixtures/seeded-repo/` if the smoke path changes.

### Scope and boundary

Change composition only. Do not change prompt resource wording beyond what the heading fix requires, the layer order, launch/checkout behavior, or `recurring_autofix.build_prompt` unless it shares the defective helper. Guided authoring (`commands.ticket._authoring_ticket`) composes through the same path: check it, and keep the ticket guide visible wherever the authoring agent needs it to edit the file. That is a design decision to record, not a guess.

## Context

Prior scope: this ticket was drafted to migrate to an experimentally selected assembly form. It is now ineligible, because tickets 02 and 04 produced no positive selection. Their evidence is `coga/tasks/v1/microkernel/03-prompt-assembly/02-compare-current-and-candidate-prompt-assembly/report.md` and `…/04-compare-prompt-assembly-output-quality/report.md`. That scope is dropped and is not to be revived here.

Implementation source: `src/coga/compose.py` (`compose_prompt_report`, `_section`, `_extract_section`, `_skill_layers`, `_step_layers`), `src/coga/taskfile.py` (`split_body`, `body_sections`) and `src/coga/blackboard.py` (`blackboard_for_prompt`). Reproduce the defects with `coga launch <ref> --prompt-report` and with `compose.compose_prompt(cfg, ref, read_ticket(ref))` for the full text.

The contract owner is `src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md` ("Layer order", "What each layer reads", "The ticket is a three-region extract", "Blocker preamble versus authoring", "What never composes"). Update it in the same PR.

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

## Rescoped (2026-11-15, owner, from 04's report-to-coga session)

- 04 ended **inconclusive** (baseline 4, C1′ 3, tie 1); the current assembly is kept. No positive selection, so the old migration scope is dead.
- The owner rewrote this ticket to fix the current assembly's defects, seen in a captured `--prompt-report` and the full composed text, and asked for unit-test coverage. The body above is the new scope.
- The title is still the old one ("03 Implement the proven prompt assembly"). It is a frontmatter field, so the owner changes it.
- The gate notes below are historical.

## Gate status (2026-11-13, design session)

- Launched without a positive selection: ticket 02 ended with C1 disqualified (owner, 2026-11-13). No spec written.
- Owner clarified that "better" means better output (PRs, documents); 02 measured rule compliance only, never output quality.
- New prerequisite drafted: `v1/microkernel/03-prompt-assembly/04-compare-prompt-assembly-output-quality` (`draft-for-human`, owner's blinded judgment as primary measure, 02's gates kept hard).
- PR #1234's ruling should state that 02 did not measure output quality; owner to comment there and run an assist on that ticket.
- Parked by owner request until 04 records a positive selection.

---

## Blockers

- [x] [2026-11-13 23:26] [agent:claude] id=20261113T232634 Parked at owner request: no positive selection. Waiting on v1/microkernel/03-prompt-assembly/04-compare-prompt-assembly-output-quality to record a positive output-quality selection before design can start.
  resolved: [2026-11-15 18:15] [human:nicktoper] Owner rescoped 2026-11-15: 04 ended inconclusive (no positive selection), so the migration gate is dropped. Ticket now fixes current-assembly defects (template comments, frontmatter, heading collisions, duplicate blockers, filler) with unit tests.

- [x] [2026-11-14 18:48] [agent:claude] id=20261114T184855 Still no positive selection (checked 2026-11-14). v1/microkernel/03-prompt-assembly/04-compare-prompt-assembly-output-quality has 16 runs complete, every gate passed, and its blind pack built; it is at step human-owns-and-finishes. Owner: fill blind/verdicts.csv for the 8 pairs, then unblind and record positive, negative or inconclusive. Design starts only on a positive selection.
  resolved: [2026-11-15 18:15] [human:nicktoper] Owner rescoped 2026-11-15: 04 ended inconclusive (no positive selection), so the migration gate is dropped. Ticket now fixes current-assembly defects (template comments, frontmatter, heading collisions, duplicate blockers, filler) with unit tests.
