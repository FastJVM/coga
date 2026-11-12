---
title: Hold dirty context edits on feature checkouts until merge
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
step: 1 (design)
agent: claude
---

## Description

The end-of-command sweep (`sync_coga_state` in `src/coga/git.py`) publishes every dirty eligible file under the Coga roots to control, even when invoked from a feature checkout. With `[layout] contexts = "docs/contexts"`, an in-progress context edit on a feature branch lands on main before review. Observed 2026-11-11: commit 39e20683e "Sync coga state" carried an unreviewed `coga-dev/current-direction` paragraph from branch `add-code-agent-merge-workflow` describing a workflow that existed only in that branch's uncommitted files. coga/state-publication already documents this as the "pre-review publication hazard" and relies on the human committing first.

Proposal: on a feature or detached checkout, treat dirty contexts, skills, workflows, and shared config the way committed ones already are: they wait for merge. Keep publishing the runtime state that must land promptly (ticket, log, recurring blackboards, machine-written siblings).

This narrows a deliberate rule. Today instruction edits "land directly" with no separate knowledge PR (coga/state-publication "The Coga roots"), and guided authoring publishes them as one guarded transaction. The design must state why feature checkouts become the exception. It must also decide whether the change is universal or a per-repo policy (`[layout]`/`[git]`). The friction is sharpest in repos like this one, whose contexts live in `docs/contexts` and are updated "in the same PR" (AGENTS.md). Repos on the default `coga/contexts` may still want direct publication.

### Design questions

- Which path classes keep publishing from a feature checkout, and which wait for merge.
- **Checkout return.** coga/checkouts/launch-boundary "Preparation and return" step 1 sweeps every dirty file before switching to control. A held file left dirty either blocks `git switch` or travels onto control, where the next sweep publishes it anyway, so holding would only delay the hazard. Decide whether return refuses, requires a commit, or does something else. Direct chat's clean-checkout requirement before `prepare-checkout` (coga/checkouts/chat) has the same interaction.
- **Recurring templates publish whole-template.** A runtime blackboard write makes the whole template directory publishable. Define what happens to a dirty definition or `ticket.py` beside a blackboard that keeps publishing.
- How `coga run publish-state PATH` treats an explicitly named held file.
- Whether guided authoring (`coga ticket`) on a feature checkout needs an exception.
- How a held file is reported so it is never silently stranded.

### Done when

- A sweep from a feature checkout leaves a dirty context or skill off control, while the ticket and log writes from the same command still land.
- Every held file is named on stderr (fail loud).
- `coga run publish-state PATH` on a held file exits 1 and does not publish the task/log writes that came with it, matching today's committed-file behavior.
- Checkout return and direct chat behave as the approved design specifies, with tests.
- Tests cover these cases in `tests/test_git.py`, `tests/test_publish_state.py`, and `tests/test_checkouts.py` as appropriate.
- The same PR updates every surface that states or cites the hazard: coga/state-publication ("The Coga roots", "When Coga publishes", "Control versus feature checkouts" including the "Pre-review publication hazard" paragraph, "Strict publication on demand"); coga/checkouts ("Start, work, end" and "Which checkout you invoke Coga from"); coga/checkouts/launch-boundary "Preparation and return" step 1; coga/checkouts/chat; and `code/self-qa/SKILL.md` "Gotchas". If the design chooses a per-repo policy, add it to the config docs too.

## Context

### Key facts and sources

- Direct publication of instruction edits is intentional today: coga/state-publication "The Coga roots" and "When Coga publishes" (guided authoring). On a feature checkout, only *committed* changes are held, by the `adopt_only` filter (`_routine_state_areas`, set in `_publish_locked`). Dirty files come from `_dirty_paths` in `_candidates` and are never filtered. See "Control versus feature checkouts".
- Checkout return sweeps dirty files before switching: coga/checkouts/launch-boundary "Preparation and return".
- Packaged sources live under `src/coga/resources/templates/coga/bootstrap/contexts/coga/` (state-publication, checkouts, checkouts/launch-boundary, checkouts/chat) and `.../skills/code/self-qa/`.

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

## Evaluator review

**Verdict: ready with edits.** The diagnosis is right and the workflow fits. The ticket still misses one structural interaction (checkout return) and doesn't admit it reverses a documented design choice.

