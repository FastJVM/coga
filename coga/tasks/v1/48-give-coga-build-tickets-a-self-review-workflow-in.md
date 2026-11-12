---
title: Give coga build tickets a self-review workflow in one-agent repos
status: in_progress
owner: zach
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
step: 1 (design)
agent: claude
---

## Description

Coga ships three workflows with `other-agent` steps: `code/with-review`, `code/design-then-implement`, and `docs/with-review`. In a repo with one declared agent those steps cannot resolve (`coga validate` reports `unresolvable-step-assignee`) and the ticket stalls at the hand-off. `coga build` hands every starter implementation ticket `code/design-then-implement`, and nothing stops a user (or the `coga ticket` interview) from picking a peer workflow either: `coga create` and activation each check only one step. One-agent repos are now the norm on single-agent machines (v1/20). Keep shipping the peer workflows, but stop defaulting to them and warn when one is picked that cannot finish.

1. **Single-agent defaults.** When no peer resolves, `coga build` gives implementation tickets `code/with-self-review`, as does dream when it files code drafts (autofix already does this); with a resolvable peer they keep today's workflows. Decide when the tickets are created, against the config at that moment — not at `init`, which is too early: a user typically inits, notices only one agent is enabled, and adds a second before `coga build`. Decision tickets keep `draft-for-human`. Shipped examples (e.g. the `coga/first-task` walkthrough) lead with a workflow that works in a one-agent repo.
2. **Warn, don't refuse.** `coga create --workflow <wf>` and activation (`coga mark active`, first `coga launch` of a draft) print one short advisory line and still succeed when a *remaining* step of the workflow is `other-agent` and no peer resolves for the ticket's (prospective) main agent.

Done when, with tests for each repo shape: in a one-agent repo, `coga build` and dream tickets carry `code/with-self-review`, and `coga create --workflow code/design-then-implement` plus activation of such a ticket each print the warning once and succeed; a three-or-more-agent repo without `peer =` gets its own warning text; a two-agent repo (with or without `peer =`) sees no warning and keeps today's workflows; megalaunch and recurring activations print nothing.

## Context

### Decisions from authoring (2026-11-11)

- **Warnings over removal.** Removing the peer workflows from the package was considered and rejected as riskier (see blackboard, Superseded designs). `coga validate` keeps `unresolvable-step-assignee` as an error and bump/launch still refuse at the peer step itself — both unchanged. `coga create` keeps refusing when step 1 itself cannot resolve (existing behavior).
- **Trigger is "no peer resolves", not "`peer =` unset".** `bump.resolve_other_agent` resolves `[agents.<main>].peer` if set, else the single other configured agent; it raises for one agent, or three or more with no `peer =`. A two-agent repo without `peer =` resolves fine and must not warn. `recurring_autofix.autofix_workflow` already makes this exact call (with `allow_prospective_default=True`) to fall back to `code/with-self-review`; extract a shared helper. The per-step check in `validate.py` (its `assignee == "other-agent"` branch) is the existing per-step version. Only steps at or after the current step count, so a ticket reactivated past its peer steps does not warn.
- **Warning text.** Short, and derived from the resolution failure rather than a bare agent count:
  - one agent: `⚠ code/design-then-implement is a two-agent workflow, and this repo has one agent. Use code/with-self-review, or declare a second agent in coga.toml.`
  - three or more, no `peer =`: `⚠ code/design-then-implement needs a second agent, but coga.toml has no peer = to pick one. Set one, or use code/with-self-review.`
  - For `docs/with-review` (no docs self-review workflow ships), drop the `code/with-self-review` suggestion and say only to declare a second agent.
  Follow the existing `⚠` advisory style (`mark._warn_if_state_not_advanced`) and match the existing "code/with-self-review without a peer agent" hint text in `commands/mark.py` / `commands/bump.py`. One line per command, not per step.
- **Print only from the command layer.** `mark.prepare_active` is documented as pure preparation and runs several times per launch (operator probe, assist prospective, real activation), plus from `mark_active`, megalaunch, and the recurring runner. Compute the advisory in a pure helper that *returns* the text; echo it from `commands/create.py`, `commands/mark.py`, and exactly one point in direct launch. Never echo inside `prepare_active` or `create.create_task` (library callers such as autofix stay quiet).
- **How `coga build` decides.** `coga build` is the alias `launch coga-build`; its agent follows `src/coga/resources/templates/coga/bootstrap/workflows/build/onboarding.md` ("Create each ticket as a draft, non-interactively"), which hard-codes `--workflow code/design-then-implement`. Prefer giving the agent a cheap CLI signal of whether a peer resolves over prose that parses `coga.toml` + `coga.local.toml`; the design step picks. The create-time warning is the backstop. Update that file's `## No other-agent code review` note too.
- **No new workflows.** Accepted cost: `code/with-self-review` has no `design` step or owner design gate, so a thin `coga build` ticket in a one-agent repo goes straight to implement.

### Where things live

- `create.create_task` (existing step-1 `resolve_operator` check); `mark.prepare_active` → `_assert_operator_resolves` (checks only the current step).
- Dream's packaged `src/coga/resources/templates/coga/recurring/dream/ticket.md` files `code/with-review` drafts.
- `bootstrap/ticket` skill (`src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md`): tell the interviewer not to pick a workflow with `other-agent` steps when no peer resolves.
- Docs to update in the same PR (edited, so cited not attached): `coga/workflows` ("Roles are the routing" and the bundled-workflow paragraph), `coga/first-task` (example uses `code/with-review`), `code/with-self-review.md`'s `## No other-agent code review`, and `coga/tickets/authoring` if it documents `create`/`mark active` output.
- Tests: `tests/test_commands.py`, `tests/test_validate.py`, `tests/test_recurring_autofix.py` already build one- and two-agent configs for `unresolvable-step-assignee`; reuse those fixtures.

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

## Superseded designs

### 2026-11-11 — Stop shipping peer-review workflows

Remove `code/with-review`, `code/design-then-implement`, and `docs/with-review` from the package (this repo keeping local copies), with no warnings. Rejected as unsafe after cold review: steps without `skills:` reload their instructions from the workflow file by name, so two-agent adopters' in-flight tickets would lose instructions on upgrade; `checkout_policy._changed_section` compares against the shipped copy, so this repo's local copies would degrade to `manual` checkout; and the change touched ~40 files.
