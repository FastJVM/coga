---
title: Show which agents are available on the machine during coga init
status: canceled
owner: zach
workflow: null
---

## Description

Spec Kit opens with a screen listing which coding agents are actually present on the machine, and how to install the integration for each one. Zach hit this while testing Spec Kit on a clean macOS VM on 2026-10-23 and flagged it as close to what coga init should be doing. Decide whether coga init should detect and present installed agents the same way, and what it should say about agents coga does not support.

Why now: coga init currently tells the user to edit a TOML file to set their agents. The marketing/fix-installer work is already reworking that step, because a fresh Mac has no application registered to open a TOML file at all, so the first instruction points at something the user cannot open. A detection screen is a candidate replacement for that step rather than something layered on top of it. See marketing/fix-installer/ask-which-agents-to-enable-during-coga-init, which removes the agents half of the same edit, and settle the two together rather than separately.

Evidence to reuse: the Spec Kit trial notes on competition-testing/test-speckit, which record how Spec Kit installs itself as Claude Code skills and where its helper scripts live.

## Context

**Superseded by `marketing/fix-installer/ask-which-agents-to-enable-during-coga-init` (2026-10-28).**
The human confirmed closing this duplicate after evaluation. The successor
already specifies supported-agent discovery on PATH, the complete agent list,
preselection, install offers, and replacement of the agent-config edit
instruction. Its owner design review also receives the remaining question
about wording for agents outside the built-in list; no separate implementation
is needed here.

The Spec Kit evidence ticket has been retired. Its final body is recoverable
with `git show 006035865^:coga/tasks/competition-testing/test-speckit.md` and
points to the private "Coga Competitor Tests" document. The detailed trial
findings stayed in that document, not the ticket; this work must not depend on
the retired path or copy private trial notes into this public repository.

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

## Evaluator review

Verdict: **do not launch this as a separate implementation ticket. Its main deliverable is already owned elsewhere.**

- `marketing/fix-installer/ask-which-agents-to-enable-during-coga-init` is at owner `review-design`. It already requires a scan line, every supported agent’s PATH status, detected agents preselected, install offers, and removal of the “set your agents” instruction. These requirements cover this draft’s central proposal; the sibling’s remaining evaluator findings belong there.
- The distinct unresolved requirement is **messaging about agents outside the built-in list**. The owner should decide whether that needs any init copy. Define “unsupported” carefully: `dependencies.AGENT_CLIS` controls built-in discovery and installation, while `config._parse_agents` permits custom agent names. PATH detection also does not establish authentication or readiness. Gemini support already has its own sibling ticket.
- Recommend folding that messaging decision into the existing installer ticket’s design review, then canceling this draft as superseded with owner approval. No separate deliverable remains unless the owner explicitly wants discovery of additional, unlisted agent CLIs.
- As written, this draft lacks an observable completion condition and has `workflow: null`. That is valid concept capture but cannot launch. If retained, distinguish a decision-only outcome from shipped behavior before selecting a workflow. The existing sibling’s `code/design-then-implement` workflow already provides the appropriate design approval gate.
- No contexts are attached, so there is no attachment bloat. If retained, add narrow required reads and current facts under `## Context`, especially `coga/init` → “Fresh repo” and “Instruction files and skill discovery.” Clarify whether “install the integration” means installing an agent CLI or creating Coga’s existing skill links.
- The evidence reference is stale: `competition-testing/test-speckit` was deleted in commit `006035865`. Its recovered final ticket points to the private “Coga Competitor Tests” document; the detailed trial findings are not in the ticket. Preserve the actionable Coga requirement without depending on a missing ticket or assuming its private findings are public.
- The supplied composition report has no layer above 40%; Context, including the preserved guide, is largest at 32.6%. Because no workflow is assigned, this does not measure any executable step’s full prompt.