**Claim accuracy (checked against the code)**
- Correct. In `src/coga/git.py`, `_candidates` takes every path from `_dirty_paths` under the pathspecs. The `adopt_only` filter (`_routine_state_areas`, set in `_publish_locked` when HEAD is not control) applies only to the committed `base..HEAD` diff. So dirty contexts publish from a feature checkout, and committed ones wait for merge.
- `git show --stat 39e20683e` confirms the incident: it touches only `docs/contexts/coga-dev/current-direction/SKILL.md`.

**Assumptions to question before launch**
1. **This is deliberate today.** coga/state-publication "The Coga roots" says there is no separate knowledge PR and instruction edits "land directly". Guided authoring (`coga ticket`) publishes context, skill, workflow and config edits as one guarded transaction. The ticket should say it narrows that rule for feature checkouts, and give the reason. The real friction is repo-specific: this repo puts contexts in `docs/contexts`, which AGENTS.md says to update "in the same PR". The design should consider whether this should be a per-repo `[layout]`/`[git]` policy rather than a universal change. Adopting repos on the default `coga/contexts` may want direct publication.
2. **Checkout return is not addressed.** coga/checkouts/launch-boundary step 1 sweeps every dirty file before switching to `main`. If held files stay dirty, `git switch` either refuses or carries them onto control, and the next sweep there publishes them anyway. Holding would then delay the hazard instead of removing it. The design must say whether return refuses, requires a commit, or something else. Direct chat's "requires a clean checkout" before `prepare-checkout` (coga/checkouts/chat) has the same problem.
3. **Recurring templates are whole-file and whole-template.** The hazard paragraph notes that a runtime blackboard write makes the whole template publishable. "Keep publishing blackboards" therefore needs a rule for dirty template definitions and `ticket.py` in the same directory.
4. **More docs to update.** Besides state-publication and checkouts, these restate or cite the hazard:
   - `code/self-qa/SKILL.md`, which names "Pre-review publication hazard"
   - coga/checkouts step 2 ("left dirty, the sweep publishes it") and "Which checkout you invoke Coga from"
   - coga/checkouts/launch-boundary step 1

   Name them all so the same-PR rule is checkable.

**Clarity and done criteria**
- A cold agent can start: the problem, the incident, the code entry points and the open questions are concrete.
- "Done" is not testable as written. Add invariants a reviewer can check, for example:
  - after a sweep from a feature checkout, a dirty context or skill is absent from control
  - the ticket and log still land
  - a held file is reported on stderr (fail loud)
  - `coga run publish-state PATH` on a held file exits 1 without publishing the task/log writes that came with it, matching the committed-file behavior
  - checkout return behaves as the design specifies
- Point tests at `tests/test_git.py` and `tests/test_publish_state.py` as well as `tests/test_checkouts.py`.

**Workflow fit:** Good. The open questions make design-then-implement the right choice. The owner `review-design` gate matters because this reverses a documented choice.

**Contexts:** I don't recommend attaching coga/state-publication whole. Most of it covers prepared transactions, human review and recovery, which this ticket doesn't touch. Do this instead:
- In `## Context`, cite the exact anchors: state-publication#the-coga-roots, #when-coga-publishes (guided authoring), #control-versus-feature-checkouts, #strict-publication-on-demand; checkouts/launch-boundary step 1.
- Copy in the two facts that drive the design: direct publication is intentional, and checkout return sweeps dirty files.

The code/design skill already tells the agent to read referenced files. The implement step edits these files, so it will read them regardless.

**Scope:** One coherent change, no split needed. If the owner prefers the per-repo policy route (point 1), that becomes the design's answer, not a sibling ticket.

**Prompt size (~5,364 tokens):** No layer is over 40%. `workflow_skill` code/design is about 25% and `task_context` about 24%. Almost all of `task_context` is the template guide comment, which the template says to keep, so this ticket adds only about 360 tokens of its own content. Shrinking that comment is a template-level trim, not a fix for this ticket. Adding ~150 words of cited Context costs far less than attaching state-publication (~3,760 words).

**Minor:** The slug is truncated ("…-unti"). Cosmetic only.
